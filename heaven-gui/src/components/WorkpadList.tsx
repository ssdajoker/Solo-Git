
import { useState, useEffect, useCallback } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { useSoloGitOperations } from '../hooks/useSoloGitOperations'
import type { NotificationType, WorkpadState } from '../types/soloGit'
import ConfirmDialog from './ConfirmDialog'
import InputDialog from './InputDialog'
import './WorkpadList.css'

interface WorkpadListProps {
  repoId: string | null | undefined
  activeWorkpadId?: string | null
  onStateUpdated?: () => void
  notify?: (message: string, type?: NotificationType) => void
}

export default function WorkpadList({ repoId, activeWorkpadId, onStateUpdated, notify }: WorkpadListProps) {
  const [workpads, setWorkpads] = useState<WorkpadState[]>([])
  const [loading, setLoading] = useState(false)
  const [pendingAction, setPendingAction] = useState<string | null>(null)
  
  // Dialog states
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showTestDialog, setShowTestDialog] = useState(false)
  const [showPatchDialog, setShowPatchDialog] = useState(false)
  const [showPromoteDialog, setShowPromoteDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showRollbackDialog, setShowRollbackDialog] = useState(false)
  const [currentWorkpadId, setCurrentWorkpadId] = useState<string | null>(null)
  const [patchMessage, setPatchMessage] = useState('')

  const loadWorkpads = useCallback(async () => {
    if (!repoId) return

    try {
      setLoading(true)
      const data = await invoke<WorkpadState[]>('list_workpads', { repoId })
      setWorkpads(data || [])
    } catch (e) {
      console.error('Failed to load workpads:', e)
    } finally {
      setLoading(false)
    }
  }, [repoId])

  useEffect(() => {
    if (repoId) {
      void loadWorkpads()
      const interval = setInterval(() => { void loadWorkpads() }, 3000)
      return () => clearInterval(interval)
    }
  }, [repoId, loadWorkpads])

  const refreshAfterOperation = useCallback(async () => {
    await loadWorkpads()
    if (onStateUpdated) {
      await onStateUpdated()
    }
  }, [loadWorkpads, onStateUpdated])

  const {
    createWorkpad: createWorkpadOperation,
    runTests: runTestsOperation,
    promoteWorkpad: promoteWorkpadOperation,
    applyPatch: applyPatchOperation,
    rollbackWorkpad: rollbackWorkpadOperation,
    deleteWorkpad: deleteWorkpadOperation,
  } = useSoloGitOperations({
    onStateUpdated: refreshAfterOperation,
  })

  const getErrorMessage = (error: unknown) => {
    if (error instanceof Error) {
      return error.message
    }
    if (typeof error === 'string') {
      return error
    }
    try {
      return JSON.stringify(error)
    } catch {
      return 'Unknown error'
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

  const handleCreateWorkpad = () => {
    if (!repoId || pendingAction) return
    setShowCreateDialog(true)
  }

  const confirmCreateWorkpad = async (title: string) => {
    if (!repoId) return
    
    setShowCreateDialog(false)
    try {
      setPendingAction('create')
      notify?.('Creating workpad...', 'info')
      await createWorkpadOperation({ repoId, title: title.trim() })
      notify?.('Workpad created', 'success')
    } catch (e) {
      console.error('Failed to create workpad:', e)
      notify?.(`Failed to create workpad: ${getErrorMessage(e)}`, 'error')
    } finally {
      setPendingAction(null)
    }
  }

  const handleRunTests = (workpadId: string) => {
    if (pendingAction) return
    setCurrentWorkpadId(workpadId)
    setShowTestDialog(true)
  }

  const confirmRunTests = async (target: string) => {
    if (!currentWorkpadId) return
    
    setShowTestDialog(false)
    const actualTarget = target.trim() || 'default'
    
    try {
      setPendingAction(currentWorkpadId)
      notify?.('Running tests...', 'info')
      await runTestsOperation({ workpadId: currentWorkpadId, target: actualTarget })
      notify?.('Tests completed', 'success')
    } catch (e) {
      console.error('Failed to run tests:', e)
      notify?.(`Failed to run tests: ${getErrorMessage(e)}`, 'error')
    } finally {
      setPendingAction(null)
      setCurrentWorkpadId(null)
    }
  }

  const handlePromote = (workpadId: string) => {
    if (pendingAction) return
    setCurrentWorkpadId(workpadId)
    setShowPromoteDialog(true)
  }

  const confirmPromote = async () => {
    if (!currentWorkpadId) return
    
    setShowPromoteDialog(false)
    try {
      setPendingAction(currentWorkpadId)
      notify?.('Promoting workpad...', 'info')
      await promoteWorkpadOperation({ workpadId: currentWorkpadId })
      notify?.('Workpad promoted', 'success')
    } catch (e) {
      console.error('Failed to promote workpad:', e)
      notify?.(`Failed to promote workpad: ${getErrorMessage(e)}`, 'error')
    } finally {
      setPendingAction(null)
      setCurrentWorkpadId(null)
    }
  }

  const handleApplyPatch = (workpadId: string) => {
    if (pendingAction) return
    setCurrentWorkpadId(workpadId)
    setPatchMessage('')
    setShowPatchDialog(true)
  }

  const confirmApplyPatch = async (message: string) => {
    if (!currentWorkpadId) return
    
    setPatchMessage(message)
    setShowPatchDialog(false)
    
    // Now ask for the diff
    const diff = window.prompt('Paste unified diff to apply', 'diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -0,0 +1,2 @@\n+example line\n')
    if (diff === null || !diff.trim()) {
      notify?.('Patch diff is required', 'warning')
      setCurrentWorkpadId(null)
      return
    }

    try {
      setPendingAction(currentWorkpadId)
      notify?.('Applying patch...', 'info')
      await applyPatchOperation({ workpadId: currentWorkpadId, message: message.trim(), diff })
      notify?.('Patch applied', 'success')
    } catch (e) {
      console.error('Failed to apply patch:', e)
      notify?.(`Failed to apply patch: ${getErrorMessage(e)}`, 'error')
    } finally {
      setPendingAction(null)
      setCurrentWorkpadId(null)
    }
  }

  const handleDelete = (workpadId: string) => {
    if (pendingAction) return
    setCurrentWorkpadId(workpadId)
    setShowDeleteDialog(true)
  }

  const confirmDelete = async () => {
    if (!currentWorkpadId) return
    
    setShowDeleteDialog(false)
    try {
      setPendingAction(currentWorkpadId)
      notify?.('Deleting workpad...', 'info')
      await deleteWorkpadOperation({ workpadId: currentWorkpadId })
      notify?.('Workpad deleted', 'success')
    } catch (e) {
      console.error('Failed to delete workpad:', e)
      notify?.(`Failed to delete workpad: ${getErrorMessage(e)}`, 'error')
    } finally {
      setPendingAction(null)
      setCurrentWorkpadId(null)
    }
  }

  const handleRollback = (workpadId: string) => {
    if (pendingAction) return
    setCurrentWorkpadId(workpadId)
    setShowRollbackDialog(true)
  }

  const confirmRollback = async (reason: string) => {
    if (!currentWorkpadId) return
    
    setShowRollbackDialog(false)
    try {
      setPendingAction(currentWorkpadId)
      notify?.('Rolling back workpad...', 'info')
      await rollbackWorkpadOperation({ workpadId: currentWorkpadId, reason: reason || undefined })
      notify?.('Workpad rolled back', 'success')
    } catch (e) {
      console.error('Failed to rollback workpad:', e)
      notify?.(`Failed to rollback workpad: ${getErrorMessage(e)}`, 'error')
    } finally {
      setPendingAction(null)
      setCurrentWorkpadId(null)
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
    <section className="workpad-list" aria-labelledby="workpad-list-heading">
      <div className="workpad-list-header">
        <h3 id="workpad-list-heading">Workpads</h3>
        {loading && (
          <span className="loading-indicator" role="status" aria-live="polite" aria-label="Loading workpads">
            ⟳
          </span>
        )}
        <div className="workpad-header-actions" role="group" aria-label="Workpad actions">
          <button
            className="workpad-create-btn"
            onClick={handleCreateWorkpad}
            disabled={pendingAction !== null}
            title="Create new workpad"
            aria-label="Create new workpad"
            aria-disabled={pendingAction !== null}
          >
            ＋
          </button>
          <button
            className="workpad-refresh-btn"
            onClick={loadWorkpads}
            disabled={pendingAction !== null}
            title="Refresh workpads list"
            aria-label="Refresh workpads list"
            aria-disabled={pendingAction !== null}
          >
            ⟳
          </button>
        </div>
      </div>

      <div 
        className="workpad-items" 
        role="list" 
        aria-label="Workpad list"
        aria-busy={loading}
      >
        {workpads.length === 0 ? (
          <p className="empty-message" role="status">No workpads</p>
        ) : (
          workpads.slice(0, 10).map((workpad) => (
            <article
              key={workpad.workpad_id}
              className={`workpad-item ${workpad.workpad_id === activeWorkpadId ? 'workpad-item-active' : ''}`}
              role="listitem"
              aria-label={`Workpad: ${workpad.title}`}
              aria-current={workpad.workpad_id === activeWorkpadId ? 'true' : undefined}
            >
              <div className="workpad-header">
                <span 
                  className={`workpad-status ${getStatusClass(workpad.status)}`}
                  role="status"
                  aria-label={`Status: ${workpad.status}`}
                >
                  {getStatusIcon(workpad.status)}
                </span>
                <span className="workpad-title">{workpad.title}</span>
                {workpad.workpad_id === activeWorkpadId && (
                  <span className="workpad-active-badge" aria-label="Active workpad">Active</span>
                )}
              </div>
              <div className="workpad-meta" aria-label="Workpad statistics">
                <span className="workpad-patches" aria-label={`${workpad.patches_applied} patches applied`}>
                  {workpad.patches_applied} patches
                </span>
                <span className="workpad-tests" aria-label={`${workpad.test_runs.length} test runs`}>
                  {workpad.test_runs.length} tests
                </span>
              </div>
              <div className="workpad-actions" role="group" aria-label={`Actions for ${workpad.title}`}>
                <button
                  onClick={() => handleRunTests(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                  aria-label={`Run tests for ${workpad.title}`}
                  aria-disabled={pendingAction !== null}
                >
                  ▶ Tests
                </button>
                <button
                  onClick={() => handleApplyPatch(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                  aria-label={`Apply patch to ${workpad.title}`}
                  aria-disabled={pendingAction !== null}
                >
                  ⬆ Patch
                </button>
                <button
                  onClick={() => handlePromote(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                  aria-label={`Promote ${workpad.title} to trunk`}
                  aria-disabled={pendingAction !== null}
                >
                  ⬈ Promote
                </button>
                <button
                  onClick={() => handleRollback(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn"
                  aria-label={`Rollback ${workpad.title}`}
                  aria-disabled={pendingAction !== null}
                >
                  ↺ Rollback
                </button>
                <button
                  onClick={() => handleDelete(workpad.workpad_id)}
                  disabled={pendingAction !== null}
                  className="workpad-action-btn danger"
                  aria-label={`Delete ${workpad.title}`}
                  aria-disabled={pendingAction !== null}
                >
                  ✕ Delete
                </button>
              </div>
            </article>
          ))
        )}
      </div>

      {/* Dialogs */}
      <InputDialog
        isOpen={showCreateDialog}
        title="Create Workpad"
        message="Enter a title for the new workpad"
        placeholder="New feature workpad"
        defaultValue="New feature workpad"
        confirmLabel="Create"
        onConfirm={confirmCreateWorkpad}
        onCancel={() => setShowCreateDialog(false)}
      />

      <InputDialog
        isOpen={showTestDialog}
        title="Run Tests"
        message="Enter test target (leave blank for default)"
        placeholder="default"
        defaultValue="default"
        confirmLabel="Run Tests"
        onConfirm={confirmRunTests}
        onCancel={() => {
          setShowTestDialog(false)
          setCurrentWorkpadId(null)
        }}
      />

      <InputDialog
        isOpen={showPatchDialog}
        title="Apply Patch"
        message="Enter a summary message for this patch"
        placeholder="Apply patch from GUI"
        defaultValue="Apply patch from GUI"
        confirmLabel="Next"
        onConfirm={confirmApplyPatch}
        onCancel={() => {
          setShowPatchDialog(false)
          setCurrentWorkpadId(null)
        }}
      />

      <InputDialog
        isOpen={showRollbackDialog}
        title="Rollback Workpad"
        message="Enter a reason for rollback (optional)"
        placeholder="Reset from GUI"
        defaultValue="Reset from GUI"
        confirmLabel="Rollback"
        onConfirm={confirmRollback}
        onCancel={() => {
          setShowRollbackDialog(false)
          setCurrentWorkpadId(null)
        }}
      />

      <ConfirmDialog
        isOpen={showPromoteDialog}
        title="Promote Workpad"
        message="Are you sure you want to promote this workpad to trunk? This action cannot be undone."
        confirmLabel="Promote"
        cancelLabel="Cancel"
        variant="default"
        onConfirm={confirmPromote}
        onCancel={() => {
          setShowPromoteDialog(false)
          setCurrentWorkpadId(null)
        }}
      />

      <ConfirmDialog
        isOpen={showDeleteDialog}
        title="Delete Workpad"
        message="Are you sure you want to delete this workpad and its history? This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => {
          setShowDeleteDialog(false)
          setCurrentWorkpadId(null)
        }}
      />
    </section>
  )
}
