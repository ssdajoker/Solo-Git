import React from 'react';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

const Header: React.FC<HeaderProps> = ({ 
  title = 'HEAVEN', 
  subtitle,
  actions 
}) => {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-heaven-bg-tertiary">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-semibold text-heaven-text-primary tracking-wider">
          {title}
        </h1>
        {subtitle && (
          <span className="text-sm text-heaven-text-tertiary">
            {subtitle}
          </span>
        )}
      </div>
      
      {actions && (
        <div className="flex items-center gap-2">
          {actions}
        </div>
      )}
    </header>
  );
};

export default Header;
