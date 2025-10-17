
// Prevents additional console window on Windows in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct GlobalState {
    version: String,
    last_updated: String,
    active_repo: Option<String>,
    active_workpad: Option<String>,
    session_start: String,
    total_operations: i32,
    total_cost_usd: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct RepositoryState {
    repo_id: String,
    name: String,
    path: String,
    trunk_branch: String,
    current_commit: Option<String>,
    created_at: String,
    updated_at: String,
    workpads: Vec<String>,
    total_commits: i32,
}

#[derive(Debug, Serialize, Deserialize)]
struct WorkpadState {
    workpad_id: String,
    repo_id: String,
    title: String,
    status: String,
    branch_name: String,
    base_commit: String,
    current_commit: Option<String>,
    created_at: String,
    updated_at: String,
    promoted_at: Option<String>,
    test_runs: Vec<String>,
    ai_operations: Vec<String>,
    patches_applied: i32,
    files_changed: Vec<String>,
}

fn get_state_dir() -> PathBuf {
    let home = dirs::home_dir().expect("Could not find home directory");
    home.join(".sologit").join("state")
}

#[tauri::command]
fn read_global_state() -> Result<GlobalState, String> {
    let state_path = get_state_dir().join("global.json");
    
    if !state_path.exists() {
        return Err("No global state found. Initialize Solo Git first.".to_string());
    }
    
    let contents = fs::read_to_string(state_path)
        .map_err(|e| format!("Failed to read global state: {}", e))?;
    
    serde_json::from_str(&contents)
        .map_err(|e| format!("Failed to parse global state: {}", e))
}

#[tauri::command]
fn list_repositories() -> Result<Vec<RepositoryState>, String> {
    let repos_dir = get_state_dir().join("repositories");
    
    if !repos_dir.exists() {
        return Ok(Vec::new());
    }
    
    let mut repos = Vec::new();
    
    for entry in fs::read_dir(repos_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        
        if path.extension().and_then(|s| s.to_str()) == Some("json") {
            let contents = fs::read_to_string(&path)
                .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;
            
            let repo: RepositoryState = serde_json::from_str(&contents)
                .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))?;
            
            repos.push(repo);
        }
    }
    
    Ok(repos)
}

#[tauri::command]
fn read_repository(repo_id: String) -> Result<RepositoryState, String> {
    let repo_path = get_state_dir().join("repositories").join(format!("{}.json", repo_id));
    
    if !repo_path.exists() {
        return Err(format!("Repository not found: {}", repo_id));
    }
    
    let contents = fs::read_to_string(repo_path)
        .map_err(|e| format!("Failed to read repository: {}", e))?;
    
    serde_json::from_str(&contents)
        .map_err(|e| format!("Failed to parse repository: {}", e))
}

#[tauri::command]
fn list_workpads(repo_id: Option<String>) -> Result<Vec<WorkpadState>, String> {
    let workpads_dir = get_state_dir().join("workpads");
    
    if !workpads_dir.exists() {
        return Ok(Vec::new());
    }
    
    let mut workpads = Vec::new();
    
    for entry in fs::read_dir(workpads_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        
        if path.extension().and_then(|s| s.to_str()) == Some("json") {
            let contents = fs::read_to_string(&path)
                .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;
            
            let workpad: WorkpadState = serde_json::from_str(&contents)
                .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))?;
            
            // Filter by repo_id if provided
            if repo_id.is_none() || repo_id.as_ref() == Some(&workpad.repo_id) {
                workpads.push(workpad);
            }
        }
    }
    
    Ok(workpads)
}

#[tauri::command]
fn read_commits(repo_id: String) -> Result<serde_json::Value, String> {
    let commits_path = get_state_dir().join("commits").join(format!("{}.json", repo_id));
    
    if !commits_path.exists() {
        return Ok(serde_json::json!({"commits": []}));
    }
    
    let contents = fs::read_to_string(commits_path)
        .map_err(|e| format!("Failed to read commits: {}", e))?;
    
    serde_json::from_str(&contents)
        .map_err(|e| format!("Failed to parse commits: {}", e))
}

fn main() {
    // Add dirs crate for home_dir
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            read_global_state,
            list_repositories,
            read_repository,
            list_workpads,
            read_commits,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
