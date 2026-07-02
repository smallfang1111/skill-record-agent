import { useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import './App.css'

import EditSkillModal from './components/EditSkillModal'
import SettingsModal from './components/SettingsModal'
import DashboardPage from './pages/DashboardPage'
import SkillsPage from './pages/SkillsPage'
import SkillDetailPage from './pages/SkillDetailPage'
import ChatPage from './pages/ChatPage'
import MemoryPage from './pages/MemoryPage'
import TimelinePage from './pages/TimelinePage'

// ── 侧边栏导航组件 ──
function Sidebar({ currentPage, onNavigate, onOpenSettings }: { currentPage: string; onNavigate: (page: string) => void; onOpenSettings: () => void }) {
  const pages = [
    { key: 'dashboard', label: '仪表盘', icon: '🏠' },
    { key: 'skills',    label: '技能管理', icon: '✅' },
    { key: 'chat',      label: 'AI 助手',  icon: '💬' },
    { key: 'memory',    label: '记忆库',   icon: '📝' },
    { key: 'timeline',  label: '时间线',   icon: '🕐' },
  ]
  return (
    <aside className="sidebar">
      <div className="logo-area">
        <div className="logo-icon">📚</div>
        <h1 className="logo-title">学习管家</h1>
        <p className="logo-sub">记录你的学习过程</p>
      </div>
      <nav className="nav-menu">
        {pages.map(p => (
          <button key={p.key} className={'nav-item' + (currentPage === p.key ? ' active' : '')}
            onClick={() => onNavigate(p.key)}>
            {p.icon} {p.label}
          </button>
        ))}
      </nav>
      <div className="sidebar-footer"><p className="footer-hint">还没有技能？去添加吧！</p></div>
      <button className="nav-settings" onClick={onOpenSettings}>&#9881; 设置</button>
    </aside>
  )
}

// ── 主布局 ──
function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()

  // 从 URL 解析当前页面
  const getPageFromPath = (path: string) => {
    if (path.startsWith('/skills')) return 'skills'
    if (path.startsWith('/chat'))   return 'chat'
    if (path.startsWith('/memory')) return 'memory'
    if (path.startsWith('/timeline')) return 'timeline'
    return 'dashboard'
  }
  const currentPage = getPageFromPath(location.pathname)

  // 编辑技能弹窗状态（从 URL search param 读取，刷新不丢失）
  const editSkillIdFromUrl = searchParams.get('edit')
  const [refreshKey, setRefreshKey] = useState(0)
  // 设置弹窗
  const [settingsOpen, setSettingsOpen] = useState(false)

  // 聊天状态提升到这里
  const [chatSessions, setChatSessions] = useState<Record<string, { id: string; title: string; messages: { role: string; content: string; timestamp: string }[] }[]>>({})
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  const onNavigate = (page: string) => {
    const pathMap: Record<string, string> = {
      dashboard: '/',
      skills: '/skills',
      chat: '/chat',
      memory: '/memory',
      timeline: '/timeline',
    }
    navigate(pathMap[page] || '/')
  }

  const openEditModal = (skillId: string) => {
    setSearchParams({ edit: skillId })
  }
  const closeEditModal = () => {
    setSearchParams({})
  }

  return (
    <div className="app-layout">
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} onOpenSettings={() => setSettingsOpen(true)} />

      <main className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage onGoSkills={() => navigate('/skills')} />} />
          <Route path="/skills" element={
            <SkillsPage onOpenEdit={openEditModal} refreshKey={refreshKey} />
          } />
          <Route path="/skills/:skillId" element={
            <SkillDetailPage onEdit={openEditModal} refreshKey={refreshKey} />
          } />
          <Route path="/chat" element={
            <ChatPage sessions={chatSessions} setSessions={setChatSessions}
              currentSessionId={currentSessionId} setCurrentSessionId={setCurrentSessionId} />
          } />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/timeline" element={<TimelinePage />} />
        </Routes>

        {/* 设置弹窗 */}
        <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} onSaved={() => setSettingsOpen(false)} />

        {/* 编辑技能弹窗（从 URL search param 控制，刷新不丢失） */}
        {editSkillIdFromUrl && (
          <EditSkillModal skillId={editSkillIdFromUrl} onClose={closeEditModal}
            onSaved={() => { closeEditModal(); setRefreshKey(k => k + 1) }} />
        )}
      </main>
    </div>
  )
}

// ── 最外层 ──
function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}

export default App
