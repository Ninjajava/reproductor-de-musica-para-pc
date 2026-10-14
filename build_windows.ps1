param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Python = (Resolve-Path $Python).Path

if (-not $SkipInstall) {
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }
    & $Python -m pip install -r requirements.txt pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de compilacion." }
}

& $Python -m PyInstaller --noconfirm --clean JULIOPRODDJ.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo generar el paquete." }

$outputDirectory = Join-Path (Get-Location) "output"
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}
$portableZip = Join-Path $outputDirectory "JULIOPRODDJ-Portable.zip"
if (Test-Path $portableZip) { Remove-Item -LiteralPath $portableZip -Force }
Compress-Archive -Path "dist\JULIOPRODDJ" -DestinationPath $portableZip -CompressionLevel Optimal

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $localIscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    if (Test-Path $localIscc) { $iscc = Get-Item $localIscc }
}
if ($iscc) {
    $compiler = $iscc.Source
    if (-not $compiler) { $compiler = $iscc.FullName }
    & $compiler "installer.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo generar el instalador." }
    Write-Host "Instalador creado en output\JULIOPRODDJ-Setup.exe"
} else {
    Write-Host "ZIP portable creado en output\JULIOPRODDJ-Portable.zip"
    Write-Host "Para generar el instalador, instala Inno Setup y vuelve a ejecutar el script."
}
