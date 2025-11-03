# Building Heaven GUI Installers for v1.0

This guide explains how to build production installers for Windows and Linux.

## Prerequisites

### All Platforms
- Node.js 18+ (`node --version`)
- npm 9+ (`npm --version`)
- Rust 1.70+ (`rustc --version`)

### Windows
- Visual Studio Build Tools 2019 or later
  - Install from: https://visualstudio.microsoft.com/downloads/
  - Select "Desktop development with C++"
- WiX Toolset 3.11+ (for MSI installer)
  - Install from: https://wixtoolset.org/releases/
  - Add to PATH

### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install -y \
    libwebkit2gtk-4.0-dev \
    build-essential \
    curl \
    wget \
    file \
    libssl-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev \
    libsoup2.4-dev \
    libjavascriptcoregtk-4.0-dev
```

## Building Installers

### 1. Install Dependencies

```bash
cd heaven-gui
npm install
```

### 2. Build Production Bundle

```bash
# Build the React frontend
npm run build

# Build Tauri app with installers
npm run tauri:build
```

This will create installers in `src-tauri/target/release/bundle/`:

### Windows Installers
- **MSI**: `heaven_1.0.0_x64_en-US.msi` (Windows Installer Package)
- **NSIS**: `heaven_1.0.0_x64-setup.exe` (Nullsoft Installer)

### Linux Installers
- **DEB**: `heaven_1.0.0_amd64.deb` (Debian/Ubuntu package)
- **AppImage**: `heaven_1.0.0_amd64.AppImage` (Universal Linux app)

## Installation Testing

### Windows

**MSI Installer:**
```powershell
# Install
msiexec /i heaven_1.0.0_x64_en-US.msi

# Launch from Start Menu or:
& "C:\Program Files\Heaven\Heaven.exe"

# Uninstall
msiexec /x heaven_1.0.0_x64_en-US.msi
```

**NSIS Installer:**
- Double-click `heaven_1.0.0_x64-setup.exe`
- Follow installation wizard
- Launch from Start Menu

### Linux

**DEB Package (Debian/Ubuntu):**
```bash
# Install
sudo dpkg -i heaven_1.0.0_amd64.deb
sudo apt-get install -f  # Fix dependencies if needed

# Launch
heaven-gui

# Uninstall
sudo apt remove heaven-gui
```

**AppImage (Universal):**
```bash
# Make executable
chmod +x heaven_1.0.0_amd64.AppImage

# Run directly (no installation needed)
./heaven_1.0.0_amd64.AppImage

# Optional: Integrate with system
./heaven_1.0.0_amd64.AppImage --appimage-integrate
```

## Configuration

Heaven GUI reads Solo-Git configuration from:
- **Windows**: `%USERPROFILE%\.sologit\config.yaml`
- **Linux**: `~/.sologit/config.yaml`

## Troubleshooting

### Build Fails on Windows

**Error: "WebView2 not found"**
- Install WebView2 Runtime: https://developer.microsoft.com/microsoft-edge/webview2/

**Error: "WiX not in PATH"**
```powershell
$env:PATH += ";C:\Program Files (x86)\WiX Toolset v3.11\bin"
```

### Build Fails on Linux

**Error: "webkit2gtk-4.0 not found"**
```bash
sudo apt install libwebkit2gtk-4.0-dev
```

**Error: "Permission denied"**
```bash
chmod +x src-tauri/target/release/bundle/appimage/heaven_1.0.0_amd64.AppImage
```

## Code Signing (Optional)

### Windows
1. Obtain code signing certificate (.pfx)
2. Set environment variables:
   ```powershell
   $env:TAURI_SIGNING_PRIVATE_KEY = "path/to/cert.pfx"
   $env:TAURI_SIGNING_PASSWORD = "your_password"
   ```
3. Build: Tauri will auto-sign

### Linux
- DEB packages can be signed with `dpkg-sig`
- AppImages can be signed with gpg

## Distribution

### Windows
- **Recommended**: Distribute both MSI and NSIS
  - MSI for enterprise/silent installs
  - NSIS for regular users (smaller, faster)

### Linux
- **Recommended**: Distribute both DEB and AppImage
  - DEB for Debian/Ubuntu users
  - AppImage for universal compatibility

## Build Artifacts

After successful build, artifacts are in:
```
src-tauri/target/release/bundle/
├── msi/
│   └── heaven_1.0.0_x64_en-US.msi
├── nsis/
│   └── heaven_1.0.0_x64-setup.exe
├── deb/
│   └── heaven_1.0.0_amd64.deb
└── appimage/
    └── heaven_1.0.0_amd64.AppImage
```

## Release Checklist

- [ ] Version updated in all files (Cargo.toml, package.json, tauri.conf.json)
- [ ] Icons present in `src-tauri/icons/`
- [ ] Build succeeds on Windows
- [ ] Build succeeds on Linux
- [ ] Windows MSI installs and launches
- [ ] Windows NSIS installs and launches
- [ ] Linux DEB installs and launches
- [ ] Linux AppImage runs
- [ ] Solo-Git CLI integration works
- [ ] Configuration file is read correctly
- [ ] AI routing system functions
- [ ] All UI panels load

## Support

For build issues, see:
- Tauri Documentation: https://tauri.app/v1/guides/
- GitHub Issues: https://github.com/ssdajoker/Solo-Git/issues
