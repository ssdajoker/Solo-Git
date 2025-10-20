import React, { useEffect, useRef, useState, useCallback } from 'react';
import Editor, { Monaco, OnMount, OnChange } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { heavenTheme, editorOptions } from '../../config/monaco-theme';

// Language mappings
const languageMap: Record<string, string> = {
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.json': 'json',
  '.html': 'html',
  '.css': 'css',
  '.scss': 'scss',
  '.md': 'markdown',
  '.py': 'python',
  '.rs': 'rust',
  '.go': 'go',
  '.yml': 'yaml',
  '.yaml': 'yaml',
  '.xml': 'xml',
  '.sql': 'sql',
  '.sh': 'shell',
  '.bash': 'shell',
  '.txt': 'plaintext',
};

export interface CodeEditorProps {
  /** File path to display */
  filePath?: string;
  
  /** File content to display */
  content?: string;
  
  /** Programming language for syntax highlighting */
  language?: string;
  
  /** Callback when content changes */
  onChange?: (value: string | undefined) => void;
  
  /** Callback when user saves (Cmd/Ctrl+S) */
  onSave?: (content: string) => void;
  
  /** Whether the editor is read-only */
  readOnly?: boolean;
  
  /** Loading state */
  loading?: boolean;
  
  /** Height of the editor */
  height?: string | number;
  
  /** Custom className for the container */
  className?: string;
  
  /** Whether to show auto-save indicator */
  showAutoSave?: boolean;
  
  /** Auto-save delay in milliseconds (0 to disable) */
  autoSaveDelay?: number;
}

export interface CodeEditorHandle {
  /** Get the current editor value */
  getValue: () => string | undefined;
  
  /** Set editor value programmatically */
  setValue: (value: string) => void;
  
  /** Format the document */
  format: () => void;
  
  /** Get the Monaco editor instance */
  getEditor: () => editor.IStandaloneCodeEditor | null;
}

export const CodeEditor = React.forwardRef<CodeEditorHandle, CodeEditorProps>(
  (
    {
      filePath,
      content = '',
      language: propLanguage,
      onChange,
      onSave,
      readOnly = false,
      loading = false,
      height = '100%',
      className = '',
      showAutoSave = true,
      autoSaveDelay = 2000,
    },
    ref
  ) => {
    const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
    const monacoRef = useRef<Monaco | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [editorValue, setEditorValue] = useState(content);

    // Determine language from file path or prop
    const language = React.useMemo(() => {
      if (propLanguage) return propLanguage;
      if (!filePath) return 'plaintext';
      
      const ext = filePath.substring(filePath.lastIndexOf('.'));
      return languageMap[ext.toLowerCase()] || 'plaintext';
    }, [filePath, propLanguage]);

    // Handle editor mount
    const handleEditorMount: OnMount = useCallback((editor, monaco) => {
      editorRef.current = editor;
      monacoRef.current = monaco;

      // Define and set the Heaven theme
      monaco.editor.defineTheme('heaven', heavenTheme);
      monaco.editor.setTheme('heaven');

      // Add keyboard shortcut for save
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        const value = editor.getValue();
        if (onSave && !readOnly) {
          setIsSaving(true);
          onSave(value);
          setLastSaved(new Date());
          setTimeout(() => setIsSaving(false), 500);
        }
      });

      // Configure TypeScript/JavaScript defaults
      monaco.languages.typescript.typescriptDefaults.setDiagnosticsOptions({
        noSemanticValidation: false,
        noSyntaxValidation: false,
      });

      monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
        target: monaco.languages.typescript.ScriptTarget.Latest,
        allowNonTsExtensions: true,
        moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
        module: monaco.languages.typescript.ModuleKind.CommonJS,
        noEmit: true,
        esModuleInterop: true,
        jsx: monaco.languages.typescript.JsxEmit.React,
        reactNamespace: 'React',
        allowJs: true,
        typeRoots: ['node_modules/@types'],
      });

      // Same for JavaScript
      monaco.languages.typescript.javascriptDefaults.setDiagnosticsOptions({
        noSemanticValidation: false,
        noSyntaxValidation: false,
      });

      monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
        target: monaco.languages.typescript.ScriptTarget.Latest,
        allowNonTsExtensions: true,
        allowJs: true,
        jsx: monaco.languages.typescript.JsxEmit.React,
      });
    }, [onSave, readOnly]);

    // Handle editor change
    const handleEditorChange: OnChange = useCallback(
      (value) => {
        setEditorValue(value || '');
        onChange?.(value);

        // Auto-save logic
        if (autoSaveDelay > 0 && onSave && !readOnly && value !== undefined) {
          // Clear existing timer
          if (autoSaveTimerRef.current) {
            clearTimeout(autoSaveTimerRef.current);
          }

          // Set new timer
          autoSaveTimerRef.current = setTimeout(() => {
            setIsSaving(true);
            onSave(value);
            setLastSaved(new Date());
            setTimeout(() => setIsSaving(false), 500);
          }, autoSaveDelay);
        }
      },
      [onChange, onSave, autoSaveDelay, readOnly]
    );

    // Expose imperative handle
    React.useImperativeHandle(
      ref,
      () => ({
        getValue: () => editorRef.current?.getValue(),
        setValue: (value: string) => {
          editorRef.current?.setValue(value);
          setEditorValue(value);
        },
        format: () => {
          editorRef.current?.getAction('editor.action.formatDocument')?.run();
        },
        getEditor: () => editorRef.current,
      }),
      []
    );

    // Update content when prop changes
    useEffect(() => {
      if (content !== editorValue && editorRef.current) {
        editorRef.current.setValue(content);
        setEditorValue(content);
      }
    }, [content]);

    // Cleanup auto-save timer
    useEffect(() => {
      return () => {
        if (autoSaveTimerRef.current) {
          clearTimeout(autoSaveTimerRef.current);
        }
      };
    }, []);

    // Format last saved time
    const formatLastSaved = (date: Date) => {
      const now = new Date();
      const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

      if (diff < 60) return 'just now';
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return date.toLocaleTimeString();
    };

    return (
      <div className={`relative h-full ${className}`}>
        {/* Auto-save indicator */}
        {showAutoSave && !readOnly && (
          <div className="absolute top-2 right-4 z-10 flex items-center gap-2 text-xs">
            {isSaving ? (
              <div className="flex items-center gap-2 text-accent-blue">
                <div className="h-2 w-2 animate-pulse rounded-full bg-accent-blue" />
                <span>Saving...</span>
              </div>
            ) : lastSaved ? (
              <div className="flex items-center gap-2 text-gray-400">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <span>Saved {formatLastSaved(lastSaved)}</span>
              </div>
            ) : null}
          </div>
        )}

        {/* Loading skeleton */}
        {loading ? (
          <div className="flex h-full items-center justify-center bg-deep-space">
            <div className="flex flex-col items-center gap-4">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-accent-blue border-t-transparent" />
              <p className="text-sm text-gray-400">Loading editor...</p>
            </div>
          </div>
        ) : (
          /* Monaco Editor */
          <Editor
            height={height}
            language={language}
            value={editorValue}
            theme="heaven"
            options={{
              ...editorOptions,
              readOnly,
            }}
            onMount={handleEditorMount}
            onChange={handleEditorChange}
            loading={
              <div className="flex h-full items-center justify-center bg-deep-space">
                <div className="flex flex-col items-center gap-4">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-accent-blue border-t-transparent" />
                  <p className="text-sm text-gray-400">Initializing editor...</p>
                </div>
              </div>
            }
          />
        )}

        {/* File path indicator */}
        {filePath && (
          <div className="absolute bottom-2 left-4 z-10 text-xs text-gray-500">
            {filePath}
          </div>
        )}

        {/* Read-only indicator */}
        {readOnly && (
          <div className="absolute bottom-2 right-4 z-10 text-xs text-amber-500">
            Read-only
          </div>
        )}
      </div>
    );
  }
);

CodeEditor.displayName = 'CodeEditor';

export default CodeEditor;
