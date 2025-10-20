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
      if (options.shift && !e.shiftKey) return
      if (options.ctrl && !e.ctrlKey) return
      if (options.alt && !e.altKey) return
      if (options.meta && !e.metaKey) return
      
      // If modifiers are required but not all are present, return
      const requiresModifier = options.shift || options.ctrl || options.alt || options.meta
      if (requiresModifier) {
        const hasRequiredModifiers = 
          (options.shift ? e.shiftKey : true) &&
          (options.ctrl ? e.ctrlKey : true) &&
          (options.alt ? e.altKey : true) &&
          (options.meta ? e.metaKey : true)
        
        if (!hasRequiredModifiers) return
      }
      
      e.preventDefault()
      toggle()
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [key, options])
  
  return {
    isVisible,
    toggle,
    show,
    hide
  }
}

export default useKeyboardVisibility
