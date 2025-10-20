import React from 'react';

export interface ActionItemProps {
  id: string;
  icon?: React.ReactNode;
  title: string;
  description?: string;
  onClick?: () => void;
  disabled?: boolean;
}

const ActionItem: React.FC<ActionItemProps> = ({
  icon,
  title,
  description,
  onClick,
  disabled = false,
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full flex items-center gap-4 p-4 bg-heaven-bg-secondary border border-heaven-bg-tertiary rounded-lg hover:bg-heaven-bg-tertiary hover:border-heaven-blue-primary/50 transition-smooth focus-visible-ring disabled:opacity-50 disabled:cursor-not-allowed text-left group"
    >
      {icon && (
        <div className="flex-shrink-0 text-heaven-text-muted group-hover:text-heaven-blue-primary transition-colors">
          {icon}
        </div>
      )}
      
      <div className="flex-1 min-w-0">
        <div className="text-heaven-text-primary font-medium group-hover:text-heaven-blue-primary transition-colors">
          {title}
        </div>
        {description && (
          <div className="text-sm text-heaven-text-tertiary mt-0.5 truncate">
            {description}
          </div>
        )}
      </div>

      <div className="flex-shrink-0 text-heaven-text-muted group-hover:text-heaven-blue-primary transition-colors">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </button>
  );
};

export default ActionItem;
