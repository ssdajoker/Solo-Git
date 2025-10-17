
import { useEffect } from 'react'

export interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  cmd?: boolean
  shift?: boolean
  alt?: boolean
  action: () => void
  description: string
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[], enabled: boolean = true) {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey : true
        const cmdMatch = shortcut.cmd ? event.metaKey : true
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey
        const altMatch = shortcut.alt ? event.altKey : !event.altKey
        
        // Check if any modifier is required
        const requiresModifier = shortcut.ctrl || shortcut.cmd || shortcut.shift || shortcut.alt
        const hasCorrectModifiers = requiresModifier 
          ? (shortcut.ctrl && event.ctrlKey) || 
            (shortcut.cmd && event.metaKey) || 
            (shortcut.shift && event.shiftKey) || 
            (shortcut.alt && event.altKey)
          : !event.ctrlKey && !event.metaKey && !event.altKey

        if (
          event.key.toLowerCase() === shortcut.key.toLowerCase() &&
          hasCorrectModifiers &&
          ctrlMatch &&
          cmdMatch &&
          shiftMatch &&
          altMatch
        ) {
          event.preventDefault()
          shortcut.action()
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [shortcuts, enabled])
}

export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = []
  
  if (shortcut.ctrl) parts.push('Ctrl')
  if (shortcut.cmd) parts.push('Cmd')
  if (shortcut.shift) parts.push('Shift')
  if (shortcut.alt) parts.push('Alt')
  parts.push(shortcut.key.toUpperCase())
  
  return parts.join('+')
}
