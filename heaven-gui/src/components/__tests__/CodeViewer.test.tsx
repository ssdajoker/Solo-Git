/**
 * React component tests for CodeViewer
 * Using React Testing Library
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CodeViewer from '../CodeViewer';

describe('CodeViewer', () => {
  it('renders code with syntax highlighting', () => {
    const code = 'const x = 10;';
    render(<CodeViewer code={code} language="typescript" />);
    
    // Check if code content is rendered
    expect(screen.getByText(/const x = 10;/)).toBeInTheDocument();
  });

  it('supports read-only mode', () => {
    const code = 'test';
    render(<CodeViewer code={code} language="typescript" readOnly={true} />);
    
    // Monaco editor should be read-only
    // This would require querying Monaco's internal state
    const editor = screen.getByRole('textbox', { hidden: true });
    expect(editor).toHaveAttribute('readonly');
  });

  it('handles empty code', () => {
    render(<CodeViewer code="" language="typescript" />);
    
    // Should not crash
    const container = screen.getByTestId('code-viewer-container');
    expect(container).toBeInTheDocument();
  });

  it('supports different languages', () => {
    const pythonCode = 'def hello():\n    print("Hello")';
    const { rerender } = render(<CodeViewer code={pythonCode} language="python" />);
    
    expect(screen.getByText(/def hello/)).toBeInTheDocument();
    
    // Change to JavaScript
    const jsCode = 'function hello() { console.log("Hello"); }';
    rerender(<CodeViewer code={jsCode} language="javascript" />);
    
    expect(screen.getByText(/function hello/)).toBeInTheDocument();
  });

  it('handles large files efficiently', () => {
    // Generate large code content (10,000 lines)
    const largeCode = Array.from({ length: 10000 }, (_, i) => `line ${i}`).join('\n');
    
    const startTime = performance.now();
    render(<CodeViewer code={largeCode} language="typescript" />);
    const endTime = performance.now();
    
    // Should render in less than 500ms
    expect(endTime - startTime).toBeLessThan(500);
  });

  it('supports line highlighting', () => {
    const code = 'line1\nline2\nline3';
    render(<CodeViewer code={code} language="typescript" highlightLines={[2]} />);
    
    // Check if line 2 is highlighted (implementation-specific)
    const highlightedLine = screen.queryByTestId('highlighted-line-2');
    expect(highlightedLine).toBeTruthy();
  });

  it('handles code changes', () => {
    const { rerender } = render(<CodeViewer code="initial" language="typescript" />);
    expect(screen.getByText(/initial/)).toBeInTheDocument();
    
    rerender(<CodeViewer code="updated" language="typescript" />);
    expect(screen.getByText(/updated/)).toBeInTheDocument();
  });

  it('supports custom theme', () => {
    render(<CodeViewer code="test" language="typescript" theme="vs-dark" />);
    
    // Monaco should use dark theme
    const editor = screen.getByTestId('monaco-editor');
    expect(editor).toHaveClass('vs-dark');
  });
});

describe('CodeViewer accessibility', () => {
  it('has proper ARIA labels', () => {
    render(<CodeViewer code="test" language="typescript" />);
    
    const editor = screen.getByRole('textbox', { hidden: true });
    expect(editor).toHaveAttribute('aria-label');
  });

  it('supports keyboard navigation', () => {
    render(<CodeViewer code="line1\nline2\nline3" language="typescript" />);
    
    const editor = screen.getByRole('textbox', { hidden: true });
    
    // Simulate keyboard navigation
    fireEvent.keyDown(editor, { key: 'ArrowDown' });
    fireEvent.keyDown(editor, { key: 'ArrowUp' });
    
    // Should not crash
    expect(editor).toBeInTheDocument();
  });
});
