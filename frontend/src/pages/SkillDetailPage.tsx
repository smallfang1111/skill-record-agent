import { useState, useEffect } from 'react';

interface Skill { id: string; name: string; goal: string; steps: { id: string; content: string; status: string; note: string; completedAt?: string }[] }

interface SkillDetailPageProps {
  skillId: string;
  onBack: () => void;
  onEdit: (id: string) => void;
}

function SkillDetailPage({ skillId, onBack, onEdit }: SkillDetailPageProps) {
  const [skill, setSkill] = useState<Skill | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/skills').then(r => r.json()).then(d => {
      const found = (d.skills || []).find((s:any) => s.id === skillId);
      if (found) setSkill(found);
    }).catch(() => {});
  }, [skillId]);

  // ── 完成步骤 ──
  const toggleDone = async (stepId: string) => {
    if (!skill) return;
    await fetch('http://localhost:8000/api/progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skill_id: skill.id, completed_step: stepId, note: '' })
    });
    fetch('http://localhost:8000/api/skills').then(r => r.json()).then(d => {
      const found = (d.skills || []).find((s:any) => s.id === skillId);
      if (found) setSkill(found);
    });
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
          <button className="btn-secondary" onClick={onBack} style={{ padding: '6px 14px', fontSize: 13 }}>&#8592; 返回</button>
          <h2>&#128218; {skill.name}</h2>
        </div>
        <button className="btn-primary" onClick={() => onEdit(skill.id)}>&#9998; 编辑技能</button>
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
          return (
            <div key={step.id} className={'step-card ' + (isDone ? 'done' : '')}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input type="checkbox" checked={isDone} onChange={() => toggleDone(step.id)} style={{ accentColor: '#e74c3c', width: 16, height: 16 }} />
                <span style={{ fontSize: 14, color: isDone ? '#999' : '#333', textDecoration: isDone ? 'line-through' : 'none', flex: 1 }}>{step.content}</span>
                {isDone && step.completedAt && (
                  <small style={{ color: '#aaa', fontSize: 11.5 }}>&#10003; {step.completedAt.split('T')[0]}</small>
                )}
              </div>
              {hasNote && (
                <div style={{ marginTop: 6, marginLeft: 26, fontSize: 12, color: '#666', background: '#f9f9f9', padding: '6px 10px', borderRadius: 6, lineHeight: 1.5, maxWidth: 500 }}>
                  &#128196; {step.note}
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
