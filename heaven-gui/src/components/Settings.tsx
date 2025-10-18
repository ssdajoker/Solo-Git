
import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import './Settings.css'

interface SettingsProps {
  isOpen: boolean
  onClose: () => void
}

interface Settings {
  theme: 'dark' | 'light'
  editor_font_size: number
  editor_font_family: string
  auto_save: boolean
  auto_format: boolean
  show_minimap: boolean
  vim_mode: boolean
  default_model: string
  cost_limit_daily: number
  notifications_enabled: boolean
  sound_enabled: boolean
}

export default function Settings({ isOpen, onClose }: SettingsProps) {
  const [settings, setSettings] = useState<Settings>({
    theme: 'dark',
    editor_font_size: 14,
    editor_font_family: 'JetBrains Mono',
    auto_save: true,
    auto_format: true,
    show_minimap: true,
    vim_mode: false,
    default_model: 'gpt-4',
    cost_limit_daily: 10,
    notifications_enabled: true,
    sound_enabled: false,
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadSettings()
    }
  }, [isOpen])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const savedSettings = await invoke<Settings>('get_settings')
      setSettings(savedSettings)
    } catch (e) {
      console.error('Failed to load settings:', e)
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    try {
      setLoading(true)
      await invoke('save_settings', { settings })
      onClose()
    } catch (e) {
      console.error('Failed to save settings:', e)
      alert('Failed to save settings')
    } finally {
      setLoading(false)
    }
  }

  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  if (!isOpen) return null

  return (
    <div 
      className="settings-overlay" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2 id="settings-title">Settings</h2>
          <button 
            className="close-btn" 
            onClick={onClose}
            aria-label="Close settings"
          >×</button>
        </div>

        <div className="settings-content">
          <section className="settings-section">
            <h3>Editor</h3>
            
            <div className="setting-item">
              <label htmlFor="font-size">Font Size</label>
              <input
                id="font-size"
                type="number"
                value={settings.editor_font_size}
                onChange={(e) => updateSetting('editor_font_size', parseInt(e.target.value))}
                min="10"
                max="24"
                aria-label="Editor font size"
                aria-describedby="font-size-hint"
              />
              <span id="font-size-hint" className="sr-only">Font size for code editor, between 10 and 24 pixels</span>
            </div>

            <div className="setting-item">
              <label htmlFor="font-family">Font Family</label>
              <select
                id="font-family"
                value={settings.editor_font_family}
                onChange={(e) => updateSetting('editor_font_family', e.target.value)}
                aria-label="Editor font family"
              >
                <option value="JetBrains Mono">JetBrains Mono</option>
                <option value="SF Mono">SF Mono</option>
                <option value="Fira Code">Fira Code</option>
                <option value="Consolas">Consolas</option>
              </select>
            </div>

            <div className="setting-item">
              <label>
                <input
                  type="checkbox"
                  checked={settings.show_minimap}
                  onChange={(e) => updateSetting('show_minimap', e.target.checked)}
                />
                Show Minimap
              </label>
            </div>

            <div className="setting-item">
              <label>
                <input
                  type="checkbox"
                  checked={settings.vim_mode}
                  onChange={(e) => updateSetting('vim_mode', e.target.checked)}
                />
                Vim Mode
              </label>
            </div>

            <div className="setting-item">
              <label>
                <input
                  type="checkbox"
                  checked={settings.auto_save}
                  onChange={(e) => updateSetting('auto_save', e.target.checked)}
                />
                Auto Save
              </label>
            </div>

            <div className="setting-item">
              <label>
                <input
                  type="checkbox"
                  checked={settings.auto_format}
                  onChange={(e) => updateSetting('auto_format', e.target.checked)}
                />
                Auto Format on Save
              </label>
            </div>
          </section>

          <section className="settings-section">
            <h3>AI & Models</h3>
            
            <div className="setting-item">
              <label>Default Model</label>
              <select
                value={settings.default_model}
                onChange={(e) => updateSetting('default_model', e.target.value)}
              >
                <option value="gpt-4">GPT-4 (Planning)</option>
                <option value="gpt-3.5-turbo">GPT-3.5 (Fast)</option>
                <option value="claude-3-opus">Claude Opus</option>
                <option value="gpt-oss-120b">OSS-120B (Local)</option>
              </select>
            </div>

            <div className="setting-item">
              <label>Daily Cost Limit ($)</label>
              <input
                type="number"
                value={settings.cost_limit_daily}
                onChange={(e) => updateSetting('cost_limit_daily', parseFloat(e.target.value))}
                min="0"
                step="0.5"
              />
            </div>
          </section>

          <section className="settings-section">
            <h3>Notifications</h3>
            
            <div className="setting-item">
              <label>
                <input
                  type="checkbox"
                  checked={settings.notifications_enabled}
                  onChange={(e) => updateSetting('notifications_enabled', e.target.checked)}
                />
                Enable Notifications
              </label>
            </div>

            <div className="setting-item">
              <label>
                <input
                  type="checkbox"
                  checked={settings.sound_enabled}
                  onChange={(e) => updateSetting('sound_enabled', e.target.checked)}
                />
                Sound Effects
              </label>
            </div>
          </section>

          <section className="settings-section">
            <h3>Appearance</h3>
            
            <div className="setting-item">
              <label>Theme</label>
              <select
                value={settings.theme}
                onChange={(e) => updateSetting('theme', e.target.value as 'dark' | 'light')}
              >
                <option value="dark">Dark (Heaven)</option>
                <option value="light">Light (Coming Soon)</option>
              </select>
            </div>
          </section>
        </div>

        <div className="settings-footer">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={saveSettings} disabled={loading}>
            {loading ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  )
}
