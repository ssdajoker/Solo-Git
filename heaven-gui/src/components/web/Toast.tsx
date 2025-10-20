
/**
 * Toast Notification Component
 * Fading pop-up notifications following the "No UI" philosophy
 */

import { useEffect, useState } from 'react'
import { cn } from '../shared/utils'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastProps {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number // milliseconds, 0 = no auto-dismiss
  onClose: (id: string) => void
  action?: {
    label: string
    onClick: () => void
  }
}

const toastIcons: Record<ToastType, string> = {
  success: '✓',
  error: '✗',
  warning: '⚠',
  info: 'ℹ',
}

const toastColors: Record<ToastType, string> = {
  success: 'border-heaven-accent-green/50 bg-heaven-accent-green/10 text-heaven-accent-green',
  error: 'border-heaven-accent-red/50 bg-heaven-accent-red/10 text-heaven-accent-red',
  warning: 'border-heaven-accent-orange/50 bg-heaven-accent-orange/10 text-heaven-accent-orange',
  info: 'border-heaven-accent-cyan/50 bg-heaven-accent-cyan/10 text-heaven-accent-cyan',
}

export function Toast({
  id,
  type,
  title,
  message,
  duration = 3000,
  onClose,
  action,
}: ToastProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [progress, setProgress] = useState(100)
  
  useEffect(() => {
    // Fade in
    requestAnimationFrame(() => {
      setIsVisible(true)
    })
    
    // Auto-dismiss
    if (duration > 0) {
      const startTime = Date.now()
      const interval = 50 // Update every 50ms for smooth animation
      
      const progressTimer = setInterval(() => {
        const elapsed = Date.now() - startTime
        const remaining = Math.max(0, 100 - (elapsed / duration) * 100)
        setProgress(remaining)
      }, interval)
      
      const dismissTimer = setTimeout(() => {
        handleClose()
      }, duration)
      
      return () => {
        clearInterval(progressTimer)
        clearTimeout(dismissTimer)
      }
    }
  }, [duration])
  
  const handleClose = () => {
    setIsVisible(false)
    // Wait for fade-out animation before removing
    setTimeout(() => {
      onClose(id)
    }, 150)
  }
  
  const handleActionClick = () => {
    action?.onClick()
    handleClose()
  }
  
  return (
    <div
      className={cn(
        'min-w-[320px] max-w-[480px] rounded-lg border backdrop-blur-sm shadow-lg',
        'transition-all duration-150 ease-in-out',
        'transform pointer-events-auto',
        isVisible 
          ? 'translate-x-0 opacity-100' 
          : 'translate-x-full opacity-0',
        toastColors[type]
      )}
      role="alert"
      aria-live="polite"
    >
      {/* Progress Bar */}
      {duration > 0 && (
        <div className="h-1 bg-white/10 rounded-t-lg overflow-hidden">
          <div
            className="h-full bg-white/30 transition-all duration-50 ease-linear"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
      
      {/* Content */}
      <div className="p-4 flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center text-base font-bold">
          {toastIcons[type]}
        </div>
        
        {/* Text Content */}
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-heaven-text-primary mb-1">
            {title}
          </h4>
          {message && (
            <p className="text-xs text-heaven-text-secondary leading-relaxed">
              {message}
            </p>
          )}
          
          {/* Action Button */}
          {action && (
            <button
              onClick={handleActionClick}
              className="mt-2 text-xs font-medium underline hover:no-underline transition-all"
            >
              {action.label}
            </button>
          )}
        </div>
        
        {/* Close Button */}
        <button
          onClick={handleClose}
          className="flex-shrink-0 w-5 h-5 flex items-center justify-center
                   text-heaven-text-tertiary hover:text-heaven-text-primary
                   transition-colors"
          aria-label="Close notification"
        >
          ×
        </button>
      </div>
    </div>
  )
}

export default Toast
