import React from 'react';
import ActionItem, { ActionItemProps } from './ActionItem';

interface ActionListProps {
  title?: string;
  actions: ActionItemProps[];
  maxWidth?: string;
}

const ActionList: React.FC<ActionListProps> = ({ 
  title,
  actions,
  maxWidth = 'max-w-md'
}) => {
  return (
    <div className={`w-full ${maxWidth} mx-auto px-6 py-8 animate-slide-up`}>
      {title && (
        <h3 className="text-lg font-semibold text-heaven-text-primary mb-4">
          {title}
        </h3>
      )}
      
      <div className="flex flex-col gap-2">
        {actions.map((action) => (
          <ActionItem key={action.id} {...action} />
        ))}
      </div>
    </div>
  );
};

export default ActionList;
