/**
 * Heaven UI Complete Demo Page
 * Showcases all components with mock data
 */

import { MainLayout } from '../components/web'
import { GlobalState, TestRun, BuildInfo, GitStatus } from '../components/shared/types'

// Mock global state
const mockGlobalState: GlobalState = {
  version: '0.1.0',
  last_updated: new Date().toISOString(),
  active_repo: 'heaven-gui',
  active_workpad: 'feature/heaven-ui-implementation',
  session_start: new Date(Date.now() - 3600000).toISOString(),
  total_operations: 42,
  total_cost_usd: 1.2345,
}

// Mock test run
const mockTestRun: TestRun = {
  id: 'test-run-1',
  timestamp: new Date().toISOString(),
  workpadId: 'feature/heaven-ui-implementation',
  suites: [
    {
      id: 'suite-1',
      name: 'unit/auth.test.ts',
      file: 'unit/auth.test.ts',
      tests: [],
      passed: 42,
      failed: 0,
      skipped: 0,
      total: 42,
      duration: 1234,
    },
    {
      id: 'suite-2',
      name: 'api/session.test.ts',
      file: 'api/session.test.ts',
      tests: [],
      passed: 27,
      failed: 0,
      skipped: 0,
      total: 27,
      duration: 890,
    },
    {
      id: 'suite-3',
      name: 'ui/plan-pane.test.ts',
      file: 'ui/plan-pane.test.ts',
      tests: [],
      passed: 11,
      failed: 0,
      skipped: 0,
      total: 11,
      duration: 567,
    },
  ],
  totalPassed: 80,
  totalFailed: 0,
  totalSkipped: 0,
  totalTests: 80,
  duration: 2691,
  status: 'passed',
}

// Mock build info
const mockBuildInfo: BuildInfo = {
  id: 'build-384',
  number: 384,
  status: 'success',
  timestamp: new Date().toISOString(),
  duration: 45000,
  platform: 'jenkins',
}

// Mock git status
const mockGitStatus: GitStatus = {
  branch: 'feature/heaven-ui-implementation',
  ahead: 3,
  behind: 0,
  staged: [
    {
      path: 'src/components/web/FileExplorer.tsx',
      status: 'modified',
      staged: true,
      additions: 120,
      deletions: 35,
    },
    {
      path: 'src/components/web/CommitTimeline.tsx',
      status: 'added',
      staged: true,
      additions: 250,
      deletions: 0,
    },
  ],
  unstaged: [
    {
      path: 'src/components/web/StatusBar.tsx',
      status: 'modified',
      staged: false,
      additions: 45,
      deletions: 12,
    },
  ],
  untracked: [
    'src/components/web/MainLayout.tsx',
  ],
  conflicted: [],
}

export function HeavenUIDemo() {
  const handleCommand = (command: string) => {
    console.log('Command received:', command)
    // In production, this would trigger AI actions
  }
  
  return (
    <div className="h-screen w-screen overflow-hidden">
      <MainLayout
        repoId="heaven-gui"
        globalState={mockGlobalState}
        testRun={mockTestRun}
        buildInfo={mockBuildInfo}
        gitStatus={mockGitStatus}
        onCommand={handleCommand}
      />
    </div>
  )
}

export default HeavenUIDemo
