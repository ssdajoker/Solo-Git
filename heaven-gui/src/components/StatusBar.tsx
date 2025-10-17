
import './StatusBar.css'

interface GlobalState {
  version: string
  active_repo: string | null
  active_workpad: string | null
  total_operations: number
  total_cost_usd: number
}

interface StatusBarProps {
  globalState: GlobalState | null
}

export default function StatusBar({ globalState }: StatusBarProps) {
  if (!globalState) {
    return (
      <footer className="status-bar">
        <span className="status-item">No state</span>
      </footer>
    )
  }

  return (
    <footer className="status-bar">
      <div className="status-left">
        <span className="status-item">
          📁 {globalState.active_repo ? globalState.active_repo.slice(0, 12) : 'No repo'}
        </span>
        <span className="status-separator">|</span>
        <span className="status-item">
          🏷️ {globalState.active_workpad ? globalState.active_workpad.slice(0, 12) : 'No workpad'}
        </span>
      </div>
      
      <div className="status-right">
        <span className="status-item">
          🤖 {globalState.total_operations} ops
        </span>
        <span className="status-separator">|</span>
        <span className="status-item">
          💰 ${globalState.total_cost_usd.toFixed(2)}
        </span>
      </div>
    </footer>
  )
}
