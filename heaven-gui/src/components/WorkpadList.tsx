
import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import './WorkpadList.css'

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
}

export default function WorkpadList({ repoId }: WorkpadListProps) {
  const [workpads, setWorkpads] = useState<Workpad[]>([])
  const [loading, setLoading] = useState(false)

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
      </div>
      
      <div className="workpad-items">
        {workpads.length === 0 ? (
          <p className="empty-message">No workpads</p>
        ) : (
          workpads.slice(0, 10).map((workpad) => (
            <div key={workpad.workpad_id} className="workpad-item">
              <div className="workpad-header">
                <span className={`workpad-status ${getStatusClass(workpad.status)}`}>
                  {getStatusIcon(workpad.status)}
                </span>
                <span className="workpad-title">{workpad.title}</span>
              </div>
              <div className="workpad-meta">
                <span className="workpad-patches">{workpad.patches_applied} patches</span>
                <span className="workpad-tests">{workpad.test_runs.length} tests</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
