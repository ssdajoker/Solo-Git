/**
 * Workflow Panel Component
 * Horizontal pipeline visualization for Solo-Git workflow
 * Appears only when workflow active, auto-collapses when complete
 */

import { useState, useEffect } from 'react'
import { cn } from '../shared/utils'

export type WorkflowStage = 'plan' | 'code' | 'test' | 'gate' | 'merge'
export type StageStatus = 'pending' | 'active' | 'complete' | 'failed' | 'skipped'

export interface WorkflowStageData {
  id: WorkflowStage
  label: string
  status: StageStatus
  estimatedTime?: number
  elapsedTime?: number
}

export interface WorkflowPanelProps {
  stages: WorkflowStageData[]
  currentStage?: WorkflowStage
  onCancel?: () => void
  onSkipTests?: () => void
  className?: string
}

export function WorkflowPanel({
  stages,
  currentStage,
  onCancel,
  onSkipTests,
  className,
}: WorkflowPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  // Auto-collapse after completion
  useEffect(() => {
    const allComplete = stages.every(s => 
      s.status === 'complete' || s.status === 'skipped'
    )
    
    if (allComplete) {
      setTimeout(() => setIsCollapsed(true), 3000)
    }
  }, [stages])
  
  const getStageIcon = (status: StageStatus) => {
    switch (status) {
      case 'complete': return '✅'
      case 'active': return '🔄'
      case 'failed': return '❌'
      case 'skipped': return '⏭️'
      default: return '⏳'
    }
  }
  
  const getStageColor = (status: StageStatus) => {
    switch (status) {
      case 'complete': return 'text-heaven-accent-green border-heaven-accent-green'
      case 'active': return 'text-heaven-accent-cyan border-heaven-accent-cyan animate-pulse'
      case 'failed': return 'text-heaven-accent-red border-heaven-accent-red'
      case 'skipped': return 'text-heaven-text-tertiary border-heaven-text-tertiary'
      default: return 'text-heaven-text-tertiary border-white/10'
    }
  }
  
  if (isCollapsed) return null
  
  const activeStage = stages.find(s => s.status === 'active')
  
  return (
    <div 
      className={cn(
        'fixed top-16 left-1/2 -translate-x-1/2 bg-heaven-bg-secondary/95 backdrop-blur-sm',
        'border border-white/10 rounded-lg shadow-xl px-6 py-4',
        'animate-in slide-in-from-top duration-300',
        'max-w-3xl w-full',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚡</span>
          <h3 className="text-sm font-semibold text-heaven-text-primary">
            Workflow in Progress
          </h3>
          {activeStage && activeStage.estimatedTime && (
            <span className="text-xs text-heaven-text-tertiary">
              ~{activeStage.estimatedTime}s remaining
            </span>
          )}
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1 text-heaven-text-secondary hover:text-heaven-text-primary transition-colors duration-150"
          aria-label="Collapse"
        >
          ▲
        </button>
      </div>
      
      {/* Pipeline Stages */}
      <div className="flex items-center justify-between gap-4 mb-4">
        {stages.map((stage, index) => (
          <div key={stage.id} className="flex items-center gap-4 flex-1">
            {/* Stage Card */}
            <div 
              className={cn(
                'flex-1 flex flex-col items-center gap-2 p-3 border-2 rounded-lg transition-all duration-150',
                getStageColor(stage.status)
              )}
            >
              <span className="text-2xl">
                {getStageIcon(stage.status)}
              </span>
              <span className="text-sm font-medium text-heaven-text-primary">
                {stage.label}
              </span>
              {stage.status === 'active' && stage.elapsedTime !== undefined && (
                <span className="text-xs text-heaven-text-tertiary">
                  {stage.elapsedTime}s
                </span>
              )}
            </div>
            
            {/* Connector */}
            {index < stages.length - 1 && (
              <div className={cn(
                'h-0.5 w-8 transition-colors duration-300',
                stage.status === 'complete' ? 'bg-heaven-accent-green' : 'bg-white/10'
              )} />
            )}
          </div>
        ))}
      </div>
      
      {/* Progress Bar */}
      <div className="mb-4">
        <div className="h-1 bg-heaven-bg-tertiary rounded-full overflow-hidden">
          <div 
            className="h-full bg-heaven-accent-cyan transition-all duration-300"
            style={{ 
              width: `${(stages.filter(s => s.status === 'complete').length / stages.length) * 100}%` 
            }}
          />
        </div>
      </div>
      
      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {currentStage === 'test' && (
            <button
              onClick={onSkipTests}
              className="px-3 py-1.5 text-sm bg-heaven-bg-tertiary text-heaven-text-primary rounded
                       hover:bg-heaven-bg-hover transition-colors duration-150"
            >
              Skip Tests
            </button>
          )}
        </div>
        
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-sm bg-heaven-accent-red/20 text-heaven-accent-red rounded
                   hover:bg-heaven-accent-red/30 transition-colors duration-150"
        >
          Cancel Workflow
        </button>
      </div>
    </div>
  )
}

export default WorkflowPanel
