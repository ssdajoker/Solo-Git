import React from 'react';

interface SidebarItem {
  id: string;
  icon: React.ReactNode;
  color: string;
  label: string;
  onClick?: () => void;
}

interface SidebarProps {
  items?: SidebarItem[];
  activeId?: string;
  onItemClick?: (id: string) => void;
}

const defaultItems: SidebarItem[] = [
  {
    id: 'chat',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
    color: 'orange',
    label: 'Chat',
  },
  {
    id: 'files',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
    ),
    color: 'green',
    label: 'Files',
  },
  {
    id: 'search',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
    color: 'cyan',
    label: 'Search',
  },
  {
    id: 'settings',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    color: 'purple',
    label: 'Settings',
  },
  {
    id: 'help',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    color: 'red',
    label: 'Help',
  },
];

const colorClasses = {
  orange: 'text-heaven-accent-orange hover:bg-heaven-accent-orange/10 active:bg-heaven-accent-orange/20',
  green: 'text-heaven-accent-green hover:bg-heaven-accent-green/10 active:bg-heaven-accent-green/20',
  cyan: 'text-heaven-accent-cyan hover:bg-heaven-accent-cyan/10 active:bg-heaven-accent-cyan/20',
  purple: 'text-heaven-accent-purple hover:bg-heaven-accent-purple/10 active:bg-heaven-accent-purple/20',
  red: 'text-heaven-accent-red hover:bg-heaven-accent-red/10 active:bg-heaven-accent-red/20',
  pink: 'text-heaven-accent-pink hover:bg-heaven-accent-pink/10 active:bg-heaven-accent-pink/20',
};

const activeColorClasses = {
  orange: 'bg-heaven-accent-orange text-white',
  green: 'bg-heaven-accent-green text-white',
  cyan: 'bg-heaven-accent-cyan text-white',
  purple: 'bg-heaven-accent-purple text-white',
  red: 'bg-heaven-accent-red text-white',
  pink: 'bg-heaven-accent-pink text-white',
};

const Sidebar: React.FC<SidebarProps> = ({ 
  items = defaultItems, 
  activeId,
  onItemClick 
}) => {
  return (
    <aside className="fixed left-0 top-0 h-screen w-sidebar bg-heaven-bg-secondary border-r border-heaven-bg-tertiary flex flex-col items-center py-4 z-50">
      {/* Logo/Brand */}
      <div className="mb-8">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-heaven-blue-primary to-heaven-accent-purple flex items-center justify-center">
          <span className="text-white font-bold text-lg">H</span>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 flex flex-col gap-3">
        {items.map((item) => {
          const isActive = activeId === item.id;
          const baseClasses = 'w-10 h-10 rounded-lg flex items-center justify-center transition-smooth cursor-pointer focus-visible-ring';
          const colorClass = colorClasses[item.color as keyof typeof colorClasses] || colorClasses.cyan;
          const activeClass = isActive ? activeColorClasses[item.color as keyof typeof activeColorClasses] : '';
          
          return (
            <button
              key={item.id}
              onClick={() => {
                onItemClick?.(item.id);
                item.onClick?.();
              }}
              className={`${baseClasses} ${isActive ? activeClass : colorClass}`}
              aria-label={item.label}
              title={item.label}
            >
              {item.icon}
            </button>
          );
        })}
      </nav>

      {/* Bottom Actions (optional) */}
      <div className="mt-auto">
        {/* Add any bottom actions here if needed */}
      </div>
    </aside>
  );
};

export default Sidebar;
