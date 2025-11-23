/**
 * Hook for keyboard-controlled visibility
 * Used for toggling components with keyboard shortcuts
 */

import { useState, useEffect } from 'react'

export interface UseKeyboardVisibilityOptions {
  shift?: boolean
  ctrl?: boolean
  alt?: boolean
  meta?: boolean
}

export function useKeyboardVisibility(
  key: string,
  options: UseKeyboardVisibilityOptions = {}
) {
  const [isVisible, setIsVisible] = useState(false)
  const { shift = false, ctrl = false, alt = false, meta = false } = options
  
  const toggle = () => {
    setIsVisible(prev => !prev)
  }
  
  const show = () => {
    setIsVisible(true)
  }
  
  const hide = () => {
    setIsVisible(false)
  }
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if the key matches
      if (e.code !== key && e.key !== key) return
      
      // Check modifiers
      if (shift && !e.shiftKey) return
      if (ctrl && !e.ctrlKey) return
      if (alt && !e.altKey) return
      if (meta && !e.metaKey) return
      
      // If modifiers are required but not all are present, return
      const requiresModifier = shift || ctrl || alt || meta
      if (requiresModifier) {
        const hasRequiredModifiers = 
          (shift ? e.shiftKey : true) &&
          (ctrl ? e.ctrlKey : true) &&
          (alt ? e.altKey : true) &&
          (meta ? e.metaKey : true)
        
        if (!hasRequiredModifiers) return
      }
      
      e.preventDefault()
      toggle()
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [alt, ctrl, key, meta, shift])
  
  return {
    isVisible,
    toggle,
    show,
    hide
  }
}

export default useKeyboardVisibility
