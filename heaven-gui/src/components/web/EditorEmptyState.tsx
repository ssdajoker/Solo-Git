/**
 * Editor Empty State Component
 * Shown when no file is open in the editor
 */

import { cn } from '../shared/utils'

export interface EditorEmptyStateProps {
  /** Callback when user wants to open a file */
  onOpenFile?: () => void
  
  /** Callback when user wants to create a new file */
  onCreateFile?: () => void
  
  /** Custom className */
  className?: string
}

export function EditorEmptyState({
  onOpenFile,
  onCreateFile,
  className,
}: EditorEmptyStateProps) {
  return (
    <div 
      className={cn(
        'flex items-center justify-center h-full bg-heaven-bg-primary',
        className
      )}
    >
      <div className="text-center max-w-md px-6">
        {/* Icon */}
        <div className="mb-6 text-6xl text-heaven-text-tertiary opacity-50">
          📝
        </div>
        
        {/* Title */}
        <h2 className="text-xl font-semibold text-heaven-text-primary mb-2">
          No File Open
        </h2>
        
        {/* Description */}
        <p className="text-sm text-heaven-text-secondary mb-6">
          Select a file from the explorer to start editing, or create a new file to begin coding.
        </p>
        
        {/* Actions */}
        <div className="flex items-center justify-center gap-3">
          {onOpenFile && (
            <button
              onClick={onOpenFile}
              className="px-4 py-2 bg-heaven-accent-cyan text-white font-medium rounded-md hover:bg-heaven-accent-cyan/90 transition-colors"
            >
              Open File
            </button>
          )}
          
          {onCreateFile && (
            <button
              onClick={onCreateFile}
              className="px-4 py-2 bg-heaven-bg-tertiary text-heaven-text-primary font-medium rounded-md hover:bg-heaven-bg-hover transition-colors border border-white/10"
            >
              Create New File
            </button>
          )}
        </div>
        
        {/* Keyboard hints */}
        <div className="mt-8 space-y-2">
          <div className="flex items-center justify-center gap-4 text-xs text-heaven-text-tertiary">
            <span className="flex items-center gap-1">
              <kbd className="px-2 py-1 bg-heaven-bg-tertiary rounded text-[10px] border border-white/5">⌘K</kbd>
              <span>Command Palette</span>
            </span>
            
            <span className="flex items-center gap-1">
              <kbd className="px-2 py-1 bg-heaven-bg-tertiary rounded text-[10px] border border-white/5">⌘B</kbd>
              <span>Toggle Explorer</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EditorEmptyState
