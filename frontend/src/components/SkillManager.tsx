import { useState, useEffect } from 'react'
import './SkillManager.css'

interface Skill {
  id: string
  name: string
  goal: string
  steps: Step[]
  createdAt: string
}

interface Step {
  id: string
  content: string
  status: 'pending' | 'completed'
  note: string
  completedAt?: string
}

function SkillManager() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newSkill, setNewSkill] = useState({ name: '', goal: '', steps: '' })
  const [loading, setLoading] = useState(false)

  // 加载技能列表
  const loadSkills = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/skills')
      const data = await res.json()
      setSkills(data.skills || [])
    } catch (error) {
      console.error('加载技能失败:', error)
    }
  }

  // 初始加载
  useEffect(() => {
    loadSkills()
  }, [])

  const createSkill = async () => {
    if (!newSkill.name || !newSkill.goal) return

    setLoading(true)
    try {
      const steps = newSkill.steps.split('\n').filter(s => s.trim())
      
      const res = await fetch('http://localhost:8000/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newSkill.name,
          goal: newSkill.goal,
          steps: steps
        })
      })

      if (res.ok) {
        setNewSkill({ name: '', goal: '', steps: '' })
        setShowCreateForm(false)
        loadSkills() // 重新加载列表
      }
    } catch (error) {
      console.error('创建技能失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const completeStep = async (skillId: string, stepId: string, note: string) => {
    try {
      await fetch('http://localhost:8000/api/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: skillId,
          completed_step: stepId,
          note: note
        })
      })
      
      loadSkills() // 重新加载
    } catch (error) {
      console.error('更新进度失败:', error)
    }
  }

  return (
    <div className="skill-manager">
      <div className="header">
        <h2>📚 我的技能</h2>
        <button 
          className="button primary"
          onClick={() => setShowCreateForm(true)}
        >
          + 添加技能
        </button>
      </div>

      {showCreateForm && (
        <div className="create-form">
          <input
            type="text"
            placeholder="技能名称（如：雅思、化妆、AI-Agent）"
            value={newSkill.name}
            onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })}
            className="input"
          />
          <input
            type="text"
            placeholder="学习目标（如：雅思7分、能画全妆）"
            value={newSkill.goal}
            onChange={(e) => setNewSkill({ ...newSkill, goal: e.target.value })}
            className="input"
          />
          <textarea
            placeholder="学习步骤（每行一个步骤）&#10;例：&#10;认识化妆工具&#10;练习画眉&#10;画全妆"
            value={newSkill.steps}
            onChange={(e) => setNewSkill({ ...newSkill, steps: e.target.value })}
            className="textarea"
            rows={6}
          />
          <div className="form-actions">
            <button className="button" onClick={() => setShowCreateForm(false)}>取消</button>
            <button className="button primary" onClick={createSkill} disabled={loading}>
              {loading ? '创建中...' : '创建'}
            </button>
          </div>
        </div>
      )}

      <div className="skills-list">
        {skills.map(skill => {
          const completedSteps = skill.steps.filter((s: any) => s.status === 'completed').length
          const totalSteps = skill.steps.length
          const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0

          return (
            <div key={skill.id} className="skill-card">
              <div className="skill-header">
                <h3>{skill.name}</h3>
                <span className="progress-badge">{progress}%</span>
              </div>
              <p className="goal">目标：{skill.goal}</p>
              
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${progress}%` }}
                ></div>
              </div>

              <div className="steps-list">
                {skill.steps.map((step: any) => (
                  <div key={step.id} className={`step-item ${step.status}`}>
                    <input
                      type="checkbox"
                      checked={step.status === 'completed'}
                      onChange={(e) => {
                        if (e.target.checked) {
                          const note = prompt('添加备注（可选）：', step.note)
                          completeStep(skill.id, step.id, note || '')
                        }
                      }}
                    />
                    <span className="step-content">{step.content}</span>
                    {step.status === 'completed' && (
                      <span className="completed-badge">✓ {step.completedAt?.split('T')[0]}</span>
                    )}
                  </div>
                ))}
              </div>
          </div>
          )
        })}
      </div>

      {skills.length === 0 && !showCreateForm && (
        <div className="empty-state">
          <p>还没有添加任何技能</p>
          <p>点击"添加技能"开始你的学习之旅！</p>
        </div>
      )}
    </div>
  )
}

export default SkillManager
