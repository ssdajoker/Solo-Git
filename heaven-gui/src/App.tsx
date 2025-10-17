import { useState, useEffect } from 'react'
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
import './styles/App.css'

interface GlobalState {
  version: string
  last_updated: string
  active_repo: string | null
  active_workpad: string | null
  session_start: string
  total_operations: number
  total_cost_usd: number
}

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

  useEffect(() => {
    loadState()
    
    // Refresh state every 3 seconds
    const interval = setInterval(loadState, 3000)
    return () => clearInterval(interval)
  }, [])

  const loadState = async () => {
    try {
      const state = await invoke<GlobalState>('read_global_state')
      setGlobalState(state)
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

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

  // Define commands for Command Palette
  const commands: any[] = [
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
        if (globalState?.active_workpad) {
          addNotification('Running tests...', 'info')
          // TODO: Invoke test run
        } else {
          addNotification('No active workpad', 'warning')
        }
      },
    },
  ]

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
        if (globalState?.active_workpad) {
          addNotification('Running tests...', 'info')
        }
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
        <header className="app-header">
          <h1>Heaven</h1>
          <div className="header-subtitle">Solo Git Interface</div>
          <div className="header-actions">
            <button 
              className="icon-btn" 
              onClick={() => setShowShortcutsHelp(true)}
              title="Keyboard Shortcuts (?)">
              ⌨️
            </button>
            <button 
              className="icon-btn" 
              onClick={() => setShowSettings(true)}
              title="Settings (Cmd+,)">
              ⚙️
            </button>
          </div>
        </header>

        {/* Main Layout */}
        <div className="app-main">
          {/* Left Sidebar */}
          {showLeftSidebar && (
            <aside className="sidebar-left">
              <FileBrowser 
                repoId={globalState?.active_repo} 
                onFileSelect={setSelectedFile}
                selectedFile={selectedFile}
              />
              <CommitGraph repoId={globalState?.active_repo} />
              <WorkpadList repoId={globalState?.active_repo} />
            </aside>
          )}

          {/* Center Panel */}
          <main className="center-panel">
            <div className="center-top">
              <CodeViewer 
                repoId={globalState?.active_repo}
                filePath={selectedFile}
              />
            </div>
            <div className="center-bottom">
              <TestDashboard workpadId={globalState?.active_workpad} />
            </div>
          </main>

          {/* Right Sidebar - AI Assistant */}
          <AIAssistant 
            repoId={globalState?.active_repo}
            workpadId={globalState?.active_workpad}
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
