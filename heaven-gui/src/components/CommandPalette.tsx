
import { useState, useEffect, useRef } from 'react'
import './CommandPalette.css'

interface Command {
  id: string
  label: string
  description: string
  shortcut?: string
  category: string
  action: () => void
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  commands: Command[]
}

export default function CommandPalette({ isOpen, onClose, commands }: CommandPaletteProps) {
  const [search, setSearch] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [filteredCommands, setFilteredCommands] = useState<Command[]>(commands)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
      setSearch('')
      setSelectedIndex(0)
    }
  }, [isOpen])

  useEffect(() => {
    // Fuzzy search
    if (!search) {
      setFilteredCommands(commands)
      return
    }

    const searchLower = search.toLowerCase()
    const filtered = commands.filter(cmd => 
      cmd.label.toLowerCase().includes(searchLower) ||
      cmd.description.toLowerCase().includes(searchLower) ||
      cmd.category.toLowerCase().includes(searchLower)
    )

    // Sort by relevance (exact match first)
    filtered.sort((a, b) => {
      const aExact = a.label.toLowerCase().startsWith(searchLower) ? 1 : 0
      const bExact = b.label.toLowerCase().startsWith(searchLower) ? 1 : 0
      return bExact - aExact
    })

    setFilteredCommands(filtered)
    setSelectedIndex(0)
  }, [search, commands])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, filteredCommands.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        if (filteredCommands[selectedIndex]) {
          executeCommand(filteredCommands[selectedIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        onClose()
        break
    }
  }

  const executeCommand = (cmd: Command) => {
    cmd.action()
    onClose()
  }

  useEffect(() => {
    // Scroll selected item into view
    if (listRef.current) {
      const selectedElement = listRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      }
    }
  }, [selectedIndex])

  if (!isOpen) return null

  return (
    <div className="command-palette-overlay" onClick={onClose}>
      <div className="command-palette" onClick={(e) => e.stopPropagation()}>
        <div className="command-palette-search">
          <span className="search-icon">⌘</span>
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search..."
            className="search-input"
          />
          <span className="hint">ESC to close</span>
        </div>

        <div className="command-list" ref={listRef}>
          {filteredCommands.length === 0 ? (
            <div className="no-results">
              <p>No commands found</p>
            </div>
          ) : (
            filteredCommands.map((cmd, index) => (
              <div
                key={cmd.id}
                className={`command-item ${index === selectedIndex ? 'selected' : ''}`}
                onClick={() => executeCommand(cmd)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                <div className="command-content">
                  <div className="command-label">{cmd.label}</div>
                  <div className="command-description">{cmd.description}</div>
                </div>
                <div className="command-meta">
                  <span className="command-category">{cmd.category}</span>
                  {cmd.shortcut && <span className="command-shortcut">{cmd.shortcut}</span>}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="command-palette-footer">
          <div className="footer-hints">
            <span><kbd>↑↓</kbd> Navigate</span>
            <span><kbd>↵</kbd> Execute</span>
            <span><kbd>ESC</kbd> Close</span>
          </div>
        </div>
      </div>
    </div>
  )
}
