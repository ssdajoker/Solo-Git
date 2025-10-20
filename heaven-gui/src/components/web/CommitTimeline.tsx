/**
 * Commit Timeline Component with Git Graph Visualization
 */

import { useState } from 'react'
import { CommitTimelineProps, Commit, CommitStatus } from '../shared/types'
import { cn } from '../shared/utils'

export function CommitTimeline({
  repoId,
  commits: externalCommits,
  selectedCommit,
  onCommitSelect,
  onCommitCompare,
  collapsed = false,
  onToggleCollapse,
  className,
}: CommitTimelineProps) {
  const [hoveredCommit, setHoveredCommit] = useState<string | null>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [compareCommits, setCompareCommits] = useState<string[]>([])
  
  // Mock commits - in production, this would come from Tauri or props
  const mockCommits: Commit[] = [
    {
      id: 'c1',
      sha: 'a9b8c7d6',
      message: 'feat: Implement AI query function',
      author: { name: 'John Ive', email: 'john@heaven.dev' },
      timestamp: '2025-10-20T12:00:00Z',
      status: 'success',
      branch: 'main',
      tags: ['AI', 'feature'],
    },
    {
      id: 'c2',
      sha: 'f1e2d3c4',
      message: 'refactor: Update Button component',
      author: { name: 'Dieter Rams', email: 'dieter@heaven.dev' },
      timestamp: '2025-10-20T11:00:00Z',
      status: 'success',
      branch: 'main',
    },
    {
      id: 'c3',
      sha: 'b5a6978f',
      message: 'fix: Correct styling issues on mobile',
      author: { name: 'Solo AI', email: 'solo@heaven.dev' },
      timestamp: '2025-10-20T10:00:00Z',
      status: 'failed',
      branch: 'feature/mobile-fix',
    },
    {
      id: 'c4',
      sha: '7g8h9i0j',
      message: 'chore: Initial project setup',
      author: { name: 'John Ive', email: 'john@heaven.dev' },
      timestamp: '2025-10-20T09:00:00Z',
      status: 'success',
      branch: 'main',
    },
  ]
  
  const commits = externalCommits || mockCommits
  
  const getStatusColor = (status: CommitStatus) => {
    switch (status) {
      case 'success':
        return 'bg-heaven-accent-green border-heaven-accent-green text-heaven-accent-green'
      case 'failed':
        return 'bg-heaven-accent-red border-heaven-accent-red text-heaven-accent-red'
      case 'pending':
        return 'bg-heaven-accent-orange border-heaven-accent-orange text-heaven-accent-orange'
      case 'ai':
        return 'bg-heaven-accent-cyan border-heaven-accent-cyan text-heaven-accent-cyan'
      default:
        return 'bg-heaven-text-tertiary border-heaven-text-tertiary text-heaven-text-tertiary'
    }
  }
  
  const getStatusIcon = (status: CommitStatus) => {
    switch (status) {
      case 'success':
        return '✓'
      case 'failed':
        return '✗'
      case 'pending':
        return '◉'
      case 'ai':
        return '✨'
      default:
        return '○'
    }
  }
  
  const formatRelativeTime = (timestamp: string) => {
    const now = new Date()
    const then = new Date(timestamp)
    const diffMs = now.getTime() - then.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }
  
  const handleCommitClick = (commitId: string) => {
    if (compareMode) {
      if (compareCommits.includes(commitId)) {
        setCompareCommits(compareCommits.filter(id => id !== commitId))
      } else if (compareCommits.length < 2) {
        const newCompareCommits = [...compareCommits, commitId]
        setCompareCommits(newCompareCommits)
        if (newCompareCommits.length === 2) {
          onCommitCompare?.(newCompareCommits[0], newCompareCommits[1])
        }
      }
    } else {
      onCommitSelect?.(commitId)
    }
  }
  
  if (collapsed) {
    return (
      <div className={cn('w-sidebar-collapsed bg-heaven-bg-secondary border-l border-white/5', className)}>
        <button
          onClick={onToggleCollapse}
          className="w-full h-header flex items-center justify-center text-heaven-text-secondary hover:text-heaven-text-primary transition-colors"
          aria-label="Expand commit timeline"
        >
          <span className="text-xl">⏱️</span>
        </button>
      </div>
    )
  }
  
  return (
    <div className={cn('w-sidebar bg-heaven-bg-secondary border-l border-white/5 flex flex-col', className)}>
      <div className="h-header flex items-center justify-between px-3 border-b border-white/5">
        <span className="text-sm font-medium text-heaven-text-primary">COMMITS</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setCompareMode(!compareMode)
              setCompareCommits([])
            }}
            className={cn(
              'px-2 py-1 text-xs rounded transition-colors',
              compareMode 
                ? 'bg-heaven-accent-cyan text-heaven-bg-primary' 
                : 'text-heaven-text-secondary hover:text-heaven-text-primary'
            )}
            aria-label="Toggle compare mode"
          >
            Compare
          </button>
          <button
            onClick={onToggleCollapse}
            className="p-1 text-heaven-text-secondary hover:text-heaven-text-primary transition-colors"
            aria-label="Collapse commit timeline"
          >
            ▶
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto py-4">
        {repoId ? (
          commits.length > 0 ? (
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-7 top-0 bottom-0 w-0.5 bg-white/10" />
              
              {commits.map((commit) => {
                const isSelected = selectedCommit === commit.id
                const isHovered = hoveredCommit === commit.id
                const isInCompare = compareCommits.includes(commit.id)
                const statusColors = getStatusColor(commit.status)
                
                return (
                  <div
                    key={commit.id}
                    className={cn(
                      'relative pl-12 pr-3 pb-6 transition-all duration-200',
                      (isSelected || isHovered) && 'bg-heaven-bg-hover/30'
                    )}
                    onMouseEnter={() => setHoveredCommit(commit.id)}
                    onMouseLeave={() => setHoveredCommit(null)}
                  >
                    {/* Graph node */}
                    <div className="absolute left-3 top-0">
                      <button
                        onClick={() => handleCommitClick(commit.id)}
                        className={cn(
                          'w-8 h-8 rounded-full border-2 flex items-center justify-center',
                          'transition-all duration-200 hover:scale-110',
                          isSelected && 'ring-2 ring-offset-2 ring-offset-heaven-bg-secondary scale-110',
                          isInCompare && 'ring-2 ring-offset-2 ring-offset-heaven-bg-secondary ring-heaven-accent-cyan',
                          statusColors
                        )}
                        aria-label={`Select commit ${commit.sha}`}
                        aria-pressed={isSelected}
                      >
                        <span className="text-xs font-bold">
                          {getStatusIcon(commit.status)}
                        </span>
                      </button>
                      
                      {/* Branch indicator */}
                      {commit.branch !== 'main' && (
                        <div className="absolute -right-1 -bottom-1 w-3 h-3 rounded-full bg-heaven-accent-purple border border-heaven-bg-secondary" />
                      )}
                    </div>
                    
                    {/* Commit info */}
                    <div 
                      className="cursor-pointer"
                      onClick={() => handleCommitClick(commit.id)}
                    >
                      <div className="flex items-start justify-between mb-1">
                        <span className="text-xs font-mono text-heaven-accent-blue">
                          {commit.sha}
                        </span>
                        <span className="text-xs text-heaven-text-tertiary">
                          {formatRelativeTime(commit.timestamp)}
                        </span>
                      </div>
                      
                      <p className="text-sm text-heaven-text-primary mb-1 line-clamp-2">
                        {commit.message}
                      </p>
                      
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-heaven-text-secondary">
                          {commit.author.name}
                        </span>
                        
                        {commit.tags && commit.tags.length > 0 && (
                          <div className="flex gap-1">
                            {commit.tags.map(tag => (
                              <span
                                key={tag}
                                className="px-1.5 py-0.5 text-xs bg-heaven-bg-tertiary text-heaven-accent-cyan rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      {commit.branch && commit.branch !== 'main' && (
                        <div className="mt-1 flex items-center gap-1 text-xs text-heaven-accent-purple">
                          <span>⎇</span>
                          <span>{commit.branch}</span>
                        </div>
                      )}
                    </div>
                    
                    {/* Hover actions */}
                    {isHovered && (
                      <div className="absolute right-3 top-0 flex gap-1">
                        <button
                          className="p-1 bg-heaven-bg-tertiary rounded hover:bg-heaven-bg-hover transition-colors"
                          aria-label="View commit details"
                          title="View details"
                        >
                          <span className="text-xs">👁️</span>
                        </button>
                        <button
                          className="p-1 bg-heaven-bg-tertiary rounded hover:bg-heaven-bg-hover transition-colors"
                          aria-label="Checkout commit"
                          title="Checkout"
                        >
                          <span className="text-xs">⎆</span>
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="p-4 text-center text-heaven-text-tertiary text-sm">
              <div className="text-2xl mb-2">📝</div>
              <p>No commits yet</p>
            </div>
          )
        ) : (
          <div className="p-4 text-center text-heaven-text-tertiary text-sm">
            <div className="text-2xl mb-2">⏱️</div>
            <p>No repository open</p>
          </div>
        )}
      </div>
      
      {/* Compare mode footer */}
      {compareMode && (
        <div className="p-3 border-t border-white/5 bg-heaven-bg-tertiary">
          <div className="text-xs text-heaven-text-secondary mb-2">
            {compareCommits.length === 0 && 'Select 2 commits to compare'}
            {compareCommits.length === 1 && 'Select 1 more commit'}
            {compareCommits.length === 2 && 'Comparing selected commits'}
          </div>
          <button
            onClick={() => {
              setCompareMode(false)
              setCompareCommits([])
            }}
            className="w-full px-3 py-1.5 text-sm bg-heaven-bg-hover hover:bg-heaven-bg-active text-heaven-text-primary rounded transition-colors"
          >
            Cancel Compare
          </button>
        </div>
      )}
    </div>
  )
}

export default CommitTimeline
