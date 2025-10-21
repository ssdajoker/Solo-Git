
import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import './WorkpadList.css'

type NotificationType = 'success' | 'error' | 'warning' | 'info'

interface Workpad {
  workpad_id: string
  repo_id: string
  title: string
  status: string
  branch_name: string
  base_commit: string
  patches_applied: number
  test_runs: string[]
  created_at: string
}

interface WorkpadListProps {
  repoId: string | null | undefined
  activeWorkpadId?: string | null
  onStateUpdated?: () => void
  notify?: (message: string, type?: NotificationType) => void
}

export default function WorkpadList({ repoId, activeWorkpadId, onStateUpdated, notify }: WorkpadListProps) {
  const [workpads, setWorkpads] = useState<Workpad[]>([])
  const [loading, setLoading] = useState(false)
  const [pendingAction, setPendingAction] = useState<string | null>(null)

  useEffect(() => {
    if (repoId) {
      loadWorkpads()
      const interval = setInterval(loadWorkpads, 3000)
      return () => clearInterval(interval)
    }
  }, [repoId])

  const loadWorkpads = async () => {
    if (!repoId) return

    try {
      setLoading(true)
      const data = await invoke<Workpad[]>('list_workpads', { repoId })
      setWorkpads(data || [])
    } catch (e) {
      console.error('Failed to load workpads:', e)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    if (status === 'passed' || status === 'promoted') return '✓'
    if (status === 'failed') return '✗'
    if (status === 'testing') return '◉'
    return '○'
  }

  const getStatusClass = (status: string) => {
    return `status-${status.toLowerCase()}`
  }

  const handleCreateWorkpad = async () => {
    if (!repoId || pendingAction) return

    const title = window.prompt('Enter a title for the new workpad', 'New feature workpad')
    if (!title || !title.trim()) {
      return
    }

    try {
      setPendingAction('create')
      notify?.('Creating workpad...', 'info')
      await invoke<Workpad>('create_workpad', { repoId, title: title.trim() })
      notify?.('Workpad created', 'success')
      await loadWorkpads()
      onStateUpdated?.()
    } catch (e) {
      console.error('Failed to create workpad:', e)
      notify?.(`Failed to create workpad: ${e}`, 'error')
    } finally {
      setPendingAction(null)
    }
  }

  const handleRunTests = async (workpadId: string) => {
    if (pendingAction) return

    const target = window.prompt('Test target (leave blank for default)', 'default') || 'default'

    try {
      setPendingAction(workpadId)
      notify?.('Running tests...', 'info')
      await invoke('run_tests', { workpadId, target })
      notify?.('Tests completed', 'success')
      await loadWorkpads()
      onStateUpdated?.()
    } catch (e) {
      console.error('Failed to run tests:', e)
      notify?.(`Failed to run tests: ${e}`, 'error')
    } finally {
      setPendingAction(null)
    }
  }

  const handlePromote = async (workpadId: string) => {
    if (pendingAction) return

    const confirm = window.confirm('Promote this workpad to trunk?')
    if (!confirm) return

    try {
      setPendingAction(workpadId)
      notify?.('Promoting workpad...', 'info')
      await invoke('promote_workpad', { workpadId })
      notify?.('Workpad promoted', 'success')
      await loadWorkpads()
      onStateUpdated?.()
    } catch (e) {
      console.error('Failed to promote workpad:', e)
      notify?.(`Failed to promote workpad: ${e}`, 'error')
    } finally {
      setPendingAction(null)
    }
  }

  const handleApplyPatch = async (workpadId: string) => {
    if (pendingAction) return

    const message = window.prompt('Patch summary message', 'Apply patch from GUI')
    if (message === null) return

    const diff = window.prompt('Paste unified diff to apply', 'diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -0,0 +1,2 @@\n+example line\n')
    if (diff === null || !diff.trim()) {
      notify?.('Patch diff is required', 'warning')
      return
    }

    try {
      setPendingAction(workpadId)
      notify?.('Applying patch...', 'info')
      await invoke('apply_patch', { workpadId, message: message.trim(), diff })
      notify?.('Patch applied', 'success')
      await loadWorkpads()
      onStateUpdated?.()
    } catch (e) {
      console.error('Failed to apply patch:', e)
      notify?.(`Failed to apply patch: ${e}`, 'error')
    } finally {
      setPendingAction(null)
    }
  }

  const handleDelete = async (workpadId: string) => {
    if (pendingAction) return

    const confirm = window.confirm('Delete this workpad and its history?')
    if (!confirm) return

    try {
      setPendingAction(workpadId)
      notify?.('Deleting workpad...', 'info')
      await invoke('delete_workpad', { workpadId })
      notify?.('Workpad deleted', 'success')
      await loadWorkpads()
      onStateUpdated?.()
    } catch (e) {
      console.error('Failed to delete workpad:', e)
      notify?.(`Failed to delete workpad: ${e}`, 'error')
    } finally {
      setPendingAction(null)
    }
  }

  const handleRollback = async (workpadId: string) => {
    if (pendingAction) return

    const reason = window.prompt('Rollback reason (optional)', 'Reset from GUI')

    try {
      setPendingAction(workpadId)
      notify?.('Rolling back workpad...', 'info')
      await invoke('rollback_workpad', { workpadId, reason: reason ?? undefined })
      notify?.('Workpad rolled back', 'success')
      await loadWorkpads()
      onStateUpdated?.()
    } catch (e) {
      console.error('Failed to rollback workpad:', e)
      notify?.(`Failed to rollback workpad: ${e}`, 'error')
    } finally {
      setPendingAction(null)
    }
  }

  if (!repoId) {
    return (
      <div className="workpad-list empty">
        <h3>Workpads</h3>
        <p className="empty-message">No repository selected</p>
      </div>
    )
  }

  return (
    <div className="workpad-list">
      <div className="workpad-list-header">
        <h3>Workpads</h3>
        {loading && <span className="loading-indicator">⟳</span>}
        <div className="workpad-header-actions">
          <button
            className="workpad-create-btn"
            onClick={handleCreateWorkpad}
            disabled={pendingAction !== null}
            title="Create workpad"
          >
            ＋
          </button>
          <button
            className="workpad-refresh-btn"
            onClick={loadWorkpads}
            disabled={pendingAction !== null}
            title="Refresh workpads"
          >
            ⟳
          </button>
        </div>
      </div>

      <div className="workpad-items">
        {workpads.length === 0 ? (
          <p className="empty-message">No workpads</p>
        ) : (
          workpads.slice(0, 10).map((workpad) => (
            <div
              key={workpad.workpad_id}
              className={`workpad-item ${workpad.workpad_id === activeWorkpadId ? 'workpad-item-active' : ''}`}
            >
              <div className="workpad-header">
                <span className={`workpad-status ${getStatusClass(workpad.status)}`}>
                  {getStatusIcon(workpad.status)}
                </span>
                <span className="workpad-title">{workpad.title}</span>
                {workpad.workpad_id === activeWorkpadId && (
                  <span className="workpad-active-badge">Active</span>
                )}
              </div>
              <div className="workpad-meta">
                <span className="workpad-patches">{workpad.patches_applied} patches</span>
                <span className="workpad-tests">{workpad.test_runs.length} tests</span>
              </div>
              <div className="workpad-actions">
                <button
                  onClick={() => handleRunTests(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                >
                  ▶ Tests
                </button>
                <button
                  onClick={() => handleApplyPatch(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                >
                  ⬆ Patch
                </button>
                <button
                  onClick={() => handlePromote(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                >
                  ⬈ Promote
                </button>
                <button
                  onClick={() => handleRollback(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                >
                  ↺ Rollback
                </button>
                <button
                  onClick={() => handleDelete(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn danger"
                >
                  ✕ Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
