
/**
 * Minimalist Status Bar Component - Contextual & Semi-Transparent
 * Following the "No UI" philosophy: only show essential info
 */

import { useState } from 'react'
import { StatusBarProps, BuildStatus } from '../shared/types'
import { cn } from '../shared/utils'

// Helper function to get build status icon
const getBuildStatusIcon = (status: BuildStatus): string => {
  switch (status) {
    case 'success':
      return '✓'
    case 'failed':
      return '✗'
    case 'running':
      return '◉'
    case 'pending':
      return '○'
    case 'cancelled':
      return '⊗'
    default:
      return '?'
  }
}

// Helper function to get build status color
const getBuildStatusColor = (status: BuildStatus): string => {
  switch (status) {
    case 'success':
      return 'text-heaven-accent-green'
    case 'failed':
      return 'text-heaven-accent-red'
    case 'running':
      return 'text-heaven-accent-orange'
    case 'pending':
      return 'text-heaven-text-tertiary'
    case 'cancelled':
      return 'text-heaven-text-secondary'
    default:
      return 'text-heaven-text-secondary'
  }
}

export function StatusBar({ 
  globalState, 
  buildInfo, 
  gitStatus,
  cursorPosition,
  language,
  encoding = 'UTF-8',
  lineEnding = 'LF',
  className 
}: StatusBarProps) {
  const [showCostPanel, setShowCostPanel] = useState(false)
  const [showBuildPanel, setShowBuildPanel] = useState(false)
  
  return (
    <div className={cn(
      'h-statusbar bg-heaven-bg-tertiary/80 backdrop-blur-sm border-t border-white/5',
      'flex items-center justify-between text-xs text-heaven-text-secondary',
      className
    )}>
      {/* Left Section: Git Status */}
      <div className="flex items-center gap-3 px-4">
        {/* Git Branch */}
        {gitStatus && (
          <button 
            className="flex items-center gap-1.5 hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150"
            aria-label="Git branch information"
          >
            <span className="text-heaven-accent-purple">⎇</span>
            <span className="font-medium">{gitStatus.branch}</span>
            {(gitStatus.ahead > 0 || gitStatus.behind > 0) && (
              <span className="text-heaven-accent-cyan">
                {gitStatus.ahead > 0 && `↑${gitStatus.ahead}`}
                {gitStatus.behind > 0 && `↓${gitStatus.behind}`}
              </span>
            )}
          </button>
        )}
        
        {/* File Changes - contextual, only show if there are changes */}
        {gitStatus && (gitStatus.staged.length > 0 || gitStatus.unstaged.length > 0) && (
          <button 
            className="flex items-center gap-1.5 hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150"
            aria-label="File changes"
          >
            {gitStatus.staged.length > 0 && (
              <span className="text-heaven-accent-green">●{gitStatus.staged.length}</span>
            )}
            {gitStatus.unstaged.length > 0 && (
              <span className="text-heaven-accent-orange">●{gitStatus.unstaged.length}</span>
            )}
          </button>
        )}
      </div>
      
      {/* Center Section: Build Info (minimal) */}
      <div className="flex items-center gap-3">
        {buildInfo && (
          <button 
            onClick={() => setShowBuildPanel(!showBuildPanel)}
            className="flex items-center gap-2 hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150"
            aria-label="Build status"
          >
            <span className={cn('text-lg', getBuildStatusColor(buildInfo.status))}>
              {getBuildStatusIcon(buildInfo.status)}
            </span>
            <span className="text-heaven-text-tertiary">
              Build #{buildInfo.number}
            </span>
          </button>
        )}
      </div>
      
      {/* Right Section: Editor Info (contextual) */}
      <div className="flex items-center gap-3 px-4">
        {/* Cursor Position - only show when provided */}
        {cursorPosition && (
          <button 
            className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150"
            aria-label="Cursor position"
          >
            Ln {cursorPosition.line}, Col {cursorPosition.column}
          </button>
        )}
        
        {/* Language */}
        {language && (
          <button 
            className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150 font-medium"
            aria-label="Current language"
          >
            {language}
          </button>
        )}
        
        {/* Encoding - only show if not UTF-8 */}
        {encoding && encoding !== 'UTF-8' && (
          <button 
            className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150"
            aria-label="File encoding"
          >
            {encoding}
          </button>
        )}
        
        {/* Line Ending - only show if not LF */}
        {lineEnding && lineEnding !== 'LF' && (
          <button 
            className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150"
            aria-label="Line ending"
          >
            {lineEnding}
          </button>
        )}
        
        {/* Cost Tracker Icon (click to expand panel) */}
        {globalState && (
          <button 
            onClick={() => setShowCostPanel(!showCostPanel)}
            className="flex items-center gap-1 hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors duration-150"
            aria-label="AI cost tracker"
          >
            <span className="text-heaven-accent-cyan">$</span>
          </button>
        )}
      </div>
      
      {/* Cost Panel (expandable) */}
      {showCostPanel && globalState && (
        <div className="absolute bottom-full right-4 mb-2 bg-heaven-bg-secondary/95 backdrop-blur-sm border border-white/10 rounded-lg p-3 shadow-xl min-w-[200px]">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-heaven-text-primary">AI Cost Tracker</h3>
            <button 
              onClick={() => setShowCostPanel(false)}
              className="text-heaven-text-secondary hover:text-heaven-text-primary"
            >
              ✕
            </button>
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs text-heaven-text-secondary">Total Cost</span>
              <span className="text-xs font-mono text-heaven-accent-cyan">
                ${globalState.total_cost_usd.toFixed(4)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-heaven-text-secondary">Active Repo</span>
              <span className="text-xs text-heaven-text-primary">
                {globalState.active_repo || 'None'}
              </span>
            </div>
          </div>
        </div>
      )}
      
      {/* Build Panel (expandable) */}
      {showBuildPanel && buildInfo && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-heaven-bg-secondary/95 backdrop-blur-sm border border-white/10 rounded-lg p-3 shadow-xl min-w-[250px]">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-heaven-text-primary">Build #{buildInfo.number}</h3>
            <button 
              onClick={() => setShowBuildPanel(false)}
              className="text-heaven-text-secondary hover:text-heaven-text-primary"
            >
              ✕
            </button>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className={cn('text-xs font-medium', getBuildStatusColor(buildInfo.status))}>
                {buildInfo.status.toUpperCase()}
              </span>
            </div>
            <button className="text-xs text-heaven-accent-cyan hover:underline">
              View pipeline →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default StatusBar
