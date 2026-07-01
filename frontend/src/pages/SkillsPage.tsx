import { useState, useEffect } from 'react';
import Modal from '../components/Modal';

interface Skill { id: string; name: string; goal: string; steps: { id: string; content: string; status: string; note: string; completedAt?: string }[] }

interface SkillsPageProps {
  onOpenDetail: (id: string) => void;
  onOpenEdit: (id: string) => void;
}

function SkillsPage({ onOpenDetail, onOpenEdit }: SkillsPageProps) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', goal: '', steps: '' });
  const [loading, setLoading] = useState(false);

  // 删除确认弹窗状态
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteSkill, setDeleteSkill] = useState<Skill | null>(null);

  // 导出下拉菜单
  const [exportMenuOpen, setExportMenuOpen] = useState(false);

  // 搜索与筛选
  const [searchKey, setSearchKey] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'completed' | 'inprogress'>('all');

  const load = () => fetch('http://localhost:8000/api/skills').then(r => r.json()).then(d => setSkills(d.skills || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  // 创建技能
  const create = async () => {
    if (!form.name || !form.goal) return;
    setLoading(true);
    const steps = form.steps.split('\n').filter(s => s.trim());
    await fetch('http://localhost:8000/api/skills', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: form.name, goal: form.goal, steps })
    });
    setForm({ name: '', goal: '', steps: '' });
    setShowForm(false);
    load();
    setLoading(false);
  };

  // 确认删除
  const confirmDelete = async () => {
    if (!deleteSkill) return;
    await fetch('http://localhost:8000/api/skills/' + deleteSkill.id, { method: 'DELETE' });
    setDeleteOpen(false);
    load();
  };

  // 导出 Markdown
  const exportMarkdown = () => {
    setExportMenuOpen(false);
    let md = '# 学习记录\n\n';
    skills.forEach(skill => {
      const completed = skill.steps.filter((s: any) => s.status === 'completed').length;
      const total = skill.steps.length;
      md += `## ${skill.name}\n\n`;
      md += `**目标**：${skill.goal}\n\n`;
      md += `**进度**：${completed}/${total} (${total ? Math.round(completed / total * 100) : 0}%)\n\n`;
      md += '**步骤**：\n';
      skill.steps.forEach((step: any) => {
        const check = step.status === 'completed' ? '✅' : '⬜';
        md += `- ${check} ${step.content}\n`;
        if (step.note) md += `  > 📝 ${step.note}\n`;
      });
      md += '\n';
    });
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `学习记录_${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 导出 PDF（打印友好页面）
  const exportPDF = () => {
    setExportMenuOpen(false);
    let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>学习记录</title>
    <style>
      body{font-family:'PingFang SC','Microsoft YaHei',sans-serif;padding:40px;color:#333;}
      h1{border-bottom:2px solid #e74c3c;padding-bottom:10px;}
      h2{color:#e74c3c;margin-top:30px;}
      .progress{color:#888;font-size:14px;margin:8px 0;}
      .step{margin:4px 0;font-size:14px;}
      .done{color:#999;text-decoration:line-through;}
      .note{color:#666;font-size:13px;margin:2px 0 2px 24px;padding:4px 8px;background:#f9f9f9;border-radius:4px;}
      @media print{.no-print{display:none;}}
    </style></head><body>
    <button class="no-print" onclick="window.print()" style="padding:8px 20px;background:#e74c3c;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;margin-bottom:20px;">打印 / 保存为 PDF</button>
    <h1>📚 学习记录</h1>`;
    skills.forEach(skill => {
      const completed = skill.steps.filter((s: any) => s.status === 'completed').length;
      const total = skill.steps.length;
      html += `<h2>${skill.name}</h2>`;
      html += `<p><strong>目标：</strong>${skill.goal}</p>`;
      html += `<p class="progress">进度：${completed}/${total}（${total ? Math.round(completed / total * 100) : 0}%）</p>`;
      html += '<div style="margin-top:10px;">';
      skill.steps.forEach((step: any) => {
        const cls = step.status === 'completed' ? 'done' : '';
        html += `<div class="step ${cls}">${step.status === 'completed' ? '✅' : '⬜'} ${step.content}</div>`;
        if (step.note) html += `<div class="note">📝 ${step.note}</div>`;
      });
      html += '</div>';
    });
    html += '</body></html>';
    const w = window.open('', '_blank');
    if (w) w.document.write(html);
  };

  // 筛选后的技能列表
  const filteredSkills = skills.filter(s => {
    const matchKey = !searchKey || s.name.includes(searchKey) || s.goal.includes(searchKey);
    if (filterStatus === 'all') return matchKey;
    if (filterStatus === 'completed') return matchKey && s.steps.filter((st: any) => st.status === 'completed').length === s.steps.length;
    if (filterStatus === 'inprogress') return matchKey && s.steps.filter((st: any) => st.status === 'completed').length < s.steps.length;
    return true;
  });

  return (
    <div className="page">
      <div className="page-header">
        <h2>✅ 技能管理</h2>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button className="btn-primary" onClick={() => setShowForm(!showForm)}>+ 新增技能</button>
          <div style={{ position: 'relative' }}>
            <button className="btn-secondary" onClick={() => setExportMenuOpen(!exportMenuOpen)}>📥 导出 ▾</button>
            {exportMenuOpen && (
              <div style={{ position: 'absolute', top: '100%', right: 0, background: '#fff', border: '1px solid #eee', borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.1)', zIndex: 100, minWidth: 140 }}>
                <button onClick={exportMarkdown} style={{ display: 'block', width: '100%', padding: '10px 16px', border: 'none', background: 'none', textAlign: 'left', cursor: 'pointer', fontSize: 13 }}>📝 导出 Markdown</button>
                <button onClick={exportPDF} style={{ display: 'block', width: '100%', padding: '10px 16px', border: 'none', background: 'none', textAlign: 'left', cursor: 'pointer', fontSize: 13 }}>🖨️ 打印 / 导出 PDF</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 搜索与筛选 */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
        <input
          className="input"
          style={{ flex: 1, maxWidth: 280 }}
          placeholder="🔍 搜索技能名称或目标..."
          value={searchKey}
          onChange={e => setSearchKey(e.target.value)}
        />
        <div style={{ display: 'flex', gap: 6, fontSize: 13 }}>
          {(['all', 'inprogress', 'completed'] as const).map(s => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              style={{
                padding: '6px 14px',
                border: '1px solid ' + (filterStatus === s ? '#e74c3c' : '#eee'),
                borderRadius: 6,
                background: filterStatus === s ? '#e74c3c' : '#fff',
                color: filterStatus === s ? '#fff' : '#666',
                cursor: 'pointer',
                fontSize: 12.5,
                fontWeight: filterStatus === s ? 600 : 400,
              }}
            >
              {s === 'all' ? '全部' : s === 'inprogress' ? '进行中' : '已完成'}
            </button>
          ))}
        </div>
      </div>

      {/* 新增技能表单 */}
      {showForm && (
        <div className="card form-card" style={{ flexDirection: 'column', gap: 12 }}>
          <div className="form-field">
            <label className="field-label"><span className="required">*</span> 技能名称</label>
            <input className="input" placeholder="例如：雅思备考、Python 编程" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-field">
            <label className="field-label"><span className="required">*</span> 学习目标</label>
            <input className="input" placeholder="例如：雅思 7.5 分、掌握基础语法" value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })} />
          </div>
          <div className="form-field">
            <label className="field-label"><span className="required">*</span> 学习步骤</label>
            <textarea className="textarea" rows={5} placeholder={"每行一个步骤，例如：\n背单词 3000 个\n听力练习每天 1 小时\n口语跟读练习"} value={form.steps} onChange={e => setForm({ ...form, steps: e.target.value })} />
          </div>
          <div className="form-actions">
            <button className="btn-secondary" onClick={() => setShowForm(false)}>取消</button>
            <button className="btn-primary" onClick={create} disabled={loading}>{loading ? '创建中...' : '确认创建'}</button>
          </div>
        </div>
      )}

      {/* 技能网格列表 */}
      {filteredSkills.length === 0 && !showForm && (
        <div className="empty-state"><p>{searchKey || filterStatus !== 'all' ? '没有符合条件的技能' : '暂无技能，点击上方按钮添加吧！'}</p></div>
      )}
      <div className="skill-grid">
        {filteredSkills.map(skill => {
          const completed = skill.steps.filter((s: any) => s.status === 'completed').length;
          const total = skill.steps.length;
          const pct = total ? Math.round(completed / total * 100) : 0;
          return (
            <div key={skill.id} className="skill-grid-card" onClick={() => onOpenDetail(skill.id)}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, width: '100%' }}>
                <div className="skill-icon">🧑</div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <h3 className="skill-grid-name" style={{ margin: 0 }}>{skill.name}</h3>
                    <div style={{ display: 'flex', gap: 4 }} onClick={e => e.stopPropagation()}>
                      <button onClick={() => onOpenEdit(skill.id)} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 14, padding: '2px 4px' }} title="编辑">✏️</button>
                      <button onClick={() => { setDeleteSkill(skill); setDeleteOpen(true); }} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 14, padding: '2px 4px' }} title="删除">🗑️</button>
                    </div>
                  </div>
                  <p className="skill-grid-goal">{skill.goal}</p>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, paddingTop: 10, borderTop: '1px solid #f0f0f0' }}>
                <span style={{ fontSize: 11.5, color: '#888' }}>步骤 {completed}/{total}</span>
                <span className="badge" style={{ fontSize: 11 }}>{pct}%</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 删除确认弹窗 */}
      <Modal open={deleteOpen} title="删除技能" onClose={() => setDeleteOpen(false)} width={420}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p style={{ fontSize: 14, color: '#333', lineHeight: 1.6, margin: 0 }}>
            确定将技能【<strong>{deleteSkill?.name}</strong>】删除吗？
          </p>
          <div className="form-actions">
            <button className="btn-secondary" onClick={() => setDeleteOpen(false)}>取消</button>
            <button className="btn-danger" onClick={confirmDelete}>确定删除</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default SkillsPage;
