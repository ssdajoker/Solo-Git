import { useState, useEffect, useRef } from 'react'
import './InputDialog.css'

export interface InputDialogProps {
  isOpen: boolean
  title: string
  message?: string
  placeholder?: string
  defaultValue?: string
  confirmLabel?: string
  cancelLabel?: string
  multiline?: boolean
  rows?: number
  required?: boolean
  onConfirm: (value: string) => void
  onCancel: () => void
}

export default function InputDialog({
  isOpen,
  title,
  message,
  placeholder = '',
  defaultValue = '',
  confirmLabel = 'OK',
  cancelLabel = 'Cancel',
  multiline = false,
  rows = 4,
  required = false,
  onConfirm,
  onCancel,
}: InputDialogProps) {
  const [value, setValue] = useState(defaultValue)
  const inputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (isOpen) {
      setValue(defaultValue)
      // Focus the input when dialog opens
      setTimeout(() => {
        if (multiline) {
          textareaRef.current?.focus()
        } else {
          inputRef.current?.focus()
        }
      }, 100)
      
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen, defaultValue, multiline])

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    if (required && !value.trim()) {
      return
    }
    onConfirm(value)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel()
    } else if (e.key === 'Enter' && !multiline) {
      e.preventDefault()
      handleSubmit()
    }
  }

  if (!isOpen) return null

  return (
    <div 
      className="input-dialog-overlay"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="input-dialog-title"
      aria-describedby={message ? "input-dialog-message" : undefined}
    >
      <div 
        className="input-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="input-dialog-header">
            <h3 id="input-dialog-title">{title}</h3>
          </div>
          
          <div className="input-dialog-body">
            {message && <p id="input-dialog-message" className="input-dialog-message">{message}</p>}
            
            {multiline ? (
              <textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                rows={rows}
                className="input-dialog-textarea"
                required={required}
                aria-label={message || title}
                aria-required={required}
              />
            ) : (
              <input
                ref={inputRef}
                type="text"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                className="input-dialog-input"
                required={required}
                aria-label={message || title}
                aria-required={required}
              />
            )}
          </div>
          
          <div className="input-dialog-footer" role="group" aria-label="Dialog actions">
            <button
              type="button"
              onClick={onCancel}
              className="input-dialog-btn btn-cancel"
              aria-label={cancelLabel}
            >
              {cancelLabel}
            </button>
            <button
              type="submit"
              className="input-dialog-btn btn-confirm"
              disabled={required && !value.trim()}
              aria-label={confirmLabel}
              aria-disabled={required && !value.trim()}
            >
              {confirmLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
