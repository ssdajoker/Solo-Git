
/**
 * Types for testing and test dashboard
 */

import { GlobalState } from './common'

export type TestStatus = 'passed' | 'failed' | 'skipped' | 'running'

export interface TestResult {
  id: string
  name: string
  file: string
  status: TestStatus
  duration?: number
  error?: string
  output?: string
}

export interface TestSuite {
  id: string
  name: string
  file: string
  tests: TestResult[]
  passed: number
  failed: number
  skipped: number
  total: number
  duration: number
}

export interface TestRun {
  id: string
  timestamp: string
  workpadId: string
  suites: TestSuite[]
  totalPassed: number
  totalFailed: number
  totalSkipped: number
  totalTests: number
  duration: number
  status: 'running' | 'passed' | 'failed' | 'cancelled'
}

export interface BuildInfo {
  id: string
  number: number
  status: 'success' | 'failed' | 'running' | 'cancelled'
  timestamp: string
  duration?: number
  platform?: string
}

export interface StatusBarProps {
  globalState: GlobalState | null
  testRun?: TestRun
  buildInfo?: BuildInfo
  className?: string
}
