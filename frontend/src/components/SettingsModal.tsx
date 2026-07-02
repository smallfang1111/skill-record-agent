import { useState, useEffect } from 'react';
import Modal from './Modal';
import './SettingsModal.css';

interface Settings {
  model: string;
  apiKey: string;
  baseUrl: string;
  models: string[];
  workspace: string;
}

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

const DEFAULT_MODELS = [
  'claude-sonnet-4-20250514',
  'claude-opus-4-20250514',
  'gpt-4o',
  'gpt-4o-mini',
  'deepseek-v3',
];

type TabKey = 'service' | 'workspace';

function SettingsModal({ open, onClose, onSaved }: SettingsModalProps) {
  const [tab, setTab] = useState<TabKey>('service');
  const [settings, setSettings] = useState<Settings>({
    model: '',
    apiKey: '',
    baseUrl: '',
    models: DEFAULT_MODELS,
    workspace: '',
  });
  const [saving, setSaving] = useState(false);
  const [shaking, setShaking] = useState(false);

  const electronAPI: any = (typeof window !== 'undefined') ? (window as any).electronAPI : undefined;

  // 加载当前配置
  useEffect(() => {
    if (!open) return;
    setTab('service');
    fetch('http://localhost:8000/api/settings')
      .then(r => r.json())
      .then(d => {
        setSettings({
          model: d.model || DEFAULT_MODELS[0],
          apiKey: d.api_key || '',
          baseUrl: d.base_url || '',
          models: d.models || DEFAULT_MODELS,
          workspace: d.workspace || '',
        });
      })
      .catch(() => {});
  }, [open]);

  // 告诉主进程：模态框打开/关闭状态
  useEffect(() => {
    if (open) electronAPI?.setModalOpen?.(true);
    return () => { electronAPI?.setModalOpen?.(false); };
  }, [open]);

  // 监听主进程发来的「抖动」指令（用户尝试关闭/刷新窗口时）
  useEffect(() => {
    const handler = () => {
      setShaking(true);
      setTimeout(() => setShaking(false), 450);
    };
    electronAPI?.onShake?.(handler);
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await fetch('http://localhost:8000/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: settings.model,
          api_key: settings.apiKey.trim(),
          base_url: settings.baseUrl.trim(),
          models: settings.models,
          workspace: settings.workspace.trim(),
        }),
      });
      onSaved();
      onClose();
    } catch {}
    setSaving(false);
  };

  // 选择目录：调用 Electron 系统目录框，返回真实绝对路径
  const pickDir = async () => {
    const p = await electronAPI?.selectDirectory?.();
    if (p) setSettings(s => ({ ...s, workspace: p }));
  };

  if (!open) return null;

  return (
    <Modal open={open} title="⚙️ 设置" onClose={onClose} width={600} closeOnOverlay={false} className={shaking ? 'shake' : ''}>
      <div className="settings-modal">
        <div className="settings-layout">
          {/* 左侧竖排 Tab */}
          <div className="settings-sidebar">
            <button className={'settings-tab' + (tab === 'service' ? ' active' : '')}
              onClick={() => setTab('service')}>智能与服务</button>
            <button className={'settings-tab' + (tab === 'workspace' ? ' active' : '')}
              onClick={() => setTab('workspace')}>工作区</button>
          </div>

          {/* 右侧内容 */}
          <div className="settings-content">
            {tab === 'service' && (
              <div className="settings-section">
                <label className="settings-label">模型与服务</label>
                <div style={{ marginTop: 8 }}>
                  <div className="form-field">
                    <label className="field-label">服务名称</label>
                    <input className="settings-input" value="OpenAI 兼容服务" readOnly style={{ opacity: 0.7 }} />
                  </div>
                  <div className="form-field" style={{ marginTop: 10 }}>
                    <label className="field-label"><span className="required">*</span> 访问密钥（API Key）</label>
                    <input className="settings-input" type="password" value={settings.apiKey}
                      onChange={e => setSettings(s => ({ ...s, apiKey: e.target.value }))}
                      placeholder="sk-xxxxxxxxxxxxxxxx" />
                    <p className="settings-hint">用于调用大模型服务，请妥善保管你的密钥。</p>
                  </div>
                  <div className="form-field" style={{ marginTop: 10 }}>
                    <label className="field-label">服务端点（Base URL）</label>
                    <input className="settings-input" value={settings.baseUrl}
                      onChange={e => setSettings(s => ({ ...s, baseUrl: e.target.value }))}
                      placeholder="https://api.deepseek.com 或 https://api.openai.com/v1" />
                  </div>
                </div>

                <div className="form-field" style={{ marginTop: 14 }}>
                  <label className="settings-label">可用模型</label>
                  <p className="settings-hint">点击选择要使用的模型</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                    {(settings.models || []).map(m => (
                      <span key={m} className={'model-tag' + (settings.model === m ? ' active' : '')}
                        onClick={() => setSettings(s => ({ ...s, model: m }))}>
                        {m === settings.model && <span>&#10003;</span>}
                        {m}
                      </span>
                    ))}
                  </div>
                  <div className="form-field" style={{ marginTop: 12, maxWidth: 320 }}>
                    <input className="settings-input" value={settings.models.includes(settings.model) ? '' : settings.model}
                      onChange={e => setSettings(s => ({ ...s, model: e.target.value }))}
                      placeholder="或输入自定义模型名称..." />
                  </div>
                </div>
              </div>
            )}

            {tab === 'workspace' && (
              <div className="settings-section">
                <label className="settings-label">工作区</label>
                <p className="settings-hint">AI 助手的聊天记录会保存在此目录下的 chat_sessions.json 中。</p>
                <div className="form-field" style={{ marginTop: 12 }}>
                  <label className="field-label">聊天记录存储目录</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input className="settings-input" value={settings.workspace}
                      onChange={e => setSettings(s => ({ ...s, workspace: e.target.value }))}
                      placeholder="例如：D:\my-chat-logs 或 /home/user/chatlogs" />
                    <button type="button" className="btn-secondary" style={{ whiteSpace: 'nowrap' }}
                      onClick={pickDir}>📁 选择目录</button>
                  </div>
                  <p className="settings-hint">
                    留空则使用默认目录（项目内 data/）。点击「选择目录」从系统文件管理器选取。
                  </p>
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="settings-actions">
              <button className="btn-secondary" onClick={onClose}>取消</button>
              <button className="btn-primary" onClick={save} disabled={saving}>
                {saving ? '保存中...' : '&#10003; 保存配置'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}

export default SettingsModal;
