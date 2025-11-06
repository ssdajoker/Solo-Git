import { useCallback, useMemo } from 'react'
import { headlessConfig } from '../config/headless'
import type { GlobalState, RepositoryState, TestRun, WorkpadState } from '../types/soloGit'

type TestTarget = 'fast' | 'full'

interface UseHeadlessServiceOptions {
  baseUrl?: string
  onStateUpdated?: () => Promise<void> | void
}

interface RunTestsOptions {
  workpadId: string
  target?: TestTarget
  parallel?: boolean
}

interface RunTestsResponse {
  run_id: string
  summary: {
    total?: number
    passed?: number
    failed?: number
    skipped?: number
    status?: string
    timeout?: number
    error?: number
  }
  results: Array<Record<string, unknown>>
  duration_ms?: number
}

const sanitizeBaseUrl = (url: string): string => {
  if (!url) {
    return ''
  }
  return url.endsWith('/') ? url.slice(0, -1) : url
}

const toOptionalString = (value: unknown): string | null => {
  if (value === undefined || value === null) {
    return null
  }
  return String(value)
}

const toStringValue = (value: unknown, fallback = ''): string => {
  if (typeof value === 'string') {
    return value
  }
  if (value === undefined || value === null) {
    return fallback
  }
  return String(value)
}

const toIsoString = (value: unknown): string => {
  const asString = toOptionalString(value)
  if (!asString) {
    return new Date().toISOString()
  }
  return asString
}

const toNumberValue = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return fallback
}

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return []
  }
  return value.map((item) => String(item))
}

const normalizeGlobalState = (data: unknown): GlobalState => {
  const record = (data as Record<string, unknown>) ?? {}
  return {
    version: toStringValue(record.version, 'unknown'),
    last_updated: toIsoString(record.last_updated),
    active_repo: toOptionalString(record.active_repo),
    active_workpad: toOptionalString(record.active_workpad),
    session_start: toIsoString(record.session_start),
    total_operations: toNumberValue(record.total_operations, 0),
    total_cost_usd: toNumberValue(record.total_cost_usd, 0),
  }
}

const normalizeRepositoryState = (data: unknown): RepositoryState => {
  const record = (data as Record<string, unknown>) ?? {}
  const state = (record.state as Record<string, unknown>) ?? {}

  return {
    repo_id: toStringValue(state.repo_id ?? record.repo_id ?? record.id ?? ''),
    name: toStringValue(state.name ?? record.name ?? ''),
    path: toStringValue(state.path ?? record.path ?? ''),
    trunk_branch: toStringValue(state.trunk_branch ?? record.trunk_branch ?? 'main'),
    current_commit: toOptionalString(state.current_commit ?? record.current_commit),
    created_at: toIsoString(state.created_at ?? record.created_at),
    updated_at: toIsoString(state.updated_at ?? record.updated_at),
    workpads: toStringArray(state.workpads ?? record.workpads),
    total_commits: toNumberValue(state.total_commits ?? record.total_commits, 0),
  }
}

const normalizeWorkpadState = (data: unknown): WorkpadState => {
  const record = (data as Record<string, unknown>) ?? {}
  const state = (record.state as Record<string, unknown>) ?? {}

  return {
    workpad_id: toStringValue(state.workpad_id ?? record.workpad_id ?? record.id ?? ''),
    repo_id: toStringValue(state.repo_id ?? record.repo_id ?? ''),
    title: toStringValue(state.title ?? record.title ?? ''),
    status: toStringValue(state.status ?? record.status ?? 'unknown'),
    branch_name: toStringValue(state.branch_name ?? record.branch_name ?? ''),
    base_commit: toStringValue(state.base_commit ?? record.base_commit ?? ''),
    current_commit: toOptionalString(state.current_commit ?? record.current_commit),
    created_at: toIsoString(state.created_at ?? record.created_at),
    updated_at: toIsoString(state.updated_at ?? record.updated_at),
    promoted_at: toOptionalString(state.promoted_at ?? record.promoted_at),
    test_runs: toStringArray(state.test_runs ?? record.test_runs),
    ai_operations: toStringArray(state.ai_operations ?? record.ai_operations),
    patches_applied: toNumberValue(state.patches_applied ?? record.patches_applied, 0),
    files_changed: toStringArray(state.files_changed ?? record.files_changed),
  }
}

const normalizeTestRun = (
  data: RunTestsResponse,
  workpadId: string,
  target: TestTarget,
  startedAt: string,
  completedAt: string,
): TestRun => {
  const summary = data.summary ?? {}
  const failed = toNumberValue(summary.failed, 0)
  const timeout = toNumberValue(summary.timeout, 0)
  const error = toNumberValue(summary.error, 0)

  return {
    run_id: toStringValue(data.run_id ?? ''),
    workpad_id: workpadId,
    target,
    status: toStringValue(summary.status, 'failed') === 'green' ? 'passed' : 'failed',
    started_at: startedAt,
    completed_at: completedAt,
    total_tests: toNumberValue(summary.total, 0),
    passed: toNumberValue(summary.passed, 0),
    failed: failed + timeout + error,
    skipped: toNumberValue(summary.skipped, 0),
    duration_ms: toNumberValue(data.duration_ms, 0),
  }
}

const buildError = (response: Response, payload: string): Error => {
  let detail = payload.trim()
  if (detail) {
    try {
      const parsed = JSON.parse(detail) as { detail?: string; error?: string; message?: string }
      detail = parsed.detail ?? parsed.error ?? parsed.message ?? detail
    } catch {
      // Payload is not JSON; use as-is.
    }
  } else {
    detail = response.statusText || 'Request failed'
  }

  return new Error(`Headless service request failed (${response.status}): ${detail}`)
}

export function useHeadlessService({ baseUrl, onStateUpdated }: UseHeadlessServiceOptions = {}) {
  const resolvedBaseUrl = useMemo(() => sanitizeBaseUrl(baseUrl ?? headlessConfig.baseUrl), [baseUrl])

  const maybeRefreshState = useCallback(async () => {
    if (!onStateUpdated) {
      return
    }

    try {
      await onStateUpdated()
    } catch (error) {
      console.error('Failed to refresh headless state after mutation', error)
    }
  }, [onStateUpdated])

  const fetchJson = useCallback(
    async <T,>(path: string, init?: RequestInit): Promise<T> => {
      const url = path.startsWith('http') ? path : `${resolvedBaseUrl}${path}`
      const headers = new Headers({ Accept: 'application/json' })
      if (init?.headers) {
        const extra = new Headers(init.headers)
        extra.forEach((value, key) => headers.set(key, value))
      }

      const response = await fetch(url, { ...init, headers })
      if (response.status === 204) {
        return undefined as T
      }

      const text = await response.text()
      if (!response.ok) {
        throw buildError(response, text)
      }

      const trimmed = text.trim()
      if (!trimmed) {
        throw new Error('Headless service returned empty response')
      }

      try {
        return JSON.parse(trimmed) as T
      } catch (error) {
        throw new Error('Failed to parse headless service response as JSON')
      }
    },
    [resolvedBaseUrl],
  )

  const getGlobalState = useCallback(async (): Promise<GlobalState> => {
    const payload = await fetchJson<Record<string, unknown>>('/state/global')
    return normalizeGlobalState(payload)
  }, [fetchJson])

  const listRepositories = useCallback(async (): Promise<RepositoryState[]> => {
    const payload = await fetchJson<{ repositories?: unknown[] }>('/repos')
    const repositories = Array.isArray(payload.repositories) ? payload.repositories : []
  return repositories.map((repo: unknown) => normalizeRepositoryState(repo))
  }, [fetchJson])

  const listWorkpads = useCallback(async (repoId: string): Promise<WorkpadState[]> => {
    if (!repoId) {
      throw new Error('Repository ID is required to list workpads')
    }

    const payload = await fetchJson<{ workpads?: unknown[] }>(`/repos/${encodeURIComponent(repoId)}/workpads`)
    const workpads = Array.isArray(payload.workpads) ? payload.workpads : []
  return workpads.map((workpad: unknown) => normalizeWorkpadState(workpad))
  }, [fetchJson])

  const runTests = useCallback(
    async ({ workpadId, target = 'fast', parallel = true }: RunTestsOptions): Promise<TestRun> => {
      if (!workpadId) {
        throw new Error('Workpad ID is required to run tests')
      }

      const startedAt = new Date().toISOString()
      const payload = await fetchJson<RunTestsResponse>(
        `/workpads/${encodeURIComponent(workpadId)}/tests`,
        {
          method: 'POST',
          body: JSON.stringify({ target, parallel }),
          headers: { 'Content-Type': 'application/json' },
        },
      )
      const completedAt = new Date().toISOString()
      const testRun = normalizeTestRun(payload, workpadId, target, startedAt, completedAt)
      await maybeRefreshState()
      return testRun
    },
    [fetchJson, maybeRefreshState],
  )

  return {
    getGlobalState,
    listRepositories,
    listWorkpads,
    runTests,
  }
}

export type UseHeadlessServiceReturn = ReturnType<typeof useHeadlessService>
