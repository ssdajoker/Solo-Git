import React, { useState, useCallback, useRef } from 'react';
import { CodeEditor, CodeEditorHandle } from '../components/web/CodeEditor';
import { CommandPalette } from '../components/web/CommandPalette';
import { Command } from '../components/shared/types/command';

interface FileItem {
  name: string;
  path: string;
  content: string;
}

// Mock file contents
const mockFiles: FileItem[] = [
  {
    name: 'Button.tsx',
    path: '/src/components/Button.tsx',
    content: `import React from 'react';

interface ButtonProps {
  text: string;
  onClick: () => void;
}

export const Button = ({ text, onClick }: ButtonProps) => {
  return (
    <button 
      onClick={onClick}
      className="bg-primary text-white font-bold py-2 px-4 rounded"
    >
      {text}
    </button>
  );
};

export default Button;
`,
  },
  {
    name: 'helpers.ts',
    path: '/src/utils/helpers.ts',
    content: `/**
 * Utility functions for common operations
 */

export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
`,
  },
  {
    name: 'README.md',
    path: '/README.md',
    content: `# Heaven UI

Solo Git Interface - A coding assistant powered by AI.

## Features

- 🌌 **Ethereal Processes**: Background AI agents working on your code
- 🧪 **Continuous Testing**: Automated test execution
- 💾 **Auto-commit**: Smart version control
- 🎯 **Command Palette**: Quick access to all features
- 🗣️ **Voice Input**: Code using natural language

## Usage

\`\`\`bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
\`\`\`

## Keyboard Shortcuts

- \`Cmd+P\`: Open Command Palette
- \`Cmd+S\`: Save file
- \`Cmd+K\`: Quick search
- \`Cmd+B\`: Toggle sidebar

## License

MIT
`,
  },
];

export const CodeEditorDemo: React.FC = () => {
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [fileContent, setFileContent] = useState(mockFiles[0].content);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showFileList, setShowFileList] = useState(true);
  const editorRef = useRef<CodeEditorHandle>(null);

  const currentFile = mockFiles[currentFileIndex];

  // Handle file selection
  const handleFileSelect = useCallback((index: number) => {
    setCurrentFileIndex(index);
    setFileContent(mockFiles[index].content);
  }, []);

  // Handle file content change
  const handleContentChange = useCallback((value: string | undefined) => {
    if (value !== undefined) {
      setFileContent(value);
    }
  }, []);

  // Handle file save
  const handleSave = useCallback((content: string) => {
    console.log(`Saving ${currentFile.path}:`, content);
    // In a real app, you would save to the backend here
  }, [currentFile]);

  // Command palette commands
  const commands: Command[] = [
    {
      id: 'toggle-sidebar',
      label: 'Toggle File List',
      description: 'Show/hide the file list',
      shortcut: 'Cmd+B',
      category: 'Navigation',
      action: () => setShowFileList(!showFileList),
    },
    {
      id: 'format-document',
      label: 'Format Document',
      description: 'Format the current document',
      shortcut: 'Shift+Alt+F',
      category: 'Editor',
      action: () => editorRef.current?.format(),
    },
    {
      id: 'save-file',
      label: 'Save File',
      description: 'Save the current file',
      shortcut: 'Cmd+S',
      category: 'Editor',
      action: () => handleSave(fileContent),
    },
  ];

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + P: Open command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
        e.preventDefault();
        setShowCommandPalette(true);
      }
      
      // Cmd/Ctrl + B: Toggle sidebar
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        setShowFileList(!showFileList);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showFileList]);

  return (
    <div className="flex h-screen flex-col bg-deep-space text-white">
      {/* Header */}
      <header className="flex h-14 items-center justify-between border-b border-gray-800 bg-space-gray px-4">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">HEAVEN</h1>
          <span className="text-sm text-gray-400">Solo Git • Monaco Editor Demo</span>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCommandPalette(true)}
            className="rounded-md bg-space-gray-light px-3 py-1.5 text-sm transition-colors hover:bg-space-gray-lighter"
            title="Open Command Palette (Cmd+P)"
          >
            ⌘ Command Palette
          </button>
          <button
            onClick={() => setShowFileList(!showFileList)}
            className="rounded-md bg-space-gray-light px-3 py-1.5 text-sm transition-colors hover:bg-space-gray-lighter"
            title="Toggle File List (Cmd+B)"
          >
            {showFileList ? '←' : '→'} Files
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* File List */}
        {showFileList && (
          <div className="w-64 border-r border-gray-800 bg-space-gray">
            <div className="border-b border-gray-800 p-3">
              <h2 className="text-sm font-semibold text-gray-300">Files</h2>
            </div>
            <div className="p-2">
              {mockFiles.map((file, index) => (
                <button
                  key={file.path}
                  onClick={() => handleFileSelect(index)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                    index === currentFileIndex
                      ? 'bg-accent-blue text-white'
                      : 'text-gray-300 hover:bg-space-gray-light'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs">
                      {file.name.endsWith('.tsx') ? '⚛️' : 
                       file.name.endsWith('.ts') ? '📘' : 
                       file.name.endsWith('.md') ? '📝' : '📄'}
                    </span>
                    <span className="truncate">{file.name}</span>
                  </div>
                  <div className="mt-1 truncate text-xs text-gray-500">{file.path}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Code Editor */}
        <div className="flex-1">
          <CodeEditor
            ref={editorRef}
            filePath={currentFile.path}
            content={fileContent}
            onChange={handleContentChange}
            onSave={handleSave}
            showAutoSave={true}
            autoSaveDelay={2000}
          />
        </div>
      </div>

      {/* Status Bar */}
      <div className="flex h-8 items-center justify-between border-t border-gray-800 bg-space-gray px-4 text-xs text-gray-400">
        <div className="flex items-center gap-4">
          <span>{currentFile.path}</span>
          <span>●</span>
        </div>
        <div className="flex items-center gap-4">
          <span>
            {currentFile.name.endsWith('.tsx') ? 'TypeScript React' :
             currentFile.name.endsWith('.ts') ? 'TypeScript' :
             currentFile.name.endsWith('.md') ? 'Markdown' : 'Plain Text'}
          </span>
          <span>UTF-8</span>
          <span>LF</span>
          <span>Ln 1, Col 1</span>
        </div>
      </div>

      {/* Command Palette */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
        commands={commands}
      />
    </div>
  );
};

export default CodeEditorDemo;
