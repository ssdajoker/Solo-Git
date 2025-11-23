use std::{env, fs, path::PathBuf};

fn copy_sidecar_if_present() {
    // Allow overriding the path to the prebuilt Python core via env var
    let custom_path = env::var("SOLOGIT_CORE_PATH").ok();
    println!("cargo:rerun-if-env-changed=SOLOGIT_CORE_PATH");

    // Determine expected destination filename based on target OS
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();
    let exe_name = if target_os == "windows" { "sologit-core.exe" } else { "sologit-core" };

    // Destination under src-tauri/bin so Tauri bundles it as an externalBin
    let mut dest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    dest.push("bin");
    // Ensure bin directory exists
    let _ = fs::create_dir_all(&dest);
    dest.push(exe_name);

    // Determine source: env var wins; otherwise look in a few common locations
    let candidates: Vec<PathBuf> = if let Some(path) = custom_path {
        vec![PathBuf::from(path)]
    } else {
        let mut list = Vec::new();

        // Repo root dist folder (PyInstaller default when run at repo root)
        let mut p_repo_dist = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        p_repo_dist.push(".."); // heaven-gui
        p_repo_dist.push(".."); // repo root
        p_repo_dist.push("dist");
        p_repo_dist.push(exe_name);
        list.push(p_repo_dist);

        // Repo root scripts/dist folder (our helper scripts copy here)
        let mut p_scripts_dist = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        p_scripts_dist.push(".."); // heaven-gui
        p_scripts_dist.push(".."); // repo root
        p_scripts_dist.push("scripts");
        p_scripts_dist.push("dist");
        p_scripts_dist.push(exe_name);
        list.push(p_scripts_dist);

        list
    };

    for src in candidates {
        if src.exists() {
            match fs::copy(&src, &dest) {
                Ok(_) => {
                    println!("cargo:warning=Bundling sidecar from {:?} -> {:?}", src, dest);
                    return;
                }
                Err(e) => {
                    println!("cargo:warning=Failed to copy sidecar from {:?}: {}", src, e);
                }
            }
        }
    }

    // Not fatal: allow GUI to build without sidecar in dev. The installer will still build,
    // but launching operations that rely on the core will need the sidecar to be present.
    println!("cargo:warning=No sologit-core sidecar found. Set SOLOGIT_CORE_PATH to include it in the bundle.");
}

fn main() {
    copy_sidecar_if_present();
    tauri_build::build()
}
