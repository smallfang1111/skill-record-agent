import { useState, useEffect } from 'react';
import './DashboardPage.css';

interface DashboardPageProps {
  onGoSkills: () => void;
}

function DashboardPage({ onGoSkills }: DashboardPageProps) {
  const [stats, setStats] = useState({ skills: 0, completed: 0, sessions: 0 });
  
  useEffect(() => {
    fetch('http://localhost:8000/api/skills')
      .then(r => r.json())
      .then(d => {
        const all = d.skills.flatMap((s: any) => s.steps);
        setStats({
          skills: d.skills.length,
          completed: all.filter((s: any) => s.status === 'completed').length,
          sessions: 0
        });
      })
      .catch(() => {});
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <h2>🏠 学习仪表盘</h2>
      </div>
      <div className="empty-state-large">
        <div className="empty-icon">🎯</div>
        <h3>开始你的学习之旅</h3>
        <p>在「技能管理」中添加技能和学习计划，<br/>追踪进度并与 AI 助手聊天来创建计划！</p>
        <button className="btn-outline" onClick={onGoSkills}>➜ 去添加技能</button>
      </div>
      <div className="stat-cards">
        <div className="stat-card">
          <span className="stat-number">{stats.skills}</span>
          <span className="stat-label">学习技能数</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{stats.completed}</span>
          <span className="stat-label">已完成步骤</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{stats.sessions}</span>
          <span className="stat-label">AI 对话次数</span>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
