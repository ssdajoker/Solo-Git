/**
 * Editor Loading State Component
 * Beautiful loading skeleton for Monaco Editor
 */

import { cn } from '../shared/utils'

export interface EditorLoadingStateProps {
  /** Loading message */
  message?: string
  
  /** Custom className */
  className?: string
}

export function EditorLoadingState({
  message = 'Loading editor...',
  className,
}: EditorLoadingStateProps) {
  return (
    <div 
      className={cn(
        'flex flex-col h-full bg-heaven-bg-primary',
        className
      )}
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      {/* Loading indicator overlay */}
      <div className="absolute inset-0 flex items-center justify-center bg-heaven-bg-primary/90 backdrop-blur-sm z-10">
        <div className="flex flex-col items-center gap-4">
          {/* Spinner */}
          <div className="relative w-12 h-12">
            <div className="absolute inset-0 border-4 border-heaven-accent-cyan/20 rounded-full" />
            <div className="absolute inset-0 border-4 border-transparent border-t-heaven-accent-cyan rounded-full animate-spin" />
          </div>
          
          {/* Message */}
          <p className="text-sm text-heaven-text-secondary font-medium">
            {message}
          </p>
        </div>
      </div>
      
      {/* Skeleton UI */}
      <div className="flex-1 p-4 space-y-3">
        {/* Line number column skeleton */}
        <div className="flex gap-4">
          <div className="w-8 flex flex-col gap-3">
            {Array.from({ length: 20 }).map((_, i) => (
              <div 
                key={i}
                className="h-4 bg-heaven-bg-tertiary/30 rounded animate-pulse"
                style={{ animationDelay: `${i * 50}ms` }}
              />
            ))}
          </div>
          
          {/* Code lines skeleton */}
          <div className="flex-1 space-y-3">
            {Array.from({ length: 20 }).map((_, i) => {
              // Random widths for realistic code appearance
              const widths = ['60%', '80%', '90%', '50%', '70%', '85%', '65%', '95%']
              const width = widths[i % widths.length]
              
              return (
                <div 
                  key={i}
                  className="h-4 bg-heaven-bg-tertiary/30 rounded animate-pulse"
                  style={{ 
                    width,
                    animationDelay: `${i * 50}ms`
                  }}
                />
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

export default EditorLoadingState
