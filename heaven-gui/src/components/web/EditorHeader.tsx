/**
 * Editor Header Component
 * Shows file breadcrumbs, status, and action buttons
 */

import { useState } from 'react'
import { cn } from '../shared/utils'
import type { GitFileStatus } from '../shared/types'

export interface EditorHeaderProps {
  /** Current file path */
  filePath: string | null
  
  /** File status */
  status?: 'saved' | 'unsaved' | 'saving' | 'read-only'
  
  /** Current language */
  language?: string
  
  /** Git status */
  gitStatus?: GitFileStatus
  
  /** Whether to show the minimap */
  showMinimap?: boolean
  
  /** Callback to toggle minimap */
  onToggleMinimap?: () => void
  
  /** Callback to format document */
  onFormat?: () => void
  
  /** Callback to change language */
  onChangeLanguage?: () => void
  
  /** Callback to toggle word wrap */
  onToggleWordWrap?: () => void
  
  /** Whether word wrap is enabled */
  wordWrapEnabled?: boolean
  
  /** Custom className */
  className?: string
}

/**
 * Split file path into breadcrumb segments
 */
function splitPath(path: string): string[] {
  return path.split('/').filter(Boolean)
}

/**
 * Get status indicator
 */
function getStatusIndicator(status?: string): { color: string; text: string; icon: string } {
  switch (status) {
    case 'saving':
      return { color: 'text-heaven-accent-cyan', text: 'Saving...', icon: '◉' }
    case 'saved':
      return { color: 'text-heaven-accent-green', text: 'Saved', icon: '✓' }
    case 'unsaved':
      return { color: 'text-heaven-accent-orange', text: 'Unsaved', icon: '●' }
    case 'read-only':
      return { color: 'text-amber-500', text: 'Read-only', icon: '🔒' }
    default:
      return { color: 'text-heaven-text-tertiary', text: '', icon: '' }
  }
}

export function EditorHeader({
  filePath,
  status,
  language,
  gitStatus,
  showMinimap = true,
  onToggleMinimap,
  onFormat,
  onChangeLanguage,
  onToggleWordWrap,
  wordWrapEnabled = false,
  className,
}: EditorHeaderProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  
  const statusInfo = getStatusIndicator(status)
  const breadcrumbs = filePath ? splitPath(filePath) : []
  
  return (
    <div 
      className={cn(
        'h-9 bg-heaven-bg-secondary border-b border-white/5',
        'flex items-center justify-between px-4',
        className
      )}
    >
      {/* Left: Breadcrumbs */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {breadcrumbs.length > 0 ? (
          <nav 
            className="flex items-center gap-1 text-xs overflow-x-auto scrollbar-none"
            aria-label="File path"
          >
            {breadcrumbs.map((segment, index) => {
              const isLast = index === breadcrumbs.length - 1
              
              return (
                <div key={index} className="flex items-center gap-1 flex-shrink-0">
                  <button
                    className={cn(
                      'px-1.5 py-0.5 rounded transition-colors',
                      isLast
                        ? 'text-heaven-text-primary font-medium cursor-default'
                        : 'text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover'
                    )}
                    disabled={isLast}
                  >
                    {segment}
                  </button>
                  
                  {!isLast && (
                    <span className="text-heaven-text-tertiary">/</span>
                  )}
                </div>
              )
            })}
          </nav>
        ) : (
          <span className="text-xs text-heaven-text-tertiary italic">
            No file open
          </span>
        )}
        
        {/* Status indicator */}
        {status && (
          <div 
            className={cn(
              'flex items-center gap-1.5 ml-3 text-xs',
              statusInfo.color
            )}
          >
            <span>{statusInfo.icon}</span>
            <span>{statusInfo.text}</span>
          </div>
        )}
        
        {/* Git status */}
        {gitStatus && (
          <div className="flex items-center gap-1 ml-2 px-2 py-0.5 bg-heaven-bg-tertiary rounded text-xs">
            <span className="text-heaven-accent-orange">●</span>
            <span className="text-heaven-text-secondary capitalize">{gitStatus}</span>
          </div>
        )}
      </div>
      
      {/* Right: Action buttons */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {/* Language selector */}
        {language && onChangeLanguage && (
          <button
            onClick={onChangeLanguage}
            className="px-2 py-1 text-xs text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover rounded transition-colors"
            aria-label="Change language mode"
            title="Change language mode"
          >
            {language}
          </button>
        )}
        
        {/* Word wrap toggle */}
        {onToggleWordWrap && (
          <button
            onClick={onToggleWordWrap}
            className={cn(
              'p-1.5 text-xs rounded transition-colors',
              wordWrapEnabled
                ? 'text-heaven-accent-cyan bg-heaven-accent-cyan/10'
                : 'text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover'
            )}
            aria-label={wordWrapEnabled ? 'Disable word wrap' : 'Enable word wrap'}
            title={wordWrapEnabled ? 'Disable word wrap' : 'Enable word wrap'}
          >
            ⤸
          </button>
        )}
        
        {/* Minimap toggle */}
        {onToggleMinimap && (
          <button
            onClick={onToggleMinimap}
            className={cn(
              'p-1.5 text-xs rounded transition-colors',
              showMinimap
                ? 'text-heaven-accent-cyan bg-heaven-accent-cyan/10'
                : 'text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover'
            )}
            aria-label={showMinimap ? 'Hide minimap' : 'Show minimap'}
            title={showMinimap ? 'Hide minimap' : 'Show minimap'}
          >
            ▭
          </button>
        )}
        
        {/* Format document */}
        {onFormat && (
          <button
            onClick={onFormat}
            className="p-1.5 text-xs text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover rounded transition-colors"
            aria-label="Format document"
            title="Format document (Shift+Alt+F)"
          >
            ✨
          </button>
        )}
        
        {/* More options */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="p-1.5 text-xs text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover rounded transition-colors"
            aria-label="More options"
            aria-expanded={isDropdownOpen}
          >
            ⋯
          </button>
          
          {/* Dropdown menu */}
          {isDropdownOpen && (
            <>
              {/* Backdrop */}
              <div 
                className="fixed inset-0 z-40"
                onClick={() => setIsDropdownOpen(false)}
              />
              
              {/* Menu */}
              <div className="absolute right-0 top-full mt-1 w-48 bg-heaven-bg-tertiary border border-white/10 rounded-md shadow-xl z-50">
                <div className="py-1">
                  <button
                    onClick={() => {
                      onFormat?.()
                      setIsDropdownOpen(false)
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors"
                  >
                    <span className="flex items-center justify-between">
                      <span>Format Document</span>
                      <span className="text-heaven-text-tertiary">⇧⌥F</span>
                    </span>
                  </button>
                  
                  <button
                    onClick={() => {
                      onChangeLanguage?.()
                      setIsDropdownOpen(false)
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors"
                  >
                    Change Language Mode
                  </button>
                  
                  <div className="h-px bg-white/5 my-1" />
                  
                  <button
                    onClick={() => {
                      onToggleWordWrap?.()
                      setIsDropdownOpen(false)
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors"
                  >
                    <span className="flex items-center justify-between">
                      <span>Toggle Word Wrap</span>
                      {wordWrapEnabled && <span className="text-heaven-accent-green">✓</span>}
                    </span>
                  </button>
                  
                  <button
                    onClick={() => {
                      onToggleMinimap?.()
                      setIsDropdownOpen(false)
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors"
                  >
                    <span className="flex items-center justify-between">
                      <span>Toggle Minimap</span>
                      {showMinimap && <span className="text-heaven-accent-green">✓</span>}
                    </span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default EditorHeader
