import { useState, useEffect } from 'react';

function MemoryPage() {
  const [list, setList] = useState<any[]>([]);
  useEffect(() => {
    fetch('http://localhost:8000/api/memories').then(r=>r.json()).then(d=>setList(d.memories||[])).catch(()=>{})
  }, []);
  return (
    <div className="page">
      <div className="page-header"><h2>📝 记忆库</h2></div>
      {list.length===0 ? <div className="empty-state"><p>暂无记忆数据</p></div> :
        list.map((m:any,i:number)=>(
          <div key={i} className="card">
            <h3>{m.filename}</h3>
            <pre className="mem-content">{(typeof m.content==='string') ? m.content : JSON.stringify(m.content, null, 2)}</pre>
          </div>
        ))
      }
    </div>
  )
}

export default MemoryPage;
