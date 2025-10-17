
import './TestDashboard.css'

interface TestDashboardProps {
  workpadId: string | null | undefined
}

export default function TestDashboard({ workpadId }: TestDashboardProps) {
  return (
    <div className="test-dashboard">
      <div className="dashboard-header">
        <h2>Test Dashboard</h2>
        {workpadId && <span className="workpad-badge">{workpadId.slice(0, 8)}</span>}
      </div>
      
      <div className="dashboard-content">
        {!workpadId ? (
          <div className="empty-state">
            <p>No active workpad</p>
            <p className="hint">Create a workpad to see test results</p>
          </div>
        ) : (
          <div className="placeholder">
            <p className="muted">Test dashboard coming soon...</p>
            <ul className="feature-list">
              <li>✓ Pass/fail trends over time</li>
              <li>✓ Average test duration</li>
              <li>✓ Flaky test detection</li>
              <li>✓ Coverage reports</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
