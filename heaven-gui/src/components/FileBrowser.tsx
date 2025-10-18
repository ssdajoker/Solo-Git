
import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import './FileBrowser.css'

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  expanded?: boolean
}

interface FileBrowserProps {
  repoId: string | null
  onFileSelect: (filePath: string) => void
  selectedFile: string | null
}

export default function FileBrowser({ repoId, onFileSelect, selectedFile }: FileBrowserProps) {
  const [fileTree, setFileTree] = useState<FileNode[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (repoId) {
      loadFileTree()
    }
  }, [repoId])

  const loadFileTree = async () => {
    if (!repoId) return
    
    try {
      setLoading(true)
      const tree = await invoke<FileNode[]>('get_file_tree', { repoId })
      setFileTree(tree || [])
    } catch (e) {
      console.error('Failed to load file tree:', e)
    } finally {
      setLoading(false)
    }
  }

  const toggleDirectory = async (_node: FileNode, path: string[]) => {
    const newTree = [...fileTree]
    let current: FileNode[] = newTree
    
    for (const index of path) {
      const idx = parseInt(index)
      if (current[idx].type === 'directory') {
        if (!current[idx].expanded) {
          current[idx].expanded = true
          if (!current[idx].children) {
            // Load children lazily
            try {
              const children = await invoke<FileNode[]>('get_directory_contents', { 
                repoId, 
                dirPath: current[idx].path 
              })
              current[idx].children = children
            } catch (e) {
              console.error('Failed to load directory:', e)
            }
          }
        } else {
          current[idx].expanded = false
        }
        current = current[idx].children || []
      }
    }
    
    setFileTree(newTree)
  }

  const renderNode = (node: FileNode, path: string[] = []): JSX.Element => {
    const isDirectory = node.type === 'directory'
    const isSelected = node.path === selectedFile
    const depth = path.length
    
    return (
      <div key={node.path} className="file-node">
        <div
          className={`file-node-content ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
          onClick={() => {
            if (isDirectory) {
              toggleDirectory(node, path)
            } else {
              onFileSelect(node.path)
            }
          }}
        >
          <span className="file-icon">
            {isDirectory ? (node.expanded ? '📂' : '📁') : '📄'}
          </span>
          <span className="file-name">{node.name}</span>
        </div>
        
        {isDirectory && node.expanded && node.children && (
          <div className="file-children">
            {node.children.map((child, index) => 
              renderNode(child, [...path, index.toString()])
            )}
          </div>
        )}
      </div>
    )
  }

  if (!repoId) {
    return (
      <div className="file-browser empty">
        <h3>Files</h3>
        <p className="empty-message">No repository selected</p>
      </div>
    )
  }

  return (
    <div className="file-browser">
      <div className="file-browser-header">
        <h3>Files</h3>
        {loading && <span className="loading-indicator">⟳</span>}
        <button className="refresh-btn" onClick={loadFileTree}>⟲</button>
      </div>
      
      <div className="file-tree">
        {fileTree.length === 0 ? (
          <p className="empty-message">No files</p>
        ) : (
          fileTree.map((node, index) => renderNode(node, [index.toString()]))
        )}
      </div>
    </div>
  )
}
