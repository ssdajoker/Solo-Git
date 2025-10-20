import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

interface MainLayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  headerActions?: React.ReactNode;
  activeNavItem?: string;
  onNavItemClick?: (id: string) => void;
  showSidebar?: boolean;
}

const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  title,
  subtitle,
  headerActions,
  activeNavItem,
  onNavItemClick,
  showSidebar = true,
}) => {
  return (
    <div className="flex h-screen bg-heaven-bg-primary overflow-hidden">
      {/* Sidebar */}
      {showSidebar && (
        <Sidebar 
          activeId={activeNavItem} 
          onItemClick={onNavItemClick}
        />
      )}

      {/* Main Content Area */}
      <main 
        className={`flex-1 flex flex-col overflow-hidden ${
          showSidebar ? 'ml-sidebar' : ''
        }`}
      >
        {/* Header */}
        {(title || subtitle || headerActions) && (
          <Header 
            title={title}
            subtitle={subtitle}
            actions={headerActions}
          />
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
