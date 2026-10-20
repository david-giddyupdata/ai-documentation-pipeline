# Starts the Quick Sight (AWS) walkthrough browser: Chrome with its own profile (kept outside
# any cloud-synced folder so sign-ins persist) and a debugging port that qs.py connects to.
# Port 9334 must match CDP_URL in qs.py and _work/student_server.py. The 1440x960 window was run on a
# 1440x900 screen; _work/common.py overrides the page size for captures.
# -StartUrl: optional; pass your own region's sign-in page, such as https://<REGION>.quicksight.aws.amazon.com/sn/start
param(
    [string]$StartUrl = "https://quicksight.aws.amazon.com/"
)
$chrome = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
$profileDir = "$env:USERPROFILE\.qs-journey\browser-profile"
New-Item -ItemType Directory -Force $profileDir | Out-Null
Start-Process $chrome -ArgumentList @(
    "--remote-debugging-port=9334",
    "--user-data-dir=`"$profileDir`"",
    "--window-size=1440,960",
    "--no-first-run",
    "--no-default-browser-check",
    $StartUrl
)
