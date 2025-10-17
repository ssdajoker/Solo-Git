
import { formatShortcut, KeyboardShortcut } from '../hooks/useKeyboardShortcuts'
import './KeyboardShortcutsHelp.css'

interface KeyboardShortcutsHelpProps {
  isOpen: boolean
  onClose: () => void
  shortcuts: KeyboardShortcut[]
}

export default function KeyboardShortcutsHelp({ isOpen, onClose, shortcuts }: KeyboardShortcutsHelpProps) {
  if (!isOpen) return null

  // Group shortcuts by category
  const categorized = shortcuts.reduce((acc, shortcut) => {
    const category = shortcut.description.includes('Command') ? 'Command Palette' :
                    shortcut.description.includes('AI') ? 'AI Assistant' :
                    shortcut.description.includes('Test') ? 'Testing' :
                    shortcut.description.includes('File') || shortcut.description.includes('Editor') ? 'Editor' :
                    shortcut.description.includes('Toggle') ? 'Navigation' :
                    'General'
    
    if (!acc[category]) acc[category] = []
    acc[category].push(shortcut)
    return acc
  }, {} as Record<string, KeyboardShortcut[]>)

  return (
    <div className="shortcuts-overlay" onClick={onClose}>
      <div className="shortcuts-panel" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-header">
          <h2>Keyboard Shortcuts</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="shortcuts-content">
          {Object.entries(categorized).map(([category, shortcuts]) => (
            <section key={category} className="shortcuts-section">
              <h3>{category}</h3>
              <div className="shortcuts-list">
                {shortcuts.map((shortcut, index) => (
                  <div key={index} className="shortcut-item">
                    <span className="shortcut-description">{shortcut.description}</span>
                    <kbd className="shortcut-keys">{formatShortcut(shortcut)}</kbd>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="shortcuts-footer">
          <p className="hint">Press <kbd>?</kbd> or <kbd>ESC</kbd> to close this panel</p>
        </div>
      </div>
    </div>
  )
}
