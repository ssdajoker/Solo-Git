/**
 * Solo-Git Specific Commands for Command Palette
 * Extends the standard command palette with Solo-Git workflow commands
 */

import { Command } from '../components/shared/types'

export const soloGitCommands: Command[] = [
  // AI Pairing Commands
  {
    id: 'pair-start',
    label: 'Pair: Start AI Pairing',
    description: 'Start AI pair programming session',
    category: 'ai',
    icon: '🤖',
    shortcut: 'Cmd+Shift+P',
    action: () => {
      console.log('Start AI pairing')
      // In production: window.__TAURI__.invoke('start_ai_pairing')
    }
  },
  {
    id: 'pair-stop',
    label: 'Pair: Stop AI Pairing',
    description: 'End current AI pair programming session',
    category: 'ai',
    icon: '🛑',
    action: () => {
      console.log('Stop AI pairing')
      // In production: window.__TAURI__.invoke('stop_ai_pairing')
    }
  },
  {
    id: 'pair-suggest',
    label: 'Pair: Ask for Suggestion',
    description: 'Get AI suggestion for current context',
    category: 'ai',
    icon: '💡',
    action: () => {
      console.log('Ask AI for suggestion')
    }
  },
  
  // Workpad Commands
  {
    id: 'workpad-create',
    label: 'Workpad: Create',
    description: 'Create new ephemeral workpad',
    category: 'git',
    icon: '📝',
    action: () => {
      console.log('Create workpad')
      // In production: window.__TAURI__.invoke('create_workpad')
    }
  },
  {
    id: 'workpad-promote',
    label: 'Workpad: Promote to Trunk',
    description: 'Promote workpad if tests pass',
    category: 'git',
    icon: '⚡',
    action: () => {
      console.log('Promote workpad')
      // In production: window.__TAURI__.invoke('promote_workpad')
    }
  },
  {
    id: 'workpad-discard',
    label: 'Workpad: Discard',
    description: 'Discard current workpad',
    category: 'git',
    icon: '🗑️',
    action: () => {
      console.log('Discard workpad')
    }
  },
  {
    id: 'workpad-list',
    label: 'Workpad: List All',
    description: 'Show all active workpads',
    category: 'git',
    icon: '📋',
    action: () => {
      console.log('List workpads')
    }
  },
  
  // Testing Commands
  {
    id: 'tests-run',
    label: 'Tests: Run',
    description: 'Run test suite',
    category: 'testing',
    icon: '🧪',
    shortcut: 'Cmd+Shift+T',
    action: () => {
      console.log('Run tests')
      // In production: window.__TAURI__.invoke('run_tests')
    }
  },
  {
    id: 'tests-run-file',
    label: 'Tests: Run Current File',
    description: 'Run tests for current file only',
    category: 'testing',
    icon: '🧪',
    action: () => {
      console.log('Run file tests')
    }
  },
  {
    id: 'tests-run-failed',
    label: 'Tests: Re-run Failed',
    description: 'Re-run only failed tests',
    category: 'testing',
    icon: '🔄',
    action: () => {
      console.log('Re-run failed tests')
    }
  },
  {
    id: 'tests-coverage',
    label: 'Tests: Show Coverage',
    description: 'Display test coverage report',
    category: 'testing',
    icon: '📊',
    action: () => {
      console.log('Show coverage')
    }
  },
  
  // CI/CD Commands
  {
    id: 'ci-pipeline',
    label: 'CI: View Pipeline',
    description: 'Open CI/CD pipeline view',
    category: 'ci',
    icon: '🏗️',
    action: () => {
      console.log('View pipeline')
      // Will open PipelineView component
    }
  },
  {
    id: 'ci-logs',
    label: 'CI: View Build Logs',
    description: 'Show latest build logs',
    category: 'ci',
    icon: '📜',
    action: () => {
      console.log('View build logs')
    }
  },
  {
    id: 'ci-retry',
    label: 'CI: Retry Failed Build',
    description: 'Retry the last failed build',
    category: 'ci',
    icon: '🔄',
    action: () => {
      console.log('Retry build')
    }
  },
  
  // AI Commit Commands
  {
    id: 'ai-commit',
    label: 'AI: Generate Commit Message',
    description: 'AI-powered commit message generation',
    category: 'ai',
    icon: '✨',
    shortcut: 'Cmd+Shift+A',
    action: () => {
      console.log('Generate AI commit message')
      // Will open AICommitAssistant component
    }
  },
  {
    id: 'ai-explain',
    label: 'AI: Explain Changes',
    description: 'Get AI explanation of current changes',
    category: 'ai',
    icon: '📖',
    action: () => {
      console.log('Explain changes')
    }
  },
  {
    id: 'ai-review',
    label: 'AI: Request Code Review',
    description: 'Get AI code review for changes',
    category: 'ai',
    icon: '👁️',
    action: () => {
      console.log('AI code review')
    }
  },
  
  // View Commands
  {
    id: 'focus-mode',
    label: 'Focus: Toggle Mode',
    description: 'Hide all panels except editor',
    category: 'view',
    icon: '🎯',
    shortcut: 'Cmd+Shift+F',
    action: () => {
      console.log('Toggle focus mode')
      // Will hide sidebars and status bar
    }
  },
  {
    id: 'zen-mode',
    label: 'Zen: Toggle Mode',
    description: 'Distraction-free editing mode',
    category: 'view',
    icon: '🧘',
    shortcut: 'Cmd+K Z',
    action: () => {
      console.log('Toggle zen mode')
    }
  },
  {
    id: 'view-test-results',
    label: 'View: Test Results',
    description: 'Open test results panel',
    category: 'view',
    icon: '📊',
    action: () => {
      console.log('Open test results')
      // Will open TestResultsPanel component
    }
  },
  {
    id: 'view-workflow',
    label: 'View: Workflow Status',
    description: 'Show current workflow pipeline',
    category: 'view',
    icon: '⚡',
    action: () => {
      console.log('Open workflow panel')
      // Will open WorkflowPanel component
    }
  },
  
  // Model Selection Commands
  {
    id: 'model-select',
    label: 'Model: Select AI Model',
    description: 'Choose AI model (GPT-4, DeepSeek, Llama)',
    category: 'ai',
    icon: '🤖',
    action: () => {
      console.log('Select model')
    }
  },
  {
    id: 'model-cost',
    label: 'Model: View Cost Breakdown',
    description: 'Show AI usage cost by model',
    category: 'ai',
    icon: '💰',
    action: () => {
      console.log('View cost breakdown')
    }
  },
  
  // Git Operations
  {
    id: 'git-status',
    label: 'Git: Show Status',
    description: 'Display git status',
    category: 'git',
    icon: '📊',
    action: () => {
      console.log('Git status')
    }
  },
  {
    id: 'git-diff',
    label: 'Git: Show Diff',
    description: 'Display git diff',
    category: 'git',
    icon: '📝',
    action: () => {
      console.log('Git diff')
    }
  },
  {
    id: 'git-stage-all',
    label: 'Git: Stage All Changes',
    description: 'Stage all modified files',
    category: 'git',
    icon: '➕',
    action: () => {
      console.log('Stage all')
    }
  },
  {
    id: 'git-unstage-all',
    label: 'Git: Unstage All',
    description: 'Unstage all staged files',
    category: 'git',
    icon: '➖',
    action: () => {
      console.log('Unstage all')
    }
  },
]

export default soloGitCommands
