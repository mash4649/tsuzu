use serde::Serialize;
use std::{path::PathBuf, process::Command};
use tauri::Manager;

#[derive(Serialize)]
struct RuntimeHealthResponse {
    status: &'static str,
}

#[tauri::command]
fn runtime_health() -> RuntimeHealthResponse {
    RuntimeHealthResponse { status: "ready" }
}

#[derive(Serialize)]
struct IngressResponse {
    output: String,
}

#[tauri::command]
fn process_desktop_ingress(app: tauri::AppHandle) -> Result<IngressResponse, String> {
    let home = app.path().home_dir().map_err(|error| error.to_string())?;
    let core_root = std::env::var_os("TSUZU_CORE_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| home.join("Desktop/++++TSUZU/Core"));
    let vault_root = std::env::var_os("TSUZU_VAULT_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| home.join("Desktop/++++TSUZU/Vault"));
    let app_local_root = app.path().app_local_data_dir().map_err(|error| error.to_string())?;
    let bundled_sidecar = std::env::current_exe()
        .map_err(|error| error.to_string())?
        .parent()
        .ok_or_else(|| "application executable has no parent directory".to_string())?
        .join("tsuzu-core");
    let sidecar = if bundled_sidecar.is_file() {
        bundled_sidecar
    } else {
        let target_name = format!("tsuzu-core-{}-apple-darwin", std::env::consts::ARCH);
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("binaries").join(target_name)
    };
    let output = Command::new(sidecar)
        .arg("--app-local-root")
        .arg(app_local_root)
        .arg("--core-root")
        .arg(core_root)
        .arg("--vault-root")
        .arg(vault_root)
        .output()
        .map_err(|error| format!("Core sidecar could not start: {error}"))?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
    }
    Ok(IngressResponse {
        output: String::from_utf8_lossy(&output.stdout).trim().to_string(),
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![
            runtime_health,
            process_desktop_ingress,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
