import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CodeViewer from '../CodeViewer'

vi.mock('@monaco-editor/react', () => ({
  default: ({ value }: { value: string }) => <pre data-testid="mock-monaco">{value}</pre>,
  Monaco: {},
}))

const invokeMock = vi.fn()

vi.mock('@tauri-apps/api/tauri', () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}))

describe('CodeViewer', () => {
  beforeEach(() => {
    invokeMock.mockReset()
  })

  it('renders empty state when no file is selected', () => {
    render(<CodeViewer repoId={null} filePath={null} />)

    expect(screen.getByTestId('code-viewer-empty')).toBeInTheDocument()
    expect(invokeMock).not.toHaveBeenCalled()
  })

  it('loads file content via Tauri invoke when repo and file are provided', async () => {
    invokeMock.mockResolvedValueOnce('console.log("hello")')

    render(<CodeViewer repoId="repo-1" filePath="src/index.ts" />)

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledWith('read_file', {
        repoId: 'repo-1',
        filePath: 'src/index.ts',
      })
    })

    expect(await screen.findByTestId('mock-monaco')).toHaveTextContent('console.log("hello")')
  })

  it('gracefully handles read errors', async () => {
    invokeMock.mockRejectedValueOnce(new Error('boom'))

    render(<CodeViewer repoId="repo-1" filePath="src/app.ts" />)

    await waitFor(() => {
      expect(screen.getByTestId('mock-monaco')).toHaveTextContent('Error loading file')
    })
  })

  it('detects language from file extension', async () => {
    invokeMock.mockResolvedValueOnce('print("hi")')

    render(<CodeViewer repoId="repo-1" filePath="scripts/run.py" />)

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalled()
    })

    expect(screen.getByText('scripts/run.py')).toBeInTheDocument()
    expect(screen.getByText('python')).toBeInTheDocument()
  })
})
