import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './SkillDetailPage.css';

interface Skill { id: string; name: string; goal: string; steps: { id: string; content: string; status: string; note: string; completedAt?: string }[] }

interface SkillDetailPageProps {
  onEdit: (id: string) => void;
  refreshKey?: number;
}

function SkillDetailPage({ onEdit, refreshKey }: SkillDetailPageProps) {
  const { skillId } = useParams<{ skillId: string }>();
  const navigate = useNavigate();
  const [skill, setSkill] = useState<Skill | null>(null);

  // ── 步骤详情编辑状态 ──
  const [editingStepId, setEditingStepId] = useState<string | null>(null);
  const [editStepForm, setEditStepForm] = useState({ content: '', note: '', status: 'inprogress' });
  const [savingStep, setSavingStep] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/skills').then(r => r.json()).then(d => {
      const found = (d.skills || []).find((s:any) => s.id === skillId);
      if (found) setSkill(found);
    }).catch(() => {});
  }, [skillId, refreshKey]);

  // ── 刷新技能数据 ──
  const refreshSkill = () => {
    fetch('http://localhost:8000/api/skills').then(r => r.json()).then(d => {
      const found = (d.skills || []).find((s:any) => s.id === skillId);
      if (found) setSkill(found);
    });
  };

  // ── 快速切换完成状态（checkbox） ──
  // 切换后自动打开步骤编辑面板，方便用户补充笔记
  const toggleDone = async (stepId: string) => {
    if (!skill) return;
    const step = skill.steps.find((s: any) => s.id === stepId);
    const newStatus = step && step.status === 'completed' ? 'inprogress' : 'completed';
    await fetch('http://localhost:8000/api/progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skill_id: skill.id, completed_step: stepId, note: '', status: newStatus })
    });
    refreshSkill();
    // 切换完成后自动打开编辑面板，方便补充笔记
    if (step) {
      setTimeout(() => {
        openStepEdit({ ...step, status: newStatus });
      }, 100);
    }
  };

  // ── 打开步骤详情编辑 ──
  const openStepEdit = (step: any) => {
    setEditStepForm({
      content: step.content,
      note: step.note || '',
      status: step.status || 'inprogress'
    });
    setEditingStepId(step.id);
  };

  // ── 关闭步骤编辑（不保存） ──
  const closeStepEdit = () => {
    setEditingStepId(null);
    setSavingStep(false);
  };

  // ── 保存步骤详情编辑 ──
  const saveStepEdit = async () => {
    if (!skill || !editingStepId) return;
    setSavingStep(true);

    // 如果状态变了，调用 progress 接口（双向都处理）
    const currentStep = skill.steps.find((s: any) => s.id === editingStepId);
    if (currentStep && currentStep.status !== editStepForm.status) {
      await fetch('http://localhost:8000/api/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: skill.id, completed_step: editingStepId, note: '', status: editStepForm.status })
      });
    }

    // 更新笔记（无论是否有变化都调一下，保持数据一致）
    await fetch('http://localhost:8000/api/notes', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        skill_id: skill.id,
        step_id: editingStepId,
        note: editStepForm.note
      })
    });

    refreshSkill();
    closeStepEdit();
  };

  if (!skill) return <div className="page"><p style={{ color: '#888' }}>加载中...</p></div>;

  const completed = skill.steps.filter((s:any) => s.status === 'completed').length;
  const total = skill.steps.length;
  const pct = total ? Math.round(completed / total * 100) : 0;

  return (
    <div className="page">
      {/* 返回 + 标题 */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn-secondary" onClick={() => navigate('/skills')} style={{ padding: '6px 14px', fontSize: 13 }}>&#8592; 返回</button>
          <h2>&#128218; {skill.name}</h2>
        </div>
        <button className="btn-primary" onClick={() => onEdit(skill?.id || '')}>&#9998; 编辑技能</button>
      </div>

      {/* 信息卡片 */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 40, flexWrap: 'wrap' }}>
          <div>
            <span className="note-step-label">学习目标</span>
            <p style={{ fontSize: 15, color: '#333', marginTop: 4 }}>{skill.goal}</p>
          </div>
          <div>
            <span className="note-step-label">完成进度</span>
            <p style={{ fontSize: 24, fontWeight: 700, color: 'var(--primary)', marginTop: 4 }}>
              {completed}/{total} <span style={{ fontSize: 13, color: '#888' }}>({pct}%)</span>
            </p>
          </div>
        </div>

        {/* 进度条 */}
        <div className="progress-bar" style={{ height: 10, borderRadius: 5, marginTop: 16 }}>
          <div className="progress-fill" style={{ width: pct + '%', height: '100%', borderRadius: 5 }} />
        </div>
      </div>

      {/* 步骤列表 */}
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>学习步骤</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {skill.steps.map((step:any) => {
          const isDone = step.status === 'completed';
          const hasNote = !!step.note;
          const isEditing = editingStepId === step.id;

          return (
            <div key={step.id} className={'step-card ' + (isDone && !isEditing ? 'done' : '') + (isEditing ? ' editing' : '')}>
              {/* 步骤头部：checkbox + 名称 + 操作按钮 */}
              {!isEditing ? (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <input type="checkbox" checked={isDone} onChange={() => toggleDone(step.id)} style={{ accentColor: '#e74c3c', width: 16, height: 16 }} />
                    <span style={{ fontSize: 14, color: isDone ? '#999' : '#333', textDecoration: isDone ? 'line-through' : 'none', flex: 1 }}
                      title={hasNote ? step.note : ''}
                    >{step.content}</span>
                    <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                      {isDone && step.completedAt && (
                        <small style={{ color: '#aaa', fontSize: 11.5 }}>&#10003; {step.completedAt.split('T')[0]}</small>
                      )}
                      <button onClick={(e) => { e.stopPropagation(); openStepEdit(step); }}
                        style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 13, padding: '2px 6px', color: '#e74c3c', opacity: 0.7 }}
                        title="编辑步骤详情"
                        onMouseEnter={e => (e.target as HTMLElement).style.opacity='1'}
                        onMouseLeave={e => (e.target as HTMLElement).style.opacity='0.7'}
                      >&#9998; 详情</button>
                    </div>
                  </div>
                  {/* 已有笔记的预览（非编辑态） */}
                  {hasNote && (
                    <div style={{ marginTop: 6, marginLeft: 26, fontSize: 12, color: '#666', background: '#f9f9f9', padding: '6px 10px', borderRadius: 6, lineHeight: 1.5, maxWidth: 500 }}
                    >
                      &#128196; {step.note.length > 80 ? step.note.substring(0, 80) + '...' : step.note}
                    </div>
                  )}
                </>
              ) : (
                /* ── 展开的步骤编辑区 ── */
                <div className="step-edit-panel">
                  {/* 第一行：状态切换 + 步骤名称 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    <label style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '4px 12px',
                      borderRadius: 20,
                      border: `1px solid ${editStepForm.status === 'completed' ? '#e74c3c' : '#ddd'}`,
                      background: editStepForm.status === 'completed' ? '#fff5f5' : '#fff',
                      color: editStepForm.status === 'completed' ? '#e74c3c' : '#666',
                      fontSize: 12.5,
                      fontWeight: 500,
                      cursor: 'pointer',
                      userSelect: 'none'
                    }} onClick={() => setEditStepForm(prev => ({ ...prev, status: prev.status === 'completed' ? 'inprogress' : 'completed' }))}>
                      <span style={{
                        width: 14, height: 14, borderRadius: '50%',
                        border: `2px solid ${editStepForm.status === 'completed' ? '#e74c3c' : '#ccc'}`,
                        background: editStepForm.status === 'completed' ? '#e74c3c' : '#fff',
                        position: 'relative'
                      }}>
                        {editStepForm.status === 'completed' && (
                          <span style={{ position: 'absolute', top: -1, left: 2, color: '#fff', fontSize: 9 }}>&#10003;</span>
                        )}
                      </span>
                      {editStepForm.status === 'completed' ? '已完成' : '进行中'}
                    </label>
                    <input className="input"
                      value={editStepForm.content}
                      onChange={e => setEditStepForm(prev => ({ ...prev, content: e.target.value }))}
                      placeholder="步骤名称"
                      style={{ flex: 1, fontSize: 14, padding: '6px 12px' }}
                    />
                  </div>

                  {/* 第二行：详细笔记 */}
                  <div className="form-field" style={{ marginBottom: 8 }}>
                    <label className="field-label">详细笔记</label>
                    <textarea
                      className="textarea"
                      rows={4}
                      value={editStepForm.note}
                      onChange={e => setEditStepForm(prev => ({ ...prev, note: e.target.value }))}
                      placeholder="记录学习心得、重点内容、参考资料..."
                      style={{ fontSize: 13 }}
                    />
                    <div className="char-count">{editStepForm.note.length} 字</div>
                  </div>

                  {/* 第三行：操作按钮 */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                    <button className="btn-secondary" onClick={closeStepEdit} disabled={savingStep}>取消</button>
                    <button className="btn-primary" onClick={saveStepEdit} disabled={savingStep || !editStepForm.content.trim()}>
                      {savingStep ? '保存中...' : '&#10003; 保存修改'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {total === 0 && <div className="empty-state"><p>暂无步骤</p></div>}
    </div>
  );
}

export default SkillDetailPage;
