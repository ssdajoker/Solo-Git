
/**
 * Types for Command Palette and command system
 */

export type CommandCategory = 
  | 'Navigation'
  | 'Editor'
  | 'Testing'
  | 'Git'
  | 'AI'
  | 'Settings'
  | 'Help'

export interface Command {
  id: string
  label: string
  description?: string
  category: CommandCategory
  shortcut?: string
  icon?: string
  action: () => void | Promise<void>
  disabled?: boolean
  hidden?: boolean
}

export interface CommandGroup {
  category: CommandCategory
  commands: Command[]
}

export interface AISuggestion {
  id: string
  label: string
  description?: string
  confidence: number  // 0-1
  icon?: string
  action: () => void | Promise<void>
}

export interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  commands?: Command[]
  aiSuggestions?: AISuggestion[]
  placeholder?: string
  className?: string
  'aria-label'?: string
}
