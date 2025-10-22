import { useCallback } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import type {
  PromotionRecord,
  RepositoryState,
  TestRun,
  WorkpadState,
} from '../types/soloGit'

interface UseSoloGitOperationsOptions {
  onStateUpdated?: () => Promise<void> | void
}

interface CreateWorkpadOptions {
  repoId: string
  title: string
}

interface RunTestsOptions {
  workpadId: string
  target: string
}

interface PromoteWorkpadOptions {
  workpadId: string
}

interface ApplyPatchOptions {
  workpadId: string
  message: string
  diff: string
}

interface RollbackWorkpadOptions {
  workpadId: string
  reason?: string
}

interface DeleteWorkpadOptions {
  workpadId: string
}

interface CreateRepositoryOptions {
  name: string
  path?: string | null
}

interface DeleteRepositoryOptions {
  repoId: string
}

const toError = (error: unknown): Error => {
  if (error instanceof Error) {
    return error
  }
  if (typeof error === 'string') {
    return new Error(error)
  }
  try {
    return new Error(JSON.stringify(error))
  } catch {
    return new Error('Unknown error')
  }
}

export function useSoloGitOperations({ onStateUpdated }: UseSoloGitOperationsOptions = {}) {
  const refreshState = useCallback(async () => {
    if (!onStateUpdated) {
      return
    }

    try {
      await onStateUpdated()
    } catch (error) {
      console.error('Failed to refresh state after operation', error)
    }
  }, [onStateUpdated])

  const createRepository = useCallback(async ({ name, path }: CreateRepositoryOptions): Promise<RepositoryState> => {
    try {
      const repository = await invoke<RepositoryState>('create_repository', {
        name,
        path: path ?? null,
      })
      await refreshState()
      return repository
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  const deleteRepository = useCallback(async ({ repoId }: DeleteRepositoryOptions): Promise<void> => {
    try {
      await invoke('delete_repository', { repoId })
      await refreshState()
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  const createWorkpad = useCallback(async ({ repoId, title }: CreateWorkpadOptions): Promise<WorkpadState> => {
    try {
      const workpad = await invoke<WorkpadState>('create_workpad', { repoId, title })
      await refreshState()
      return workpad
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  const runTests = useCallback(async ({ workpadId, target }: RunTestsOptions): Promise<TestRun> => {
    try {
      const testRun = await invoke<TestRun>('run_tests', { workpadId, target })
      await refreshState()
      return testRun
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  const promoteWorkpad = useCallback(async ({ workpadId }: PromoteWorkpadOptions): Promise<PromotionRecord> => {
    try {
      const record = await invoke<PromotionRecord>('promote_workpad', { workpadId })
      await refreshState()
      return record
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  const applyPatch = useCallback(async ({ workpadId, message, diff }: ApplyPatchOptions): Promise<WorkpadState> => {
    try {
      const workpad = await invoke<WorkpadState>('apply_patch', { workpadId, message, diff })
      await refreshState()
      return workpad
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  const rollbackWorkpad = useCallback(async ({ workpadId, reason }: RollbackWorkpadOptions): Promise<WorkpadState> => {
    try {
      const workpad = await invoke<WorkpadState>('rollback_workpad', { workpadId, reason })
      await refreshState()
      return workpad
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  const deleteWorkpad = useCallback(async ({ workpadId }: DeleteWorkpadOptions): Promise<void> => {
    try {
      await invoke('delete_workpad', { workpadId })
      await refreshState()
    } catch (error) {
      throw toError(error)
    }
  }, [refreshState])

  return {
    createRepository,
    deleteRepository,
    createWorkpad,
    runTests,
    promoteWorkpad,
    applyPatch,
    rollbackWorkpad,
    deleteWorkpad,
  }
}

export type UseSoloGitOperationsReturn = ReturnType<typeof useSoloGitOperations>
