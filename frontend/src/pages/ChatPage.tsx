import { useState, useEffect, useCallback } from 'react';
import './ChatPage.css';

interface Session { id: string; title: string; messages: { role: string; content: string; timestamp: string }[] }

interface ChatPageProps {
  sessions: Record<string, Session[]>;
  setSessions: (s: Record<string, Session[]>) => void;
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
}

function ChatPage({ sessions, setSessions, currentSessionId, setCurrentSessionId }: ChatPageProps) {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/api/sessions');
      const data = await res.json();
      setSessions(data.groups || {});
    } catch (e) {}
  }, [setSessions]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch('http://localhost:8000/api/sessions');
        const data: any = await res.json();
        if (!mounted) return;
        const all = Object.values(data.groups || {}).flat() as any[];
        if (all.length > 0 && !currentSessionId) {
          setCurrentSessionId(all[0].id);
        }
        setSessions(data.groups || {});
      } catch (e) {}
    })();
    return () => { mounted = false; }
  }, []);

  const handleNewChat = async () => {
    const res = await fetch('http://localhost:8000/api/sessions', { method: 'POST' });
    const data = await res.json();
    setCurrentSessionId(data.session.id);
    loadSessions();
  };

  const selectSession = async (id: string) => {
    setCurrentSessionId(id);
  };

  const send = async () => {
    if (!message.trim() || !currentSessionId || loading) return;
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId, message: message.trim() })
      });
      const data = await res.json();
      if (data.session) {
        const updated = { ...sessions };
        for (const group of Object.values(updated)) {
          for (const s of group as any[]) {
            if (s.id === data.session.id) {
              s.messages = data.session.messages;
              break;
            }
          }
        }
        setSessions(updated);
      }
      setMessage('');
    } catch (e) {}
    setLoading(false);
  };

  const del = async (id: string) => {
    if (!confirm('确定删除这个对话吗？')) return;
    await fetch('http://localhost:8000/api/sessions/' + id, { method: 'DELETE' });
    loadSessions();
    if (currentSessionId === id) {
      const all = Object.values(sessions).flat().filter((s: any) => s.id !== id);
      if (all.length > 0) selectSession(all[0].id);
      else { setCurrentSessionId(null); handleNewChat(); }
    }
  };

  const currentSessionFull = (() => {
    if (!currentSessionId) return null;
    for (const group of Object.values(sessions)) {
      for (const s of group) {
        if ((s as any).id === currentSessionId) return s;
      }
    }
    return null;
  })();

  return (
    <div className="page chat-page">
      <div className="page-header"><h2>💬 AI 学习助手</h2><button className="btn-primary" onClick={handleNewChat}>+ New chat</button></div>

      <div className="chat-body">
        <aside className="chat-sidebar">
          <div className="session-list-inner">
            {!Object.values(sessions).some(g => g.length > 0) && (
              <p style={{ padding: 20, textAlign: 'center', color: '#bbb', fontSize: 13 }}>暂无对话</p>
            )}
            {Object.entries(sessions).map(([g, list]) => {
              if (list.length === 0) return null;
              return (
                <div key={g} className="session-group">
                  <div className="group-label">{g}</div>
                  {(list as any[]).map((s: any) => (
                    <div key={s.id} className={'session-row'+(currentSessionId===s.id?' active':'')}>
                      <span className="session-name" onClick={() => selectSession(s.id)}>{s.title || '新对话'}</span>
                      <button className="del-btn" onClick={() => del(s.id)}>&times;</button>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </aside>

        <section className="chat-main">
          {currentSessionFull ? (
            <>
              <div className="messages-box">
                {currentSessionFull.messages.map((m: any, i: number) => (
                  <div key={i} className={'msg '+m.role}><div className="msg-bubble">{m.content.split('\n').map((l: string, ii: number) => <p key={ii}>{l}</p>)}</div></div>
                ))}
                {loading && <div className="msg assistant"><div className="msg-bubble"><span className="dots"><span>&#9679;</span><span>&#9679;</span><span>&#9679;</span></span></div></div>}
                <div ref={(el: HTMLDivElement|null)=>el?.scrollIntoView()}></div>
              </div>
              <div className="input-box">
                <textarea value={message} onChange={e=>setMessage(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder="输入你的问题..." rows={1} disabled={loading}/>
                <button className="send-btn" onClick={send} disabled={!message.trim()||loading}>发送</button>
              </div>
            </>
          ) : (
            <div className="welcome-large">
              <div className="welcome-icon">💬</div>
              <h3>Start chatting with 学习助手</h3>
              <p>点击左侧 "New chat" 或下方按钮开始新对话</p>
              <button className="btn-outline" onClick={handleNewChat}>➜ 开始新对话</button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default ChatPage;
