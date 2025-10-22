import { useState, useEffect, useCallback, useMemo } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { useKeyboardShortcuts, KeyboardShortcut } from './hooks/useKeyboardShortcuts'
import ErrorBoundary from './components/ErrorBoundary'
import CommitGraph from './components/CommitGraph'
import WorkpadList from './components/WorkpadList'
import TestDashboard from './components/TestDashboard'
import StatusBar from './components/StatusBar'
import CodeViewer from './components/CodeViewer'
import FileBrowser from './components/FileBrowser'
import AIAssistant from './components/AIAssistant'
import CommandPalette from './components/CommandPalette'
import Settings from './components/Settings'
import NotificationSystem, { Notification } from './components/NotificationSystem'
import KeyboardShortcutsHelp from './components/KeyboardShortcutsHelp'
import { useSoloGitOperations } from './hooks/useSoloGitOperations'
import type { GlobalState } from './types/soloGit'
import './styles/App.css'

type ViewMode = 'idle' | 'navigation' | 'planning' | 'coding' | 'commit'

function App() {
  const [globalState, setGlobalState] = useState<GlobalState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('idle')
  
  // UI State
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [showLeftSidebar, setShowLeftSidebar] = useState(true)
  const [showRightSidebar, setShowRightSidebar] = useState(false)
  const [showCommandPalette, setShowCommandPalette] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])

  const loadState = useCallback(async () => {
    try {
      const state = await invoke<GlobalState>('read_global_state')
      setGlobalState(state)
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadState()

    // Refresh state every 3 seconds
    const interval = setInterval(() => {
      void loadState()
    }, 3000)
    return () => clearInterval(interval)
  }, [loadState])

  const addNotification = (message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    const notification: Notification = {
      id: Date.now().toString(),
      type,
      message,
      duration: 5000,
    }
    setNotifications(prev => [...prev, notification])
  }

  const dismissNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const ensureActiveRepo = () => {
    if (!globalState?.active_repo) {
      addNotification('No active repository selected', 'warning')
      return null
    }
    return globalState.active_repo
  }

  const ensureActiveWorkpad = () => {
    if (!globalState?.active_workpad) {
      addNotification('No active workpad selected', 'warning')
      return null
    }
    return globalState.active_workpad
  }

  const {
    createRepository: createRepositoryOperation,
    deleteRepository: deleteRepositoryOperation,
    createWorkpad: createWorkpadOperation,
    runTests: runTestsOperation,
    promoteWorkpad: promoteWorkpadOperation,
    applyPatch: applyPatchOperation,
    rollbackWorkpad: rollbackWorkpadOperation,
    deleteWorkpad: deleteWorkpadOperation,
  } = useSoloGitOperations({
    onStateUpdated: loadState,
  })

  const getErrorMessage = useCallback((error: unknown) => {
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
  }, [])

  const createRepository = async () => {
    const name = window.prompt('Repository name', 'new-repository')
    if (!name || !name.trim()) {
      return
    }

    const path = window.prompt('Optional repository path (leave blank for default)', '')

    try {
      addNotification('Creating repository...', 'info')
      await createRepositoryOperation({
        name: name.trim(),
        path: path && path.trim() ? path.trim() : null,
      })
      addNotification('Repository created', 'success')
    } catch (e) {
      addNotification(`Failed to create repository: ${getErrorMessage(e)}`, 'error')
    }
  }

  const deleteRepository = async () => {
    const repoId = ensureActiveRepo()
    if (!repoId) return

    if (!window.confirm('Delete the active repository and its data?')) {
      return
    }

    try {
      addNotification('Deleting repository...', 'info')
      await deleteRepositoryOperation({ repoId })
      addNotification('Repository deleted', 'success')
    } catch (e) {
      addNotification(`Failed to delete repository: ${getErrorMessage(e)}`, 'error')
    }
  }

  const createWorkpad = async () => {
    const repoId = ensureActiveRepo()
    if (!repoId) return

    const title = window.prompt('Workpad title', 'New workpad')
    if (!title || !title.trim()) return

    try {
      addNotification('Creating workpad...', 'info')
      await createWorkpadOperation({ repoId, title: title.trim() })
      addNotification('Workpad created', 'success')
    } catch (e) {
      addNotification(`Failed to create workpad: ${getErrorMessage(e)}`, 'error')
    }
  }

  const runTestsOnWorkpad = useCallback(async (workpadId: string, target: string) => {
    await runTestsOperation({ workpadId, target })
  }, [runTestsOperation])

  const runTestsForActive = async (target?: string) => {
    const workpadId = ensureActiveWorkpad()
    if (!workpadId) return

    const promptResult = target ?? window.prompt('Test target (leave blank for default)', 'default') ?? 'default'
    const actualTarget = promptResult && promptResult.trim() ? promptResult.trim() : 'default'

    try {
      addNotification('Running tests...', 'info')
      await runTestsOnWorkpad(workpadId, actualTarget)
      addNotification('Tests completed', 'success')
    } catch (e) {
      addNotification(`Failed to run tests: ${getErrorMessage(e)}`, 'error')
    }
  }

  const promoteActiveWorkpad = async () => {
    const workpadId = ensureActiveWorkpad()
    if (!workpadId) return

    if (!window.confirm('Promote the active workpad?')) return

    try {
      addNotification('Promoting workpad...', 'info')
      await promoteWorkpadOperation({ workpadId })
      addNotification('Workpad promoted', 'success')
    } catch (e) {
      addNotification(`Failed to promote workpad: ${getErrorMessage(e)}`, 'error')
    }
  }

  const applyPatchToActive = async () => {
    const workpadId = ensureActiveWorkpad()
    if (!workpadId) return

    const message = window.prompt('Patch summary message', 'Apply patch from GUI')
    if (message === null) return

    const diff = window.prompt('Paste unified diff to apply', 'diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -0,0 +1,2 @@\n+example line\n')
    if (diff === null || !diff.trim()) {
      addNotification('Patch diff is required', 'warning')
      return
    }

    try {
      addNotification('Applying patch...', 'info')
      await applyPatchOperation({ workpadId, message: message.trim(), diff })
      addNotification('Patch applied', 'success')
    } catch (e) {
      addNotification(`Failed to apply patch: ${getErrorMessage(e)}`, 'error')
    }
  }

  const rollbackActiveWorkpad = async () => {
    const workpadId = ensureActiveWorkpad()
    if (!workpadId) return

    const reason = window.prompt('Rollback reason (optional)', 'Reset from GUI')

    try {
      addNotification('Rolling back workpad...', 'info')
      await rollbackWorkpadOperation({ workpadId, reason: reason ?? undefined })
      addNotification('Workpad rolled back', 'success')
    } catch (e) {
      addNotification(`Failed to rollback workpad: ${getErrorMessage(e)}`, 'error')
    }
  }

  const deleteActiveWorkpad = async () => {
    const workpadId = ensureActiveWorkpad()
    if (!workpadId) return

    if (!window.confirm('Delete the active workpad and its state?')) return

    try {
      addNotification('Deleting workpad...', 'info')
      await deleteWorkpadOperation({ workpadId })
      addNotification('Workpad deleted', 'success')
    } catch (e) {
      addNotification(`Failed to delete workpad: ${getErrorMessage(e)}`, 'error')
    }
  }

  // Define commands for Command Palette
  const commands = useMemo(() => ([
    {
      id: 'toggle-command-palette',
      label: 'Toggle Command Palette',
      description: 'Open or close the command palette',
      category: 'Navigation',
      shortcut: 'Cmd+P',
      action: () => setShowCommandPalette(prev => !prev),
    },
    {
      id: 'toggle-left-sidebar',
      label: 'Toggle Left Sidebar',
      description: 'Show or hide file browser and commit graph',
      category: 'Navigation',
      shortcut: 'Cmd+B',
      action: () => setShowLeftSidebar(prev => !prev),
    },
    {
      id: 'toggle-right-sidebar',
      label: 'Toggle AI Assistant',
      description: 'Show or hide AI assistant panel',
      category: 'AI',
      shortcut: 'Cmd+/',
      action: () => setShowRightSidebar(prev => !prev),
    },
    {
      id: 'open-settings',
      label: 'Open Settings',
      description: 'Configure Heaven Interface settings',
      category: 'Settings',
      shortcut: 'Cmd+,',
      action: () => setShowSettings(true),
    },
    {
      id: 'show-shortcuts',
      label: 'Show Keyboard Shortcuts',
      description: 'Display all available keyboard shortcuts',
      category: 'Help',
      shortcut: '?',
      action: () => setShowShortcutsHelp(true),
    },
    {
      id: 'focus-editor',
      label: 'Focus Editor',
      description: 'Focus on the code editor (Zen mode)',
      category: 'Editor',
      shortcut: 'Cmd+E',
      action: () => {
        setShowLeftSidebar(false)
        setShowRightSidebar(false)
        setViewMode('coding')
      },
    },
    {
      id: 'run-tests',
      label: 'Run Tests',
      description: 'Run tests for active workpad',
      category: 'Testing',
      shortcut: 'Cmd+T',
      action: () => {
        void runTestsForActive('default')
      },
    },
    {
      id: 'create-workpad',
      label: 'Create Workpad',
      description: 'Create a new workpad in the active repository',
      category: 'Workpads',
      action: () => {
        void createWorkpad()
      },
    },
    {
      id: 'promote-workpad',
      label: 'Promote Workpad',
      description: 'Promote the active workpad to trunk',
      category: 'Workpads',
      action: () => {
        void promoteActiveWorkpad()
      },
    },
    {
      id: 'apply-patch-workpad',
      label: 'Apply Patch to Workpad',
      description: 'Apply a diff patch to the active workpad',
      category: 'Workpads',
      action: () => {
        void applyPatchToActive()
      },
    },
    {
      id: 'rollback-workpad',
      label: 'Rollback Workpad',
      description: 'Rollback the active workpad to its base commit',
      category: 'Workpads',
      action: () => {
        void rollbackActiveWorkpad()
      },
    },
    {
      id: 'delete-workpad',
      label: 'Delete Active Workpad',
      description: 'Delete the active workpad from state',
      category: 'Workpads',
      action: () => {
        void deleteActiveWorkpad()
      },
    },
    {
      id: 'create-repository',
      label: 'Create Repository',
      description: 'Initialize a new repository in state',
      category: 'Repositories',
      action: () => {
        void createRepository()
      },
    },
    {
      id: 'delete-repository',
      label: 'Delete Active Repository',
      description: 'Remove the active repository from state',
      category: 'Repositories',
      action: () => {
        void deleteRepository()
      },
    },
  ]), [
    runTestsForActive,
    createWorkpad,
    promoteActiveWorkpad,
    applyPatchToActive,
    rollbackActiveWorkpad,
    deleteActiveWorkpad,
    createRepository,
    deleteRepository,
  ])

  // Define keyboard shortcuts
  const shortcuts: KeyboardShortcut[] = [
    {
      key: 'p',
      cmd: true,
      action: () => setShowCommandPalette(prev => !prev),
      description: 'Toggle Command Palette',
    },
    {
      key: 'k',
      cmd: true,
      action: () => setShowCommandPalette(true),
      description: 'Quick Search',
    },
    {
      key: 'b',
      cmd: true,
      action: () => setShowLeftSidebar(prev => !prev),
      description: 'Toggle Left Sidebar',
    },
    {
      key: '/',
      cmd: true,
      action: () => setShowRightSidebar(prev => !prev),
      description: 'Toggle AI Assistant',
    },
    {
      key: ',',
      cmd: true,
      action: () => setShowSettings(true),
      description: 'Open Settings',
    },
    {
      key: 'e',
      cmd: true,
      action: () => {
        setShowLeftSidebar(false)
        setShowRightSidebar(false)
        setViewMode('coding')
      },
      description: 'Focus Editor (Zen Mode)',
    },
    {
      key: 't',
      cmd: true,
      action: () => {
        void runTestsForActive('default')
      },
      description: 'Run Tests',
    },
    {
      key: '?',
      action: () => setShowShortcutsHelp(true),
      description: 'Show Keyboard Shortcuts Help',
    },
    {
      key: 'Escape',
      action: () => {
        setShowCommandPalette(false)
        setShowSettings(false)
        setShowShortcutsHelp(false)
      },
      description: 'Close Modals',
    },
  ]

  useKeyboardShortcuts(shortcuts)

  if (loading) {
    return (
      <div className="app-container loading">
        <div className="spinner"></div>
        <p>Loading Heaven Interface...</p>
      </div>
    )
  }

  if (error && !globalState) {
    return (
      <div className="app-container error">
        <div className="error-panel">
          <h2>⚠️ No State Found</h2>
          <p>{error}</p>
          <p className="hint">Initialize Solo Git first:</p>
          <code>evogitctl repo init --zip &lt;file&gt;</code>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className={`app-container view-mode-${viewMode}`}>
        {/* Header */}
        <header className="app-header" role="banner">
          <h1>Heaven</h1>
          <div className="header-subtitle" aria-label="Application subtitle">Solo Git Interface</div>
          <div className="header-actions">
            <button
              className="icon-btn"
              onClick={() => setShowShortcutsHelp(true)}
              title="Keyboard Shortcuts (?)"
              aria-label="Show keyboard shortcuts">
              ⌨️
            </button>
            <button
              className="icon-btn"
              onClick={() => setShowSettings(true)}
              title="Settings (Cmd+,)"
              aria-label="Open settings">
              ⚙️
            </button>
            <button
              className="icon-btn"
              onClick={() => { void createRepository() }}
              title="Create Repository"
              aria-label="Create repository">
              🆕
            </button>
            <button
              className="icon-btn"
              onClick={() => { void deleteRepository() }}
              title="Delete Repository"
              aria-label="Delete repository">
              🗑️
            </button>
          </div>
        </header>

        {/* Main Layout */}
        <div className="app-main">
          {/* Left Sidebar */}
          {showLeftSidebar && (
            <aside className="sidebar-left">
              <FileBrowser
                repoId={globalState?.active_repo ?? null}
                onFileSelect={setSelectedFile}
                selectedFile={selectedFile}
              />
              <CommitGraph repoId={globalState?.active_repo ?? null} />
              <WorkpadList
                repoId={globalState?.active_repo ?? null}
                activeWorkpadId={globalState?.active_workpad ?? null}
                notify={addNotification}
                onStateUpdated={() => { void loadState() }}
              />
            </aside>
          )}

          {/* Center Panel */}
          <main className="center-panel">
            <div className="center-top">
              <CodeViewer 
                repoId={globalState?.active_repo ?? null}
                filePath={selectedFile}
              />
            </div>
            <div className="center-bottom">
              <TestDashboard
                workpadId={globalState?.active_workpad ?? null}
                notify={addNotification}
                onStateUpdated={() => { void loadState() }}
                onRunTests={runTestsOnWorkpad}
              />
            </div>
          </main>

          {/* Right Sidebar - AI Assistant */}
          <AIAssistant 
            repoId={globalState?.active_repo ?? null}
            workpadId={globalState?.active_workpad ?? null}
            collapsed={!showRightSidebar}
            onToggle={() => setShowRightSidebar(prev => !prev)}
          />
        </div>

        {/* Status Bar */}
        <StatusBar globalState={globalState} />

        {/* Modals and Overlays */}
        <CommandPalette 
          isOpen={showCommandPalette}
          onClose={() => setShowCommandPalette(false)}
          commands={commands}
        />

        <Settings 
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
        />

        <KeyboardShortcutsHelp 
          isOpen={showShortcutsHelp}
          onClose={() => setShowShortcutsHelp(false)}
          shortcuts={shortcuts}
        />

        <NotificationSystem 
          notifications={notifications}
          onDismiss={dismissNotification}
        />
      </div>
    </ErrorBoundary>
  )
}

export default App
