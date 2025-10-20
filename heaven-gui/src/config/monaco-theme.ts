/**
 * Monaco Editor Theme Configuration
 * Custom theme matching Heaven UI design system
 */

import type { editor } from 'monaco-editor';

export const heavenTheme: editor.IStandaloneThemeData = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    // Keywords (let, const, function, class, etc.)
    { token: 'keyword', foreground: 'C792EA', fontStyle: 'bold' },
    { token: 'keyword.control', foreground: 'C792EA', fontStyle: 'bold' },
    { token: 'keyword.operator', foreground: 'C792EA' },
    
    // Functions and methods
    { token: 'entity.name.function', foreground: '82AAFF' },
    { token: 'support.function', foreground: '82AAFF' },
    { token: 'meta.function-call', foreground: '82AAFF' },
    
    // Strings
    { token: 'string', foreground: 'C3E88D' },
    { token: 'string.quoted', foreground: 'C3E88D' },
    { token: 'string.template', foreground: 'C3E88D' },
    
    // Numbers
    { token: 'constant.numeric', foreground: 'F78C6C' },
    { token: 'number', foreground: 'F78C6C' },
    
    // Comments
    { token: 'comment', foreground: '546E7A', fontStyle: 'italic' },
    { token: 'comment.line', foreground: '546E7A', fontStyle: 'italic' },
    { token: 'comment.block', foreground: '546E7A', fontStyle: 'italic' },
    
    // Variables and parameters
    { token: 'variable', foreground: 'EEFFFF' },
    { token: 'variable.parameter', foreground: 'EEFFFF' },
    { token: 'variable.other', foreground: 'EEFFFF' },
    
    // HTML/JSX Tags
    { token: 'tag', foreground: 'F07178' },
    { token: 'meta.tag', foreground: 'F07178' },
    { token: 'entity.name.tag', foreground: 'F07178' },
    
    // Types
    { token: 'entity.name.type', foreground: 'FFCB6B' },
    { token: 'support.type', foreground: 'FFCB6B' },
    { token: 'storage.type', foreground: 'FFCB6B' },
    
    // Classes
    { token: 'entity.name.class', foreground: 'FFCB6B' },
    { token: 'support.class', foreground: 'FFCB6B' },
    
    // Properties
    { token: 'variable.other.property', foreground: '89DDFF' },
    { token: 'support.type.property-name', foreground: '89DDFF' },
    
    // Constants
    { token: 'constant', foreground: 'F78C6C' },
    { token: 'constant.language', foreground: 'F78C6C', fontStyle: 'bold' },
    
    // Operators
    { token: 'keyword.operator.new', foreground: 'C792EA' },
    { token: 'keyword.operator.expression', foreground: 'C792EA' },
    
    // Punctuation
    { token: 'punctuation', foreground: '89DDFF' },
    { token: 'delimiter', foreground: '89DDFF' },
    
    // Attributes
    { token: 'entity.other.attribute-name', foreground: 'C792EA' },
    
    // JSON keys
    { token: 'support.type.property-name.json', foreground: '89DDFF' },
    
    // Markdown
    { token: 'markup.heading', foreground: '82AAFF', fontStyle: 'bold' },
    { token: 'markup.bold', foreground: 'EEFFFF', fontStyle: 'bold' },
    { token: 'markup.italic', foreground: 'EEFFFF', fontStyle: 'italic' },
    { token: 'markup.inline.raw', foreground: 'C3E88D' },
    { token: 'markup.list', foreground: 'C792EA' },
  ],
  colors: {
    // Editor background
    'editor.background': '#0A0E1A',
    'editor.foreground': '#EEFFFF',
    
    // Editor UI
    'editor.lineHighlightBackground': '#1A1F2E',
    'editor.selectionBackground': '#2D3748',
    'editor.inactiveSelectionBackground': '#1A1F2E',
    'editor.selectionHighlightBackground': '#2D374855',
    
    // Line numbers
    'editorLineNumber.foreground': '#4A5568',
    'editorLineNumber.activeForeground': '#718096',
    
    // Cursor
    'editorCursor.foreground': '#82AAFF',
    
    // Gutter
    'editorGutter.background': '#0A0E1A',
    'editorGutter.modifiedBackground': '#82AAFF',
    'editorGutter.addedBackground': '#4CAF50',
    'editorGutter.deletedBackground': '#F44336',
    
    // Indentation guides
    'editorIndentGuide.background': '#2D3748',
    'editorIndentGuide.activeBackground': '#4A5568',
    
    // Whitespace
    'editorWhitespace.foreground': '#2D3748',
    
    // Brackets
    'editorBracketMatch.background': '#2D374844',
    'editorBracketMatch.border': '#89DDFF',
    
    // Scrollbar
    'scrollbar.shadow': '#00000000',
    'scrollbarSlider.background': '#2D374844',
    'scrollbarSlider.hoverBackground': '#2D374866',
    'scrollbarSlider.activeBackground': '#2D374888',
    
    // Minimap
    'minimap.background': '#0D1117',
    
    // Widgets
    'editorWidget.background': '#1A1F2E',
    'editorWidget.border': '#2D3748',
    'editorWidget.foreground': '#EEFFFF',
    
    // Suggestions
    'editorSuggestWidget.background': '#1A1F2E',
    'editorSuggestWidget.border': '#2D3748',
    'editorSuggestWidget.foreground': '#EEFFFF',
    'editorSuggestWidget.selectedBackground': '#2D3748',
    'editorSuggestWidget.highlightForeground': '#82AAFF',
    
    // Hover widget
    'editorHoverWidget.background': '#1A1F2E',
    'editorHoverWidget.border': '#2D3748',
    
    // Find widget
    'editorWidget.resizeBorder': '#2D3748',
    'inputOption.activeBackground': '#2D3748',
    'inputOption.activeBorder': '#82AAFF',
    
    // Peek view
    'peekView.border': '#82AAFF',
    'peekViewEditor.background': '#1A1F2E',
    'peekViewResult.background': '#0A0E1A',
    
    // Diff editor
    'diffEditor.insertedTextBackground': '#4CAF5022',
    'diffEditor.removedTextBackground': '#F4433622',
  },
};

export const editorOptions: editor.IStandaloneEditorConstructionOptions = {
  fontSize: 14,
  fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace",
  fontLigatures: true,
  lineHeight: 22,
  letterSpacing: 0.5,
  
  // Line numbers
  lineNumbers: 'on',
  lineNumbersMinChars: 3,
  
  // Cursor
  cursorBlinking: 'smooth',
  cursorSmoothCaretAnimation: 'on',
  cursorWidth: 2,
  
  // Scrolling
  smoothScrolling: true,
  mouseWheelScrollSensitivity: 1,
  fastScrollSensitivity: 5,
  scrollBeyondLastLine: false,
  
  // Minimap
  minimap: {
    enabled: true,
    side: 'right',
    showSlider: 'mouseover',
    renderCharacters: false,
  },
  
  // Code features
  automaticLayout: true,
  formatOnPaste: true,
  formatOnType: true,
  autoClosingBrackets: 'always',
  autoClosingQuotes: 'always',
  autoIndent: 'full',
  tabSize: 2,
  insertSpaces: true,
  wordWrap: 'off',
  
  // UI
  folding: true,
  foldingStrategy: 'indentation',
  showFoldingControls: 'mouseover',
  matchBrackets: 'always',
  renderLineHighlight: 'all',
  renderWhitespace: 'selection',
  renderControlCharacters: false,
  guides: {
    indentation: true,
    highlightActiveIndentation: true,
  },
  
  // Code lens
  codeLens: false,
  
  // Suggestions
  quickSuggestions: {
    other: true,
    comments: false,
    strings: false,
  },
  suggestOnTriggerCharacters: true,
  acceptSuggestionOnCommitCharacter: true,
  acceptSuggestionOnEnter: 'on',
  snippetSuggestions: 'top',
  
  // Padding
  padding: {
    top: 16,
    bottom: 16,
  },
  
  // Scrollbar
  scrollbar: {
    vertical: 'auto',
    horizontal: 'auto',
    useShadows: false,
    verticalScrollbarSize: 10,
    horizontalScrollbarSize: 10,
  },
  
  // Performance
  stopRenderingLineAfter: 10000,
  maxTokenizationLineLength: 20000,
};
