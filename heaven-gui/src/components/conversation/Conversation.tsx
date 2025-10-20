import React from 'react';
import MessageList from './MessageList';
import { MessageProps } from './Message';

interface ConversationProps {
  messages: MessageProps[];
  title?: string;
  subtitle?: string;
  autoScroll?: boolean;
  headerActions?: React.ReactNode;
}

const Conversation: React.FC<ConversationProps> = ({
  messages,
  title,
  subtitle,
  autoScroll = true,
  headerActions,
}) => {
  return (
    <div className="flex flex-col h-full">
      {/* Conversation Header */}
      {(title || subtitle) && (
        <div className="px-6 py-4 border-b border-heaven-bg-tertiary">
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h2 className="text-lg font-semibold text-heaven-text-primary">
                  {title}
                </h2>
              )}
              {subtitle && (
                <p className="text-sm text-heaven-text-tertiary mt-1">
                  {subtitle}
                </p>
              )}
            </div>
            {headerActions && (
              <div className="flex items-center gap-2">
                {headerActions}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} autoScroll={autoScroll} />
      </div>
    </div>
  );
};

export default Conversation;
