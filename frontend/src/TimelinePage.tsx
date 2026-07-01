import { useState, useEffect } from 'react'

interface TimelineEvent {
  date: string
  skill: string
  action: string
  detail: string
}

function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([])

  useEffect(() => {
    // 从技能数据生成时间线
    fetch('http://localhost:8000/api/skills')
      .then(r => r.json())
      .then(data => {
        const allEvents: TimelineEvent[] = []
        ;(data.skills || []).forEach((skill: any) => {
          // 创建事件
          allEvents.push({
            date: skill.createdAt || '',
            skill: skill.name,
            action: '创建技能',
            detail: `目标：${skill.goal}`
          })
          // 步骤完成事件
          ;(skill.steps || []).forEach((step: any) => {
            if (step.status === 'completed' && step.completedAt) {
              allEvents.push({
                date: step.completedAt,
                skill: skill.name,
                action: '完成步骤',
                detail: step.content
              })
            }
          })
        })
        // 按日期排序（新的在前）
        allEvents.sort((a, b) => b.date.localeCompare(a.date))
        setEvents(allEvents)
      })
      .catch(() => {})
  }, [])

  // 按日期分组
  const grouped = events.reduce((acc, event) => {
    const date = event.date.split('T')[0]
    if (!acc[date]) acc[date] = []
    acc[date].push(event)
    return acc
  }, {} as Record<string, TimelineEvent[]>)

  return (
    <div className="page">
      <div className="page-header"><h2>📅 学习时间线</h2></div>

      {events.length === 0 ? (
        <div className="empty-state"><p>暂无学习记录</p></div>
      ) : (
        <div className="timeline">
          {Object.entries(grouped).map(([date, dayEvents]) => (
            <div key={date} className="timeline-day">
              <div className="timeline-date">{date}</div>
              <div className="timeline-events">
                {dayEvents.map((event, i) => (
                  <div key={i} className="timeline-event">
                    <div className="timeline-dot"></div>
                    <div className="timeline-content">
                      <strong>{event.skill}</strong> — {event.action}
                      <p>{event.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TimelinePage
