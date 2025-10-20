
/**
 * Types for Git operations and status
 */

export type GitFileStatus = 
  | 'untracked'
  | 'added'
  | 'modified'
  | 'deleted'
  | 'renamed'
  | 'copied'
  | 'unmodified'
  | 'ignored'

export interface GitFileChange {
  path: string
  status: GitFileStatus
  staged: boolean
  additions: number
  deletions: number
}

export interface GitBranch {
  name: string
  current: boolean
  remote?: string
  upstream?: string
  ahead?: number
  behind?: number
}

export interface GitRemote {
  name: string
  url: string
  fetch: string
  push: string
}

export interface GitStatus {
  branch: string
  ahead: number
  behind: number
  staged: GitFileChange[]
  unstaged: GitFileChange[]
  untracked: string[]
  conflicted: string[]
}

export interface Repository {
  id: string
  name: string
  path: string
  branch: string
  remote?: string
  lastCommit?: string
  status?: GitStatus
}
