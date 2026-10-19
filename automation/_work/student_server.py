"""Session 9: "student" browser tools for an agentic walkthrough (an AI follows the manual like a person).

The student may only look and use the mouse and keyboard: screenshot, click, move, drag, type, key, scroll,
wait. No DOM, no automation ids, no URLs. Coordinates are pixels in the screenshots it gets (1200 x 841 =
the 1427 x 1000 CSS viewport scaled by 0.841).

One long-lived connection (menus close when a CDP client disconnects), so this runs as a local server:
    python _work/student_server.py <run dir> [--max 300]       # background; port 8765
    python <run dir>/student.py click 300 210                   # the student's client (see CLIENT below)
Every action waits a moment and returns a fresh screenshot path. Actions are logged to <run dir>/actions.jsonl.
"""
import base64
import io
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9334"
PORT = 8765
VW, VH = 1427, 1000
SW = 1200
S = SW / VW

CLIENT = r'''"""Student tools. Every command prints the path of a new screenshot: Read it to see the screen.
    python student.py shot
    python student.py click X Y            [--right] [--double]
    python student.py move X Y             (hover)
    python student.py drag X1 Y1 X2 Y2
    python student.py down X Y             (press the mouse button and hold it: a slow drag you can watch)
    python student.py move X Y             (while held: the screenshot shows drop hints such as tooltips)
    python student.py up X Y               (move there and release)
    python student.py type "text"
    python student.py key Enter            (Escape, Tab, Backspace, Control+A, ArrowDown, ...)
    python student.py scroll X Y DY        (DY > 0 scrolls down, in pixels)
    python student.py wait SECONDS         (max 10)
    python student.py files                (when a file picker is open: list the course download folder)
    python student.py upload NAME          (choose that file in the open file picker)
X, Y are pixels in the 1200 x 841 screenshots."""
import json, sys, urllib.request
a = sys.argv[1:]
if not a:
    sys.exit(__doc__)
cmd, rest = a[0], a[1:]
flags = [r for r in rest if r.startswith("--")]
args = [r for r in rest if not r.startswith("--")]
req = urllib.request.Request("http://127.0.0.1:8765/", data=json.dumps({"cmd": cmd, "args": args, "flags": flags}).encode(),
                             headers={"Content-Type": "application/json"})
print(urllib.request.urlopen(req, timeout=120).read().decode())
'''


class Student:
    def __init__(self, run, max_actions):
        self.run, self.max = run, max_actions
        (run / "shots").mkdir(parents=True, exist_ok=True)
        (run / "student.py").write_text(CLIENT, encoding="utf-8")
        self.n = 0
        self.pw = sync_playwright().start()
        ctx = self.pw.chromium.connect_over_cdp(CDP_URL).contexts[0]
        self.page = next((p for p in ctx.pages if "quicksight" in p.url), None)
        if self.page is None:
            raise SystemExit("No Quick Sight tab in the automation Chrome")
        self.page.bring_to_front()
        self.cdp = ctx.new_cdp_session(self.page)
        self.cdp.send("Emulation.setDeviceMetricsOverride", {"width": VW, "height": VH, "deviceScaleFactor": 1, "mobile": False})
        # A file picker (e.g. Upload file) is answered from <run>/downloads, the student's course download folder
        self.downloads, self.chooser = run / "downloads", None
        self.page.on("filechooser", lambda fc: setattr(self, "chooser", fc))

    def shot(self):
        png = base64.b64decode(self.cdp.send("Page.captureScreenshot", {"format": "png"})["data"])
        im = Image.open(io.BytesIO(png)).convert("RGB").resize((SW, round(VH * S)), Image.LANCZOS)
        path = self.run / "shots" / f"{self.n:03d}.png"
        im.save(path)
        return path

    def xy(self, x, y):
        return float(x) / S, float(y) / S

    def do(self, cmd, args, flags):
        m = self.page.mouse
        if cmd == "files":
            names = sorted(f.name for f in self.downloads.glob("*")) if self.downloads.exists() else []
            return ("File picker open. " if self.chooser else "No file picker is open. ") +                 "Course download folder: " + (", ".join(names) or "(empty)")
        if cmd == "upload":
            if self.chooser is None:
                return "No file picker is open. Click the button that opens one first."
            f = self.downloads / " ".join(args)
            if not f.is_file():
                return f"No file {f.name!r} in the course download folder. Use `files` to list it."
            self.chooser.set_files(str(f)); self.chooser = None
            time.sleep(2.0)
        elif cmd != "shot":
            if self.n >= self.max:
                return f"REFUSED: the action limit ({self.max}) is used up. Stop and write your report."
            self.n += 1
        if cmd == "click":
            x, y = self.xy(*args[:2])
            m.click(x, y, button="right" if "--right" in flags else "left", click_count=2 if "--double" in flags else 1)
        elif cmd == "move":
            m.move(*self.xy(*args[:2]), steps=5)
        elif cmd == "drag":
            x1, y1 = self.xy(*args[:2]); x2, y2 = self.xy(*args[2:4])
            m.move(x1, y1, steps=3); m.down(); time.sleep(0.2)
            m.move(x1 + 8, y1 + 8, steps=4); m.move(x2, y2, steps=25); time.sleep(0.4); m.up()
        elif cmd == "down":
            m.move(*self.xy(*args[:2]), steps=3); m.down(); time.sleep(0.2)
            m.move(*[v + 6 for v in self.xy(*args[:2])], steps=3)
        elif cmd == "up":
            m.move(*self.xy(*args[:2]), steps=10); time.sleep(0.6); m.up()
        elif cmd == "type":
            self.page.keyboard.type(" ".join(args), delay=30)
        elif cmd == "key":
            self.page.keyboard.press(args[0])
        elif cmd == "scroll":
            m.move(*self.xy(*args[:2])); m.wheel(0, float(args[2]) / S)
        elif cmd == "wait":
            time.sleep(min(10.0, float(args[0])))
        elif cmd not in ("shot", "upload"):
            return f"ERROR: unknown command {cmd!r}. Use shot, click, move, drag, down, up, type, key, scroll, wait, files, upload."
        if cmd not in ("shot", "wait"):
            time.sleep(1.2)
        path = self.shot()
        with (self.run / "actions.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(t=time.strftime("%H:%M:%S"), n=self.n, cmd=cmd, args=args, flags=flags,
                                    shot=path.name)) + "\n")
        note = "  A file picker is open: use `files` and `upload NAME`." if self.chooser else ""
        return f"screenshot: {path}  (actions used {self.n}/{self.max}){note}"


def main():
    run = Path(sys.argv[1]).resolve()
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 300
    st = Student(run, mx)

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                out = st.do(body["cmd"], body.get("args", []), body.get("flags", []))
            except Exception as e:                      # report, keep serving
                out = f"ERROR: {type(e).__name__}: {e}"
            data = out.encode()
            self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    print(f"student server on 127.0.0.1:{PORT}, run dir {run}", flush=True)
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
