
/**
 * Types for commit history and timeline
 */

export type CommitStatus = 
  | 'success'    // Merged, all tests passed
  | 'pending'    // In progress
  | 'failed'     // Tests failed or merge conflict
  | 'ai'         // AI-assisted commit

export interface Commit {
  id: string
  sha: string
  message: string
  author: {
    name: string
    email: string
  }
  timestamp: string
  status: CommitStatus
  branch?: string
  tags?: string[]
  parent?: string
  children?: string[]
}

export interface CommitNode extends Commit {
  x: number
  y: number
  connections: string[]  // IDs of connected commits
}

export interface CommitTimelineProps {
  repoId: string | null
  commits?: Commit[]
  selectedCommit?: string | null
  onCommitSelect?: (commitId: string) => void
  onCommitCompare?: (commitId1: string, commitId2: string) => void
  className?: string
  collapsed?: boolean
  onToggleCollapse?: () => void
}

export interface CommitGraphProps {
  commits: CommitNode[]
  width: number
  height: number
  onNodeClick?: (commit: CommitNode) => void
}
