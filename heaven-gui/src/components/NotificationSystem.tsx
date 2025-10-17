
import { useState, useEffect } from 'react'
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
    <div className="notification-system">
      {notifications.map((notification) => (
        <div 
          key={notification.id} 
          className={`notification notification-${notification.type}`}
        >
          <span className="notification-icon">{getIcon(notification.type)}</span>
          <span className="notification-message">{notification.message}</span>
          <button 
            className="notification-dismiss" 
            onClick={() => onDismiss(notification.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
