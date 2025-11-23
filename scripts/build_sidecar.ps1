# Build the Solo-Git sidecar (sologit-core) with PyInstaller
# Usage: powershell -ExecutionPolicy Bypass -File scripts\build_sidecar.ps1

param(
  [string]$PythonExe = "python"
)

Write-Host "[sidecar] Ensuring dependencies..."
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt

Write-Host "[sidecar] Building onefile binary via PyInstaller..."
$entry = "scripts/sidecar_entry.py"
& $PythonExe -m PyInstaller --onefile --name sologit-core --console $entry

if ($LASTEXITCODE -ne 0) {
  Write-Error "[sidecar] PyInstaller build failed with code $LASTEXITCODE"
  exit $LASTEXITCODE
}

# Copy artifact into scripts/dist for Tauri build.rs pickup
$distOut = Join-Path (Get-Location) "dist"
$scriptsDist = Join-Path (Get-Location) "scripts/dist"
if (-not (Test-Path $scriptsDist)) { New-Item -ItemType Directory -Force -Path $scriptsDist | Out-Null }

# Determine artifact name cross-shell
if ($env:OS -eq 'Windows_NT') {
  $exeName = 'sologit-core.exe'
} else {
  $exeName = 'sologit-core'
}
$srcPath = Join-Path $distOut $exeName
$dstPath = Join-Path $scriptsDist $exeName

if (Test-Path $srcPath) {
  Copy-Item -Force $srcPath $dstPath
  Write-Host "[sidecar] Copied $srcPath -> $dstPath"
} else {
  Write-Warning "[sidecar] Expected artifact not found: $srcPath"
}

Write-Host "[sidecar] Done. You can now run Tauri build."