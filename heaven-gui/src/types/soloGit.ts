export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface GlobalState {
  version: string
  last_updated: string
  active_repo: string | null
  active_workpad: string | null
  session_start: string
  total_operations: number
  total_cost_usd: number
}

export interface RepositoryState {
  repo_id: string
  name: string
  path: string
  trunk_branch: string
  current_commit: string | null
  created_at: string
  updated_at: string
  workpads: string[]
  total_commits: number
}

export interface WorkpadState {
  workpad_id: string
  repo_id: string
  title: string
  status: string
  branch_name: string
  base_commit: string
  current_commit: string | null
  created_at: string
  updated_at: string
  promoted_at: string | null
  test_runs: string[]
  ai_operations: string[]
  patches_applied: number
  files_changed: string[]
}

export interface TestRun {
  run_id: string
  workpad_id: string | null
  target: string
  status: string
  started_at: string
  completed_at: string | null
  total_tests: number
  passed: number
  failed: number
  skipped: number
  duration_ms: number
}

export interface PromotionRecord {
  record_id: string
  repo_id: string
  workpad_id: string
  decision: string
  can_promote: boolean
  auto_promote_requested: boolean
  promoted: boolean
  commit_hash: string | null
  message: string
  test_run_id: string | null
  ci_status: string | null
  ci_message: string | null
  created_at: string
}
