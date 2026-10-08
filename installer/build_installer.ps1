# Builds dist\FluffVRStats-Setup-<version>.exe
#   needs: Windows, a normal Python 3.12 install (for tkinter files), Inno Setup 6 (iscc on PATH or default folder)
#   run from the repo root:  powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
# GitHub Actions runs this for every release (see .github\workflows\release.yml).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$version = (Get-Content VERSION -Raw).Trim().TrimStart("v")
$build = Join-Path $root "build"
$app = Join-Path $build "app"
$py = Join-Path $app "python"
Remove-Item $build -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $py | Out-Null

# 1. the app files: exactly what's in git (so no local secrets or configs sneak in)
git archive --format=zip -o "$build\app.zip" HEAD
Expand-Archive "$build\app.zip" -DestinationPath $app -Force
Remove-Item -Recurse -Force "$app\docs", "$app\quest", "$app\.github" -ErrorAction SilentlyContinue

# 2. a private Python (embeddable) + tkinter copied from the normal install
$full = (python -c "import sys; print(sys.base_prefix)").Trim()
$pyver = (python -c "import platform; print(platform.python_version())").Trim()
$tag = ($pyver -split "\.")[0..1] -join ""
Invoke-WebRequest "https://www.python.org/ftp/python/$pyver/python-$pyver-embed-amd64.zip" -OutFile "$build\embed.zip"
Expand-Archive "$build\embed.zip" -DestinationPath $py -Force
Copy-Item "$full\tcl" "$py\tcl" -Recurse -Force
Copy-Item "$full\Lib\tkinter" "$py\Lib\tkinter" -Recurse -Force
foreach ($f in "_tkinter.pyd", "tcl86t.dll", "tk86t.dll", "zlib1.dll") {
  if (Test-Path "$full\DLLs\$f") { Copy-Item "$full\DLLs\$f" $py -Force }
}
# let the embedded Python see site-packages, tkinter + the app folder
Set-Content "$py\python$tag._pth" "python$tag.zip`r`n.`r`nLib`r`nLib\site-packages`r`n..`r`nimport site"

# 3. pip + the app's packages, inside the private Python
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile "$build\get-pip.py"
& "$py\python.exe" "$build\get-pip.py" --no-warn-script-location
& "$py\python.exe" -m pip install --no-warn-script-location -r "$app\requirements.txt"
& "$py\python.exe" -m pip install --no-warn-script-location winrt-runtime winrt-Windows.Foundation `
  winrt-Windows.Media.Control winrt-Windows.Storage.Streams
& "$py\python.exe" -c "import tkinter, openvr, PIL, cryptography; print('private python ok')"

# 4. the installer
$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
& $iscc "/DAppVersion=$version" "installer\FluffVRStats.iss"
Write-Host "built dist\FluffVRStats-Setup-$version.exe :3"
