
/**
 * Voice-Enabled Input Component
 */

import { useState, useRef } from 'react'
import { cn } from '../shared/utils'

export interface VoiceInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit?: () => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export function VoiceInput({
  value,
  onChange,
  onSubmit,
  placeholder = 'Type or hold to speak',
  disabled,
  className,
}: VoiceInputProps) {
  const [isRecording, setIsRecording] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  
  const handleVoiceClick = () => {
    // In production, this would use Web Speech API or Tauri plugin
    setIsRecording(!isRecording)
    console.log('Voice input toggled')
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit?.()
    }
  }
  
  return (
    <div className={cn(
      'h-input bg-heaven-bg-tertiary rounded-full px-5 flex items-center gap-3',
      'border border-white/5 focus-within:border-heaven-blue-primary focus-within:shadow-focus transition-all',
      disabled && 'opacity-50 cursor-not-allowed',
      className
    )}>
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 bg-transparent text-heaven-text-primary text-sm outline-none placeholder:text-heaven-text-tertiary disabled:cursor-not-allowed"
        aria-label={placeholder}
      />
      
      <button
        onClick={handleVoiceClick}
        disabled={disabled}
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center transition-all',
          'hover:bg-heaven-bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-heaven-blue-primary',
          isRecording && 'bg-heaven-accent-cyan text-heaven-bg-primary animate-pulse-subtle',
          !isRecording && 'text-heaven-accent-cyan'
        )}
        aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
      >
        <span className="text-lg" aria-hidden="true">
          {isRecording ? '⏸' : '🎤'}
        </span>
      </button>
    </div>
  )
}

export default VoiceInput
