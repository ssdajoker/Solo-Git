
/**
 * Hook to detect clicks outside a ref element
 */

import { useEffect, RefObject } from 'react'

export function useClickOutside(
  ref: RefObject<HTMLElement>,
  handler: (event: MouseEvent | TouchEvent) => void,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return
    
    const listener = (event: MouseEvent | TouchEvent) => {
      if (!ref.current || ref.current.contains(event.target as Node)) {
        return
      }
      handler(event)
    }
    
    document.addEventListener('mousedown', listener)
    document.addEventListener('touchstart', listener)
    
    return () => {
      document.removeEventListener('mousedown', listener)
      document.removeEventListener('touchstart', listener)
    }
  }, [ref, handler, enabled])
}
