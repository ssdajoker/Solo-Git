
/**
 * Pipeline View Component
 * Jenkins-like horizontal pipeline visualization
 * Full-width modal overlay for CI/CD pipeline
 */

import { useState } from 'react'
import { cn } from '../shared/utils'

export type PipelineStage = 'build' | 'unit' | 'integration' | 'e2e' | 'deploy'
export type PipelineStageStatus = 'pending' | 'running' | 'success' | 'failed' | 'unstable' | 'cancelled'

export interface PipelineStageData {
  id: PipelineStage
  label: string
  status: PipelineStageStatus
  duration?: number
  logs?: string[]
}

export type BuildStatus = 'success' | 'failed' | 'running' | 'pending' | 'cancelled'

export interface PipelineViewProps {
  buildNumber: number
  stages: PipelineStageData[]
  isOpen: boolean
  onClose: () => void
  onRetryStage?: (stageId: PipelineStage) => void
  onCancel?: () => void
  recentBuilds?: Array<{
    number: number
    status: BuildStatus
    timestamp: string
  }>
  className?: string
}

// Helper function to get pipeline stage status icon
const getStageStatusIcon = (status: PipelineStageStatus): string => {
  switch (status) {
    case 'success':
      return '✓'
    case 'failed':
      return '✗'
    case 'running':
      return '◉'
    case 'pending':
      return '○'
    case 'unstable':
      return '⚠'
    case 'cancelled':
      return '⊗'
    default:
      return '?'
  }
}

// Helper function to get build status color
const getBuildStatusColor = (status: BuildStatus | PipelineStageStatus): string => {
  switch (status) {
    case 'success':
      return 'text-heaven-accent-green'
    case 'failed':
      return 'text-heaven-accent-red'
    case 'running':
      return 'text-heaven-accent-blue'
    case 'pending':
      return 'text-heaven-text-tertiary'
    case 'unstable':
      return 'text-heaven-accent-orange'
    case 'cancelled':
      return 'text-heaven-text-secondary'
    default:
      return 'text-heaven-text-secondary'
  }
}

export function PipelineView({
  buildNumber,
  stages,
  isOpen,
  onClose,
  onRetryStage,
  onCancel,
  recentBuilds = [],
  className,
}: PipelineViewProps) {
  const [expandedStage, setExpandedStage] = useState<PipelineStage | null>(null)
  
  if (!isOpen) return null
  
  const getStageIcon = (status: PipelineStageStatus) => {
    switch (status) {
      case 'success': return '✓'
      case 'failed': return '✗'
      case 'running': return '◉'
      case 'unstable': return '⚠'
      case 'pending': return '○'
      case 'cancelled': return '⊗'
      default: return '?'
    }
  }
  
  const getStageColor = (status: PipelineStageStatus) => {
    switch (status) {
      case 'success': return 'bg-heaven-accent-green/20 border-heaven-accent-green text-heaven-accent-green'
      case 'failed': return 'bg-heaven-accent-red/20 border-heaven-accent-red text-heaven-accent-red'
      case 'running': return 'bg-heaven-accent-cyan/20 border-heaven-accent-cyan text-heaven-accent-cyan'
      case 'unstable': return 'bg-heaven-accent-orange/20 border-heaven-accent-orange text-heaven-accent-orange'
      case 'pending': return 'bg-heaven-bg-tertiary border-white/10 text-heaven-text-tertiary'
      case 'cancelled': return 'bg-heaven-bg-tertiary border-white/5 text-heaven-text-secondary'
      default: return 'bg-heaven-bg-tertiary border-white/10 text-heaven-text-tertiary'
    }
  }
  
  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 animate-in fade-in duration-150"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div 
        className={cn(
          'fixed inset-x-8 top-20 bottom-8 bg-heaven-bg-secondary border border-white/10 rounded-lg shadow-2xl z-50',
          'animate-in slide-in-from-top duration-300',
          'flex flex-col',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-heaven-text-primary">
              Build #{buildNumber} Pipeline
            </h2>
            
            {/* Recent Builds */}
            <div className="flex items-center gap-1">
              {recentBuilds.slice(0, 10).map((build) => {
                const buildColor = build.status === 'success' 
                  ? 'bg-heaven-accent-green/20 text-heaven-accent-green hover:bg-heaven-accent-green/30'
                  : build.status === 'failed'
                  ? 'bg-heaven-accent-red/20 text-heaven-accent-red hover:bg-heaven-accent-red/30'
                  : build.status === 'running'
                  ? 'bg-heaven-accent-cyan/20 text-heaven-accent-cyan hover:bg-heaven-accent-cyan/30'
                  : build.status === 'pending'
                  ? 'bg-heaven-bg-tertiary text-heaven-text-tertiary hover:bg-heaven-bg-hover'
                  : build.status === 'cancelled'
                  ? 'bg-heaven-bg-tertiary text-heaven-text-secondary hover:bg-heaven-bg-hover'
                  : 'bg-heaven-bg-tertiary text-heaven-text-tertiary hover:bg-heaven-bg-hover'
                
                return (
                  <button
                    key={build.number}
                    className={cn(
                      'w-6 h-6 rounded flex items-center justify-center text-xs transition-colors duration-150',
                      buildColor
                    )}
                    title={`Build #${build.number} - ${build.status}`}
                  >
                    {build.number === buildNumber ? '●' : '○'}
                  </button>
                )
              })}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {onCancel && (
              <button
                onClick={onCancel}
                className="px-4 py-2 bg-heaven-accent-red/20 text-heaven-accent-red rounded
                         hover:bg-heaven-accent-red/30 transition-colors duration-150 text-sm"
              >
                Cancel Pipeline
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-heaven-text-secondary hover:text-heaven-text-primary transition-colors duration-150"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>
        
        {/* Pipeline Stages */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="flex items-start gap-4">
            {stages.map((stage, index) => (
              <div key={stage.id} className="flex items-start gap-4 flex-1">
                {/* Stage Card */}
                <button
                  onClick={() => setExpandedStage(expandedStage === stage.id ? null : stage.id)}
                  className={cn(
                    'w-full p-4 border-2 rounded-lg transition-all duration-150 text-left',
                    getStageColor(stage.status),
                    expandedStage === stage.id && 'ring-2 ring-white/20'
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">
                      {getStageIcon(stage.status)}
                    </span>
                    {stage.duration && (
                      <span className="text-xs text-heaven-text-tertiary">
                        {stage.duration}s
                      </span>
                    )}
                  </div>
                  
                  <h3 className="text-sm font-semibold mb-1">
                    {stage.label}
                  </h3>
                  
                  <p className="text-xs opacity-75 capitalize">
                    {stage.status}
                  </p>
                  
                  {stage.status === 'failed' && onRetryStage && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onRetryStage(stage.id)
                      }}
                      className="mt-2 w-full px-3 py-1.5 bg-heaven-bg-tertiary rounded text-xs
                               hover:bg-heaven-bg-hover transition-colors duration-150"
                    >
                      Retry
                    </button>
                  )}
                </button>
                
                {/* Connector */}
                {index < stages.length - 1 && (
                  <div className="flex items-center justify-center pt-8">
                    <div className={cn(
                      'h-0.5 w-12 transition-colors duration-300',
                      stage.status === 'success' ? 'bg-heaven-accent-green' : 'bg-white/10'
                    )} />
                  </div>
                )}
              </div>
            ))}
          </div>
          
          {/* Expanded Stage Logs */}
          {expandedStage && (
            <div className="mt-6 bg-heaven-bg-tertiary rounded-lg p-4 animate-in slide-in-from-top duration-150">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-heaven-text-primary">
                  {stages.find(s => s.id === expandedStage)?.label} Logs
                </h4>
                <button
                  onClick={() => setExpandedStage(null)}
                  className="text-xs text-heaven-text-secondary hover:text-heaven-text-primary"
                >
                  Hide
                </button>
              </div>
              
              <div className="bg-heaven-bg-primary rounded p-3 max-h-64 overflow-y-auto font-mono text-xs">
                {stages.find(s => s.id === expandedStage)?.logs?.map((log, i) => (
                  <div key={i} className="text-heaven-text-secondary py-0.5">
                    {log}
                  </div>
                )) || (
                  <div className="text-heaven-text-tertiary italic">No logs available</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default PipelineView
