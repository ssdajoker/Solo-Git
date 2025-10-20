
/**
 * Enhanced Voice-Enabled Input Component with Waveform Visualization
 */

import { useState, useRef, useEffect } from 'react'
import { cn } from '../shared/utils'

export interface VoiceInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit?: () => void
  placeholder?: string
  disabled?: boolean
  showWaveform?: boolean
  className?: string
}

export function VoiceInput({
  value,
  onChange,
  onSubmit,
  placeholder = 'Type or hold to speak',
  disabled,
  showWaveform = true,
  className,
}: VoiceInputProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [waveformData, setWaveformData] = useState<number[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const animationRef = useRef<number>()
  
  // Simulate waveform animation when recording
  useEffect(() => {
    if (isRecording) {
      const animate = () => {
        // Generate random waveform data (simulated audio levels)
        const newData = Array.from({ length: 20 }, () => Math.random() * 100)
        setWaveformData(newData)
        animationRef.current = requestAnimationFrame(animate)
      }
      animate()
      
      return () => {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current)
        }
      }
    } else {
      setWaveformData([])
    }
  }, [isRecording])
  
  const handleVoiceClick = () => {
    if (!isRecording) {
      // Start recording
      setIsRecording(true)
      setTranscript('')
      
      // In production, this would initialize Web Speech API or Tauri plugin
      // Example: const recognition = new webkitSpeechRecognition()
      // recognition.start()
      
      // Simulate transcription after 2 seconds
      setTimeout(() => {
        const mockTranscript = "Create a new React component named"
        setTranscript(mockTranscript)
        onChange(value + (value ? ' ' : '') + mockTranscript)
      }, 2000)
    } else {
      // Stop recording
      setIsRecording(false)
      setTranscript('')
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit?.()
    }
  }
  
  // Hold spacebar to record
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && e.ctrlKey && !isRecording && inputRef.current !== document.activeElement) {
        e.preventDefault()
        handleVoiceClick()
      }
    }
    
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space' && isRecording) {
        e.preventDefault()
        handleVoiceClick()
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [isRecording])
  
  return (
    <div className={cn('relative', className)}>
      {/* Main Input Container */}
      <div className={cn(
        'h-input bg-heaven-bg-tertiary rounded-full px-5 flex items-center gap-3',
        'border border-white/5 focus-within:border-heaven-blue-primary focus-within:shadow-focus transition-all',
        disabled && 'opacity-50 cursor-not-allowed',
        isRecording && 'border-heaven-accent-cyan ring-2 ring-heaven-accent-cyan/20'
      )}>
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isRecording ? 'Listening...' : placeholder}
          disabled={disabled}
          className="flex-1 bg-transparent text-heaven-text-primary text-sm outline-none placeholder:text-heaven-text-tertiary disabled:cursor-not-allowed"
          aria-label={placeholder}
          aria-live="polite"
        />
        
        {/* Recording Indicator */}
        {isRecording && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-heaven-accent-red animate-pulse" />
            <span className="text-xs text-heaven-text-secondary">Recording</span>
          </div>
        )}
        
        {/* Voice Button */}
        <button
          onClick={handleVoiceClick}
          disabled={disabled}
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center transition-all relative',
            'hover:bg-heaven-bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-heaven-blue-primary',
            isRecording && 'bg-heaven-accent-cyan text-heaven-bg-primary scale-110',
            !isRecording && 'text-heaven-accent-cyan'
          )}
          aria-label={isRecording ? 'Stop recording (or release Ctrl+Space)' : 'Start voice input (or hold Ctrl+Space)'}
          title={isRecording ? 'Stop recording' : 'Click or Ctrl+Space'}
        >
          <span className="text-lg" aria-hidden="true">
            {isRecording ? '⏸' : '🎤'}
          </span>
          
          {/* Pulse animation ring */}
          {isRecording && (
            <span className="absolute inset-0 rounded-full border-2 border-heaven-accent-cyan animate-ping" />
          )}
        </button>
      </div>
      
      {/* Waveform Visualization */}
      {showWaveform && isRecording && (
        <div className="absolute -bottom-12 left-0 right-0 h-8 flex items-end justify-center gap-1 px-5">
          {waveformData.map((height, index) => (
            <div
              key={index}
              className="w-1 bg-heaven-accent-cyan rounded-full transition-all duration-100"
              style={{ height: `${Math.max(height / 4, 4)}px` }}
              aria-hidden="true"
            />
          ))}
        </div>
      )}
      
      {/* Transcript Preview (appears below input) */}
      {transcript && isRecording && (
        <div className="absolute -bottom-16 left-0 right-0 px-5">
          <div className="bg-heaven-bg-secondary border border-white/10 rounded-lg p-3 text-sm">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-heaven-text-tertiary">Transcript</span>
              <span className="text-xs text-heaven-accent-cyan">●  Live</span>
            </div>
            <p className="text-heaven-text-primary" aria-live="polite">
              {transcript}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default VoiceInput
