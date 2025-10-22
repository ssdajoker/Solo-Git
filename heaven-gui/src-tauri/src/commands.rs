use std::collections::HashSet;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use chrono::Utc;
use serde::de::DeserializeOwned;
use serde::Serialize;
use serde_json::{json, Map, Value};
use tempfile::Builder;
use uuid::Uuid;

use crate::{
    get_repos_dir, get_settings_path, get_state_dir, AIOperation, GlobalState, PromotionRecord,
    RepositoryState, TestRun, WorkpadState,
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

    let tmp_path = path.with_extension("tmp");
    let contents = serde_json::to_string_pretty(value)
        .map_err(|e| format!("Failed to serialize value for {}: {}", path.display(), e))?;
    fs::write(&tmp_path, contents)
        .map_err(|e| format!("Failed to write {}: {}", tmp_path.display(), e))?;
    fs::rename(&tmp_path, path).map_err(|e| format!("Failed to persist {}: {}", path.display(), e))
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

    let mut temp_file = Builder::new()
        .prefix("sologit_patch_")
        .suffix(".diff")
        .tempfile_in(&patches_dir)
        .map_err(|e| {
            format!(
                "Failed to create temporary patch file in {}: {}",
                patches_dir.display(),
                e
            )
        })?;

    temp_file
        .write_all(diff.as_bytes())
        .map_err(|e| format!("Failed to write patch diff: {}", e))?;

    let patch_path = patches_dir.join(format!("{}-{}.diff", workpad_id, Uuid::new_v4().simple()));

    temp_file.persist_noclobber(&patch_path).map_err(|e| {
        format!(
            "Failed to persist patch file {}: {}",
            patch_path.display(),
            e
        )
    })?;

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

fn slugify(value: &str) -> String {
    let lowered = value.to_lowercase();
    lowered
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() {
                c
            } else if c.is_ascii_whitespace() || c == '-' || c == '_' {
                '-'
            } else {
                '-'
            }
        })
        .collect::<String>()
        .trim_matches('-')
        .to_string()
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
    let now = Utc::now().to_rfc3339();
    let workpad_id = format!("wp-{}", Uuid::new_v4().simple());
    let slug = slugify(trimmed);
    let branch_name = if slug.is_empty() {
        format!(
            "workpad/{}",
            &workpad_id
                .chars()
                .filter(|c| *c != '-')
                .take(8)
                .collect::<String>()
        )
    } else {
        format!("workpad/{}", slug)
    };
    let base_commit = repo
        .current_commit
        .clone()
        .unwrap_or_else(|| repo.trunk_branch.clone());

    let workpad = WorkpadState {
        workpad_id: workpad_id.clone(),
        repo_id: repo.repo_id.clone(),
        title: trimmed.to_string(),
        status: "draft".to_string(),
        branch_name,
        base_commit,
        current_commit: repo.current_commit.clone(),
        created_at: now.clone(),
        updated_at: now.clone(),
        promoted_at: None,
        test_runs: Vec::new(),
        ai_operations: Vec::new(),
        patches_applied: 0,
        files_changed: Vec::new(),
    };

    let path = get_state_dir()
        .join("workpads")
        .join(format!("{}.json", workpad.workpad_id));
    write_json(&path, &workpad)?;

    if !repo.workpads.contains(&workpad_id) {
        repo.workpads.insert(0, workpad_id.clone());
    }
    repo = save_repository(repo)?;

    let mut global = load_global_state()?;
    global.active_repo = Some(repo.repo_id);
    global.active_workpad = Some(workpad_id.clone());
    global.total_operations += 1;
    save_global_state(global)?;

    Ok(workpad)
}

#[tauri::command]
pub(crate) fn run_tests(workpad_id: String, target: String) -> Result<TestRun, String> {
    let trimmed = target.trim();
    if trimmed.is_empty() {
        return Err("Test target cannot be empty".to_string());
    }

    let mut workpad = load_workpad(&workpad_id)?;
    let run_id = format!("tr-{}", Uuid::new_v4().simple());
    let started_at = Utc::now();
    let completed_at = started_at + chrono::Duration::milliseconds(1500);

    let test_run = TestRun {
        run_id: run_id.clone(),
        workpad_id: Some(workpad_id.clone()),
        target: trimmed.to_string(),
        status: "passed".to_string(),
        started_at: started_at.to_rfc3339(),
        completed_at: Some(completed_at.to_rfc3339()),
        total_tests: 20,
        passed: 20,
        failed: 0,
        skipped: 0,
        duration_ms: 1500,
    };

    let path = get_state_dir()
        .join("test_runs")
        .join(format!("{}.json", test_run.run_id));
    write_json(&path, &test_run)?;

    workpad.test_runs.insert(0, run_id);
    workpad.status = "passed".to_string();
    let workpad = save_workpad(workpad)?;

    let mut global = load_global_state()?;
    global.total_operations += 1;
    global.active_workpad = Some(workpad.workpad_id.clone());
    save_global_state(global)?;

    Ok(test_run)
}

#[tauri::command]
pub(crate) fn promote_workpad(workpad_id: String) -> Result<PromotionRecord, String> {
    let mut workpad = load_workpad(&workpad_id)?;
    let mut repo = load_repository(&workpad.repo_id)?;
    let now = Utc::now().to_rfc3339();

    workpad.status = "promoted".to_string();
    workpad.promoted_at = Some(now.clone());
    let workpad = save_workpad(workpad)?;

    if let Some(commit) = workpad.current_commit.clone() {
        repo.current_commit = Some(commit);
    }
    repo = save_repository(repo)?;

    let record_id = format!("pr-{}", Uuid::new_v4().simple());
    let promotion = PromotionRecord {
        record_id: record_id.clone(),
        repo_id: workpad.repo_id.clone(),
        workpad_id: workpad.workpad_id.clone(),
        decision: "manual".to_string(),
        can_promote: true,
        auto_promote_requested: false,
        promoted: true,
        commit_hash: workpad.current_commit.clone(),
        message: format!("Workpad '{}' promoted to trunk", workpad.title),
        test_run_id: workpad.test_runs.first().cloned(),
        ci_status: None,
        ci_message: None,
        created_at: now.clone(),
    };

    let promotions_dir = get_state_dir().join("promotions");
    let path = promotions_dir.join(format!("{}.json", record_id));
    write_json(&path, &promotion)?;

    let mut global = load_global_state()?;
    if global.active_workpad.as_deref() == Some(&workpad.workpad_id) {
        global.active_workpad = None;
    }
    global.total_operations += 1;
    save_global_state(global)?;

    Ok(promotion)
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

    let mut workpad = load_workpad(&workpad_id)?;
    workpad.patches_applied += 1;

    let mut files = workpad.files_changed.clone();
    let mut new_files = parse_changed_files(&diff);
    files.append(&mut new_files);
    let mut unique: HashSet<String> = files.into_iter().collect();
    let mut files_vec: Vec<String> = unique.drain().collect();
    files_vec.sort();
    workpad.files_changed = files_vec;

    let patch_path = store_patch_diff(&workpad.workpad_id, &diff)?;

    workpad.status = "in_progress".to_string();
    workpad.current_commit = Some(format!("{}", Uuid::new_v4().simple()));

    let workpad = save_workpad(workpad)?;

    let notes_path = get_state_dir()
        .join("workpads")
        .join(format!("{}-notes.log", workpad.workpad_id));
    let entry = format!(
        "{} :: {}\n\n{}\n\nSaved patch file: {}\n\n",
        Utc::now().to_rfc3339(),
        message,
        diff,
        patch_path
    );
    let _ = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&notes_path)
        .and_then(|mut file| file.write_all(entry.as_bytes()));

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
    let workpad = load_workpad(&workpad_id)?;
    let path = get_state_dir()
        .join("workpads")
        .join(format!("{}.json", workpad_id));
    fs::remove_file(&path).map_err(|e| format!("Failed to delete workpad: {}", e))?;

    let mut repo = load_repository(&workpad.repo_id)?;
    repo.workpads.retain(|id| id != &workpad_id);
    let _ = save_repository(repo)?;

    let mut global = load_global_state()?;
    if global.active_workpad.as_deref() == Some(&workpad_id) {
        global.active_workpad = None;
    }
    global.total_operations += 1;
    save_global_state(global)?;

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
            .and_then(|mut file| {
                use std::io::Write;
                file.write_all(entry.as_bytes())
            });
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

    let uuid_string = Uuid::new_v4().simple().to_string();
    let repo_id = format!("repo-{}", &uuid_string.chars().take(12).collect::<String>());
    let now = Utc::now().to_rfc3339();

    let repo_path = if let Some(custom) = path.and_then(|p| {
        let trimmed = p.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(trimmed.to_string())
        }
    }) {
        PathBuf::from(custom)
    } else {
        get_repos_dir().join(&repo_id)
    };

    fs::create_dir_all(&repo_path).map_err(|e| {
        format!(
            "Failed to create repository directory {}: {}",
            repo_path.display(),
            e
        )
    })?;

    let repo = RepositoryState {
        repo_id: repo_id.clone(),
        name: trimmed.to_string(),
        path: repo_path.to_string_lossy().to_string(),
        trunk_branch: "main".to_string(),
        current_commit: None,
        created_at: now.clone(),
        updated_at: now.clone(),
        workpads: Vec::new(),
        total_commits: 0,
    };

    let path = get_state_dir()
        .join("repositories")
        .join(format!("{}.json", repo_id));
    write_json(&path, &repo)?;

    let mut global = load_global_state()?;
    global.active_repo = Some(repo.repo_id.clone());
    global.active_workpad = None;
    global.total_operations += 1;
    save_global_state(global)?;

    Ok(repo)
}

#[tauri::command]
pub(crate) fn delete_repository(repo_id: String) -> Result<(), String> {
    let repo = load_repository(&repo_id)?;
    let repo_state_path = get_state_dir()
        .join("repositories")
        .join(format!("{}.json", repo_id));
    fs::remove_file(&repo_state_path).map_err(|e| format!("Failed to remove repository: {}", e))?;

    let workpads_dir = get_state_dir().join("workpads");
    let mut removed_workpads = Vec::new();
    if workpads_dir.exists() {
        for entry in fs::read_dir(&workpads_dir)
            .map_err(|e| format!("Failed to read workpads directory: {}", e))?
        {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                if let Some(workpad) = read_json::<WorkpadState>(&path)? {
                    if workpad.repo_id == repo_id {
                        fs::remove_file(&path).map_err(|e| {
                            format!("Failed to remove workpad {}: {}", workpad.workpad_id, e)
                        })?;
                        removed_workpads.push(workpad.workpad_id);
                    }
                }
            }
        }
    }

    let tests_dir = get_state_dir().join("test_runs");
    if tests_dir.exists() {
        for entry in fs::read_dir(&tests_dir)
            .map_err(|e| format!("Failed to read test runs directory: {}", e))?
        {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                if let Some(test_run) = read_json::<TestRun>(&path)? {
                    if test_run
                        .workpad_id
                        .as_ref()
                        .map(|id| removed_workpads.contains(id))
                        .unwrap_or(false)
                    {
                        fs::remove_file(&path).map_err(|e| {
                            format!("Failed to remove test run {}: {}", test_run.run_id, e)
                        })?;
                    }
                }
            }
        }
    }

    let ai_dir = get_state_dir().join("ai_operations");
    if ai_dir.exists() {
        for entry in fs::read_dir(&ai_dir)
            .map_err(|e| format!("Failed to read AI operations directory: {}", e))?
        {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                if let Some(op) = read_json::<AIOperation>(&path)? {
                    if op
                        .workpad_id
                        .as_ref()
                        .map(|id| removed_workpads.contains(id))
                        .unwrap_or(false)
                    {
                        fs::remove_file(&path).map_err(|e| {
                            format!("Failed to remove AI operation {}: {}", op.operation_id, e)
                        })?;
                    }
                }
            }
        }
    }

    let promotions_dir = get_state_dir().join("promotions");
    if promotions_dir.exists() {
        for entry in fs::read_dir(&promotions_dir)
            .map_err(|e| format!("Failed to read promotions directory: {}", e))?
        {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                if let Some(record) = read_json::<PromotionRecord>(&path)? {
                    if record.repo_id == repo_id {
                        fs::remove_file(&path).map_err(|e| {
                            format!(
                                "Failed to remove promotion record {}: {}",
                                record.record_id, e
                            )
                        })?;
                    }
                }
            }
        }
    }

    let repos_root = get_repos_dir();
    let repo_path = PathBuf::from(&repo.path);
    if repo_path.starts_with(&repos_root) && repo_path.exists() {
        let _ = fs::remove_dir_all(&repo_path);
    }

    let mut global = load_global_state()?;
    if global.active_repo.as_deref() == Some(&repo_id) {
        global.active_repo = None;
    }
    if global
        .active_workpad
        .as_ref()
        .map(|id| removed_workpads.contains(id))
        .unwrap_or(false)
    {
        global.active_workpad = None;
    }
    global.total_operations += 1;
    save_global_state(global)?;

    Ok(())
}
