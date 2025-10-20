
/**
 * Hook to trap focus within a component (for modals)
 */

import { useEffect, RefObject } from 'react'

export function useFocusTrap(ref: RefObject<HTMLElement>, enabled: boolean = true) {
  useEffect(() => {
    if (!enabled || !ref.current) return
    
    const element = ref.current
    const focusableElements = element.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    
    if (focusableElements.length === 0) return
    
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]
    
    // Focus first element on mount
    firstElement.focus()
    
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return
      
      if (event.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          event.preventDefault()
          lastElement.focus()
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          event.preventDefault()
          firstElement.focus()
        }
      }
    }
    
    element.addEventListener('keydown', handleKeyDown)
    
    return () => {
      element.removeEventListener('keydown', handleKeyDown)
    }
  }, [ref, enabled])
}
