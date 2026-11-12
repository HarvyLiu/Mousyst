param([switch]$Practice, [string]$BundleName, [switch]$Desktop)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
$originalSearchPath = $env:PATH
try {
    $pythonExe = (Get-Command python).Source
    $qtDirectory = & $pythonExe -c 'import pathlib, PySide6; print(pathlib.Path(PySide6.__file__).parent)'
    if ($LASTEXITCODE -ne 0) { throw 'Install requirements-dev.txt before building.' }
    # Avoid collecting incompatible ICU/CRT DLLs from unrelated developer tools.
    $env:PATH = "$qtDirectory;$(Split-Path $pythonExe);$env:SystemRoot\System32;$env:SystemRoot"
    if (-not $BundleName) { $BundleName = if ($Desktop) { 'MousystDesktop' } elseif ($Practice) { 'MousystPractice' } else { 'Mousyst' } }
    if ($Desktop) {
        & $pythonExe -c "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"
        if ($LASTEXITCODE -ne 0) { throw 'Could not generate Windows accessibility bindings.' }
    }
    $entryPoint = if ($Desktop) { 'src/desktop_app.py' } elseif ($Practice) { 'src/practice.py' } else { 'src/main.py' }
    & $pythonExe -m PyInstaller --noconfirm --clean --onedir --windowed --name $bundleName --icon src/ui/mousyst.ico --add-data 'src/ui:ui' --add-data 'src/data:data' --paths src --exclude-module tkinter $entryPoint
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    Copy-Item -LiteralPath README.md -Destination "dist/$bundleName/README.md"
    if ($Practice) { Copy-Item -LiteralPath EXPERIMENT.md -Destination "dist/$bundleName/EXPERIMENT.md" }
    if ($Desktop) { Copy-Item -LiteralPath DESKTOP.md -Destination "dist/$bundleName/DESKTOP.md" }
    Compress-Archive -Path "dist/$bundleName" -DestinationPath "dist/$bundleName-preview-windows-x64.zip" -Force
} finally {
    $env:PATH = $originalSearchPath
    Pop-Location
}
