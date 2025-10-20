
/**
 * File Explorer Component with Tree View
 */

import { useState } from 'react'
import { FileExplorerProps, FileNode } from '../shared/types'
import { getFileIcon, cn } from '../shared/utils'

export function FileExplorer({
  repoId,
  selectedFile,
  onFileSelect,
  onFileOpen,
  collapsed = false,
  onToggleCollapse,
  className,
}: FileExplorerProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['/']))
  
  // Mock file tree - in production, this would come from Tauri
  const mockFileTree: FileNode = {
    id: 'root',
    name: 'heaven-gui',
    path: '/',
    type: 'directory',
    expanded: true,
    children: [
      { id: 'readme', name: 'README.md', path: '/README.md', type: 'file', languageId: 'markdown' },
      {
        id: 'src',
        name: 'src',
        path: '/src',
        type: 'directory',
        expanded: true,
        children: [
          { id: 'main', name: 'main.ts', path: '/src/main.ts', type: 'file', languageId: 'typescript' },
          { id: 'auth', name: 'auth.ts', path: '/src/auth.ts', type: 'file', languageId: 'typescript' },
          { id: 'session', name: 'session.ts', path: '/src/session.ts', type: 'file', languageId: 'typescript' },
        ],
      },
      {
        id: 'tests',
        name: 'tests',
        path: '/tests',
        type: 'directory',
        children: [],
      },
      { id: 'package', name: 'package.json', path: '/package.json', type: 'file', languageId: 'json' },
    ],
  }
  
  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }
  
  const renderNode = (node: FileNode, depth: number = 0) => {
    const isDirectory = node.type === 'directory'
    const isExpanded = expandedFolders.has(node.path)
    const isSelected = node.path === selectedFile
    const icon = getFileIcon(node.name, isDirectory, isExpanded)
    
    return (
      <div key={node.id}>
        <button
          onClick={() => {
            if (isDirectory) {
              toggleFolder(node.path)
            } else {
              onFileSelect(node.path)
              onFileOpen?.(node.path)
            }
          }}
          className={cn(
            'w-full h-list-item flex items-center gap-2 px-3 text-sm text-left transition-colors',
            'hover:bg-heaven-bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-heaven-blue-primary',
            isSelected && 'bg-heaven-bg-active text-heaven-blue-primary'
          )}
          style={{ paddingLeft: `${depth * 16 + 12}px` }}
          aria-expanded={isDirectory ? isExpanded : undefined}
        >
          <span style={{ color: icon.color }} className="flex-shrink-0 w-4 text-center" aria-hidden="true">
            {icon.icon}
          </span>
          <span className="flex-1 truncate">{node.name}</span>
        </button>
        
        {isDirectory && isExpanded && node.children && (
          <div role="group">
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }
  
  if (collapsed) {
    return (
      <div className={cn('w-sidebar-collapsed bg-heaven-bg-secondary border-r border-white/5', className)}>
        <button
          onClick={onToggleCollapse}
          className="w-full h-header flex items-center justify-center text-heaven-text-secondary hover:text-heaven-text-primary transition-colors"
          aria-label="Expand file explorer"
        >
          <span className="text-xl">📁</span>
        </button>
      </div>
    )
  }
  
  return (
    <div className={cn('w-sidebar bg-heaven-bg-secondary border-r border-white/5 flex flex-col', className)}>
      <div className="h-header flex items-center justify-between px-3 border-b border-white/5">
        <span className="text-sm font-medium text-heaven-text-primary">FILES</span>
        <button
          onClick={onToggleCollapse}
          className="p-1 text-heaven-text-secondary hover:text-heaven-text-primary transition-colors"
          aria-label="Collapse file explorer"
        >
          ◀
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto py-2" role="tree">
        {repoId ? (
          renderNode(mockFileTree)
        ) : (
          <div className="p-4 text-center text-heaven-text-tertiary text-sm">
            <div className="text-2xl mb-2">📂</div>
            <p>No repository open</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default FileExplorer
