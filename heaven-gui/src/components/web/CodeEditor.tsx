import React, { useEffect, useRef, useState, useCallback } from 'react';
import Editor, { Monaco, OnMount, OnChange } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { heavenTheme, editorOptions } from '../../config/monaco-theme';
import { EditorHeader } from './EditorHeader';
import { EditorLoadingState } from './EditorLoadingState';
import { EditorContextMenu, EditorContextMenuItem } from './EditorContextMenu';
import { cn } from '../shared/utils';
import type { GitFileStatus } from '../shared/types';

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
  
  /** Git status of the file */
  gitStatus?: GitFileStatus;
  
  /** Whether to show the header */
  showHeader?: boolean;
  
  /** Callback when cursor position changes */
  onCursorPositionChange?: (line: number, column: number) => void;
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
      onCursorPositionChange,
      readOnly = false,
      loading = false,
      height = '100%',
      className = '',
      autoSaveDelay = 2000,
      gitStatus,
      showHeader = true,
    },
    ref
  ) => {
    const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
    const monacoRef = useRef<Monaco | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [editorValue, setEditorValue] = useState(content);
    const [showMinimap, setShowMinimap] = useState(true);
    const [wordWrapEnabled, setWordWrapEnabled] = useState(false);
    const [contextMenuPosition, setContextMenuPosition] = useState<{ x: number; y: number } | null>(null);

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

      // Track cursor position
      editor.onDidChangeCursorPosition((e) => {
        onCursorPositionChange?.(e.position.lineNumber, e.position.column);
      });

      // Add keyboard shortcut for save (Cmd/Ctrl+S)
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        const value = editor.getValue();
        if (onSave && !readOnly) {
          setIsSaving(true);
          onSave(value);
          setLastSaved(new Date());
          setTimeout(() => setIsSaving(false), 500);
        }
      });

      // Add keyboard shortcut for format (Shift+Alt+F)
      editor.addCommand(
        monaco.KeyMod.Shift | monaco.KeyMod.Alt | monaco.KeyCode.KeyF,
        () => {
          editor.getAction('editor.action.formatDocument')?.run();
        }
      );

      // Add keyboard shortcut for toggle comment (Cmd/Ctrl+/)
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Slash, () => {
        editor.getAction('editor.action.commentLine')?.run();
      });

      // Handle context menu
      editor.onContextMenu((e) => {
        e.event.preventDefault();
        setContextMenuPosition({ x: e.event.posx, y: e.event.posy });
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
    }, [onSave, onCursorPositionChange, readOnly]);

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

    // Get editor status
    const getEditorStatus = (): 'saved' | 'unsaved' | 'saving' | 'read-only' | undefined => {
      if (readOnly) return 'read-only';
      if (isSaving) return 'saving';
      if (lastSaved) return 'saved';
      if (editorValue !== content) return 'unsaved';
      return undefined;
    };
    
    // Format document handler
    const handleFormat = useCallback(() => {
      editorRef.current?.getAction('editor.action.formatDocument')?.run();
    }, []);
    
    // Toggle minimap handler
    const handleToggleMinimap = useCallback(() => {
      setShowMinimap(prev => {
        const newValue = !prev;
        editorRef.current?.updateOptions({
          minimap: { enabled: newValue }
        });
        return newValue;
      });
    }, []);
    
    // Toggle word wrap handler
    const handleToggleWordWrap = useCallback(() => {
      setWordWrapEnabled(prev => {
        const newValue = !prev;
        editorRef.current?.updateOptions({
          wordWrap: newValue ? 'on' : 'off'
        });
        return newValue;
      });
    }, []);
    
    // Context menu items
    const contextMenuItems: EditorContextMenuItem[] = [
      {
        id: 'cut',
        label: 'Cut',
        shortcut: '⌘X',
        disabled: readOnly,
        action: () => editorRef.current?.getAction('editor.action.clipboardCutAction')?.run(),
      },
      {
        id: 'copy',
        label: 'Copy',
        shortcut: '⌘C',
        action: () => editorRef.current?.getAction('editor.action.clipboardCopyAction')?.run(),
      },
      {
        id: 'paste',
        label: 'Paste',
        shortcut: '⌘V',
        disabled: readOnly,
        action: () => editorRef.current?.getAction('editor.action.clipboardPasteAction')?.run(),
      },
      {
        id: 'separator-1',
        label: '',
        separator: true,
      },
      {
        id: 'format',
        label: 'Format Document',
        shortcut: '⇧⌥F',
        disabled: readOnly,
        action: handleFormat,
      },
      {
        id: 'separator-2',
        label: '',
        separator: true,
      },
      {
        id: 'find',
        label: 'Find',
        shortcut: '⌘F',
        action: () => editorRef.current?.getAction('actions.find')?.run(),
      },
      {
        id: 'replace',
        label: 'Replace',
        shortcut: '⌘H',
        disabled: readOnly,
        action: () => editorRef.current?.getAction('editor.action.startFindReplaceAction')?.run(),
      },
    ];

    // Determine language display name
    const languageDisplayName = React.useMemo(() => {
      const lang = language.toLowerCase();
      const names: Record<string, string> = {
        'typescript': 'TypeScript',
        'javascript': 'JavaScript',
        'json': 'JSON',
        'html': 'HTML',
        'css': 'CSS',
        'scss': 'SCSS',
        'markdown': 'Markdown',
        'python': 'Python',
        'rust': 'Rust',
        'go': 'Go',
        'yaml': 'YAML',
        'xml': 'XML',
        'sql': 'SQL',
        'shell': 'Shell',
        'plaintext': 'Plain Text',
      };
      return names[lang] || lang.charAt(0).toUpperCase() + lang.slice(1);
    }, [language]);

    return (
      <div className={cn('flex flex-col h-full border border-white/5 rounded-md shadow-lg overflow-hidden', className)}>
        {/* Header */}
        {showHeader && (
          <EditorHeader
            filePath={filePath || null}
            status={getEditorStatus()}
            language={languageDisplayName}
            gitStatus={gitStatus}
            showMinimap={showMinimap}
            wordWrapEnabled={wordWrapEnabled}
            onToggleMinimap={handleToggleMinimap}
            onFormat={handleFormat}
            onToggleWordWrap={handleToggleWordWrap}
          />
        )}
        
        {/* Editor Container */}
        <div className="flex-1 relative bg-heaven-bg-primary">
          {/* Loading state */}
          {loading ? (
            <EditorLoadingState message="Loading editor..." />
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
                minimap: { ...editorOptions.minimap, enabled: showMinimap },
                wordWrap: wordWrapEnabled ? 'on' : 'off',
              }}
              onMount={handleEditorMount}
              onChange={handleEditorChange}
              loading={<EditorLoadingState message="Initializing editor..." />}
            />
          )}
        </div>
        
        {/* Context Menu */}
        <EditorContextMenu
          items={contextMenuItems}
          position={contextMenuPosition}
          onClose={() => setContextMenuPosition(null)}
        />
      </div>
    );
  }
);

CodeEditor.displayName = 'CodeEditor';

export default CodeEditor;
