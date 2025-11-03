/**
 * AI Commit Assistant Component
 * Floating panel for AI-generated commit messages
 * Cmd+Shift+A to toggle
 */

import { useState, useEffect } from 'react'
import { cn } from '../shared/utils'
import { useKeyboardVisibility } from '../hooks/useKeyboardVisibility'
import { useSoloGitOperations } from '../hooks/useSoloGitOperations'
import { notifications } from '../utils/notifications'

export interface AICommitAssistantProps {
  workpadId?: string
  gitDiff?: string
  onAccept?: (message: string) => void
  onEdit?: (message: string) => void
  className?: string
}

export function AICommitAssistant({
  workpadId,
  gitDiff,
  onAccept,
  onEdit,
  className,
}: AICommitAssistantProps) {
  const [commitMessage, setCommitMessage] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [isGenerating, setIsGenerating] = useState(false)
  const [provider, setProvider] = useState<string>('')
  const [model, setModel] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  
  const { generateCommitMessage: generateFromBackend } = useSoloGitOperations()
  
  const { isVisible, toggle } = useKeyboardVisibility('KeyA', { 
    shift: true, 
    meta: true 
  })
  
  // Generate commit message when visible and workpadId is available
  useEffect(() => {
    if (isVisible && workpadId) {
      generateCommitMessage()
    }
  }, [isVisible, workpadId])
  
  const generateCommitMessage = async () => {
    if (!workpadId) {
      setError('No workpad selected')
      notifications.error('AI Commit Error', 'No workpad selected')
      return
    }
    
    setIsGenerating(true)
    setError(null)
    
    try {
      const response = await generateFromBackend({ workpadId })
      
      if (!response.success) {
        setError(response.error || 'Failed to generate commit message')
        notifications.error('AI Commit Error', response.error || 'Failed to generate commit message')
        setIsGenerating(false)
        return
      }
      
      if (response.message) {
        setCommitMessage(response.message)
        setProvider(response.provider || '')
        setModel(response.model || '')
        
        // Calculate confidence based on message quality (simple heuristic)
        const confidence = calculateConfidence(response.message, response.fallback_used)
        setConfidence(confidence)
        
        notifications.success('AI Commit Generated', `Using ${response.provider || 'AI'} provider`)
        
        if (response.fallback_used) {
          notifications.warning('Fallback Used', 'Primary provider failed, fallback was used')
        }
      }
      
      setIsGenerating(false)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMsg)
      notifications.error('AI Commit Failed', errorMsg)
      setIsGenerating(false)
    }
  }
  
  // Calculate confidence score based on message quality
  const calculateConfidence = (message: string, fallbackUsed?: boolean | null): number => {
    let score = 70 // Base score
    
    // Check for conventional commit format
    if (/^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .+/.test(message)) {
      score += 15
    }
    
    // Check for descriptive message (not too short)
    if (message.length > 30) {
      score += 10
    }
    
    // Check for body/detailed description
    if (message.includes('\n\n')) {
      score += 5
    }
    
    // Reduce score if fallback was used
    if (fallbackUsed) {
      score -= 10
    }
    
    return Math.min(100, Math.max(0, score))
  }
  
  const handleRegenerate = () => {
    generateCommitMessage()
  }
  
  const handleAccept = () => {
    onAccept?.(commitMessage)
    toggle() // Close after accepting
  }
  
  const handleEdit = () => {
    onEdit?.(commitMessage)
  }
  
  if (!isVisible) return null
  
  return (
    <div 
      className={cn(
        'fixed bottom-12 right-6 w-96 bg-heaven-bg-secondary/95 backdrop-blur-sm',
        'border border-white/10 rounded-lg shadow-xl p-4',
        'animate-in fade-in slide-in-from-bottom-2 duration-150',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">✨</span>
          <h3 className="text-sm font-semibold text-heaven-text-primary">
            AI Commit Message
          </h3>
        </div>
        <button
          onClick={toggle}
          className="p-1 text-heaven-text-secondary hover:text-heaven-text-primary transition-colors duration-150"
          aria-label="Close (Cmd+Shift+A)"
        >
          ✕
        </button>
      </div>
      
      {/* Confidence Score */}
      {!isGenerating && commitMessage && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-heaven-text-secondary">Confidence</span>
            <span className={cn(
              "text-xs font-semibold",
              confidence >= 80 && "text-heaven-accent-green",
              confidence >= 60 && confidence < 80 && "text-heaven-accent-orange",
              confidence < 60 && "text-heaven-accent-red"
            )}>
              {confidence}%
            </span>
          </div>
          <div className="h-1 bg-heaven-bg-tertiary rounded-full overflow-hidden">
            <div 
              className={cn(
                "h-full transition-all duration-300",
                confidence >= 80 && "bg-heaven-accent-green",
                confidence >= 60 && confidence < 80 && "bg-heaven-accent-orange",
                confidence < 60 && "bg-heaven-accent-red"
              )}
              style={{ width: `${confidence}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Message Preview */}
      <div className="mb-3">
        {isGenerating ? (
          <div className="flex items-center gap-2 py-4 text-heaven-text-secondary">
            <div className="w-4 h-4 border-2 border-heaven-accent-cyan border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Analyzing changes...</span>
          </div>
        ) : error ? (
          <div className="bg-heaven-accent-red/10 border border-heaven-accent-red/30 rounded p-3">
            <p className="text-sm text-heaven-accent-red">{error}</p>
          </div>
        ) : commitMessage ? (
          <>
            <div className="bg-heaven-bg-tertiary rounded p-3 mb-2">
              <pre className="text-sm text-heaven-text-primary whitespace-pre-wrap font-mono">
                {commitMessage}
              </pre>
            </div>
            {provider && (
              <div className="text-xs text-heaven-text-tertiary">
                Provider: {provider} {model && `(${model})`}
              </div>
            )}
          </>
        ) : (
          <div className="text-sm text-heaven-text-tertiary py-4 text-center">
            No workpad selected
          </div>
        )}
      </div>
      
      {/* Actions */}
      {!isGenerating && commitMessage && (
        <div className="flex items-center gap-2">
          <button
            onClick={handleAccept}
            className="flex-1 px-4 py-2 bg-heaven-accent-cyan text-heaven-bg-primary rounded
                     hover:bg-heaven-accent-cyan/90 transition-colors duration-150 text-sm font-medium"
          >
            Accept
          </button>
          <button
            onClick={handleEdit}
            className="flex-1 px-4 py-2 bg-heaven-bg-tertiary text-heaven-text-primary rounded
                     hover:bg-heaven-bg-hover transition-colors duration-150 text-sm"
          >
            Edit
          </button>
          <button
            onClick={handleRegenerate}
            className="px-4 py-2 bg-heaven-bg-tertiary text-heaven-text-primary rounded
                     hover:bg-heaven-bg-hover transition-colors duration-150 text-sm"
            aria-label="Regenerate"
            title="Regenerate"
          >
            🔄
          </button>
        </div>
      )}
      
      {/* Keyboard Hint */}
      <div className="mt-3 pt-3 border-t border-white/5">
        <p className="text-xs text-heaven-text-tertiary text-center">
          Press <kbd className="px-1 py-0.5 bg-heaven-bg-tertiary rounded text-heaven-text-secondary">Cmd+Shift+A</kbd> to toggle
        </p>
      </div>
    </div>
  )
}

export default AICommitAssistant
