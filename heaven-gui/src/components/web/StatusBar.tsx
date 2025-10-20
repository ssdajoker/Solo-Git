
/**
 * Enhanced Status Bar Component with Git Status, Test Results, and System Info
 */

import { useState } from 'react'
import { StatusBarProps } from '../shared/types'
import { cn } from '../shared/utils'

export function StatusBar({ 
  globalState, 
  testRun, 
  buildInfo, 
  gitStatus,
  cursorPosition,
  language,
  encoding = 'UTF-8',
  lineEnding = 'LF',
  className 
}: StatusBarProps) {
  const [showDetails, setShowDetails] = useState(false)
  
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }
  
  return (
    <div className={cn(
      'h-statusbar bg-heaven-bg-tertiary border-t border-white/5',
      'flex items-center justify-between text-xs text-heaven-text-secondary',
      className
    )}>
      {/* Left Section: Git Status & Activity */}
      <div className="flex items-center gap-4 px-4">
        {/* Status Indicator */}
        {globalState?.active_repo && (
          <button 
            className="flex items-center gap-2 hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors"
            onClick={() => setShowDetails(!showDetails)}
            aria-label="Toggle status details"
          >
            <span 
              className={cn(
                "w-2 h-2 rounded-full",
                testRun?.status === 'running' && 'bg-heaven-accent-orange animate-pulse',
                testRun?.status === 'passed' && 'bg-heaven-accent-green',
                testRun?.status === 'failed' && 'bg-heaven-accent-red',
                !testRun && 'bg-heaven-accent-green'
              )} 
              aria-label="Status indicator" 
            />
            <span>
              {testRun?.status === 'running' && 'Running tests...'}
              {testRun?.status === 'passed' && 'All tests passed'}
              {testRun?.status === 'failed' && 'Tests failed'}
              {!testRun && 'Ready'}
            </span>
          </button>
        )}
        
        {/* Git Branch */}
        {gitStatus && (
          <button 
            className="flex items-center gap-1.5 hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors"
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
        
        {/* File Changes */}
        {gitStatus && (gitStatus.staged.length > 0 || gitStatus.unstaged.length > 0) && (
          <button 
            className="flex items-center gap-1.5 hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors"
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
      
      {/* Center Section: Test Results Summary */}
      <div className="flex items-center gap-4">
        {testRun && (
          <div className="flex items-center gap-3">
            {/* Total Summary */}
            <div className="flex items-center gap-2">
              <span className="text-heaven-accent-green font-medium">
                ✓ {testRun.totalPassed}
              </span>
              {testRun.totalFailed > 0 && (
                <span className="text-heaven-accent-red font-medium">
                  ✗ {testRun.totalFailed}
                </span>
              )}
              {testRun.totalSkipped > 0 && (
                <span className="text-heaven-text-tertiary">
                  ○ {testRun.totalSkipped}
                </span>
              )}
              <span className="text-heaven-text-tertiary">
                / {testRun.totalTests}
              </span>
            </div>
            
            {/* Duration */}
            {testRun.duration > 0 && (
              <span className="text-heaven-text-tertiary">
                {formatDuration(testRun.duration)}
              </span>
            )}
            
            {/* View Details Button */}
            <button 
              className="hover:text-heaven-text-primary transition-colors underline"
              aria-label="View test details"
            >
              details
            </button>
          </div>
        )}
        
        {/* Build Info */}
        {buildInfo && (
          <div className="flex items-center gap-2 px-3 py-1 bg-heaven-bg-secondary rounded">
            <span className="text-heaven-text-tertiary">
              Build #{buildInfo.number}
            </span>
            <span className={cn(
              'font-medium',
              buildInfo.status === 'success' && 'text-heaven-accent-green',
              buildInfo.status === 'failed' && 'text-heaven-accent-red',
              buildInfo.status === 'running' && 'text-heaven-accent-orange'
            )}>
              {buildInfo.status === 'success' && '✓'}
              {buildInfo.status === 'failed' && '✗'}
              {buildInfo.status === 'running' && '◉'}
              {' '}{buildInfo.status.toUpperCase()}
            </span>
          </div>
        )}
      </div>
      
      {/* Right Section: Editor Info & System */}
      <div className="flex items-center gap-4 px-4">
        {/* Cursor Position */}
        {cursorPosition && (
          <button 
            className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors"
            aria-label="Cursor position"
          >
            Ln {cursorPosition.line}, Col {cursorPosition.column}
          </button>
        )}
        
        {/* Language */}
        {language && (
          <button 
            className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors font-medium"
            aria-label="Current language"
          >
            {language}
          </button>
        )}
        
        {/* Encoding */}
        <button 
          className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors"
          aria-label="File encoding"
        >
          {encoding}
        </button>
        
        {/* Line Ending */}
        <button 
          className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors"
          aria-label="Line ending"
        >
          {lineEnding}
        </button>
        
        {/* Cost Tracker */}
        {globalState && (
          <div className="flex items-center gap-2 px-2 py-1 bg-heaven-bg-secondary rounded">
            <span className="text-heaven-accent-cyan">$</span>
            <span className="font-mono">{globalState.total_cost_usd.toFixed(4)}</span>
          </div>
        )}
        
        {/* Notifications */}
        <button 
          className="hover:bg-heaven-bg-hover px-2 py-1 rounded transition-colors relative"
          aria-label="Notifications"
        >
          <span>🔔</span>
          <span className="absolute -top-1 -right-1 w-2 h-2 bg-heaven-accent-red rounded-full" />
        </button>
      </div>
      
      {/* Details Panel (when expanded) */}
      {showDetails && testRun && (
        <div className="absolute bottom-full left-0 right-0 bg-heaven-bg-secondary border-t border-white/10 p-4 shadow-xl">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-heaven-text-primary">Test Run Details</h3>
              <button 
                onClick={() => setShowDetails(false)}
                className="text-heaven-text-secondary hover:text-heaven-text-primary"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-2">
              {testRun.suites.map(suite => (
                <div key={suite.id} className="flex items-center justify-between p-2 bg-heaven-bg-tertiary rounded">
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      'text-lg',
                      suite.failed > 0 ? 'text-heaven-accent-red' : 'text-heaven-accent-green'
                    )}>
                      {suite.failed > 0 ? '✗' : '✓'}
                    </span>
                    <span className="text-sm text-heaven-text-primary">{suite.file}</span>
                  </div>
                  
                  <div className="flex items-center gap-4 text-xs">
                    <span className="text-heaven-accent-green">✓ {suite.passed}</span>
                    {suite.failed > 0 && (
                      <span className="text-heaven-accent-red">✗ {suite.failed}</span>
                    )}
                    {suite.skipped > 0 && (
                      <span className="text-heaven-text-tertiary">○ {suite.skipped}</span>
                    )}
                    <span className="text-heaven-text-tertiary">{formatDuration(suite.duration)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StatusBar
