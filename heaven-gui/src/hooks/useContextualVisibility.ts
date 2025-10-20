
/**
 * Contextual Visibility Hook
 * Implements the "show on demand" pattern for UI elements
 */

import { useState, useEffect, useRef } from 'react'

export interface UseContextualVisibilityOptions {
  /** How long to wait before hiding (ms) */
  hideDelay?: number
  
  /** Show on initial mount */
  initiallyVisible?: boolean
  
  /** Keep visible while condition is true */
  keepVisibleWhen?: boolean
  
  /** Callback when visibility changes */
  onVisibilityChange?: (visible: boolean) => void
}

export function useContextualVisibility(
  options: UseContextualVisibilityOptions = {}
) {
  const {
    hideDelay = 5000,
    initiallyVisible = false,
    keepVisibleWhen = false,
    onVisibilityChange,
  } = options
  
  const [isVisible, setIsVisible] = useState(initiallyVisible)
  const hideTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const elementRef = useRef<HTMLElement | null>(null)
  
  // Clear hide timer
  const clearHideTimer = () => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = undefined
    }
  }
  
  // Show the element
  const show = () => {
    clearHideTimer()
    if (!isVisible) {
      setIsVisible(true)
      onVisibilityChange?.(true)
    }
  }
  
  // Hide the element (with optional delay)
  const hide = (immediate = false) => {
    clearHideTimer()
    
    if (keepVisibleWhen) {
      return // Don't hide if keepVisibleWhen is true
    }
    
    if (immediate) {
      setIsVisible(false)
      onVisibilityChange?.(false)
    } else if (hideDelay > 0) {
      hideTimerRef.current = setTimeout(() => {
        setIsVisible(false)
        onVisibilityChange?.(false)
      }, hideDelay)
    }
  }
  
  // Toggle visibility
  const toggle = () => {
    if (isVisible) {
      hide(true)
    } else {
      show()
    }
  }
  
  // Keep visible when condition changes
  useEffect(() => {
    if (keepVisibleWhen) {
      show()
    } else if (isVisible && !keepVisibleWhen) {
      hide()
    }
  }, [keepVisibleWhen])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearHideTimer()
    }
  }, [])
  
  // Ref callback to attach to element
  const ref = (node: HTMLElement | null) => {
    elementRef.current = node
  }
  
  // Mouse enter handler
  const onMouseEnter = () => {
    show()
  }
  
  // Mouse leave handler
  const onMouseLeave = () => {
    hide()
  }
  
  // Focus handler
  const onFocus = () => {
    show()
  }
  
  // Blur handler
  const onBlur = () => {
    hide()
  }
  
  return {
    isVisible,
    show,
    hide,
    toggle,
    ref,
    // Event handlers for easy attachment
    handlers: {
      onMouseEnter,
      onMouseLeave,
      onFocus,
      onBlur,
    },
  }
}

/**
 * Hook for hover-to-reveal pattern
 */
export function useHoverReveal(options: UseContextualVisibilityOptions = {}) {
  return useContextualVisibility({
    hideDelay: 500,
    ...options,
  })
}

/**
 * Hook for keyboard-triggered visibility
 */
export function useKeyboardVisibility(
  key: string,
  options: UseContextualVisibilityOptions = {}
) {
  const contextual = useContextualVisibility(options)
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === key || e.code === key) {
        contextual.toggle()
      }
    }
    
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        contextual.hide(true)
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [key])
  
  return contextual
}
