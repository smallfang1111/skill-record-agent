import { useState, useEffect } from 'react';
import Modal from './Modal';

interface Skill { id: string; name: string; goal: string; steps: { id: string; content: string; status: string; note: string; completedAt?: string }[] }

interface EditSkillModalProps {
  skillId: string;
  onClose: () => void;
  onSaved: () => void;
}

function EditSkillModal({ skillId, onClose, onSaved }: EditSkillModalProps) {
  const [skill, setSkill] = useState<Skill | null>(null);
  const [form, setForm] = useState({ name: '', goal: '', steps: '' });
  const [loading, setLoading] = useState(false);

  // 加载技能数据
  useEffect(() => {
    fetch('http://localhost:8000/api/skills').then(r => r.json()).then(d => {
      const found = (d.skills || []).find((s: any) => s.id === skillId);
      if (found) {
        setSkill(found);
        setForm({
          name: found.name,
          goal: found.goal,
          steps: found.steps.map((s: any) => s.content).join('\n')
        });
      }
    }).catch(() => {});
  }, [skillId]);

  // 提交编辑
  const submitEdit = async () => {
    if (!form.name || !form.goal) return;
    setLoading(true);
    const steps = form.steps.split('\n').filter(s => s.trim());
    await fetch('http://localhost:8000/api/skills/' + skillId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.name,
        goal: form.goal,
        steps: steps
      })
    });
    setLoading(false);
    onSaved();
  };

  if (!skill) return null;

  return (
    <Modal open={true} title="编辑技能" onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="form-field">
          <label className="field-label"><span className="required">*</span> 技能名称</label>
          <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="输入技能名称" />
        </div>
        <div className="form-field">
          <label className="field-label"><span className="required">*</span> 学习目标</label>
          <input className="input" value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })} placeholder="输入学习目标" />
        </div>
        <div className="form-field">
          <label className="field-label"><span className="required">*</span> 学习步骤</label>
          <textarea className="textarea" rows={6} value={form.steps} onChange={e => setForm({ ...form, steps: e.target.value })} placeholder="每行一个步骤" />
        </div>
        <div className="form-actions">
          <button className="btn-secondary" onClick={onClose}>取消</button>
          <button className="btn-primary" onClick={submitEdit} disabled={loading}>{loading ? '保存中...' : '确定'}</button>
        </div>
      </div>
    </Modal>
  );
}

export default EditSkillModal;
