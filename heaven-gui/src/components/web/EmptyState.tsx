
/**
 * Empty State Component
 */

import { cn } from '../shared/utils'

export interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export function EmptyState({
  icon = '📦',
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center p-12 text-center',
      className
    )}>
      <div className="text-6xl mb-4 opacity-50" aria-hidden="true">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-heaven-text-primary mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-heaven-text-secondary max-w-md mb-6">
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-heaven-blue-primary hover:bg-heaven-blue-hover text-white rounded transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-heaven-blue-primary focus-visible:ring-offset-2 focus-visible:ring-offset-heaven-bg-primary"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

export default EmptyState
