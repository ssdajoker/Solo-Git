
/**
 * Test Results Panel Component
 * Slide-in panel from right for detailed test results
 * Esc to close, live streaming test output
 */

import { useState } from 'react'
import { cn } from '../shared/utils'

// Import shared TestStatus type
export type TestStatus = 'passed' | 'failed' | 'skipped' | 'running' | 'pending'

export interface TestCase {
  id: string
  name: string
  status: TestStatus
  duration: number
  error?: string
  assertion?: string
}

export interface TestSuite {
  id: string
  file: string
  tests: TestCase[]
  passed: number
  failed: number
  skipped: number
  duration: number
}

export interface TestResultsPanelProps {
  isOpen: boolean
  onClose: () => void
  suites: TestSuite[]
  totalTests: number
  totalPassed: number
  totalFailed: number
  totalSkipped: number
  duration: number
  isLiveStreaming?: boolean
  className?: string
}

// Helper function to get status icon for any status value
const getTestStatusIcon = (status: TestStatus): string => {
  switch (status) {
    case 'passed':
      return '✓'
    case 'failed':
      return '✗'
    case 'running':
      return '◉'
    case 'pending':
      return '○'
    case 'skipped':
      return '⊘'
    default:
      return '?'
  }
}

// Helper function to get status color class
const getTestStatusColor = (status: TestStatus): string => {
  switch (status) {
    case 'passed':
      return 'text-heaven-accent-green'
    case 'failed':
      return 'text-heaven-accent-red'
    case 'running':
      return 'text-heaven-accent-blue'
    case 'pending':
      return 'text-heaven-text-tertiary'
    case 'skipped':
      return 'text-heaven-text-tertiary'
    default:
      return 'text-heaven-text-secondary'
  }
}

export function TestResultsPanel({
  isOpen,
  onClose,
  suites,
  totalTests,
  totalPassed,
  totalFailed,
  totalSkipped,
  duration,
  isLiveStreaming = false,
  className,
}: TestResultsPanelProps) {
  const [expandedSuites, setExpandedSuites] = useState<Set<string>>(new Set())
  const [selectedTest, setSelectedTest] = useState<TestCase | null>(null)
  const [filterStatus, setFilterStatus] = useState<TestStatus | 'all'>('all')
  
  if (!isOpen) return null
  
  const toggleSuite = (suiteId: string) => {
    setExpandedSuites(prev => {
      const next = new Set(prev)
      if (next.has(suiteId)) {
        next.delete(suiteId)
      } else {
        next.add(suiteId)
      }
      return next
    })
  }
  
  const filteredSuites = suites.map(suite => ({
    ...suite,
    tests: filterStatus === 'all' 
      ? suite.tests 
      : suite.tests.filter(t => t.status === filterStatus)
  }))
  
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }
  
  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 animate-in fade-in duration-150"
        onClick={onClose}
      />
      
      {/* Panel */}
      <div 
        className={cn(
          'fixed top-0 right-0 bottom-0 w-[600px] bg-heaven-bg-secondary border-l border-white/10 shadow-2xl z-50',
          'animate-in slide-in-from-right duration-300',
          'flex flex-col',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div>
            <h2 className="text-lg font-semibold text-heaven-text-primary mb-1">
              Test Results
            </h2>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-heaven-accent-green">✓ {totalPassed}</span>
              {totalFailed > 0 && (
                <span className="text-heaven-accent-red">✗ {totalFailed}</span>
              )}
              {totalSkipped > 0 && (
                <span className="text-heaven-text-tertiary">○ {totalSkipped}</span>
              )}
              <span className="text-heaven-text-tertiary">/ {totalTests}</span>
              <span className="text-heaven-text-tertiary">{formatDuration(duration)}</span>
              {isLiveStreaming && (
                <span className="flex items-center gap-1 text-heaven-accent-cyan">
                  <span className="w-2 h-2 rounded-full bg-heaven-accent-cyan animate-pulse" />
                  Live
                </span>
              )}
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 text-heaven-text-secondary hover:text-heaven-text-primary transition-colors duration-150"
            aria-label="Close (Esc)"
          >
            ✕
          </button>
        </div>
        
        {/* Filter Bar */}
        <div className="flex items-center gap-2 p-4 border-b border-white/5">
          <button
            onClick={() => setFilterStatus('all')}
            className={cn(
              'px-3 py-1.5 text-xs rounded transition-colors duration-150',
              filterStatus === 'all'
                ? 'bg-heaven-accent-cyan text-heaven-bg-primary'
                : 'bg-heaven-bg-tertiary text-heaven-text-secondary hover:bg-heaven-bg-hover'
            )}
          >
            All ({totalTests})
          </button>
          <button
            onClick={() => setFilterStatus('failed')}
            className={cn(
              'px-3 py-1.5 text-xs rounded transition-colors duration-150',
              filterStatus === 'failed'
                ? 'bg-heaven-accent-red text-white'
                : 'bg-heaven-bg-tertiary text-heaven-text-secondary hover:bg-heaven-bg-hover'
            )}
          >
            Failed ({totalFailed})
          </button>
          <button
            onClick={() => setFilterStatus('passed')}
            className={cn(
              'px-3 py-1.5 text-xs rounded transition-colors duration-150',
              filterStatus === 'passed'
                ? 'bg-heaven-accent-green text-white'
                : 'bg-heaven-bg-tertiary text-heaven-text-secondary hover:bg-heaven-bg-hover'
            )}
          >
            Passed ({totalPassed})
          </button>
          <button
            onClick={() => setFilterStatus('skipped')}
            className={cn(
              'px-3 py-1.5 text-xs rounded transition-colors duration-150',
              filterStatus === 'skipped'
                ? 'bg-heaven-text-tertiary text-white'
                : 'bg-heaven-bg-tertiary text-heaven-text-secondary hover:bg-heaven-bg-hover'
            )}
          >
            Skipped ({totalSkipped})
          </button>
        </div>
        
        {/* Test Suites */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {filteredSuites.map((suite) => (
            <div key={suite.id} className="bg-heaven-bg-tertiary rounded-lg overflow-hidden">
              {/* Suite Header */}
              <button
                onClick={() => toggleSuite(suite.id)}
                className="w-full flex items-center justify-between p-3 hover:bg-heaven-bg-hover transition-colors duration-150"
              >
                <div className="flex items-center gap-3">
                  <span className={cn(
                    'text-lg',
                    suite.failed > 0 ? 'text-heaven-accent-red' : 'text-heaven-accent-green'
                  )}>
                    {suite.failed > 0 ? '✗' : '✓'}
                  </span>
                  <div className="text-left">
                    <div className="text-sm font-medium text-heaven-text-primary">
                      {suite.file}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-heaven-text-tertiary">
                      <span className="text-heaven-accent-green">✓ {suite.passed}</span>
                      {suite.failed > 0 && (
                        <span className="text-heaven-accent-red">✗ {suite.failed}</span>
                      )}
                      {suite.skipped > 0 && (
                        <span>○ {suite.skipped}</span>
                      )}
                      <span>{formatDuration(suite.duration)}</span>
                    </div>
                  </div>
                </div>
                
                <span className={cn(
                  'text-heaven-text-tertiary transition-transform duration-150',
                  expandedSuites.has(suite.id) && 'rotate-90'
                )}>
                  ▶
                </span>
              </button>
              
              {/* Test Cases */}
              {expandedSuites.has(suite.id) && (
                <div className="border-t border-white/5">
                  {suite.tests.map((test) => (
                    <button
                      key={test.id}
                      onClick={() => setSelectedTest(test)}
                      className={cn(
                        'w-full flex items-center justify-between p-3 hover:bg-heaven-bg-hover transition-colors duration-150',
                        selectedTest?.id === test.id && 'bg-heaven-bg-active'
                      )}
                    >
                      <div className="flex items-center gap-2 flex-1 text-left">
                        <span className={cn('text-sm', getTestStatusColor(test.status))}>
                          {getTestStatusIcon(test.status)}
                        </span>
                        <span className="text-sm text-heaven-text-primary truncate">
                          {test.name}
                        </span>
                      </div>
                      <span className="text-xs text-heaven-text-tertiary">
                        {formatDuration(test.duration)}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Selected Test Details */}
        {selectedTest && (
          <div className="border-t border-white/5 p-4 bg-heaven-bg-tertiary max-h-64 overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-heaven-text-primary">
                {selectedTest.name}
              </h3>
              <button
                onClick={() => setSelectedTest(null)}
                className="text-xs text-heaven-text-secondary hover:text-heaven-text-primary"
              >
                Hide
              </button>
            </div>
            
            {selectedTest.error && (
              <div className="mb-2">
                <div className="text-xs text-heaven-text-secondary mb-1">Error:</div>
                <div className="bg-heaven-bg-primary rounded p-2 text-xs text-heaven-accent-red font-mono">
                  {selectedTest.error}
                </div>
              </div>
            )}
            
            {selectedTest.assertion && (
              <div>
                <div className="text-xs text-heaven-text-secondary mb-1">Assertion:</div>
                <div className="bg-heaven-bg-primary rounded p-2 text-xs text-heaven-text-primary font-mono">
                  {selectedTest.assertion}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Footer */}
        <div className="p-4 border-t border-white/5 flex items-center justify-between">
          <button
            className="text-xs text-heaven-accent-cyan hover:underline"
            onClick={() => {
              // Export as JSON
              const data = { suites, totalTests, totalPassed, totalFailed, totalSkipped, duration }
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = 'test-results.json'
              a.click()
            }}
          >
            Export as JSON
          </button>
          
          <span className="text-xs text-heaven-text-tertiary">
            Press Esc to close
          </span>
        </div>
      </div>
    </>
  )
}

export default TestResultsPanel
