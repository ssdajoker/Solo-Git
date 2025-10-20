
/**
 * Notification Manager
 * Queue system for toast notifications with priority levels and deduplication
 */

import { ToastType } from '../components/web/Toast'

export interface Notification {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
  priority?: 'low' | 'normal' | 'high' | 'critical'
  action?: {
    label: string
    onClick: () => void
  }
  timestamp: number
}

export type NotificationListener = (notifications: Notification[]) => void

class NotificationManager {
  private notifications: Map<string, Notification> = new Map()
  private listeners: Set<NotificationListener> = new Set()
  private maxNotifications = 5
  private recentlyDismissed: Set<string> = new Set() // For deduplication
  
  /**
   * Subscribe to notification changes
   */
  subscribe(listener: NotificationListener): () => void {
    this.listeners.add(listener)
    // Immediately call with current state
    listener(Array.from(this.notifications.values()))
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener)
    }
  }
  
  /**
   * Notify all listeners of changes
   */
  private notifyListeners() {
    const notifications = Array.from(this.notifications.values())
      .sort((a, b) => {
        // Sort by priority, then timestamp
        const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 }
        const aPriority = priorityOrder[a.priority || 'normal']
        const bPriority = priorityOrder[b.priority || 'normal']
        
        if (aPriority !== bPriority) {
          return aPriority - bPriority
        }
        
        return b.timestamp - a.timestamp // Newer first
      })
      .slice(0, this.maxNotifications) // Limit to max notifications
    
    this.listeners.forEach(listener => listener(notifications))
  }
  
  /**
   * Show a notification
   */
  show(notification: Omit<Notification, 'id' | 'timestamp'>): string {
    // Generate unique ID
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    
    // Check for deduplication (same title within 5 seconds)
    const dedupeKey = `${notification.type}-${notification.title}`
    if (this.recentlyDismissed.has(dedupeKey)) {
      console.log('[NotificationManager] Deduplicated notification:', notification.title)
      return id
    }
    
    const fullNotification: Notification = {
      ...notification,
      id,
      timestamp: Date.now(),
      priority: notification.priority || 'normal',
      duration: notification.duration ?? this.getDefaultDuration(notification.priority),
    }
    
    this.notifications.set(id, fullNotification)
    this.notifyListeners()
    
    // Auto-dismiss based on priority
    if (fullNotification.duration && fullNotification.duration > 0) {
      setTimeout(() => {
        this.dismiss(id)
      }, fullNotification.duration)
    }
    
    // Add to recently dismissed for deduplication
    this.recentlyDismissed.add(dedupeKey)
    setTimeout(() => {
      this.recentlyDismissed.delete(dedupeKey)
    }, 5000)
    
    return id
  }
  
  /**
   * Get default duration based on priority
   */
  private getDefaultDuration(priority?: 'low' | 'normal' | 'high' | 'critical'): number {
    switch (priority) {
      case 'low':
        return 2000
      case 'normal':
        return 3000
      case 'high':
        return 5000
      case 'critical':
        return 0 // Don't auto-dismiss critical
      default:
        return 3000
    }
  }
  
  /**
   * Dismiss a notification
   */
  dismiss(id: string) {
    if (this.notifications.delete(id)) {
      this.notifyListeners()
    }
  }
  
  /**
   * Dismiss all notifications
   */
  dismissAll() {
    this.notifications.clear()
    this.notifyListeners()
  }
  
  /**
   * Convenience methods for different notification types
   */
  success(title: string, message?: string, options?: Partial<Notification>) {
    return this.show({ type: 'success', title, message, ...options })
  }
  
  error(title: string, message?: string, options?: Partial<Notification>) {
    return this.show({ 
      type: 'error', 
      title, 
      message, 
      priority: 'high',
      ...options 
    })
  }
  
  warning(title: string, message?: string, options?: Partial<Notification>) {
    return this.show({ 
      type: 'warning', 
      title, 
      message, 
      priority: 'normal',
      ...options 
    })
  }
  
  info(title: string, message?: string, options?: Partial<Notification>) {
    return this.show({ type: 'info', title, message, ...options })
  }
  
  /**
   * Show a progress notification (no auto-dismiss)
   */
  progress(title: string, message?: string) {
    return this.show({ 
      type: 'info', 
      title, 
      message, 
      duration: 0,
      priority: 'normal'
    })
  }
}

// Export singleton instance
export const notifications = new NotificationManager()

// Export hook for React components
export { useNotifications } from '../hooks/useNotifications'
