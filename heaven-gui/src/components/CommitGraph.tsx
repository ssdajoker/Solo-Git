
import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import './CommitGraph.css'

interface Commit {
  sha: string
  short_sha: string
  message: string
  author: string
  timestamp: string
  parent_sha: string | null
  workpad_id: string | null
  test_status: string | null
  ci_status: string | null
  is_trunk: boolean
}

interface CommitGraphProps {
  repoId: string | null | undefined
}

export default function CommitGraph({ repoId }: CommitGraphProps) {
  const [commits, setCommits] = useState<Commit[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (repoId) {
      loadCommits()
      const interval = setInterval(loadCommits, 5000)
      return () => clearInterval(interval)
    }
  }, [repoId])

  const loadCommits = async () => {
    if (!repoId) return
    
    try {
      setLoading(true)
      const data = await invoke<Commit[]>('list_commits', { repoId, limit: 20 })
      setCommits(data || [])
    } catch (e) {
      console.error('Failed to load commits:', e)
      setCommits([]) // Set empty array on error
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string | null) => {
    if (!status) return '○'
    if (status === 'passed') return '✓'
    if (status === 'failed') return '✗'
    if (status === 'running') return '◉'
    return '○'
  }

  const getStatusClass = (status: string | null) => {
    if (!status) return 'status-none'
    return `status-${status}`
  }

  if (!repoId) {
    return (
      <div className="commit-graph empty">
        <h3>Commit Graph</h3>
        <p className="empty-message">No repository selected</p>
      </div>
    )
  }

  return (
    <div className="commit-graph">
      <div className="commit-graph-header">
        <h3>Commit Graph</h3>
        {loading && <span className="loading-indicator">⟳</span>}
      </div>
      
      <div className="commit-list">
        {commits.length === 0 ? (
          <p className="empty-message">No commits yet</p>
        ) : (
          commits.slice(0, 15).map((commit, index) => (
            <div key={commit.sha} className="commit-item">
              <div className="commit-node">
                <span className={`node ${commit.is_trunk ? 'trunk' : 'workpad'}`}>
                  {commit.is_trunk ? '●' : '○'}
                </span>
                {index < commits.length - 1 && <span className="connector">│</span>}
              </div>
              
              <div className="commit-info">
                <div className="commit-header">
                  <span className={`test-status ${getStatusClass(commit.test_status)}`}>
                    {getStatusIcon(commit.test_status)}
                  </span>
                  <span className="commit-sha">{commit.short_sha}</span>
                </div>
                <p className="commit-message">{commit.message.slice(0, 50)}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
