import React, { useRef, useEffect } from 'react';
import Message, { MessageProps } from './Message';

interface MessageListProps {
  messages: MessageProps[];
  autoScroll?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({ 
  messages,
  autoScroll = true 
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, autoScroll]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-heaven-bg-tertiary flex items-center justify-center">
            <svg className="w-8 h-8 text-heaven-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-heaven-text-primary mb-2">No messages yet</h3>
          <p className="text-sm text-heaven-text-tertiary">Start a conversation by typing a message below</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 px-6 py-4">
      {messages.map((message) => (
        <Message key={message.id} {...message} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;
