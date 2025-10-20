import React, { useState, useRef, useEffect } from 'react';

export type BubbleInputState = 'idle' | 'focused' | 'sheet' | 'sending' | 'done';

interface BubbleInputProps {
  onSend?: (message: string) => void;
  onVoiceInput?: () => void;
  placeholder?: string;
  initialState?: BubbleInputState;
  disabled?: boolean;
}

const BubbleInput: React.FC<BubbleInputProps> = ({
  onSend,
  onVoiceInput,
  placeholder = 'Ask anything...',
  initialState = 'idle',
  disabled = false,
}) => {
  const [state, setState] = useState<BubbleInputState>(initialState);
  const [message, setMessage] = useState('');
  const [transcriptText, setTranscriptText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (state === 'focused' && inputRef.current) {
      inputRef.current.focus();
    }
    if (state === 'sheet' && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [state]);

  useEffect(() => {
    if (state === 'done') {
      const timer = setTimeout(() => {
        setState('idle');
        setTranscriptText('');
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [state]);

  const handleFocus = () => {
    if (state === 'idle') {
      setState('focused');
    }
  };

  const handleBlur = () => {
    if (state === 'focused' && !message) {
      setState('idle');
    }
  };

  const handleSend = () => {
    if (!message.trim() || disabled) return;
    
    setState('sending');
    onSend?.(message);
    
    // Simulate sending
    setTimeout(() => {
      setTranscriptText(message.slice(0, 50) + (message.length > 50 ? '...' : ''));
      setMessage('');
      setState('done');
    }, 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === 'Escape') {
      setState('idle');
      setMessage('');
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      setState('sheet');
    }
  };

  const handleVoiceClick = () => {
    onVoiceInput?.();
  };

  // Idle State
  if (state === 'idle') {
    return (
      <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40 animate-slide-up">
        <button
          onClick={handleFocus}
          className="flex items-center gap-3 px-6 py-3 bg-heaven-bg-secondary border border-heaven-bg-tertiary rounded-full shadow-2xl hover:bg-heaven-bg-tertiary transition-smooth focus-visible-ring"
          aria-label="Open input"
        >
          <span className="text-heaven-text-tertiary text-sm">{placeholder}</span>
          <svg className="w-5 h-5 text-heaven-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </button>
      </div>
    );
  }

  // Done State (Transcript Chip)
  if (state === 'done') {
    return (
      <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40 animate-fade-in">
        <div className="flex items-center gap-2 px-4 py-2 bg-heaven-blue-primary/20 border border-heaven-blue-primary/50 rounded-full shadow-xl">
          <svg className="w-4 h-4 text-heaven-blue-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-sm text-heaven-text-secondary truncate max-w-xs">
            {transcriptText}
          </span>
        </div>
      </div>
    );
  }

  // Sending State
  if (state === 'sending') {
    return (
      <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40">
        <div className="flex items-center gap-3 px-6 py-4 bg-heaven-bg-secondary border-2 border-heaven-blue-primary/50 rounded-3xl shadow-2xl w-[500px]">
          <div className="flex-1 text-heaven-text-secondary">{message}</div>
          <div className="flex gap-2 items-center">
            <svg className="w-5 h-5 text-heaven-blue-primary animate-pulse-soft" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
        </div>
      </div>
    );
  }

  // Focused State (Single-line)
  if (state === 'focused') {
    return (
      <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40 animate-slide-up">
        <div className="flex items-center gap-3 px-6 py-4 bg-heaven-bg-tertiary border-2 border-heaven-blue-primary rounded-full shadow-2xl w-[500px]">
          <input
            ref={inputRef}
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-heaven-text-primary placeholder-heaven-text-muted outline-none"
            disabled={disabled}
          />
          <div className="flex gap-2 items-center">
            <button
              onClick={handleVoiceClick}
              className="text-heaven-text-muted hover:text-heaven-accent-cyan transition-colors focus-visible-ring rounded"
              aria-label="Voice input"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </button>
            <button
              onClick={handleSend}
              disabled={!message.trim() || disabled}
              className={`transition-colors focus-visible-ring rounded ${
                message.trim() && !disabled
                  ? 'text-heaven-blue-primary hover:text-heaven-blue-hover'
                  : 'text-heaven-text-muted cursor-not-allowed'
              }`}
              aria-label="Send message"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
        <div className="text-center mt-2">
          <span className="text-xs text-heaven-text-muted">
            Press <kbd className="px-1.5 py-0.5 bg-heaven-bg-tertiary rounded text-heaven-text-secondary">⌘K</kbd> for multi-line
          </span>
        </div>
      </div>
    );
  }

  // Sheet State (Multi-line)
  if (state === 'sheet') {
    return (
      <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40 animate-slide-up">
        <div className="flex flex-col gap-3 p-6 bg-heaven-bg-tertiary border-2 border-heaven-blue-primary rounded-2xl shadow-2xl w-[600px]">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full h-40 bg-transparent text-heaven-text-primary placeholder-heaven-text-muted outline-none resize-none"
            disabled={disabled}
          />
          <div className="flex items-center justify-between">
            <div className="text-xs text-heaven-text-muted">
              Press <kbd className="px-1.5 py-0.5 bg-heaven-bg-secondary rounded text-heaven-text-secondary">Esc</kbd> to collapse
            </div>
            <div className="flex gap-2 items-center">
              <button
                onClick={handleVoiceClick}
                className="p-2 text-heaven-accent-cyan hover:bg-heaven-accent-cyan/10 rounded-lg transition-colors focus-visible-ring"
                aria-label="Voice input"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </button>
              <button
                onClick={handleSend}
                disabled={!message.trim() || disabled}
                className={`px-4 py-2 rounded-lg font-medium transition-colors focus-visible-ring ${
                  message.trim() && !disabled
                    ? 'bg-heaven-blue-primary text-white hover:bg-heaven-blue-hover'
                    : 'bg-heaven-bg-secondary text-heaven-text-muted cursor-not-allowed'
                }`}
                aria-label="Send message"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default BubbleInput;
