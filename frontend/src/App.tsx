import { useState } from 'react'
import './App.css'

type Page = 'dashboard' | 'skills' | 'chat' | 'memory' | 'timeline'

import EditSkillModal from './components/EditSkillModal'
import DashboardPage from './pages/DashboardPage'
import SkillsPage from './pages/SkillsPage'
import SkillDetailPage from './pages/SkillDetailPage'
import ChatPage from './pages/ChatPage'
import MemoryPage from './pages/MemoryPage'
import TimelinePage from './pages/TimelinePage'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [detailSkillId, setDetailSkillId] = useState<string | null>(null)
  const [editSkillId, setEditSkillId] = useState<string | null>(null)

  // 聊天状态提升到这里，避免切 tab 时丢失
  const [chatSessions, setChatSessions] = useState<Record<string, { id: string; title: string; messages: { role: string; content: string; timestamp: string }[] }[]>>({})
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  return (
    <div className="app-layout">
      {/* 左侧边栏 */}
      <aside className="sidebar">
        <div className="logo-area">
          <div className="logo-icon">📚</div>
          <h1 className="logo-title">学习管家</h1>
          <p className="logo-sub">记录你的学习过程</p>
        </div>

        <nav className="nav-menu">
          <button className={'nav-item'+(currentPage==='dashboard'?' active':'')} onClick={()=>setCurrentPage('dashboard')}>🏠 仪表盘</button>
          <button className={'nav-item'+(currentPage==='skills'?' active':'')} onClick={()=>setCurrentPage('skills')}>✅ 技能管理</button>
          <button className={'nav-item'+(currentPage==='chat'?' active':'')} onClick={()=>setCurrentPage('chat')}>💬 AI 助手</button>
          <button className={'nav-item'+(currentPage==='memory'?' active':'')} onClick={()=>setCurrentPage('memory')}>📝 记忆库</button>
          <button className={'nav-item'+(currentPage==='timeline'?' active':'')} onClick={()=>setCurrentPage('timeline')}>🕐 时间线</button>
        </nav>

        <div className="sidebar-footer"><p className="footer-hint">还没有技能？去添加吧！</p></div>
      </aside>

      {/* 右侧内容区 */}
      <main className="main-content">
        <div style={{display: currentPage!=='dashboard' ? 'none' : 'block'}}>
          <DashboardPage onGoSkills={()=>setCurrentPage('skills')} />
        </div>
        <div style={{display: currentPage!=='skills' ? 'none' : 'block'}}>
          {detailSkillId
            ? <SkillDetailPage skillId={detailSkillId} onBack={()=>setDetailSkillId(null)} onEdit={(id)=>{setEditSkillId(id);}} />
            : <SkillsPage onOpenDetail={setDetailSkillId} onOpenEdit={setEditSkillId} />
          }
          {/* 编辑技能弹窗（从 App 层管理，这样详情页也能打开） */}
          {editSkillId && <EditSkillModal skillId={editSkillId} onClose={()=>setEditSkillId(null)} onSaved={()=>{setEditSkillId(null);setDetailSkillId(null);}} />}
        </div>
        <div style={{display: currentPage!=='chat' ? 'none' : 'block'}}>
          <ChatPage
            sessions={chatSessions}
            setSessions={setChatSessions}
            currentSessionId={currentSessionId}
            setCurrentSessionId={setCurrentSessionId}
          />
        </div>
        <div style={{display: currentPage!=='memory' ? 'none' : 'block'}}>
          <MemoryPage />
        </div>
        <div style={{display: currentPage!=='timeline' ? 'none' : 'block'}}>
          <TimelinePage />
        </div>
      </main>
    </div>
  )
}

export default App
