# Preflight: Verify Tauri build environment on Windows
# Usage: powershell -ExecutionPolicy Bypass -File scripts/preflight/tauri_env_check.ps1

Write-Host "[preflight] Checking Node.js..."
$node = (Get-Command node -ErrorAction SilentlyContinue)
$npm = (Get-Command npm -ErrorAction SilentlyContinue)
if (-not $node) { Write-Warning "Node.js not found (node). Install Node LTS." } else { node -v }
if (-not $npm) { Write-Warning "npm not found. Install Node LTS." } else { npm -v }

Write-Host "[preflight] Checking Rust toolchain..."
$rustc = (Get-Command rustc -ErrorAction SilentlyContinue)
$cargo = (Get-Command cargo -ErrorAction SilentlyContinue)
if (-not $rustc) { Write-Warning "Rust (rustc) not found. Install from https://rustup.rs" } else { rustc -V }
if (-not $cargo) { Write-Warning "Cargo not found. Install Rust via rustup." } else { cargo -V }

Write-Host "[preflight] Checking sidecar artifact..."
$root = (Get-Location)
$distPath = Join-Path $root "dist/sologit-core.exe"
$scriptsDistPath = Join-Path $root "scripts/dist/sologit-core.exe"
if (Test-Path $distPath) { Write-Host "Found: $distPath" } else { Write-Warning "Missing: $distPath" }
if (Test-Path $scriptsDistPath) { Write-Host "Found: $scriptsDistPath" } else { Write-Warning "Missing: $scriptsDistPath" }

Write-Host "[preflight] Recommended next steps:"
Write-Host " - Install Node LTS (20.x) and reopen terminal"
Write-Host " - Install Rust via rustup (stable toolchain)"
Write-Host " - cd heaven-gui; npm ci; npm run tauri build"
