
/**
 * React hook for using the notification system
 */

import { useState, useEffect } from 'react'
import { notifications, Notification } from '../utils/notifications'

export function useNotifications() {
  const [toasts, setToasts] = useState<Notification[]>([])
  
  useEffect(() => {
    const unsubscribe = notifications.subscribe(setToasts)
    return unsubscribe
  }, [])
  
  return {
    toasts,
    notifications, // Expose the manager for easy access
  }
}
