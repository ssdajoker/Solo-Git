
import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import './styles/App.css'
import CommitGraph from './components/CommitGraph'
import WorkpadList from './components/WorkpadList'
import TestDashboard from './components/TestDashboard'
import StatusBar from './components/StatusBar'

interface GlobalState {
  version: string
  last_updated: string
  active_repo: string | null
  active_workpad: string | null
  session_start: string
  total_operations: number
  total_cost_usd: number
}

function App() {
  const [globalState, setGlobalState] = useState<GlobalState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>Heaven</h1>
        <div className="header-subtitle">Solo Git Interface</div>
      </header>

      {/* Main Layout */}
      <div className="app-main">
        {/* Left Sidebar */}
        <aside className="sidebar-left">
          <CommitGraph repoId={globalState?.active_repo} />
          <WorkpadList repoId={globalState?.active_repo} />
        </aside>

        {/* Center Panel */}
        <main className="center-panel">
          <TestDashboard workpadId={globalState?.active_workpad} />
        </main>

        {/* Right Sidebar (placeholder for AI Assistant) */}
        <aside className="sidebar-right">
          <div className="ai-assistant-placeholder">
            <h3>AI Assistant</h3>
            <p className="muted">Coming soon...</p>
          </div>
        </aside>
      </div>

      {/* Status Bar */}
      <StatusBar globalState={globalState} />
    </div>
  )
}

export default App
