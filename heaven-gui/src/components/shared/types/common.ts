
/**
 * Common types used across the application
 */

export type ViewMode = 'idle' | 'navigation' | 'planning' | 'coding' | 'commit'

export type ThemeMode = 'dark' | 'light' | 'auto'

export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  type: NotificationType
  message: string
  title?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

export interface GlobalState {
  version: string
  last_updated: string
  active_repo: string | null
  active_workpad: string | null
  session_start: string
  total_operations: number
  total_cost_usd: number
}

export interface Position {
  line: number
  column: number
}

export interface Range {
  start: Position
  end: Position
}

export interface Dimensions {
  width: number
  height: number
}

export interface Point {
  x: number
  y: number
}
