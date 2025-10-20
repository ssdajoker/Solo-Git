/**
 * Enhanced Command Palette Component
 * Features: AI suggestions, command grouping, keyboard navigation
 */

import { useState, useRef, useEffect } from 'react'
import { CommandPaletteProps, Command, CommandGroup } from '../shared/types'
import { useClickOutside, useFocusTrap, useDebounce } from '../shared/hooks'
import { cn, formatShortcut } from '../shared/utils'

export function CommandPalette({
  isOpen,
  onClose,
  commands = [],
  aiSuggestions = [],
  placeholder = 'Search commands...',
  className,
  'aria-label': ariaLabel = 'Command Palette',
}: CommandPaletteProps) {
  const [search, setSearch] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const modalRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const debouncedSearch = useDebounce(search, 150)
  
  useClickOutside(modalRef, () => isOpen && onClose(), isOpen)
  useFocusTrap(modalRef, isOpen)
  
  // Reset state when opening
  useEffect(() => {
    if (isOpen) {
      setSearch('')
      setSelectedIndex(0)
      inputRef.current?.focus()
    }
  }, [isOpen])
  
  // Filter commands based on search
  const filteredCommands = commands.filter(cmd =>
    cmd.label.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
    cmd.description?.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
    cmd.category.toLowerCase().includes(debouncedSearch.toLowerCase())
  )
  
  // Group commands by category
  const groupedCommands: CommandGroup[] = Object.entries(
    filteredCommands.reduce((acc, cmd) => {
      if (!acc[cmd.category]) acc[cmd.category] = []
      acc[cmd.category].push(cmd)
      return acc
    }, {} as Record<string, Command[]>)
  ).map(([category, commands]) => ({ category: category as any, commands }))
  
  // Filter AI suggestions
  const filteredSuggestions = aiSuggestions.filter(suggestion =>
    search === '' || 
    suggestion.label.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
    suggestion.description?.toLowerCase().includes(debouncedSearch.toLowerCase())
  )
  
  // Total items for keyboard navigation
  const totalItems = filteredSuggestions.length + filteredCommands.length
  
  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => (prev + 1) % totalItems)
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => (prev - 1 + totalItems) % totalItems)
        break
      case 'Enter':
        e.preventDefault()
        handleSelect(selectedIndex)
        break
      case 'Escape':
        e.preventDefault()
        onClose()
        break
    }
  }
  
  // Handle item selection
  const handleSelect = (index: number) => {
    if (index < filteredSuggestions.length) {
      // AI suggestion selected
      const suggestion = filteredSuggestions[index]
      suggestion.action()
    } else {
      // Command selected
      const commandIndex = index - filteredSuggestions.length
      const command = filteredCommands[commandIndex]
      command?.action()
    }
    onClose()
  }
  
  if (!isOpen) return null
  
  return (
    <div
      className="fixed inset-0 z-modal-backdrop bg-black/50 backdrop-blur-sm flex items-start justify-center pt-[20vh] animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
    >
      <div
        ref={modalRef}
        className={cn(
          'w-full max-w-command-palette bg-heaven-bg-tertiary rounded-lg shadow-2xl',
          'overflow-hidden animate-scale-in',
          className
        )}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input */}
        <div className="p-4 border-b border-white/5">
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setSelectedIndex(0)
            }}
            placeholder={placeholder}
            className="w-full bg-transparent text-heaven-text-primary text-base outline-none placeholder:text-heaven-text-tertiary"
            aria-label="Search commands"
            autoComplete="off"
          />
        </div>
        
        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto">
          {/* AI Suggestions Section */}
          {filteredSuggestions.length > 0 && (
            <div className="py-2">
              <div className="px-4 py-2 text-xs font-medium text-heaven-accent-purple uppercase tracking-wide flex items-center gap-2">
                <span className="text-heaven-accent-purple">✨</span>
                AI Suggestions
              </div>
              {filteredSuggestions.map((suggestion, index) => (
                <CommandItem
                  key={suggestion.id}
                  label={suggestion.label}
                  description={suggestion.description}
                  icon={suggestion.icon || '✨'}
                  isSelected={index === selectedIndex}
                  onClick={() => handleSelect(index)}
                  confidence={suggestion.confidence}
                />
              ))}
            </div>
          )}
          
          {/* Commands Section */}
          {groupedCommands.length > 0 && (
            <div className="py-2">
              {groupedCommands.map((group, groupIndex) => (
                <div key={group.category}>
                  {(filteredSuggestions.length > 0 || groupIndex > 0) && (
                    <div className="h-px bg-white/5 my-2" />
                  )}
                  <div className="px-4 py-2 text-xs font-medium text-heaven-text-tertiary uppercase tracking-wide">
                    {group.category}
                  </div>
                  {group.commands.map((command, commandIndex) => {
                    const globalIndex =
                      filteredSuggestions.length +
                      groupedCommands
                        .slice(0, groupIndex)
                        .reduce((sum, g) => sum + g.commands.length, 0) +
                      commandIndex
                    return (
                      <CommandItem
                        key={command.id}
                        label={command.label}
                        description={command.description}
                        icon={command.icon}
                        shortcut={command.shortcut}
                        isSelected={globalIndex === selectedIndex}
                        disabled={command.disabled}
                        onClick={() => !command.disabled && handleSelect(globalIndex)}
                      />
                    )
                  })}
                </div>
              ))}
            </div>
          )}
          
          {/* Empty State */}
          {totalItems === 0 && (
            <div className="py-12 px-4 text-center text-heaven-text-tertiary">
              <div className="text-4xl mb-2">🔍</div>
              <div className="text-sm">No results found</div>
              {search && (
                <div className="text-xs mt-1">
                  Try a different search term
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="px-4 py-3 border-t border-white/5 flex items-center justify-between text-xs text-heaven-text-tertiary">
          <div className="flex items-center gap-4">
            <span>
              <kbd className="px-1.5 py-0.5 bg-white/5 rounded">↑↓</kbd> Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-white/5 rounded">Enter</kbd> Select
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-white/5 rounded">Esc</kbd> Close
            </span>
          </div>
          {totalItems > 0 && (
            <span>{totalItems} result{totalItems !== 1 ? 's' : ''}</span>
          )}
        </div>
      </div>
    </div>
  )
}

interface CommandItemProps {
  label: string
  description?: string
  icon?: string
  shortcut?: string
  isSelected: boolean
  disabled?: boolean
  confidence?: number
  onClick: () => void
}

function CommandItem({
  label,
  description,
  icon,
  shortcut,
  isSelected,
  disabled,
  confidence,
  onClick,
}: CommandItemProps) {
  return (
    <button
      className={cn(
        'w-full px-4 py-2.5 flex items-center gap-3 text-left transition-colors',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-heaven-blue-primary focus-visible:ring-inset',
        isSelected && 'bg-heaven-bg-hover',
        disabled && 'opacity-50 cursor-not-allowed',
        !disabled && 'hover:bg-heaven-bg-hover cursor-pointer'
      )}
      onClick={onClick}
      disabled={disabled}
      aria-disabled={disabled}
    >
      {/* Icon */}
      {icon && (
        <span className="text-lg flex-shrink-0" aria-hidden="true">
          {icon}
        </span>
      )}
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-heaven-text-primary font-medium truncate">
            {label}
          </span>
          {confidence !== undefined && (
            <span className="text-xs text-heaven-accent-purple">
              {Math.round(confidence * 100)}%
            </span>
          )}
        </div>
        {description && (
          <p className="text-xs text-heaven-text-secondary truncate mt-0.5">
            {description}
          </p>
        )}
      </div>
      
      {/* Shortcut */}
      {shortcut && (
        <span className="text-xs text-heaven-text-tertiary flex-shrink-0 font-mono">
          {formatShortcut(shortcut)}
        </span>
      )}
    </button>
  )
}

export default CommandPalette
