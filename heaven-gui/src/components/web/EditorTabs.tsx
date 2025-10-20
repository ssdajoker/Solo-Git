/**
 * Editor Tabs Component
 * Manages multiple open files with tabs matching Heaven UI design
 */

import { useState, useRef, useEffect } from 'react'
import { cn, getFileIcon } from '../shared/utils'
import type { GitFileStatus } from '../shared/types'

export interface EditorTab {
  /** Unique identifier for the tab */
  id: string
  
  /** File path */
  path: string
  
  /** File name (derived from path) */
  name: string
  
  /** Whether the file has unsaved changes */
  isDirty: boolean
  
  /** Whether the file is read-only */
  isReadOnly?: boolean
  
  /** Git status of the file */
  gitStatus?: GitFileStatus
}

export interface EditorTabsProps {
  /** Array of open tabs */
  tabs: EditorTab[]
  
  /** Currently active tab ID */
  activeTabId: string | null
  
  /** Callback when a tab is clicked */
  onTabClick: (tabId: string) => void
  
  /** Callback when a tab close button is clicked */
  onTabClose: (tabId: string) => void
  
  /** Callback when user attempts to close a dirty tab (returns false to cancel) */
  onBeforeTabClose?: (tabId: string) => Promise<boolean>
  
  /** Custom className */
  className?: string
}

/**
 * Get git status indicator color and symbol
 */
function getGitStatusIndicator(status?: GitFileStatus): { color: string; symbol: string } | null {
  if (!status) return null
  
  switch (status) {
    case 'modified':
      return { color: 'text-heaven-accent-orange', symbol: 'M' }
    case 'added':
      return { color: 'text-heaven-accent-green', symbol: 'A' }
    case 'deleted':
      return { color: 'text-heaven-accent-red', symbol: 'D' }
    case 'renamed':
      return { color: 'text-heaven-accent-cyan', symbol: 'R' }
    case 'untracked':
      return { color: 'text-heaven-accent-purple', symbol: 'U' }
    default:
      return null
  }
}

export function EditorTabs({
  tabs,
  activeTabId,
  onTabClick,
  onTabClose,
  onBeforeTabClose,
  className,
}: EditorTabsProps) {
  const tabsContainerRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)
  
  // Check scroll position
  const checkScroll = () => {
    const container = tabsContainerRef.current
    if (!container) return
    
    setCanScrollLeft(container.scrollLeft > 0)
    setCanScrollRight(
      container.scrollLeft < container.scrollWidth - container.clientWidth - 1
    )
  }
  
  useEffect(() => {
    checkScroll()
    window.addEventListener('resize', checkScroll)
    return () => window.removeEventListener('resize', checkScroll)
  }, [tabs])
  
  // Scroll tabs
  const scrollTabs = (direction: 'left' | 'right') => {
    const container = tabsContainerRef.current
    if (!container) return
    
    const scrollAmount = 200
    const newPosition = direction === 'left' 
      ? container.scrollLeft - scrollAmount
      : container.scrollLeft + scrollAmount
    
    container.scrollTo({ left: newPosition, behavior: 'smooth' })
  }
  
  // Handle tab close with confirmation
  const handleTabClose = async (e: React.MouseEvent, tabId: string) => {
    e.stopPropagation() // Prevent tab activation
    
    if (onBeforeTabClose) {
      const shouldClose = await onBeforeTabClose(tabId)
      if (!shouldClose) return
    }
    
    onTabClose(tabId)
  }
  
  // Scroll active tab into view
  useEffect(() => {
    if (!activeTabId || !tabsContainerRef.current) return
    
    const activeTabElement = tabsContainerRef.current.querySelector(
      `[data-tab-id="${activeTabId}"]`
    ) as HTMLElement
    
    if (activeTabElement) {
      activeTabElement.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      })
    }
  }, [activeTabId])
  
  if (tabs.length === 0) return null
  
  return (
    <div 
      className={cn(
        'flex items-center h-10 bg-heaven-bg-secondary border-b border-white/5',
        className
      )}
      role="tablist"
      aria-label="Open files"
    >
      {/* Left scroll button */}
      {canScrollLeft && (
        <button
          onClick={() => scrollTabs('left')}
          className="flex-shrink-0 px-2 h-full text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover transition-all"
          aria-label="Scroll tabs left"
        >
          ‹
        </button>
      )}
      
      {/* Tabs container */}
      <div
        ref={tabsContainerRef}
        className="flex-1 flex overflow-x-auto scrollbar-none"
        onScroll={checkScroll}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTabId
          const gitIndicator = getGitStatusIndicator(tab.gitStatus)
          const icon = getFileIcon(tab.name)
          
          return (
            <button
              key={tab.id}
              data-tab-id={tab.id}
              onClick={() => onTabClick(tab.id)}
              role="tab"
              aria-selected={isActive}
              aria-label={`${tab.name}${tab.isDirty ? ' (modified)' : ''}${tab.isReadOnly ? ' (read-only)' : ''}`}
              className={cn(
                'group flex items-center gap-2 px-3 h-full border-r border-white/5',
                'transition-all duration-150 flex-shrink-0 max-w-[200px]',
                isActive
                  ? 'bg-heaven-bg-primary text-heaven-text-primary border-t-2 border-t-heaven-accent-cyan'
                  : 'bg-heaven-bg-secondary text-heaven-text-secondary hover:bg-heaven-bg-hover hover:text-heaven-text-primary border-t-2 border-t-transparent'
              )}
            >
              {/* File icon */}
              <span 
                className="flex-shrink-0 text-base"
                style={{ color: icon.color }}
              >
                {icon.icon}
              </span>
              
              {/* File name */}
              <span className="flex-1 truncate text-xs font-medium">
                {tab.name}
              </span>
              
              {/* Git status indicator */}
              {gitIndicator && (
                <span 
                  className={cn('flex-shrink-0 text-[10px] font-bold', gitIndicator.color)}
                  aria-label={`Git status: ${tab.gitStatus}`}
                >
                  {gitIndicator.symbol}
                </span>
              )}
              
              {/* Dirty indicator */}
              {tab.isDirty && (
                <span 
                  className="flex-shrink-0 w-2 h-2 rounded-full bg-heaven-accent-orange"
                  aria-label="Unsaved changes"
                />
              )}
              
              {/* Read-only indicator */}
              {tab.isReadOnly && (
                <span 
                  className="flex-shrink-0 text-[10px] text-amber-500"
                  aria-label="Read-only"
                >
                  🔒
                </span>
              )}
              
              {/* Close button */}
              <button
                onClick={(e) => handleTabClose(e, tab.id)}
                className={cn(
                  'flex-shrink-0 w-4 h-4 rounded flex items-center justify-center',
                  'text-heaven-text-tertiary hover:text-heaven-text-primary hover:bg-heaven-bg-tertiary',
                  'transition-all duration-150',
                  'opacity-0 group-hover:opacity-100',
                  isActive && 'opacity-100'
                )}
                aria-label={`Close ${tab.name}`}
              >
                ×
              </button>
            </button>
          )
        })}
      </div>
      
      {/* Right scroll button */}
      {canScrollRight && (
        <button
          onClick={() => scrollTabs('right')}
          className="flex-shrink-0 px-2 h-full text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover transition-all"
          aria-label="Scroll tabs right"
        >
          ›
        </button>
      )}
    </div>
  )
}

export default EditorTabs
