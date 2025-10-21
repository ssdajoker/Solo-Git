
import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import './TestDashboard.css'

type NotificationType = 'success' | 'error' | 'warning' | 'info'

interface TestRun {
  test_run_id: string
  workpad_id: string
  status: 'passed' | 'failed' | 'running'
  total_tests: number
  passed_tests: number
  failed_tests: number
  duration_ms: number
  timestamp: string
}

interface TestDashboardProps {
  workpadId: string | null | undefined
  notify?: (message: string, type?: NotificationType) => void
  onStateUpdated?: () => void
  onRunTests?: (workpadId: string, target: string) => Promise<void>
}

export default function TestDashboard({ workpadId, notify, onStateUpdated, onRunTests }: TestDashboardProps) {
  const [testRuns, setTestRuns] = useState<TestRun[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'trends' | 'duration' | 'coverage'>('trends')
  const [runningTests, setRunningTests] = useState(false)

  useEffect(() => {
    if (workpadId) {
      loadTestRuns()
      const interval = setInterval(loadTestRuns, 5000)
      return () => clearInterval(interval)
    }
  }, [workpadId])

  const loadTestRuns = async () => {
    if (!workpadId) return
    
    try {
      setLoading(true)
      const runs = await invoke<TestRun[]>('list_test_runs', { workpadId })
      setTestRuns(runs || [])
    } catch (e) {
      console.error('Failed to load test runs:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleRunTests = async () => {
    if (!workpadId || runningTests) {
      if (!workpadId) {
        notify?.('No active workpad', 'warning')
      }
      return
    }

    const target = window.prompt('Test target (leave blank for default)', 'default') || 'default'

    try {
      setRunningTests(true)
      notify?.('Running tests...', 'info')
      if (onRunTests) {
        await onRunTests(workpadId, target)
      } else {
        await invoke('run_tests', { workpadId, target })
      }
      notify?.('Tests completed', 'success')
      await loadTestRuns()
      onStateUpdated?.()
    } catch (e) {
      console.error('Failed to run tests:', e)
      notify?.(`Failed to run tests: ${e}`, 'error')
    } finally {
      setRunningTests(false)
    }
  }

  const calculateStats = () => {
    if (testRuns.length === 0) return { totalRuns: 0, passRate: 0, avgDuration: 0 }
    
    const totalRuns = testRuns.length
    const passedRuns = testRuns.filter(r => r.status === 'passed').length
    const passRate = (passedRuns / totalRuns) * 100
    const avgDuration = testRuns.reduce((sum, r) => sum + r.duration_ms, 0) / totalRuns
    
    return { totalRuns, passRate, avgDuration }
  }

  const prepareChartData = () => {
    return testRuns.slice(-10).map((run, index) => ({
      name: `Run ${index + 1}`,
      timestamp: new Date(run.timestamp).toLocaleTimeString(),
      passed: run.passed_tests,
      failed: run.failed_tests,
      duration: run.duration_ms / 1000, // Convert to seconds
      passRate: (run.passed_tests / run.total_tests) * 100,
    }))
  }

  const stats = calculateStats()
  const chartData = prepareChartData()

  return (
    <div className="test-dashboard">
      <div className="dashboard-header">
        <h2>Test Dashboard</h2>
        {workpadId && <span className="workpad-badge">{workpadId.slice(0, 8)}</span>}
        <div className="dashboard-header-actions">
          <button
            className="run-tests-btn"
            onClick={handleRunTests}
            disabled={!workpadId || runningTests}
          >
            {runningTests ? 'Running…' : 'Run Tests'}
          </button>
          {(loading || runningTests) && <span className="loading-indicator">⟳</span>}
        </div>
      </div>
      
      <div className="dashboard-content">
        {!workpadId ? (
          <div className="empty-state">
            <p>No active workpad</p>
            <p className="hint">Create a workpad to see test results</p>
          </div>
        ) : testRuns.length === 0 ? (
          <div className="empty-state">
            <p>No test runs yet</p>
            <p className="hint">Run tests to see metrics</p>
          </div>
        ) : (
          <>
            <div className="dashboard-stats">
              <div className="stat-card">
                <h4>Total Runs</h4>
                <p className="stat-value">{stats.totalRuns}</p>
              </div>
              <div className="stat-card">
                <h4>Pass Rate</h4>
                <p className="stat-value stat-success">{stats.passRate.toFixed(1)}%</p>
              </div>
              <div className="stat-card">
                <h4>Avg Duration</h4>
                <p className="stat-value">{(stats.avgDuration / 1000).toFixed(2)}s</p>
              </div>
            </div>

            <div className="dashboard-tabs">
              <button 
                className={activeTab === 'trends' ? 'active' : ''} 
                onClick={() => setActiveTab('trends')}
              >
                Pass/Fail Trends
              </button>
              <button 
                className={activeTab === 'duration' ? 'active' : ''} 
                onClick={() => setActiveTab('duration')}
              >
                Duration
              </button>
              <button 
                className={activeTab === 'coverage' ? 'active' : ''} 
                onClick={() => setActiveTab('coverage')}
              >
                Coverage
              </button>
            </div>

            <div className="dashboard-charts">
              {activeTab === 'trends' && (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="name" stroke="#6A737D" />
                    <YAxis stroke="#6A737D" />
                    <Tooltip 
                      contentStyle={{ background: '#1E1E1E', border: '1px solid #333' }}
                      labelStyle={{ color: '#DDDDDD' }}
                    />
                    <Legend wrapperStyle={{ color: '#DDDDDD' }} />
                    <Bar dataKey="passed" fill="#98C379" name="Passed" />
                    <Bar dataKey="failed" fill="#E06C75" name="Failed" />
                  </BarChart>
                </ResponsiveContainer>
              )}

              {activeTab === 'duration' && (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="name" stroke="#6A737D" />
                    <YAxis stroke="#6A737D" />
                    <Tooltip 
                      contentStyle={{ background: '#1E1E1E', border: '1px solid #333' }}
                      labelStyle={{ color: '#DDDDDD' }}
                    />
                    <Legend wrapperStyle={{ color: '#DDDDDD' }} />
                    <Line 
                      type="monotone" 
                      dataKey="duration" 
                      stroke="#61AFEF" 
                      strokeWidth={2}
                      name="Duration (s)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}

              {activeTab === 'coverage' && (
                <div className="coverage-placeholder">
                  <p className="muted">Coverage data coming soon...</p>
                  <p className="hint">Integrate with your test coverage tool</p>
                </div>
              )}
            </div>

            <div className="recent-runs">
              <h4>Recent Test Runs</h4>
              <div className="runs-list">
                {testRuns.slice(0, 5).map((run) => (
                  <div key={run.test_run_id} className="run-item">
                    <span className={`run-status run-status-${run.status}`}>
                      {run.status === 'passed' ? '✓' : run.status === 'failed' ? '✗' : '◉'}
                    </span>
                    <div className="run-info">
                      <span className="run-tests">
                        {run.passed_tests}/{run.total_tests} passed
                      </span>
                      <span className="run-duration">
                        {(run.duration_ms / 1000).toFixed(2)}s
                      </span>
                      <span className="run-time">
                        {new Date(run.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
