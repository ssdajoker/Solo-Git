
/**
 * Toast Container Component
 * Manages the display and stacking of toast notifications
 */

import { Toast, ToastProps } from './Toast'
import { cn } from '../shared/utils'

export interface ToastContainerProps {
  toasts: ToastProps[]
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
  className?: string
}

const positionClasses: Record<string, string> = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
}

export function ToastContainer({
  toasts,
  position = 'top-right',
  className,
}: ToastContainerProps) {
  if (toasts.length === 0) return null
  
  return (
    <div
      className={cn(
        'fixed z-toast pointer-events-none',
        'flex flex-col gap-3',
        positionClasses[position],
        className
      )}
      aria-live="polite"
      aria-atomic="false"
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} />
      ))}
    </div>
  )
}

export default ToastContainer
