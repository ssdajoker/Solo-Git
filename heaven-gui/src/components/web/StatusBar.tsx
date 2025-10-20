
/**
 * Enhanced Status Bar Component
 */

import { StatusBarProps } from '../shared/types'
import { cn } from '../shared/utils'

export function StatusBar({ globalState, testRun, buildInfo, className }: StatusBarProps) {
  return (
    <div className={cn(
      'h-statusbar bg-heaven-bg-tertiary border-t border-white/5',
      'flex items-center justify-between px-4 text-xs text-heaven-text-secondary',
      className
    )}>
      {/* Left Section: Status */}
      <div className="flex items-center gap-4">
        {globalState?.active_repo && (
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-heaven-accent-green" aria-label="Ready" />
            <span>Ready</span>
          </div>
        )}
        {testRun?.status === 'running' && (
          <div className="flex items-center gap-2 animate-pulse-subtle">
            <span className="w-2 h-2 rounded-full bg-heaven-accent-orange" />
            <span>running tests...</span>
          </div>
        )}
      </div>
      
      {/* Center Section: Test Results */}
      <div className="flex items-center gap-4">
        {testRun && testRun.suites.map(suite => (
          <div key={suite.id} className="flex items-center gap-2">
            <span className={cn(
              suite.failed > 0 ? 'text-heaven-accent-red' : 'text-heaven-accent-green'
            )}>
              {suite.failed > 0 ? '✗' : '✓'}
            </span>
            <span>{suite.file} {suite.passed} passed</span>
          </div>
        ))}
      </div>
      
      {/* Right Section: Build Info */}
      <div className="flex items-center gap-4">
        {buildInfo && (
          <div className="flex items-center gap-2">
            <span>build #{buildInfo.number}</span>
            <span className={cn(
              buildInfo.status === 'success' && 'text-heaven-accent-green',
              buildInfo.status === 'failed' && 'text-heaven-accent-red',
              buildInfo.status === 'running' && 'text-heaven-accent-orange'
            )}>
              {buildInfo.platform || 'jenkins'}: {buildInfo.status.toUpperCase()}
            </span>
          </div>
        )}
        {globalState && (
          <span>${globalState.total_cost_usd.toFixed(4)}</span>
        )}
      </div>
    </div>
  )
}

export default StatusBar
