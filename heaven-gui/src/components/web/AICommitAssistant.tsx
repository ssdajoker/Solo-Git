/**
 * AI Commit Assistant Component
 * Floating panel for AI-generated commit messages
 * Cmd+Shift+A to toggle
 */

import { useState, useEffect } from 'react'
import { cn } from '../shared/utils'
import { useKeyboardVisibility } from '../hooks/useKeyboardVisibility'

export interface AICommitAssistantProps {
  gitDiff?: string
  onAccept?: (message: string) => void
  onEdit?: (message: string) => void
  className?: string
}

export function AICommitAssistant({
  gitDiff,
  onAccept,
  onEdit,
  className,
}: AICommitAssistantProps) {
  const [commitMessage, setCommitMessage] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [isGenerating, setIsGenerating] = useState(false)
  const { isVisible, toggle } = useKeyboardVisibility('KeyA', { 
    shift: true, 
    meta: true 
  })
  
  // Generate commit message when diff changes
  useEffect(() => {
    if (gitDiff && isVisible) {
      generateCommitMessage(gitDiff)
    }
  }, [gitDiff, isVisible])
  
  const generateCommitMessage = async (diff: string) => {
    setIsGenerating(true)
    
    // Simulate AI generation - in production, this would call Tauri
    setTimeout(() => {
      const mockMessage = 'feat: Implement AI-powered commit message generation\n\nAdd AICommitAssistant component with confidence scoring'
      setCommitMessage(mockMessage)
      setConfidence(92)
      setIsGenerating(false)
    }, 1500)
  }
  
  const handleRegenerate = () => {
    if (gitDiff) {
      generateCommitMessage(gitDiff)
    }
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
        ) : commitMessage ? (
          <div className="bg-heaven-bg-tertiary rounded p-3">
            <pre className="text-sm text-heaven-text-primary whitespace-pre-wrap font-mono">
              {commitMessage}
            </pre>
          </div>
        ) : (
          <div className="text-sm text-heaven-text-tertiary py-4 text-center">
            No changes to commit
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
