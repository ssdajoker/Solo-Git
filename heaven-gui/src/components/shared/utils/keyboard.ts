
/**
 * Keyboard utilities and helpers
 */

export function isMacOS(): boolean {
  if (typeof navigator === 'undefined') return false
  return navigator.platform.toUpperCase().indexOf('MAC') >= 0
}

export function getModifierKey(): 'Cmd' | 'Ctrl' {
  return isMacOS() ? 'Cmd' : 'Ctrl'
}

export function formatShortcut(shortcut: string): string {
  return shortcut.replace('Cmd', isMacOS() ? '⌘' : 'Ctrl')
}

export function matchesShortcut(
  event: KeyboardEvent,
  key: string,
  modifiers?: {
    cmd?: boolean
    ctrl?: boolean
    shift?: boolean
    alt?: boolean
  }
): boolean {
  const keyMatch = event.key.toLowerCase() === key.toLowerCase()
  const cmdMatch = modifiers?.cmd ? (isMacOS() ? event.metaKey : event.ctrlKey) : true
  const ctrlMatch = modifiers?.ctrl ? event.ctrlKey : true
  const shiftMatch = modifiers?.shift ? event.shiftKey : true
  const altMatch = modifiers?.alt ? event.altKey : true
  
  return keyMatch && cmdMatch && ctrlMatch && shiftMatch && altMatch
}
