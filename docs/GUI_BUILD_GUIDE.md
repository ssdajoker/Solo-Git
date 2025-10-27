# Heaven GUI Build Guide

This guide provides instructions for building the Heaven GUI on a Debian/Ubuntu-based system.

## Prerequisites

You need to have Node.js, npm, and the Rust toolchain (including `cargo`) installed.

## System Dependencies

The Heaven GUI is a Tauri application that relies on several system libraries for its web renderer and GTK components. Before building, you must install the following development packages:

```bash
sudo apt-get update
sudo apt-get install -y libglib2.0-dev libgtk-3-dev libsoup2.4-dev libwebkit2gtk-4.1-dev libjavascriptcoregtk-4.1-dev
```

## Versioning Workaround for WebKitGTK

The Tauri build process for `heaven-gui` specifically looks for version `4.0` of the `webkit2gtk` and `javascriptcoregtk` libraries. If your system has a newer version (e.g., `4.1`), the build will fail.

To work around this, you need to create symbolic links to make the build system find the `4.1` libraries when it looks for `4.0`.

1.  **Link pkg-config files:**
    ```bash
    sudo ln -s /usr/lib/x86_64-linux-gnu/pkgconfig/webkit2gtk-4.1.pc /usr/lib/x86_64-linux-gnu/pkgconfig/webkit2gtk-4.0.pc
    sudo ln -s /usr/lib/x86_64-linux-gnu/pkgconfig/javascriptcoregtk-4.1.pc /usr/lib/x86_64-linux-gnu/pkgconfig/javascriptcoregtk-4.0.pc
    ```

2.  **Link shared library (.so) files:**
    First, find the exact path of the `.so` files:
    ```bash
    find /usr -name "libwebkit2gtk-4.1.so"
    find /usr -name "libjavascriptcoregtk-4.1.so"
    ```
    Then, create the symbolic links using the paths you found. For a standard installation, the commands will be:
    ```bash
    sudo ln -s /usr/lib/x86_64-linux-gnu/libwebkit2gtk-4.1.so /usr/lib/x86_64-linux-gnu/libwebkit2gtk-4.0.so
    sudo ln -s /usr/lib/x86_64-linux-gnu/libjavascriptcoregtk-4.1.so /usr/lib/x86_64-linux-gnu/libjavascriptcoregtk-4.0.so
    ```

## Building the Application

Once the dependencies are installed and the workarounds are applied, you can build the application.

1.  **Install Node.js dependencies:**
    ```bash
    cd heaven-gui
    npm install
    ```

2.  **Run the development server (optional):**
    This will build and launch the app in development mode with hot-reloading. Note that this may fail in a headless environment.
    ```bash
    npm run tauri:dev
    ```

3.  **Create a production build:**
    This will compile the application and bundle it into installers (`.deb`, `.rpm`).
    ```bash
    npm run tauri:build
    ```
    The build may fail during the final AppImage creation step, but the `.deb` and `.rpm` packages should be successfully created in `heaven-gui/src-tauri/target/release/bundle/`.
# Heaven GUI Build Verification Guide

## Overview
This guide summarizes the steps taken to verify the Heaven GUI build inside the Solo-Git repository. It documents prerequisite tooling, build commands, observed outcomes, and known blockers encountered in this environment.

## Prerequisites
- Node.js and npm (for installing the frontend dependencies).
- Rust toolchain with Cargo (required by Tauri for native builds).
- System packages that provide the GTK / GLib development headers required by `glib-sys`.
  - On Debian/Ubuntu systems install them with: `apt-get update && apt-get install -y libgtk-3-dev libglib2.0-dev`.
  - Ensure `pkg-config` can locate `glib-2.0.pc` (set `PKG_CONFIG_PATH` if the file is in a non-standard directory).
- (Optional) Sample Solo-Git state data under `~/.sologit/state/*.json` for validating data loading in the UI.

## Build Commands and Results
Run the following commands from the `heaven-gui/` directory:

1. `npm install`
   - Installs JavaScript dependencies. This completed successfully during verification.
2. `npm run tauri:dev`
   - Builds the Rust backend and launches the development Tauri shell. The command failed because the container lacks the `glib-2.0` system library that the `glib-sys` crate requires during compilation.
3. `npm run tauri:build`
   - Produces a production bundle. The Vite frontend build succeeded, but the Rust compilation step failed with the same missing `glib-2.0` dependency.

## Observed Errors
Both `tauri:dev` and `tauri:build` halted with the following message:

```
error: failed to run custom build command for `glib-sys v0.15.10`
...
The system library `glib-2.0` required by crate `glib-sys` was not found.
The file `glib-2.0.pc` needs to be installed and the PKG_CONFIG_PATH environment variable must contain its parent directory.
```

The absence of GLib/GDK packages prevents producing a runnable desktop binary in this container.

## Validation Status
Because the native build fails, the following validation tasks remain unverified:
- Launching the packaged GUI executable.
- Exercising the 12 Tauri read commands (repository listing, workpad retrieval, etc.).
- Loading persisted state data from `~/.sologit/state/*.json`.
- Rendering UI components such as the Monaco editor, D3 commit graph, file explorer, test dashboard, and AI assistant panel.

## Next Steps for Successful Verification
1. Install the required system dependencies (see **Prerequisites**).
2. Re-run `npm run tauri:dev` and `npm run tauri:build` to confirm the Rust compilation completes.
3. Launch the generated binary to validate UI functionality with sample data.
4. Document the successful validation results once the environment includes the necessary GTK/GLib packages.
