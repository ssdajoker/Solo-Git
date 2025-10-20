
/**
 * Types for file system and file browser
 */

export type FileType = 
  | 'file'
  | 'directory'
  | 'symlink'
  | 'unknown'

export type LanguageId = 
  | 'javascript'
  | 'typescript'
  | 'jsx'
  | 'tsx'
  | 'html'
  | 'css'
  | 'json'
  | 'markdown'
  | 'python'
  | 'rust'
  | 'go'
  | 'yaml'
  | 'toml'
  | 'text'
  | 'unknown'

export interface FileNode {
  id: string
  name: string
  path: string
  type: FileType
  size?: number
  modified?: string
  children?: FileNode[]
  expanded?: boolean
  selected?: boolean
  languageId?: LanguageId
}

export interface FileTree {
  root: FileNode
  selectedPath: string | null
  expandedPaths: Set<string>
}

export interface FileExplorerProps {
  repoId: string | null
  selectedFile: string | null
  onFileSelect: (path: string) => void
  onFileOpen?: (path: string) => void
  onFileCreate?: (path: string, type: FileType) => void
  onFileDelete?: (path: string) => void
  onFileRename?: (oldPath: string, newPath: string) => void
  className?: string
  collapsed?: boolean
  onToggleCollapse?: () => void
}

export interface FileIcon {
  icon: string
  color: string
}
