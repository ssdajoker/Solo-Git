import React from 'react';
import Editor from '@monaco-editor/react';

interface CodeEditorProps {
  value?: string;
  onChange?: (value: string | undefined) => void;
  language?: string;
  height?: string;
  readOnly?: boolean;
  theme?: string;
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  value = '',
  onChange,
  language = 'typescript',
  height = '100%',
  readOnly = false,
  theme = 'heaven-dark',
}) => {
  const handleEditorChange = (value: string | undefined) => {
    onChange?.(value);
  };

  // Define custom theme before mounting
  const handleEditorWillMount = (monaco: any) => {
    monaco.editor.defineTheme('heaven-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '6B7280', fontStyle: 'italic' },
        { token: 'keyword', foreground: 'F97316', fontStyle: 'bold' },
        { token: 'string', foreground: '22C55E' },
        { token: 'number', foreground: '06B6D4' },
        { token: 'function', foreground: '3B82F6' },
        { token: 'variable', foreground: 'A855F7' },
        { token: 'type', foreground: 'EC4899' },
      ],
      colors: {
        'editor.background': '#0A0E1A',
        'editor.foreground': '#FFFFFF',
        'editor.lineHighlightBackground': '#1A1F2E',
        'editor.selectionBackground': '#3B82F640',
        'editor.inactiveSelectionBackground': '#3B82F620',
        'editorLineNumber.foreground': '#4B5563',
        'editorLineNumber.activeForeground': '#9CA3AF',
        'editorCursor.foreground': '#3B82F6',
        'editor.findMatchBackground': '#3B82F640',
        'editor.findMatchHighlightBackground': '#3B82F620',
      },
    });
  };

  return (
    <div className="w-full h-full">
      <Editor
        height={height}
        language={language}
        value={value}
        onChange={handleEditorChange}
        theme={theme}
        beforeMount={handleEditorWillMount}
        options={{
          fontSize: 14,
          fontFamily: "'Fira Code', 'Monaco', 'Consolas', 'Courier New', monospace",
          lineHeight: 1.6,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          readOnly,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          lineNumbers: 'on',
          renderWhitespace: 'selection',
          cursorBlinking: 'smooth',
          cursorSmoothCaretAnimation: 'on',
          smoothScrolling: true,
          padding: { top: 16, bottom: 16 },
        }}
        loading={
          <div className="flex items-center justify-center h-full">
            <div className="text-heaven-text-muted">Loading editor...</div>
          </div>
        }
      />
    </div>
  );
};

export default CodeEditor;
