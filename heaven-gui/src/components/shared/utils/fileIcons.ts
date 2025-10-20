
/**
 * File icon utilities for the file explorer
 */

import { LanguageId, FileIcon } from '../types'

const FILE_ICON_MAP: Record<string, FileIcon> = {
  // JavaScript/TypeScript
  '.js': { icon: '󰌞', color: '#F0DB4F' },
  '.jsx': { icon: '󰜈', color: '#61DAFB' },
  '.ts': { icon: '󰛦', color: '#3178C6' },
  '.tsx': { icon: '󰜈', color: '#3178C6' },
  '.mjs': { icon: '󰌞', color: '#F0DB4F' },
  
  // Web
  '.html': { icon: '󰌝', color: '#E34C26' },
  '.htm': { icon: '󰌝', color: '#E34C26' },
  '.css': { icon: '󰌜', color: '#264DE4' },
  '.scss': { icon: '󰌜', color: '#CC6699' },
  '.sass': { icon: '󰌜', color: '#CC6699' },
  '.less': { icon: '󰌜', color: '#1D365D' },
  
  // Data
  '.json': { icon: '󰘦', color: '#5FB04C' },
  '.yaml': { icon: '󰘦', color: '#CB171E' },
  '.yml': { icon: '󰘦', color: '#CB171E' },
  '.toml': { icon: '󰘦', color: '#9C4121' },
  '.xml': { icon: '󰗀', color: '#FF6600' },
  
  // Documentation
  '.md': { icon: '󰍔', color: '#0969DA' },
  '.mdx': { icon: '󰍔', color: '#0969DA' },
  '.txt': { icon: '󰈙', color: '#9CA3AF' },
  '.pdf': { icon: '󰈦', color: '#EF4444' },
  
  // Config
  '.env': { icon: '󰪻', color: '#ECD53F' },
  '.gitignore': { icon: '󰊢', color: '#F97316' },
  '.npmrc': { icon: '󰎙', color: '#CB3837' },
  '.editorconfig': { icon: '󰅪', color: '#9CA3AF' },
  
  // Build
  'package.json': { icon: '󰎙', color: '#CB3837' },
  'package-lock.json': { icon: '󰎙', color: '#CB3837' },
  'tsconfig.json': { icon: '󰛦', color: '#3178C6' },
  'vite.config': { icon: '󰹣', color: '#646CFF' },
  'tailwind.config': { icon: '󱏿', color: '#06B6D4' },
  
  // Other
  '.py': { icon: '󰌠', color: '#3776AB' },
  '.rs': { icon: '󱘗', color: '#CE422B' },
  '.go': { icon: '󰟓', color: '#00ADD8' },
  '.java': { icon: '󰬷', color: '#F89820' },
  '.rb': { icon: '󰴭', color: '#CC342D' },
  '.php': { icon: '󰌟', color: '#777BB4' },
  
  // Images
  '.png': { icon: '󰈟', color: '#A855F7' },
  '.jpg': { icon: '󰈟', color: '#A855F7' },
  '.jpeg': { icon: '󰈟', color: '#A855F7' },
  '.gif': { icon: '󰈟', color: '#A855F7' },
  '.svg': { icon: '󰜡', color: '#FF9800' },
  '.ico': { icon: '󰈟', color: '#A855F7' },
  
  // Default
  'folder': { icon: '󰉋', color: '#3B82F6' },
  'folder-open': { icon: '󰷏', color: '#3B82F6' },
  'file': { icon: '󰈙', color: '#9CA3AF' },
}

export function getFileIcon(filename: string, isDirectory: boolean = false, isOpen: boolean = false): FileIcon {
  if (isDirectory) {
    return isOpen ? FILE_ICON_MAP['folder-open'] : FILE_ICON_MAP['folder']
  }
  
  // Check for exact filename match first
  if (FILE_ICON_MAP[filename.toLowerCase()]) {
    return FILE_ICON_MAP[filename.toLowerCase()]
  }
  
  // Check for extension
  const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase()
  if (FILE_ICON_MAP[ext]) {
    return FILE_ICON_MAP[ext]
  }
  
  return FILE_ICON_MAP['file']
}

export function getLanguageFromFilename(filename: string): LanguageId {
  const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase()
  
  const languageMap: Record<string, LanguageId> = {
    '.js': 'javascript',
    '.jsx': 'jsx',
    '.ts': 'typescript',
    '.tsx': 'tsx',
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'css',
    '.sass': 'css',
    '.json': 'json',
    '.md': 'markdown',
    '.mdx': 'markdown',
    '.py': 'python',
    '.rs': 'rust',
    '.go': 'go',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
  }
  
  return languageMap[ext] || 'text'
}
