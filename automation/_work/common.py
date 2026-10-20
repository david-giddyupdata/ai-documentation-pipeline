import sys; sys.path.insert(0, '.')
from qs import page, capture, peek, shot
import os
TEST = "<ANALYSIS_ID>"  # the ID of your own Quick Sight (AWS) analysis, from its URL
TAB = os.environ.get("QS_TAB", TEST)      # set QS_TAB=quicksight to use whatever QS page is open
p = page(TAB)
assert TAB in p.url, p.url
# The real page area was only 759 css px tall (start_browser.ps1's 1440x960 window on a 1440x900
# screen); render 1000 px so long field menus fit. The override lasts only while this script's CDP
# session is open.
_cdp = p.context.new_cdp_session(p)
_cdp.send("Emulation.setDeviceMetricsOverride", {"width": 1427, "height": 1000, "deviceScaleFactor": 2, "mobile": False})
import qs; qs.CDP = _cdp
p.wait_for_timeout(1500)
def A(i):  return p.locator(f'[data-automation-id="{i}"]').locator("visible=true").first
def T(t, exact=True): return p.get_by_text(t, exact=exact).locator("visible=true").first
def tabname(): return p.locator('[data-automation-id="selectedTab_sheet_name_container"]').locator("visible=true").first

def value_pill(n):
    """n-th (0-based) pill in the VALUES well."""
    # dataset-specific: the course's measure pills read "flights (...)"; change this for your own data
    lab = p.locator(r'text=/^flights \(/').locator("visible=true").nth(n)
    return lab.locator("xpath=ancestor::*[.//button][1]")

def M(label):
    """First visible item with this exact text inside an open menu (prefix match if label ends with '*')."""
    menus = p.locator('[role="menu"]').locator("visible=true")
    if label.endswith("*"):
        return menus.get_by_text(label[:-1], exact=False).locator("visible=true").first
    return menus.get_by_text(label, exact=True).locator("visible=true").first

def close_menus():
    for _ in range(4):
        if not p.locator('[role="menu"]').locator("visible=true").count():
            return
        p.keyboard.press("Escape"); p.wait_for_timeout(400)

def center(el):
    b = el.bounding_box(); return b["x"] + b["width"]/2, b["y"] + b["height"]/2

def field_menu(pill, path, name=None, extra=None):
    """Open a well pill's menu, walk the submenu path with straight mouse moves
    (so no other submenu opens), optionally capture, then click the last item."""
    close_menus()
    pill.locator("button").last.click(); p.wait_for_timeout(1000)
    marks = {"pill": pill, "menu_btn": pill.locator("button").last}
    for i, lab in enumerate(path):
        el = M(lab)
        x, y = center(el)
        if i == 0:
            p.mouse.move(x, y, steps=10)
        else:
            cx, cy = center(marks[f"m{i-1}"])
            b = el.bounding_box()
            p.mouse.move(b["x"] + 15, cy, steps=8)       # straight right, into the submenu
            p.mouse.move(b["x"] + 15, y, steps=8)        # then down/up to the item
            p.mouse.move(x, y, steps=4)
        p.wait_for_timeout(900)
        marks[f"m{i}"] = el
    if name:
        marks.update(extra or {})
        capture(p, name, marks)
    p.mouse.click(*center(marks[f"m{len(path)-1}"])); p.wait_for_timeout(2500)

def tabs():
    return [t.strip() for t in p.locator('.sheet-tab').all_inner_texts()]

def add_sheet(name, caps=None):
    """Add an interactive sheet and rename it. caps = dict of step->shot name to capture."""
    caps = caps or {}
    close_menus()
    plus = A("sheetTabsBar_button_addSheet"); plus.hover(); p.wait_for_timeout(800)
    if "plus" in caps: capture(p, caps["plus"], {"plus": plus, "tab": T(tabs()[-1])})
    plus.click(); p.wait_for_timeout(2500)
    dlg = p.get_by_role("dialog").locator("visible=true").first
    add = dlg.get_by_role("button", name="Add", exact=True)
    if "dialog" in caps: capture(p, caps["dialog"], {"dialog": dlg, "interactive": T("Interactive sheet"), "add": add})
    add.click(); p.wait_for_timeout(3500)
    tab = tabname(); tab.locator('button, [role=button]').last.click(); p.wait_for_timeout(1000)
    ren = M("Rename"); p.mouse.move(*center(ren), steps=6); p.wait_for_timeout(500)
    if "rename" in caps: capture(p, caps["rename"], {"tab": tab, "rename": ren})
    p.mouse.click(*center(ren)); p.wait_for_timeout(800)
    p.keyboard.press("Control+A"); p.keyboard.type(name); p.keyboard.press("Enter"); p.wait_for_timeout(1500)
    p.mouse.move(1000, 700)
    if "named" in caps: capture(p, caps["named"], {"tab": tabname()})

def calc_editor_text():
    return p.evaluate("""() => { const ed = document.querySelector('.monaco-editor .view-lines');
        return ed ? ed.innerText : null; }""")

def calc_field(name, formula, cap=None, save=True):
    """Fill the open 'Add calculated field' panel. Closes the Add items popover first."""
    pop = p.get_by_text("Add items", exact=True).locator("visible=true")
    if pop.count():
        pop.first.locator("xpath=ancestor::*[.//button][1]").locator("button").first.click(); p.wait_for_timeout(600)
    nm = p.get_by_placeholder("Add name").locator("visible=true").first
    nm.fill(name)
    ed = p.locator('.monaco-editor').locator("visible=true").first
    ed.click(); p.keyboard.press("Control+A"); p.keyboard.press("Delete")
    p.keyboard.insert_text(formula); p.wait_for_timeout(1200)
    p.keyboard.press("Escape"); p.wait_for_timeout(400)   # dismiss autocomplete
    got = calc_editor_text()
    print("editor:", repr(got))
    if cap:
        capture(p, cap, {"name": nm, "editor": ed, "save": p.get_by_role("button", name="Save", exact=True).locator("visible=true").first})
    if save:
        p.get_by_role("button", name="Save", exact=True).locator("visible=true").first.click(); p.wait_for_timeout(2500)

def field(name):
    """A field in the Data pane (not a well pill or visual header)."""
    return p.locator('[data-automation-id="analysis_visualize_field"]').locator("visible=true").get_by_text(name, exact=True).first

def drag(src, dst):
    s = src.bounding_box(); d = dst.bounding_box()
    sx, sy = s["x"] + s["width"] * 0.3, s["y"] + s["height"] / 2
    dx, dy = d["x"] + d["width"] / 2, d["y"] + d["height"] / 2
    p.mouse.move(sx, sy); p.mouse.down(); p.wait_for_timeout(200)
    p.mouse.move(sx + 15, sy - 5, steps=5); p.wait_for_timeout(200)
    p.mouse.move(dx, dy, steps=25); p.wait_for_timeout(500)
    p.mouse.up(); p.wait_for_timeout(2500)

def well_pill(name):
    """The pill for a field in the field wells (Visuals pane), by its menu button."""
    btns = p.locator(f'[aria-label="menu options for {name}"]').locator("visible=true")
    for i in range(btns.count()):
        b = btns.nth(i).bounding_box()
        if b and 330 < b["x"] < 660:
            return btns.nth(i).locator("xpath=ancestor::*[.//button][1]")
    raise LookupError(name)
