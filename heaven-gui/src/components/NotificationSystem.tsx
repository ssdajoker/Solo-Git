
import { useEffect } from 'react'
import './NotificationSystem.css'

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

interface NotificationSystemProps {
  notifications: Notification[]
  onDismiss: (id: string) => void
}

export default function NotificationSystem({ notifications, onDismiss }: NotificationSystemProps) {
  useEffect(() => {
    notifications.forEach((notification) => {
      if (notification.duration) {
        const timer = setTimeout(() => {
          onDismiss(notification.id)
        }, notification.duration)
        
        return () => clearTimeout(timer)
      }
    })
  }, [notifications, onDismiss])

  const getIcon = (type: string) => {
    switch (type) {
      case 'success': return '✓'
      case 'error': return '✗'
      case 'warning': return '⚠'
      case 'info': return 'ℹ'
      default: return '●'
    }
  }

  return (
    <div 
      className="notification-system" 
      role="region" 
      aria-label="Notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      {notifications.map((notification) => (
        <div 
          key={notification.id} 
          className={`notification notification-${notification.type}`}
          role="alert"
          aria-live={notification.type === 'error' ? 'assertive' : 'polite'}
        >
          <span 
            className="notification-icon" 
            aria-hidden="true"
          >
            {getIcon(notification.type)}
          </span>
          <span className="notification-message">
            {notification.message}
          </span>
          <button 
            className="notification-dismiss" 
            onClick={() => onDismiss(notification.id)}
            aria-label={`Dismiss ${notification.type} notification: ${notification.message}`}
            title="Dismiss notification"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
