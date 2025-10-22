
import { useState, useEffect, useRef } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import './AIAssistant.css'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  cost_usd?: number
  model?: string
  tokens?: number
}

// AI operation status type aligned with backend schema
export type AIOperationStatus = 'pending' | 'planning' | 'coding' | 'reviewing' | 'completed' | 'failed'

interface AIOperation {
  operation_id: string
  type: string
  status: AIOperationStatus
  prompt: string
  response: string | null
  cost_usd: number
  tokens_used: number
  model: string
  created_at: string
}

// Helper function to get AI operation status icon
const getOperationStatusIcon = (status: AIOperationStatus): string => {
  switch (status) {
    case 'completed':
      return '✓'
    case 'failed':
      return '✗'
    case 'pending':
      return '○'
    case 'planning':
    case 'coding':
    case 'reviewing':
      return '◉'
    default:
      return '?'
  }
}

interface AIAssistantProps {
  repoId: string | null
  workpadId: string | null
  collapsed?: boolean
  onToggle?: () => void
}

export default function AIAssistant({ repoId, workpadId, collapsed = false, onToggle }: AIAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [operations, setOperations] = useState<AIOperation[]>([])
  const [totalCost, setTotalCost] = useState(0)
  const [selectedModel, setSelectedModel] = useState('gpt-4')
  const [activeTab, setActiveTab] = useState<'chat' | 'history' | 'cost'>('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (repoId && !collapsed) {
      loadOperations()
      const interval = setInterval(loadOperations, 5000)
      return () => clearInterval(interval)
    }
  }, [repoId, collapsed])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadOperations = async () => {
    if (!repoId) return
    
    try {
      const data = await invoke<AIOperation[]>('list_ai_operations', { repoId })
      setOperations(data || [])
      
      const cost = data.reduce((sum, op) => sum + op.cost_usd, 0)
      setTotalCost(cost)
    } catch (e) {
      console.error('Failed to load AI operations:', e)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || !repoId) return
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    
    try {
      await invoke('trigger_ai_operation', {
        workpadId: workpadId ?? '',
        prompt: input,
      })

      const response = await invoke<any>('ai_chat', {
        repoId,
        workpadId,
        prompt: input,
        model: selectedModel,
      })
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
        cost_usd: response.cost_usd,
        model: response.model,
        tokens: response.tokens_used,
      }
      
      setMessages(prev => [...prev, assistantMessage])
      await loadOperations()
    } catch (e) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: `Error: ${e}`,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (collapsed) {
    return (
      <div 
        className="ai-assistant collapsed" 
        onClick={onToggle}
        role="button"
        tabIndex={0}
        aria-label="Expand AI Assistant"
        onKeyPress={(e) => e.key === 'Enter' && onToggle?.()}
      >
        <div className="collapsed-indicator">
          <span className="icon" aria-hidden="true">🤖</span>
          <span className="label">AI</span>
        </div>
      </div>
    )
  }

  return (
    <div className="ai-assistant" role="region" aria-label="AI Assistant">
      <div className="ai-assistant-header">
        <h3 id="ai-assistant-title">AI Assistant</h3>
        <div className="header-actions">
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            className="model-select"
            aria-label="Select AI model"
          >
            <option value="gpt-4">GPT-4 (Planning)</option>
            <option value="gpt-3.5-turbo">GPT-3.5 (Fast)</option>
            <option value="claude-3-opus">Claude Opus</option>
            <option value="gpt-oss-120b">OSS-120B (Local)</option>
          </select>
          <button 
            className="collapse-btn" 
            onClick={onToggle}
            aria-label="Collapse AI Assistant"
          >→</button>
        </div>
      </div>

      <div className="ai-assistant-tabs" role="tablist" aria-label="AI Assistant sections">
        <button 
          className={activeTab === 'chat' ? 'active' : ''} 
          onClick={() => setActiveTab('chat')}
          role="tab"
          aria-selected={activeTab === 'chat'}
          aria-controls="chat-panel"
          id="chat-tab"
        >
          Chat
        </button>
        <button 
          className={activeTab === 'history' ? 'active' : ''} 
          onClick={() => setActiveTab('history')}
          role="tab"
          aria-selected={activeTab === 'history'}
          aria-controls="history-panel"
          id="history-tab"
        >
          History ({operations.length})
        </button>
        <button 
          className={activeTab === 'cost' ? 'active' : ''} 
          onClick={() => setActiveTab('cost')}
          role="tab"
          aria-selected={activeTab === 'cost'}
          aria-controls="cost-panel"
          id="cost-tab"
        >
          Cost (${totalCost.toFixed(2)})
        </button>
      </div>

      <div className="ai-assistant-content">
        {activeTab === 'chat' && (
          <div 
            role="tabpanel" 
            id="chat-panel" 
            aria-labelledby="chat-tab"
          >
            <div className="messages-container" role="log" aria-live="polite" aria-label="Chat messages">
              {messages.length === 0 && (
                <div className="empty-chat">
                  <p className="hint">Start a conversation with the AI assistant</p>
                  <div className="suggestions">
                    <button onClick={() => setInput('Create a new feature for user authentication')}>
                      💡 Plan a feature
                    </button>
                    <button onClick={() => setInput('Explain the current codebase structure')}>
                      📚 Explain code
                    </button>
                    <button onClick={() => setInput('Debug the failing test')}>
                      🐛 Debug issue
                    </button>
                  </div>
                </div>
              )}
              
              {messages.map((msg) => (
                <div key={msg.id} className={`message message-${msg.role}`}>
                  <div className="message-header">
                    <span className="role">{msg.role === 'user' ? '👤' : msg.role === 'assistant' ? '🤖' : '⚠️'}</span>
                    <span className="timestamp">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                    {msg.model && <span className="model">{msg.model}</span>}
                    {msg.cost_usd && <span className="cost">${msg.cost_usd.toFixed(4)}</span>}
                  </div>
                  <div className="message-content">{msg.content}</div>
                </div>
              ))}
              
              {loading && (
                <div className="message message-assistant loading">
                  <div className="message-header">
                    <span className="role">🤖</span>
                    <span className="timestamp">Thinking...</span>
                  </div>
                  <div className="message-content">
                    <span className="loading-dots">●●●</span>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
            
            <div className="input-container">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask AI to plan, code, or explain... (Enter to send, Shift+Enter for new line)"
                disabled={loading || !repoId}
                rows={3}
                aria-label="AI chat input"
                aria-describedby="chat-input-hint"
              />
              <span id="chat-input-hint" className="sr-only">Type your message and press Enter to send, or Shift+Enter for a new line</span>
              <button 
                onClick={handleSend} 
                disabled={loading || !input.trim() || !repoId}
                className="send-btn"
                aria-label={loading ? 'Sending message' : 'Send message'}
              >
                {loading ? '⟳' : '→'}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div 
            className="operations-list"
            role="tabpanel"
            id="history-panel"
            aria-labelledby="history-tab"
          >
            {operations.length === 0 ? (
              <p className="empty-message">No operations yet</p>
            ) : (
              operations.slice(0, 20).map((op) => (
                <div key={op.operation_id} className="operation-item">
                  <div className="operation-header">
                    <span className={`status status-${op.status}`}>
                      {getOperationStatusIcon(op.status)}
                    </span>
                    <span className="operation-type">{op.type}</span>
                    <span className="operation-cost">${op.cost_usd.toFixed(4)}</span>
                  </div>
                  <p className="operation-prompt">{op.prompt.slice(0, 80)}...</p>
                  <div className="operation-meta">
                    <span>{op.model}</span>
                    <span>{op.tokens_used} tokens</span>
                    <span>{new Date(op.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'cost' && (
          <div 
            className="cost-dashboard"
            role="tabpanel"
            id="cost-panel"
            aria-labelledby="cost-tab"
          >
            <div className="cost-summary">
              <div className="cost-card">
                <h4>Total Cost</h4>
                <p className="cost-value">${totalCost.toFixed(2)}</p>
              </div>
              <div className="cost-card">
                <h4>Operations</h4>
                <p className="cost-value">{operations.length}</p>
              </div>
              <div className="cost-card">
                <h4>Avg per Op</h4>
                <p className="cost-value">
                  ${operations.length > 0 ? (totalCost / operations.length).toFixed(4) : '0.00'}
                </p>
              </div>
            </div>
            
            <div className="cost-breakdown">
              <h4>By Model</h4>
              {Array.from(new Set(operations.map(op => op.model))).map(model => {
                const modelOps = operations.filter(op => op.model === model)
                const modelCost = modelOps.reduce((sum, op) => sum + op.cost_usd, 0)
                return (
                  <div key={model} className="cost-item">
                    <span className="model-name">{model}</span>
                    <span className="model-count">{modelOps.length} ops</span>
                    <span className="model-cost">${modelCost.toFixed(4)}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
