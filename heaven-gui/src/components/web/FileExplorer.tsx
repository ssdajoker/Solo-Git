
/**
 * Enhanced File Explorer Component with Search, Keyboard Navigation, and Context Menu
 */

import { useState, useRef, useEffect, useMemo } from 'react'
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
  const [searchQuery, setSearchQuery] = useState('')
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: FileNode } | null>(null)
  const [focusedPath, setFocusedPath] = useState<string | null>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const treeRef = useRef<HTMLDivElement>(null)
  
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
          {
            id: 'components',
            name: 'components',
            path: '/src/components',
            type: 'directory',
            children: [
              { id: 'button', name: 'Button.tsx', path: '/src/components/Button.tsx', type: 'file', languageId: 'tsx' },
              { id: 'input', name: 'Input.tsx', path: '/src/components/Input.tsx', type: 'file', languageId: 'tsx' },
            ],
          },
        ],
      },
      {
        id: 'tests',
        name: 'tests',
        path: '/tests',
        type: 'directory',
        children: [
          { id: 'auth-test', name: 'auth.test.ts', path: '/tests/auth.test.ts', type: 'file', languageId: 'typescript' },
        ],
      },
      { id: 'package', name: 'package.json', path: '/package.json', type: 'file', languageId: 'json' },
      { id: 'tsconfig', name: 'tsconfig.json', path: '/tsconfig.json', type: 'file', languageId: 'json' },
    ],
  }
  
  // Flatten file tree for search
  const flattenedFiles = useMemo(() => {
    const files: FileNode[] = []
    const traverse = (node: FileNode) => {
      files.push(node)
      if (node.children) {
        node.children.forEach(traverse)
      }
    }
    traverse(mockFileTree)
    return files
  }, [])
  
  // Filter files based on search query
  const filteredFiles = useMemo(() => {
    if (!searchQuery.trim()) return null
    return flattenedFiles.filter(file => 
      file.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      file.type === 'file'
    )
  }, [searchQuery, flattenedFiles])
  
  // Close context menu on click outside
  useEffect(() => {
    const handleClickOutside = () => setContextMenu(null)
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [contextMenu])
  
  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!focusedPath) return
      
      const allPaths = flattenedFiles.map(f => f.path)
      const currentIndex = allPaths.indexOf(focusedPath)
      
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        const nextIndex = Math.min(currentIndex + 1, allPaths.length - 1)
        setFocusedPath(allPaths[nextIndex])
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        const prevIndex = Math.max(currentIndex - 1, 0)
        setFocusedPath(allPaths[prevIndex])
      } else if (e.key === 'Enter') {
        const node = flattenedFiles.find(f => f.path === focusedPath)
        if (node) {
          if (node.type === 'directory') {
            toggleFolder(node.path)
          } else {
            onFileSelect(node.path)
            onFileOpen?.(node.path)
          }
        }
      }
    }
    
    if (treeRef.current) {
      treeRef.current.addEventListener('keydown', handleKeyDown)
      return () => treeRef.current?.removeEventListener('keydown', handleKeyDown)
    }
  }, [focusedPath, flattenedFiles])
  
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
  
  const handleContextMenu = (e: React.MouseEvent, node: FileNode) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, node })
  }
  
  const renderNode = (node: FileNode, depth: number = 0) => {
    const isDirectory = node.type === 'directory'
    const isExpanded = expandedFolders.has(node.path)
    const isSelected = node.path === selectedFile
    const isFocused = node.path === focusedPath
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
            setFocusedPath(node.path)
          }}
          onContextMenu={(e) => handleContextMenu(e, node)}
          className={cn(
            'w-full h-list-item flex items-center gap-2 px-3 text-sm text-left transition-all duration-150',
            'hover:bg-heaven-bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-heaven-blue-primary',
            isSelected && 'bg-heaven-bg-active text-heaven-blue-primary',
            isFocused && 'ring-2 ring-inset ring-heaven-accent-cyan/30'
          )}
          style={{ paddingLeft: `${depth * 16 + 12}px` }}
          aria-expanded={isDirectory ? isExpanded : undefined}
          tabIndex={0}
        >
          <span 
            style={{ color: icon.color }} 
            className={cn(
              "flex-shrink-0 w-4 text-center transition-transform duration-200",
              isDirectory && isExpanded && "transform rotate-90"
            )}
            aria-hidden="true"
          >
            {icon.icon}
          </span>
          <span className="flex-1 truncate">{node.name}</span>
          {node.type === 'file' && node.languageId && (
            <span className="text-xs text-heaven-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity">
              {node.languageId === 'typescript' && 'TS'}
              {node.languageId === 'tsx' && 'TSX'}
              {node.languageId === 'javascript' && 'JS'}
              {node.languageId === 'jsx' && 'JSX'}
              {node.languageId === 'json' && 'JSON'}
              {node.languageId === 'markdown' && 'MD'}
            </span>
          )}
        </button>
        
        {isDirectory && isExpanded && node.children && (
          <div role="group" className="transition-all duration-200">
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
      
      {/* Search Bar */}
      <div className="p-2 border-b border-white/5">
        <input
          ref={searchInputRef}
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search files..."
          className="w-full px-3 py-1.5 text-sm bg-heaven-bg-tertiary border border-white/5 rounded
                   text-heaven-text-primary placeholder:text-heaven-text-tertiary
                   focus:outline-none focus:border-heaven-blue-primary focus:ring-1 focus:ring-heaven-blue-primary
                   transition-colors"
          aria-label="Search files"
        />
      </div>
      
      <div 
        ref={treeRef}
        className="flex-1 overflow-y-auto py-2" 
        role="tree"
        tabIndex={0}
      >
        {repoId ? (
          <>
            {filteredFiles ? (
              // Show search results
              <div className="space-y-0.5">
                {filteredFiles.length > 0 ? (
                  filteredFiles.map(file => (
                    <button
                      key={file.id}
                      onClick={() => {
                        onFileSelect(file.path)
                        onFileOpen?.(file.path)
                        setSearchQuery('')
                      }}
                      className={cn(
                        'w-full h-list-item flex items-center gap-2 px-3 text-sm text-left transition-colors',
                        'hover:bg-heaven-bg-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-heaven-blue-primary',
                        file.path === selectedFile && 'bg-heaven-bg-active text-heaven-blue-primary'
                      )}
                    >
                      <span style={{ color: getFileIcon(file.name, false, false).color }} className="flex-shrink-0 w-4 text-center">
                        {getFileIcon(file.name, false, false).icon}
                      </span>
                      <span className="flex-1 truncate">{file.path}</span>
                    </button>
                  ))
                ) : (
                  <div className="p-4 text-center text-heaven-text-tertiary text-sm">
                    <p>No files found</p>
                  </div>
                )}
              </div>
            ) : (
              // Show file tree
              renderNode(mockFileTree)
            )}
          </>
        ) : (
          <div className="p-4 text-center text-heaven-text-tertiary text-sm">
            <div className="text-2xl mb-2">📂</div>
            <p>No repository open</p>
          </div>
        )}
      </div>
      
      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-heaven-bg-tertiary border border-white/10 rounded-md shadow-xl py-1 min-w-[160px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button className="w-full px-3 py-1.5 text-sm text-left text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors">
            Open
          </button>
          <button className="w-full px-3 py-1.5 text-sm text-left text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors">
            Rename
          </button>
          <button className="w-full px-3 py-1.5 text-sm text-left text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors">
            Delete
          </button>
          <div className="h-px bg-white/5 my-1" />
          <button className="w-full px-3 py-1.5 text-sm text-left text-heaven-text-primary hover:bg-heaven-bg-hover transition-colors">
            Copy Path
          </button>
        </div>
      )}
    </div>
  )
}

export default FileExplorer
