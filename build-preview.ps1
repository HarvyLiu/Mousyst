$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
$originalSearchPath = $env:PATH
try {
    $pythonExe = (Get-Command python).Source
    $qtDirectory = & $pythonExe -c 'import pathlib, PySide6; print(pathlib.Path(PySide6.__file__).parent)'
    if ($LASTEXITCODE -ne 0) { throw 'Install requirements-dev.txt before building.' }
    # Avoid collecting incompatible ICU/CRT DLLs from unrelated developer tools.
    $env:PATH = "$qtDirectory;$(Split-Path $pythonExe);$env:SystemRoot\System32;$env:SystemRoot"
    & $pythonExe -m PyInstaller --noconfirm --clean --onedir --windowed --name Mousyst --add-data 'src/ui:ui' --paths src --exclude-module tkinter src/main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    Copy-Item -LiteralPath README.md -Destination dist/Mousyst/README.md
    Compress-Archive -Path dist/Mousyst -DestinationPath dist/Mousyst-preview-windows-x64.zip -Force
} finally {
    $env:PATH = $originalSearchPath
    Pop-Location
}
