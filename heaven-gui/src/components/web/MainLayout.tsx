/**
 * Enhanced Main Layout Component with Resizable Panels
 * Integrates FileExplorer, CodeEditor, CommitTimeline, StatusBar, and VoiceInput
 */

import { useState, useRef, useEffect } from 'react'
import { FileExplorer } from './FileExplorer'
import { CodeEditor } from './CodeEditor'
import { EditorTabs, EditorTab } from './EditorTabs'
import { EditorEmptyState } from './EditorEmptyState'
import { CommitTimeline } from './CommitTimeline'
import { StatusBar } from './StatusBar'
import { VoiceInput } from './VoiceInput'
import { CommandPalette } from './CommandPalette'
import { cn } from '../shared/utils'
import { GlobalState, TestRun, BuildInfo, GitStatus } from '../shared/types'

export interface MainLayoutProps {
  repoId: string | null
  globalState: GlobalState | null
  testRun?: TestRun
  buildInfo?: BuildInfo
  gitStatus?: GitStatus
  onCommand?: (command: string) => void
  className?: string
}

export function MainLayout({
  repoId,
  globalState,
  testRun,
  buildInfo,
  gitStatus,
  onCommand,
  className,
}: MainLayoutProps) {
  // Layout state
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false)
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false)
  const [leftPanelWidth, setLeftPanelWidth] = useState(280)
  const [rightPanelWidth, setRightPanelWidth] = useState(320)
  
  // File and editor state
  const [openTabs, setOpenTabs] = useState<EditorTab[]>([])
  const [activeTabId, setActiveTabId] = useState<string | null>(null)
  const [fileContents, setFileContents] = useState<Record<string, string>>({})
  const [dirtyFiles, setDirtyFiles] = useState<Set<string>>(new Set())
  
  // Cursor position - updated by editor
  const [cursorPosition, setCursorPosition] = useState({ line: 1, column: 1 })
  
  // Get active tab
  const activeTab = openTabs.find(tab => tab.id === activeTabId)
  const activeContent = activeTabId ? fileContents[activeTabId] : ''
  
  // Voice input state
  const [voiceQuery, setVoiceQuery] = useState('')
  
  // Command palette state
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  
  // Resize state
  const [isResizingLeft, setIsResizingLeft] = useState(false)
  const [isResizingRight, setIsResizingRight] = useState(false)
  
  const layoutRef = useRef<HTMLDivElement>(null)
  
  // Helper to determine language from file path
  const getLanguageFromPath = (path: string): string | undefined => {
    const ext = path.substring(path.lastIndexOf('.')).toLowerCase()
    const languageMap: Record<string, string> = {
      '.ts': 'TypeScript',
      '.tsx': 'TypeScript React',
      '.js': 'JavaScript',
      '.jsx': 'JavaScript React',
      '.json': 'JSON',
      '.html': 'HTML',
      '.css': 'CSS',
      '.scss': 'SCSS',
      '.md': 'Markdown',
      '.py': 'Python',
      '.rs': 'Rust',
      '.go': 'Go',
      '.yml': 'YAML',
      '.yaml': 'YAML',
      '.xml': 'XML',
      '.sql': 'SQL',
      '.sh': 'Shell',
      '.bash': 'Shell',
      '.txt': 'Plain Text',
    }
    return languageMap[ext]
  }
  
  // Handle file selection
  const handleFileSelect = (path: string) => {
    // Check if file is already open
    const existingTab = openTabs.find(tab => tab.path === path)
    
    if (existingTab) {
      // Just switch to existing tab
      setActiveTabId(existingTab.id)
    } else {
      // Create new tab
      const fileName = path.split('/').pop() || path
      const tabId = `tab-${Date.now()}-${Math.random()}`
      
      const newTab: EditorTab = {
        id: tabId,
        path,
        name: fileName,
        isDirty: false,
        gitStatus: undefined, // In production, get from git status
      }
      
      setOpenTabs(prev => [...prev, newTab])
      setActiveTabId(tabId)
      
      // Mock file content - in production, load from Tauri
      const mockContent = `// ${path}\n\nfunction example() {\n  console.log('Hello from ${path}');\n}\n\nexport default example;`
      setFileContents(prev => ({ ...prev, [tabId]: mockContent }))
    }
  }
  
  // Handle tab close
  const handleTabClose = (tabId: string) => {
    const tabIndex = openTabs.findIndex(t => t.id === tabId)
    if (tabIndex === -1) return
    
    // Remove tab
    setOpenTabs(prev => prev.filter(t => t.id !== tabId))
    
    // Clean up content
    setFileContents(prev => {
      const newContents = { ...prev }
      delete newContents[tabId]
      return newContents
    })
    
    setDirtyFiles(prev => {
      const newDirty = new Set(prev)
      newDirty.delete(tabId)
      return newDirty
    })
    
    // Switch to another tab if this was active
    if (activeTabId === tabId) {
      if (openTabs.length > 1) {
        // Switch to next tab, or previous if this was last
        const newIndex = tabIndex < openTabs.length - 1 ? tabIndex + 1 : tabIndex - 1
        setActiveTabId(openTabs[newIndex].id)
      } else {
        setActiveTabId(null)
      }
    }
  }
  
  // Handle before tab close (ask for confirmation if dirty)
  const handleBeforeTabClose = async (tabId: string): Promise<boolean> => {
    if (dirtyFiles.has(tabId)) {
      // In production, show confirmation dialog
      // For now, just allow closing
      return confirm('File has unsaved changes. Close anyway?')
    }
    return true
  }
  
  // Handle content change
  const handleContentChange = (value: string | undefined) => {
    if (!activeTabId || value === undefined) return
    
    setFileContents(prev => ({ ...prev, [activeTabId]: value }))
    
    // Mark as dirty
    const tab = openTabs.find(t => t.id === activeTabId)
    if (tab) {
      setDirtyFiles(prev => new Set(prev).add(activeTabId))
      setOpenTabs(prev => prev.map(t => 
        t.id === activeTabId ? { ...t, isDirty: true } : t
      ))
    }
  }
  
  // Handle save
  const handleSave = (content: string) => {
    if (!activeTabId) return
    
    // In production, save to file system via Tauri
    console.log('Saving file:', activeTab?.path, content)
    
    // Mark as clean
    setDirtyFiles(prev => {
      const newDirty = new Set(prev)
      newDirty.delete(activeTabId)
      return newDirty
    })
    
    setOpenTabs(prev => prev.map(t => 
      t.id === activeTabId ? { ...t, isDirty: false } : t
    ))
  }
  
  // Handle voice input submission
  const handleVoiceSubmit = () => {
    if (voiceQuery.trim()) {
      onCommand?.(voiceQuery)
      setVoiceQuery('')
    }
  }
  
  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K for command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(true)
      }
      
      // Cmd/Ctrl + B to toggle left panel
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault()
        setLeftPanelCollapsed(!leftPanelCollapsed)
      }
      
      // Cmd/Ctrl + J to toggle right panel
      if ((e.metaKey || e.ctrlKey) && e.key === 'j') {
        e.preventDefault()
        setRightPanelCollapsed(!rightPanelCollapsed)
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [leftPanelCollapsed, rightPanelCollapsed])
  
  // Handle left panel resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingLeft) {
        const newWidth = Math.max(200, Math.min(500, e.clientX))
        setLeftPanelWidth(newWidth)
      }
    }
    
    const handleMouseUp = () => {
      setIsResizingLeft(false)
    }
    
    if (isResizingLeft) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isResizingLeft])
  
  // Handle right panel resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingRight && layoutRef.current) {
        const layoutWidth = layoutRef.current.offsetWidth
        const newWidth = Math.max(200, Math.min(500, layoutWidth - e.clientX))
        setRightPanelWidth(newWidth)
      }
    }
    
    const handleMouseUp = () => {
      setIsResizingRight(false)
    }
    
    if (isResizingRight) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isResizingRight])
  
  return (
    <div 
      ref={layoutRef}
      className={cn('h-screen flex flex-col bg-heaven-bg-primary overflow-hidden', className)}
    >
      {/* Header */}
      <header className="h-header bg-heaven-bg-secondary border-b border-white/5 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">✨</span>
            <span className="text-sm font-semibold text-heaven-text-primary">HEAVEN</span>
          </div>
          
          {repoId && (
            <div className="text-xs text-heaven-text-tertiary">
              {repoId}
            </div>
          )}
        </div>
        
        {/* Voice Input in Header */}
        <div className="flex-1 max-w-2xl mx-4">
          <VoiceInput
            value={voiceQuery}
            onChange={setVoiceQuery}
            onSubmit={handleVoiceSubmit}
            placeholder="What can I do for you?"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="px-3 py-1.5 text-xs bg-heaven-bg-tertiary text-heaven-text-secondary hover:text-heaven-text-primary rounded transition-colors"
            aria-label="Open command palette"
          >
            ⌘K
          </button>
          
          <button className="p-2 text-heaven-text-secondary hover:text-heaven-text-primary transition-colors">
            ⚙️
          </button>
        </div>
      </header>
      
      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - File Explorer */}
        {!leftPanelCollapsed && (
          <>
            <div style={{ width: leftPanelWidth }}>
              <FileExplorer
                repoId={repoId}
                selectedFile={activeTab?.path || null}
                onFileSelect={handleFileSelect}
                onToggleCollapse={() => setLeftPanelCollapsed(true)}
              />
            </div>
            
            {/* Left Resize Handle */}
            <div
              className="w-1 bg-white/5 hover:bg-heaven-accent-cyan cursor-col-resize transition-colors"
              onMouseDown={() => setIsResizingLeft(true)}
              aria-label="Resize file explorer"
            />
          </>
        )}
        
        {leftPanelCollapsed && (
          <FileExplorer
            repoId={repoId}
            selectedFile={activeTab?.path || null}
            onFileSelect={handleFileSelect}
            collapsed
            onToggleCollapse={() => setLeftPanelCollapsed(false)}
          />
        )}
        
        {/* Center Panel - Editor with Tabs */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Editor Tabs */}
          {openTabs.length > 0 && (
            <EditorTabs
              tabs={openTabs}
              activeTabId={activeTabId}
              onTabClick={setActiveTabId}
              onTabClose={handleTabClose}
              onBeforeTabClose={handleBeforeTabClose}
            />
          )}
          
          {/* Editor or Empty State */}
          {activeTab ? (
            <CodeEditor
              content={activeContent}
              onChange={handleContentChange}
              onSave={handleSave}
              onCursorPositionChange={(line, column) => setCursorPosition({ line, column })}
              filePath={activeTab.path}
              gitStatus={activeTab.gitStatus}
              readOnly={activeTab.isReadOnly}
              showHeader={false} // Header shown above tabs
              className="flex-1"
            />
          ) : (
            <EditorEmptyState
              onOpenFile={() => setLeftPanelCollapsed(false)}
            />
          )}
        </div>
        
        {/* Right Panel - Commit Timeline */}
        {!rightPanelCollapsed && (
          <>
            {/* Right Resize Handle */}
            <div
              className="w-1 bg-white/5 hover:bg-heaven-accent-cyan cursor-col-resize transition-colors"
              onMouseDown={() => setIsResizingRight(true)}
              aria-label="Resize commit timeline"
            />
            
            <div style={{ width: rightPanelWidth }}>
              <CommitTimeline
                repoId={repoId}
                onToggleCollapse={() => setRightPanelCollapsed(true)}
              />
            </div>
          </>
        )}
        
        {rightPanelCollapsed && (
          <CommitTimeline
            repoId={repoId}
            collapsed
            onToggleCollapse={() => setRightPanelCollapsed(false)}
          />
        )}
      </div>
      
      {/* Status Bar */}
      <StatusBar
        globalState={globalState}
        testRun={testRun}
        buildInfo={buildInfo}
        gitStatus={gitStatus}
        cursorPosition={cursorPosition}
        language={activeTab ? getLanguageFromPath(activeTab.path) : undefined}
      />
      
      {/* Command Palette */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />
    </div>
  )
}

export default MainLayout
