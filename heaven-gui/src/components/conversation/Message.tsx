import React from 'react';

export type MessageRole = 'user' | 'assistant' | 'system';

export interface MessageProps {
  id: string;
  role: MessageRole;
  content: string;
  timestamp?: Date;
  isLoading?: boolean;
}

const Message: React.FC<MessageProps> = ({
  role,
  content,
  timestamp,
  isLoading = false,
}) => {
  const isUser = role === 'user';
  const isSystem = role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center py-2">
        <span className="text-xs text-heaven-text-muted bg-heaven-bg-tertiary px-3 py-1 rounded-full">
          {content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-up`}>
      <div className={`max-w-[80%] ${isUser ? 'ml-auto' : 'mr-auto'}`}>
        {/* Message Bubble */}
        <div
          className={`rounded-xl px-5 py-3 ${
            isUser
              ? 'bg-heaven-blue-primary/10 border border-heaven-blue-primary/30'
              : 'bg-heaven-bg-tertiary border border-heaven-bg-tertiary'
          }`}
        >
          {isLoading ? (
            <div className="flex gap-2 items-center py-2">
              <div className="w-2 h-2 bg-heaven-text-muted rounded-full animate-pulse-soft" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-heaven-text-muted rounded-full animate-pulse-soft" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-heaven-text-muted rounded-full animate-pulse-soft" style={{ animationDelay: '300ms' }} />
            </div>
          ) : (
            <p className="text-heaven-text-primary text-base leading-relaxed whitespace-pre-wrap break-words">
              {content}
            </p>
          )}
        </div>

        {/* Timestamp */}
        {timestamp && !isLoading && (
          <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mt-1 px-2`}>
            <span className="text-xs text-heaven-text-muted">
              {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default Message;
