
import { useState, useEffect, useRef } from 'react'
import Editor, { Monaco } from '@monaco-editor/react'
import { invoke } from '@tauri-apps/api/tauri'
import './CodeViewer.css'

interface CodeViewerProps {
  repoId: string | null
  filePath: string | null
  showDiff?: boolean
  diffContent?: string
}

export default function CodeViewer({ repoId, filePath, showDiff = false, diffContent }: CodeViewerProps) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [language, setLanguage] = useState('plaintext')
  const editorRef = useRef<any>(null)

  useEffect(() => {
    if (repoId && filePath) {
      loadFile()
    }
  }, [repoId, filePath])

  const loadFile = async () => {
    if (!repoId || !filePath) return
    
    try {
      setLoading(true)
      const fileContent = await invoke<string>('read_file', { repoId, filePath })
      setContent(fileContent)
      
      // Detect language from file extension
      const ext = filePath.split('.').pop()?.toLowerCase()
      setLanguage(detectLanguage(ext || ''))
    } catch (e) {
      console.error('Failed to load file:', e)
      setContent(`// Error loading file: ${e}`)
    } finally {
      setLoading(false)
    }
  }

  const detectLanguage = (ext: string): string => {
    const langMap: Record<string, string> = {
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'py': 'python',
      'rs': 'rust',
      'go': 'go',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'html': 'html',
      'css': 'css',
      'json': 'json',
      'md': 'markdown',
      'yml': 'yaml',
      'yaml': 'yaml',
      'xml': 'xml',
      'sh': 'shell',
      'bash': 'shell',
      'sql': 'sql',
    }
    return langMap[ext] || 'plaintext'
  }

  const handleEditorDidMount = (editor: any, monaco: Monaco) => {
    editorRef.current = editor
    
    // Configure Heaven theme
    monaco.editor.defineTheme('heaven-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '6A737D', fontStyle: 'italic' },
        { token: 'keyword', foreground: '61AFEF', fontStyle: 'bold' },
        { token: 'string', foreground: '98C379' },
        { token: 'number', foreground: 'D19A66' },
        { token: 'function', foreground: 'C678DD' },
      ],
      colors: {
        'editor.background': '#1E1E1E',
        'editor.foreground': '#DDDDDD',
        'editor.lineHighlightBackground': '#2A2A2A',
        'editor.selectionBackground': '#264F78',
        'editorCursor.foreground': '#61AFEF',
      }
    })
    monaco.editor.setTheme('heaven-dark')
  }

  if (!filePath) {
    return (
      <div className="code-viewer empty">
        <div className="empty-state">
          <h3>No file selected</h3>
          <p className="hint">Select a file from the file browser</p>
        </div>
      </div>
    )
  }

  return (
    <div className="code-viewer">
      <div className="code-viewer-header">
        <span className="file-path">{filePath}</span>
        <span className="file-language">{language}</span>
        {loading && <span className="loading-indicator">⟳</span>}
      </div>
      
      <div className="editor-container">
        <Editor
          height="100%"
          language={language}
          value={content}
          theme="heaven-dark"
          onMount={handleEditorDidMount}
          options={{
            readOnly: false,
            minimap: { enabled: true },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            automaticLayout: true,
            padding: { top: 16, bottom: 16 },
            fontFamily: 'JetBrains Mono, SF Mono, Consolas, monospace',
            lineHeight: 24,
            renderLineHighlight: 'all',
            cursorBlinking: 'smooth',
            smoothScrolling: true,
          }}
        />
      </div>
    </div>
  )
}
