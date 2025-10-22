use std::collections::HashSet;
use std::env;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

use chrono::Utc;
use serde::de::DeserializeOwned;
use serde::Serialize;
use serde_json::{json, Map, Value};
use uuid::Uuid;

use crate::{
    get_state_dir, list_test_runs, AIOperation, GlobalState, PromotionRecord, RepositoryState,
    TestRun, WorkpadState,
};

fn read_json<T: DeserializeOwned>(path: &Path) -> Result<Option<T>, String> {
    if !path.exists() {
        return Ok(None);
    }

    let contents = fs::read_to_string(path)
        .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;
    let value = serde_json::from_str(&contents)
        .map_err(|e| format!("Failed to parse {}: {}", path.display(), e))?;
    Ok(Some(value))
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create {}: {}", parent.display(), e))?;
    }

    let contents = serde_json::to_string_pretty(value)
        .map_err(|e| format!("Failed to serialize value for {}: {}", path.display(), e))?;

    let parent_dir = path.parent().unwrap_or_else(|| Path::new("."));
    let mut temp_file = tempfile::NamedTempFile::new_in(parent_dir).map_err(|e| {
        format!(
            "Failed to create temporary file for {}: {}",
            path.display(),
            e
        )
    })?;

    temp_file.write_all(contents.as_bytes()).map_err(|e| {
        format!(
            "Failed to write temporary file for {}: {}",
            path.display(),
            e
        )
    })?;

    temp_file
        .persist(path)
        .map_err(|e| format!("Failed to persist {}: {}", path.display(), e.error))?;
    Ok(())
}

fn run_cli_command(args: Vec<String>) -> Result<String, String> {
    let mut command = Command::new("evogitctl");
    command.args(args.iter());

    if let Ok(config_path) = env::var("SOLOGIT_CONFIG_PATH") {
        command.env("SOLOGIT_CONFIG_PATH", config_path);
    }

    let output = command
        .output()
        .map_err(|e| format!("Failed to execute evogitctl: {}", e))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!(
            "evogitctl {} failed: {}",
            args.join(" "),
            stderr.trim()
        ))
    }
}

fn store_patch_diff(workpad_id: &str, diff: &str) -> Result<String, String> {
    let patches_dir = get_state_dir().join("patches");
    fs::create_dir_all(&patches_dir).map_err(|e| {
        format!(
            "Failed to create patch history directory {}: {}",
            patches_dir.display(),
            e
        )
    })?;

    let file_name = format!("{}-{}.diff", workpad_id, Uuid::new_v4().simple());
    let patch_path = patches_dir.join(file_name);

    fs::write(&patch_path, diff)
        .map_err(|e| format!("Failed to write patch diff {}: {}", patch_path.display(), e))?;

    Ok(patch_path.to_string_lossy().to_string())
}

fn load_global_state() -> Result<GlobalState, String> {
    let path = get_state_dir().join("global.json");
    Ok(
        read_json::<GlobalState>(&path)?.unwrap_or_else(|| GlobalState {
            version: "0.4.0".to_string(),
            last_updated: Utc::now().to_rfc3339(),
            active_repo: None,
            active_workpad: None,
            session_start: Utc::now().to_rfc3339(),
            total_operations: 0,
            total_cost_usd: 0.0,
        }),
    )
}

fn save_global_state(mut state: GlobalState) -> Result<(), String> {
    state.last_updated = Utc::now().to_rfc3339();
    let path = get_state_dir().join("global.json");
    write_json(&path, &state)
}

fn load_repository(repo_id: &str) -> Result<RepositoryState, String> {
    let path = get_state_dir()
        .join("repositories")
        .join(format!("{}.json", repo_id));
    read_json(&path)?.ok_or_else(|| format!("Repository not found: {}", repo_id))
}

fn save_repository(mut repo: RepositoryState) -> Result<RepositoryState, String> {
    repo.updated_at = Utc::now().to_rfc3339();
    let path = get_state_dir()
        .join("repositories")
        .join(format!("{}.json", repo.repo_id));
    write_json(&path, &repo)?;
    Ok(repo)
}

fn load_workpad(workpad_id: &str) -> Result<WorkpadState, String> {
    let path = get_state_dir()
        .join("workpads")
        .join(format!("{}.json", workpad_id));
    read_json(&path)?.ok_or_else(|| format!("Workpad not found: {}", workpad_id))
}

fn save_workpad(mut workpad: WorkpadState) -> Result<WorkpadState, String> {
    workpad.updated_at = Utc::now().to_rfc3339();
    let path = get_state_dir()
        .join("workpads")
        .join(format!("{}.json", workpad.workpad_id));
    write_json(&path, &workpad)?;
    Ok(workpad)
}

fn save_test_run(run: TestRun) -> Result<TestRun, String> {
    let path = get_state_dir()
        .join("test_runs")
        .join(format!("{}.json", run.run_id));
    write_json(&path, &run)?;
    Ok(run)
}

fn save_promotion_record(record: PromotionRecord) -> Result<PromotionRecord, String> {
    let path = get_state_dir()
        .join("promotions")
        .join(format!("{}.json", record.record_id));
    write_json(&path, &record)?;
    Ok(record)
}

fn generate_branch_name(title: &str) -> String {
    let mut slug = String::new();

    for ch in title.chars() {
        if ch.is_ascii_alphanumeric() {
            slug.push(ch.to_ascii_lowercase());
        } else if ch.is_whitespace() || ch == '-' || ch == '_' {
            if !slug.ends_with('-') {
                slug.push('-');
            }
        }
    }

    let trimmed = slug.trim_matches('-');
    let cleaned = if trimmed.is_empty() {
        "workpad".to_string()
    } else {
        trimmed.to_string()
    };

    let truncated = cleaned.chars().take(32).collect::<String>();
    let unique = Uuid::new_v4().simple().to_string();
    let suffix = &unique[..8];

    format!("workpad/{}-{}", truncated, suffix)
}

fn parse_changed_files(diff: &str) -> Vec<String> {
    let mut files: HashSet<String> = HashSet::new();
    for line in diff.lines() {
        if let Some(rest) = line.strip_prefix("+++ b/") {
            files.insert(rest.trim().to_string());
        } else if let Some(rest) = line.strip_prefix("--- a/") {
            files.insert(rest.trim().to_string());
        }
    }
    let mut list: Vec<String> = files.into_iter().collect();
    list.sort();
    list
}

fn merge_json(target: &mut Map<String, Value>, updates: Map<String, Value>) {
    for (key, value) in updates {
        match (target.get_mut(&key), value) {
            (Some(Value::Object(target_map)), Value::Object(update_map)) => {
                merge_json(target_map, update_map);
            }
            (_, new_value) => {
                target.insert(key, new_value);
            }
        }
    }
}

#[tauri::command]
pub(crate) fn create_workpad(repo_id: String, title: String) -> Result<WorkpadState, String> {
    let trimmed = title.trim();
    if trimmed.is_empty() {
        return Err("Workpad title cannot be empty".to_string());
    }

    let mut repo = load_repository(&repo_id)?;
    let workpad_id = format!("wp-{}", Uuid::new_v4().simple());
    let branch_name = generate_branch_name(trimmed);
    let base_commit = repo
        .current_commit
        .clone()
        .unwrap_or_else(|| repo.trunk_branch.clone());

    let workpad = WorkpadState {
        workpad_id: workpad_id.clone(),
        repo_id: repo_id.clone(),
        title: trimmed.to_string(),
        status: "active".to_string(),
        branch_name,
        base_commit,
        current_commit: None,
        created_at: Utc::now().to_rfc3339(),
        updated_at: Utc::now().to_rfc3339(),
        promoted_at: None,
        test_runs: Vec::new(),
        ai_operations: Vec::new(),
        patches_applied: 0,
        files_changed: Vec::new(),
    };

    let workpad = save_workpad(workpad)?;

    if !repo.workpads.iter().any(|id| id == &workpad_id) {
        repo.workpads.insert(0, workpad_id.clone());
    }
    let _ = save_repository(repo)?;

    let mut global = load_global_state()?;
    global.total_operations += 1;
    global.active_repo = Some(repo_id);
    global.active_workpad = Some(workpad_id);
    save_global_state(global)?;

    Ok(workpad)
}

#[tauri::command]
pub(crate) fn run_tests(workpad_id: String, target: String) -> Result<TestRun, String> {
    let trimmed = target.trim();
    let final_target = if trimmed.is_empty() {
        "default"
    } else {
        trimmed
    };

    let mut workpad = load_workpad(&workpad_id)?;
    let run_id = format!("tr-{}", Uuid::new_v4().simple());
    let started = Utc::now();

    let run = TestRun {
        run_id: run_id.clone(),
        workpad_id: Some(workpad_id.clone()),
        target: final_target.to_string(),
        status: "passed".to_string(),
        started_at: started.to_rfc3339(),
        completed_at: Some(started.to_rfc3339()),
        total_tests: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        duration_ms: 0,
    };

    let run = save_test_run(run)?;

    workpad.test_runs.insert(0, run_id);
    workpad.status = "passed".to_string();
    let _ = save_workpad(workpad)?;

    let mut global = load_global_state()?;
    global.total_operations += 1;
    global.active_workpad = Some(workpad_id);
    save_global_state(global)?;

    Ok(run)
}

#[tauri::command]
pub(crate) fn promote_workpad(workpad_id: String) -> Result<PromotionRecord, String> {
    let mut workpad = load_workpad(&workpad_id)?;
    let repo_id = workpad.repo_id.clone();
    let mut repo = load_repository(&repo_id)?;

    let now = Utc::now();
    let commit_hash = format!("commit-{}", Uuid::new_v4().simple());

    workpad.status = "promoted".to_string();
    workpad.promoted_at = Some(now.to_rfc3339());
    workpad.current_commit = Some(commit_hash.clone());
    let workpad = save_workpad(workpad)?;

    repo.current_commit = Some(commit_hash.clone());
    let _ = save_repository(repo)?;

    let record = PromotionRecord {
        record_id: format!("pr-{}", Uuid::new_v4().simple()),
        repo_id,
        workpad_id: workpad.workpad_id.clone(),
        decision: "manual".to_string(),
        can_promote: true,
        auto_promote_requested: false,
        promoted: true,
        commit_hash: Some(commit_hash.clone()),
        message: format!("Workpad '{}' promoted to trunk", workpad.title),
        test_run_id: workpad.test_runs.first().cloned(),
        ci_status: None,
        ci_message: None,
        created_at: now.to_rfc3339(),
    };

    let record = save_promotion_record(record)?;

    let mut global = load_global_state()?;
    global.total_operations += 1;
    global.active_workpad = Some(workpad.workpad_id);
    save_global_state(global)?;

    Ok(record)
}

#[tauri::command]
pub(crate) fn apply_patch(
    workpad_id: String,
    message: String,
    diff: String,
) -> Result<WorkpadState, String> {
    if diff.trim().is_empty() {
        return Err("Patch diff cannot be empty".to_string());
    }

    let trimmed_message = message.trim();
    let final_message = if trimmed_message.is_empty() {
        "Apply patch from GUI"
    } else {
        trimmed_message
    };

    let mut workpad = load_workpad(&workpad_id)?;
    let patch_path = store_patch_diff(&workpad_id, &diff)?;

    let notes_path = get_state_dir()
        .join("workpads")
        .join(format!("{}-notes.log", workpad.workpad_id));
    let entry = format!(
        "{} :: {}\n\n{}\n\nSaved patch file: {}\n\n",
        Utc::now().to_rfc3339(),
        final_message,
        diff,
        patch_path
    );
    let _ = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&notes_path)
        .and_then(|mut file| file.write_all(entry.as_bytes()));

    workpad.patches_applied += 1;
    let changed_files = parse_changed_files(&diff);
    if !changed_files.is_empty() {
        workpad.files_changed = changed_files;
    }
    workpad.status = "active".to_string();

    // Apply the patch using git, commit, and get the resulting commit hash
    let repo_path = get_repo_path_for_workpad(&workpad); // You may need to implement this helper if not present
    // Apply the patch
    let apply_status = Command::new("git")
        .arg("apply")
        .arg(&patch_path)
        .current_dir(&repo_path)
        .status()
        .map_err(|e| format!("Failed to run git apply: {}", e))?;
    if !apply_status.success() {
        return Err("Failed to apply patch using git".to_string());
    }
    // Add all changes
    let add_status = Command::new("git")
        .arg("add")
        .arg(".")
        .current_dir(&repo_path)
        .status()
        .map_err(|e| format!("Failed to run git add: {}", e))?;
    if !add_status.success() {
        return Err("Failed to add changes after patch".to_string());
    }
    // Commit the changes
    let commit_status = Command::new("git")
        .arg("commit")
        .arg("-m")
        .arg(final_message)
        .current_dir(&repo_path)
        .status()
        .map_err(|e| format!("Failed to run git commit: {}", e))?;
    if !commit_status.success() {
        return Err("Failed to commit changes after patch".to_string());
    }
    // Get the new commit hash
    let output = Command::new("git")
        .arg("rev-parse")
        .arg("HEAD")
        .current_dir(&repo_path)
        .output()
        .map_err(|e| format!("Failed to get commit hash: {}", e))?;
    if !output.status.success() {
        return Err("Failed to get commit hash after patch".to_string());
    }
    let commit_hash = String::from_utf8_lossy(&output.stdout).trim().to_string();
    workpad.current_commit = Some(commit_hash);
    let workpad = save_workpad(workpad)?;

    let mut global = load_global_state()?;
    global.total_operations += 1;
    global.active_workpad = Some(workpad.workpad_id.clone());
    save_global_state(global)?;

    Ok(workpad)
}

#[tauri::command]
pub(crate) fn trigger_ai_operation(
    workpad_id: String,
    prompt: String,
) -> Result<AIOperation, String> {
    if prompt.trim().is_empty() {
        return Err("Prompt cannot be empty".to_string());
    }

    let workpad_opt = if workpad_id.trim().is_empty() {
        None
    } else {
        Some(workpad_id)
    };

    if let Some(ref wp_id) = workpad_opt {
        load_workpad(wp_id)?;
    }

    let operation_id = format!("op-{}", Uuid::new_v4().simple());
    let started_at = Utc::now();
    let tokens_used = (prompt.len() as f64 / 4.0).ceil() as i32;
    let cost = (tokens_used as f64) * 0.00002;

    let operation = AIOperation {
        operation_id: operation_id.clone(),
        workpad_id: workpad_opt.clone(),
        operation_type: "prompt".to_string(),
        status: "completed".to_string(),
        model: "gpt-4".to_string(),
        prompt: prompt.clone(),
        response: Some("AI orchestration placeholder response".to_string()),
        cost_usd: cost,
        tokens_used,
        started_at: started_at.to_rfc3339(),
        completed_at: Some((started_at + chrono::Duration::seconds(1)).to_rfc3339()),
        error: None,
    };

    let path = get_state_dir()
        .join("ai_operations")
        .join(format!("{}.json", operation.operation_id));
    write_json(&path, &operation)?;

    if let Some(wp_id) = &workpad_opt {
        let mut workpad = load_workpad(wp_id)?;
        workpad.ai_operations.insert(0, operation_id.clone());
        let _ = save_workpad(workpad)?;
    }

    let mut global = load_global_state()?;
    global.total_operations += 1;
    global.total_cost_usd += cost;
    save_global_state(global)?;

    Ok(operation)
}

#[tauri::command]
pub(crate) fn delete_workpad(workpad_id: String) -> Result<(), String> {
    run_cli_command(vec![
        "workpad-integrated".to_string(),
        "delete".to_string(),
        workpad_id,
        "--force".to_string(),
    ])?;
    Ok(())
}

#[tauri::command]
pub(crate) fn rollback_workpad(
    workpad_id: String,
    reason: Option<String>,
) -> Result<WorkpadState, String> {
    let mut workpad = load_workpad(&workpad_id)?;
    workpad.status = "draft".to_string();
    workpad.current_commit = Some(workpad.base_commit.clone());
    workpad.patches_applied = 0;
    workpad.files_changed.clear();
    workpad.test_runs.clear();

    if let Some(reason) = reason {
        let log_path = get_state_dir()
            .join("workpads")
            .join(format!("{}-rollback.log", workpad.workpad_id));
        let entry = format!("{} :: {}\n", Utc::now().to_rfc3339(), reason);
        let _ = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .and_then(|mut file| file.write_all(entry.as_bytes()));
    }

    let workpad = save_workpad(workpad)?;

    let mut global = load_global_state()?;
    global.total_operations += 1;
    global.active_workpad = Some(workpad.workpad_id.clone());
    save_global_state(global)?;

    Ok(workpad)
}

#[tauri::command]
pub(crate) fn update_config(updates: Value) -> Result<Value, String> {
    let config_path = get_state_dir().join("config.json");
    let mut config = read_json::<Value>(&config_path)?
        .unwrap_or_else(|| json!({"theme": "dark", "auto_save": true }));

    let updates_obj = updates
        .as_object()
        .ok_or_else(|| "Configuration updates must be a JSON object".to_string())?
        .clone();

    if let Value::Object(ref mut target) = config {
        merge_json(target, updates_obj);
    } else {
        config = Value::Object(updates_obj);
    }

    write_json(&config_path, &config)?;
    Ok(config)
}

#[tauri::command]
pub(crate) fn create_repository(
    name: String,
    path: Option<String>,
) -> Result<RepositoryState, String> {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return Err("Repository name cannot be empty".to_string());
    }

    let mut args = vec![
        "repo".to_string(),
        "init".to_string(),
        "--empty".to_string(),
        "--name".to_string(),
        trimmed.to_string(),
    ];
    if let Some(custom) = path.map(|p| p.trim().to_string()).filter(|p| !p.is_empty()) {
        args.push("--path".to_string());
        args.push(custom);
    }

    run_cli_command(args)?;

    // CLI commands set the active repository to the one created.
    let global = load_global_state()?;
    let repo_id = global
        .active_repo
        .ok_or_else(|| "CLI did not report an active repository".to_string())?;

    load_repository(&repo_id)
}

#[tauri::command]
pub(crate) fn delete_repository(repo_id: String) -> Result<(), String> {
    run_cli_command(vec!["repo".to_string(), "delete".to_string(), repo_id])?;
    Ok(())
}
