// Prevents additional console window on Windows in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::process::Command;

mod commands;

// ============================================================================
// Data Structures (matching Python state schema)
// ============================================================================

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct GlobalState {
    version: String,
    last_updated: String,
    active_repo: Option<String>,
    active_workpad: Option<String>,
    session_start: String,
    total_operations: i32,
    total_cost_usd: f64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct RepositoryState {
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

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct WorkpadState {
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

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct TestRun {
    run_id: String,
    workpad_id: Option<String>,
    target: String,
    status: String,
    started_at: String,
    completed_at: Option<String>,
    total_tests: i32,
    passed: i32,
    failed: i32,
    skipped: i32,
    duration_ms: i32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct AIOperation {
    operation_id: String,
    workpad_id: Option<String>,
    operation_type: String,
    status: String,
    model: String,
    prompt: String,
    response: Option<String>,
    cost_usd: f64,
    tokens_used: i32,
    started_at: String,
    completed_at: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct CommitNode {
    sha: String,
    short_sha: String,
    message: String,
    author: String,
    timestamp: String,
    parent_sha: Option<String>,
    workpad_id: Option<String>,
    test_status: Option<String>,
    ci_status: Option<String>,
    is_trunk: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct FileNode {
    name: String,
    path: String,
    is_directory: bool,
    children: Option<Vec<FileNode>>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct Settings {
    theme: String,
    font_size: i32,
    auto_save: bool,
    show_line_numbers: bool,
    enable_ai: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub(crate) struct PromotionRecord {
    record_id: String,
    repo_id: String,
    workpad_id: String,
    decision: String,
    can_promote: bool,
    auto_promote_requested: bool,
    promoted: bool,
    commit_hash: Option<String>,
    message: String,
    test_run_id: Option<String>,
    ci_status: Option<String>,
    ci_message: Option<String>,
    created_at: String,
}

// ============================================================================
// Helper Functions
// ============================================================================

pub(crate) fn get_state_dir() -> PathBuf {
    let home = dirs::home_dir().expect("Could not find home directory");
    home.join(".sologit").join("state")
}

pub(crate) fn get_repos_dir() -> PathBuf {
    let home = dirs::home_dir().expect("Could not find home directory");
    home.join(".sologit").join("data").join("repos")
}

// ============================================================================
// State Management Commands
// ============================================================================

#[tauri::command]
fn read_global_state() -> Result<GlobalState, String> {
    let state_path = get_state_dir().join("global.json");

    if !state_path.exists() {
        // Return default state if file doesn't exist
        return Ok(GlobalState {
            version: "0.4.0".to_string(),
            last_updated: chrono::Utc::now().to_rfc3339(),
            active_repo: None,
            active_workpad: None,
            session_start: chrono::Utc::now().to_rfc3339(),
            total_operations: 0,
            total_cost_usd: 0.0,
        });
    }

    let contents = fs::read_to_string(state_path)
        .map_err(|e| format!("Failed to read global state: {}", e))?;

    serde_json::from_str(&contents).map_err(|e| format!("Failed to parse global state: {}", e))
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

    // Sort by created_at descending
    repos.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    Ok(repos)
}

#[tauri::command]
fn verify_cli_install() -> Result<String, String> {
    let output = Command::new("evogitctl")
        .arg("--version")
        .output()
        .map_err(|e| format!("Failed to execute evogitctl: {}", e))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
    }
}

#[tauri::command]
fn read_repository(repo_id: String) -> Result<RepositoryState, String> {
    let repo_path = get_state_dir()
        .join("repositories")
        .join(format!("{}.json", repo_id));

    if !repo_path.exists() {
        return Err(format!("Repository not found: {}", repo_id));
    }

    let contents =
        fs::read_to_string(repo_path).map_err(|e| format!("Failed to read repository: {}", e))?;

    serde_json::from_str(&contents).map_err(|e| format!("Failed to parse repository: {}", e))
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

    // Sort by created_at descending
    workpads.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    Ok(workpads)
}

#[tauri::command]
fn read_workpad(workpad_id: String) -> Result<WorkpadState, String> {
    let workpad_path = get_state_dir()
        .join("workpads")
        .join(format!("{}.json", workpad_id));

    if !workpad_path.exists() {
        return Err(format!("Workpad not found: {}", workpad_id));
    }

    let contents =
        fs::read_to_string(workpad_path).map_err(|e| format!("Failed to read workpad: {}", e))?;

    serde_json::from_str(&contents).map_err(|e| format!("Failed to parse workpad: {}", e))
}

#[tauri::command]
fn list_commits(repo_id: String, limit: Option<i32>) -> Result<Vec<CommitNode>, String> {
    let commits_path = get_state_dir()
        .join("commits")
        .join(format!("{}.json", repo_id));

    if !commits_path.exists() {
        return Ok(Vec::new());
    }

    let contents =
        fs::read_to_string(commits_path).map_err(|e| format!("Failed to read commits: {}", e))?;

    let data: serde_json::Value =
        serde_json::from_str(&contents).map_err(|e| format!("Failed to parse commits: {}", e))?;

    let commits: Vec<CommitNode> =
        serde_json::from_value(data["commits"].clone()).unwrap_or_default();

    let limit = limit.unwrap_or(100) as usize;
    Ok(commits.into_iter().take(limit).collect())
}

#[tauri::command]
fn list_test_runs(workpad_id: Option<String>) -> Result<Vec<TestRun>, String> {
    let tests_dir = get_state_dir().join("test_runs");

    if !tests_dir.exists() {
        return Ok(Vec::new());
    }

    let mut test_runs = Vec::new();

    for entry in fs::read_dir(tests_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();

        if path.extension().and_then(|s| s.to_str()) == Some("json") {
            let contents = fs::read_to_string(&path)
                .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

            let test_run: TestRun = serde_json::from_str(&contents)
                .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))?;

            // Filter by workpad_id if provided
            if workpad_id.is_none() || test_run.workpad_id.as_ref() == workpad_id.as_ref() {
                test_runs.push(test_run);
            }
        }
    }

    // Sort by started_at descending
    test_runs.sort_by(|a, b| b.started_at.cmp(&a.started_at));
    Ok(test_runs)
}

#[tauri::command]
fn read_test_run(run_id: String) -> Result<TestRun, String> {
    let test_path = get_state_dir()
        .join("test_runs")
        .join(format!("{}.json", run_id));

    if !test_path.exists() {
        return Err(format!("Test run not found: {}", run_id));
    }

    let contents =
        fs::read_to_string(test_path).map_err(|e| format!("Failed to read test run: {}", e))?;

    serde_json::from_str(&contents).map_err(|e| format!("Failed to parse test run: {}", e))
}

#[tauri::command]
fn list_ai_operations(workpad_id: Option<String>) -> Result<Vec<AIOperation>, String> {
    let ai_ops_dir = get_state_dir().join("ai_operations");

    if !ai_ops_dir.exists() {
        return Ok(Vec::new());
    }

    let mut operations = Vec::new();

    for entry in fs::read_dir(ai_ops_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();

        if path.extension().and_then(|s| s.to_str()) == Some("json") {
            let contents = fs::read_to_string(&path)
                .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

            let operation: AIOperation = serde_json::from_str(&contents)
                .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))?;

            // Filter by workpad_id if provided
            if workpad_id.is_none() || operation.workpad_id.as_ref() == workpad_id.as_ref() {
                operations.push(operation);
            }
        }
    }

    // Sort by started_at descending
    operations.sort_by(|a, b| b.started_at.cmp(&a.started_at));
    Ok(operations)
}

#[tauri::command]
fn read_ai_operation(operation_id: String) -> Result<AIOperation, String> {
    let operation_path = get_state_dir()
        .join("ai_operations")
        .join(format!("{}.json", operation_id));

    if !operation_path.exists() {
        return Err(format!("AI operation not found: {}", operation_id));
    }

    let contents = fs::read_to_string(operation_path)
        .map_err(|e| format!("Failed to read AI operation: {}", e))?;

    serde_json::from_str(&contents).map_err(|e| format!("Failed to parse AI operation: {}", e))
}

// ============================================================================
// File Operations
// ============================================================================

#[tauri::command]
fn read_file(repo_id: String, file_path: String) -> Result<String, String> {
    let full_path = get_repos_dir().join(&repo_id).join(&file_path);

    if !full_path.exists() {
        return Err(format!("File not found: {}", file_path));
    }

    fs::read_to_string(full_path).map_err(|e| format!("Failed to read file: {}", e))
}

#[tauri::command]
fn list_repository_files(repo_id: String) -> Result<Vec<String>, String> {
    let repo_dir = get_repos_dir().join(&repo_id);

    if !repo_dir.exists() {
        return Err(format!("Repository directory not found: {}", repo_id));
    }

    fn collect_files(dir: &std::path::Path, base: &std::path::Path) -> Result<Vec<String>, String> {
        let mut files = Vec::new();

        for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();

            // Skip .git directory
            if path.file_name().and_then(|n| n.to_str()) == Some(".git") {
                continue;
            }

            if path.is_file() {
                let rel_path = path
                    .strip_prefix(base)
                    .map_err(|e| e.to_string())?
                    .to_string_lossy()
                    .to_string();
                files.push(rel_path);
            } else if path.is_dir() {
                files.extend(collect_files(&path, base)?);
            }
        }

        Ok(files)
    }

    let mut files = collect_files(&repo_dir, &repo_dir)?;
    files.sort();
    Ok(files)
}

#[tauri::command]
fn get_file_tree(repo_id: String) -> Result<Vec<FileNode>, String> {
    let repo_dir = get_repos_dir().join(&repo_id);

    if !repo_dir.exists() {
        return Err(format!("Repository directory not found: {}", repo_id));
    }

    fn build_tree(dir: &std::path::Path, base: &std::path::Path) -> Result<Vec<FileNode>, String> {
        let mut nodes = Vec::new();

        for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();

            // Skip .git directory and hidden files
            let file_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if file_name == ".git" || file_name.starts_with('.') {
                continue;
            }

            let rel_path = path
                .strip_prefix(base)
                .map_err(|e| e.to_string())?
                .to_string_lossy()
                .to_string();

            let is_dir = path.is_dir();
            let children = if is_dir {
                Some(build_tree(&path, base)?)
            } else {
                None
            };

            nodes.push(FileNode {
                name: file_name.to_string(),
                path: rel_path,
                is_directory: is_dir,
                children,
            });
        }

        // Sort: directories first, then alphabetically
        nodes.sort_by(|a, b| match (a.is_directory, b.is_directory) {
            (true, false) => std::cmp::Ordering::Less,
            (false, true) => std::cmp::Ordering::Greater,
            _ => a.name.cmp(&b.name),
        });

        Ok(nodes)
    }

    build_tree(&repo_dir, &repo_dir)
}

#[tauri::command]
fn get_directory_contents(repo_id: String, dir_path: String) -> Result<Vec<FileNode>, String> {
    let full_path = get_repos_dir().join(&repo_id).join(&dir_path);

    if !full_path.exists() || !full_path.is_dir() {
        return Err(format!("Directory not found: {}", dir_path));
    }

    let mut nodes = Vec::new();

    for entry in fs::read_dir(&full_path).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();

        let file_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
        if file_name.starts_with('.') {
            continue;
        }

        let is_dir = path.is_dir();

        nodes.push(FileNode {
            name: file_name.to_string(),
            path: format!("{}/{}", dir_path, file_name),
            is_directory: is_dir,
            children: None,
        });
    }

    // Sort: directories first, then alphabetically
    nodes.sort_by(|a, b| match (a.is_directory, b.is_directory) {
        (true, false) => std::cmp::Ordering::Less,
        (false, true) => std::cmp::Ordering::Greater,
        _ => a.name.cmp(&b.name),
    });

    Ok(nodes)
}

pub(crate) fn get_settings_path() -> PathBuf {
    let home = dirs::home_dir().expect("Could not find home directory");
    home.join(".sologit").join("gui_settings.json")
}

#[tauri::command]
fn get_settings() -> Result<Settings, String> {
    let settings_path = get_settings_path();

    if !settings_path.exists() {
        // Return default settings
        return Ok(Settings {
            theme: "dark".to_string(),
            font_size: 14,
            auto_save: true,
            show_line_numbers: true,
            enable_ai: true,
        });
    }

    let contents =
        fs::read_to_string(settings_path).map_err(|e| format!("Failed to read settings: {}", e))?;

    serde_json::from_str(&contents).map_err(|e| format!("Failed to parse settings: {}", e))
}

#[tauri::command]
fn save_settings(settings: Settings) -> Result<(), String> {
    let settings_path = get_settings_path();

    // Create directory if it doesn't exist
    if let Some(parent) = settings_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create settings directory: {}", e))?;
    }

    let contents = serde_json::to_string_pretty(&settings)
        .map_err(|e| format!("Failed to serialize settings: {}", e))?;

    fs::write(settings_path, contents).map_err(|e| format!("Failed to write settings: {}", e))
}

#[tauri::command]
fn ai_chat(
    repo_id: String,
    workpad_id: Option<String>,
    prompt: String,
    model: String,
) -> Result<serde_json::Value, String> {
    // This is a stub that returns a simulated response
    // In production, this would call the actual Solo Git AI orchestrator
    // For now, we'll return a placeholder response

    Ok(serde_json::json!({
        "content": "AI integration is being implemented. This feature will connect to the Solo Git AI orchestrator to provide planning, code generation, and debugging assistance.",
        "model": model,
        "cost_usd": 0.0,
        "tokens_used": 0,
        "error": "AI chat functionality requires integration with the Solo Git backend. Please use the CLI commands for AI features until GUI integration is complete."
    }))
}

// ============================================================================
// Main Application
// ============================================================================

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            // State management
            read_global_state,
            list_repositories,
            read_repository,
            list_workpads,
            read_workpad,
            list_commits,
            list_test_runs,
            read_test_run,
            list_ai_operations,
            read_ai_operation,
            verify_cli_install,
            // File operations
            read_file,
            list_repository_files,
            get_file_tree,
            get_directory_contents,
            // Settings
            get_settings,
            save_settings,
            // AI operations
            ai_chat,
            // Write operations
            commands::create_repository,
            commands::delete_repository,
            commands::create_workpad,
            commands::apply_patch,
            commands::run_tests,
            commands::promote_workpad,
            commands::delete_workpad,
            commands::rollback_workpad,
            commands::trigger_ai_operation,
            commands::update_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
