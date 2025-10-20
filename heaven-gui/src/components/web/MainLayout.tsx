/**
 * Enhanced Main Layout Component with Resizable Panels
 * Integrates FileExplorer, CodeEditor, CommitTimeline, StatusBar, and VoiceInput
 */

import { useState, useRef, useEffect } from 'react'
import { FileExplorer } from './FileExplorer'
import { CodeEditor } from './CodeEditor'
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
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState('')
  const [language, setLanguage] = useState<string>()
  
  // Mock cursor position - in production, this would come from Monaco editor
  const cursorPosition = { line: 1, column: 1 }
  
  // Voice input state
  const [voiceQuery, setVoiceQuery] = useState('')
  
  // Command palette state
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  
  // Resize state
  const [isResizingLeft, setIsResizingLeft] = useState(false)
  const [isResizingRight, setIsResizingRight] = useState(false)
  
  const layoutRef = useRef<HTMLDivElement>(null)
  
  // Handle file selection
  const handleFileSelect = (path: string) => {
    setSelectedFile(path)
    
    // Mock file content - in production, load from Tauri
    const mockContent = `// ${path}\n\nfunction example() {\n  console.log('Hello from ${path}');\n}\n\nexport default example;`
    setFileContent(mockContent)
    
    // Determine language from extension
    if (path.endsWith('.ts')) setLanguage('TypeScript')
    else if (path.endsWith('.tsx')) setLanguage('TypeScript React')
    else if (path.endsWith('.js')) setLanguage('JavaScript')
    else if (path.endsWith('.json')) setLanguage('JSON')
    else if (path.endsWith('.md')) setLanguage('Markdown')
    else setLanguage(undefined)
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
                selectedFile={selectedFile}
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
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            collapsed
            onToggleCollapse={() => setLeftPanelCollapsed(false)}
          />
        )}
        
        {/* Center Panel - Code Editor */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedFile ? (
            <CodeEditor
              content={fileContent}
              onChange={(value) => setFileContent(value || '')}
              language={language?.toLowerCase().replace(' ', '')}
              filePath={selectedFile}
              className="flex-1"
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-heaven-text-tertiary">
              <div className="text-center">
                <div className="text-4xl mb-4">📝</div>
                <p className="text-lg mb-2">No file selected</p>
                <p className="text-sm">Select a file from the explorer to start editing</p>
              </div>
            </div>
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
        language={language}
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
