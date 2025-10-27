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
