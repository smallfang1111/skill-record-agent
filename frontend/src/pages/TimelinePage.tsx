import { useState, useEffect } from 'react';

function TimelinePage() {
  const [events, setEvents] = useState<any[]>([]);
  useEffect(()=>{
    fetch('http://localhost:8000/api/timeline').then(r=>r.json()).then(d=>setEvents(d.events||[])).catch(()=>{})
  },[]);

  // 按日期分组
  const grouped: Record<string, any[]> = {};
  events.forEach(e => {
    const d = e.date || '未知日期';
    if (!grouped[d]) grouped[d] = [];
    grouped[d].push(e);
  });
  const dates = Object.keys(grouped).sort().reverse();

  const typeIcon: Record<string, string> = { create: '✨', complete: '✅', update: '📝' };
  const typeColor: Record<string, string> = { create: '#4CAF50', complete: '#e74c3c', update: '#2196F3' };

  return (
    <div className="page">
      <div className="page-header"><h2>🕐 学习时间线</h2></div>
      {dates.length === 0 && <div className="empty-state"><p>暂无学习记录</p></div>}
      <div className="timeline">
        {dates.map(date => (
          <div key={date}>
            <div className="timeline-date">{date}</div>
            {grouped[date].map((e: any, i: number) => (
              <div key={i} className="timeline-item">
                <div className="timeline-dot" style={{background: typeColor[e.type] || '#999'}}></div>
                <div className="timeline-content">
                  <span className="timeline-icon">{typeIcon[e.type] || '📌'}</span>
                  <span className="timeline-text">{e.content}</span>
                  {e.note && <div className="timeline-note">📄 {e.note.length > 50 ? e.note.substring(0,50)+'...' : e.note}</div>}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export default TimelinePage;
