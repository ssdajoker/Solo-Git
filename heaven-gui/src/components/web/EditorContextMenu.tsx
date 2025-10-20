/**
 * Editor Context Menu Component
 * Right-click context menu for Monaco Editor
 */

import { useEffect, useRef } from 'react'
import { cn } from '../shared/utils'

export interface EditorContextMenuItem {
  /** Unique identifier */
  id: string
  
  /** Menu item label */
  label: string
  
  /** Keyboard shortcut to display */
  shortcut?: string
  
  /** Whether the item is disabled */
  disabled?: boolean
  
  /** Whether this is a separator */
  separator?: boolean
  
  /** Action to perform */
  action?: () => void
}

export interface EditorContextMenuProps {
  /** Menu items to display */
  items: EditorContextMenuItem[]
  
  /** Position of the menu */
  position: { x: number; y: number } | null
  
  /** Callback when menu closes */
  onClose: () => void
  
  /** Custom className */
  className?: string
}

export function EditorContextMenu({
  items,
  position,
  onClose,
  className,
}: EditorContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)
  
  // Close on click outside
  useEffect(() => {
    if (!position) return
    
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [position, onClose])
  
  // Position adjustment to keep menu in viewport
  useEffect(() => {
    if (!position || !menuRef.current) return
    
    const menu = menuRef.current
    const rect = menu.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    
    let { x, y } = position
    
    // Adjust horizontal position
    if (x + rect.width > viewportWidth) {
      x = viewportWidth - rect.width - 10
    }
    
    // Adjust vertical position
    if (y + rect.height > viewportHeight) {
      y = viewportHeight - rect.height - 10
    }
    
    menu.style.left = `${x}px`
    menu.style.top = `${y}px`
  }, [position])
  
  if (!position) return null
  
  const handleItemClick = (item: EditorContextMenuItem) => {
    if (item.disabled || item.separator) return
    
    item.action?.()
    onClose()
  }
  
  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-[100]"
        onClick={onClose}
      />
      
      {/* Menu */}
      <div
        ref={menuRef}
        className={cn(
          'fixed z-[101] min-w-[200px] max-w-[300px]',
          'bg-heaven-bg-tertiary border border-white/10 rounded-md shadow-2xl',
          'py-1 overflow-hidden',
          className
        )}
        style={{ left: position.x, top: position.y }}
        role="menu"
        aria-label="Context menu"
      >
        {items.map((item, index) => {
          if (item.separator) {
            return (
              <div 
                key={item.id || `separator-${index}`}
                className="h-px bg-white/5 my-1"
                role="separator"
              />
            )
          }
          
          return (
            <button
              key={item.id}
              onClick={() => handleItemClick(item)}
              disabled={item.disabled}
              role="menuitem"
              className={cn(
                'w-full px-3 py-2 text-left text-sm',
                'flex items-center justify-between gap-4',
                'transition-colors',
                item.disabled
                  ? 'text-heaven-text-tertiary cursor-not-allowed'
                  : 'text-heaven-text-secondary hover:text-heaven-text-primary hover:bg-heaven-bg-hover cursor-pointer'
              )}
            >
              <span className="flex-1">{item.label}</span>
              
              {item.shortcut && (
                <span className="text-xs text-heaven-text-tertiary font-mono">
                  {item.shortcut}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </>
  )
}

export default EditorContextMenu
