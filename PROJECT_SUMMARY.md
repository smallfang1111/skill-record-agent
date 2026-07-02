# 学习管家 (Skill Record Agent) — 项目总结

> 最后更新：2026-07-01 15:12

---

## 一、项目初衷

**目标用户**：需要并行学习多种技能的人（如学雅思 + 学编程 + 学化妆）

**核心需求**：
- 记录从 0 到 1 的完整学习过程（不只是"完成了"，而是过程）
- 支持用户自定义技能（不预设固定技能）
- 多技能并行管理，互不干扰
- 跨会话记住学习偏好和目标

**技术定位**：前端转大模型应用开发的 **作品集项目**，需要看起来专业、能演示

---

## 二、技术架构

```
skill-record-agent/          ← 项目根目录
├── frontend/                ← React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx         ← 主组件（只保留路由 + 状态管理，~80行）
│   │   ├── App.css         ← 全局样式（变量 + 布局 + 通用工具类）
│   │   ├── components/     ← 通用组件
│   │   │   ├── Modal.tsx
│   │   │   ├── Modal.css
│   │   │   ├── EditSkillModal.tsx
│   │   │   └── EditSkillModal.css
│   │   └── pages/         ← 页面组件（每个对应一个 .css）
│   │       ├── DashboardPage.tsx / .css
│   │       ├── SkillsPage.tsx / .css
│   │       ├── SkillDetailPage.tsx / .css
│   │       ├── ChatPage.tsx / .css
│   │       ├── MemoryPage.tsx / .css
│   │       └── TimelinePage.tsx / .css
│   ├── index.html
│   └── package.json
│
├── backend/
│   └── main.py              ← FastAPI 后端（所有 API 接口）
│
├── src/
│   ├── agent/               ← AI 核心模块
│   │   ├── core.py         ← agent_loop 主循环 + 压缩管道
│   │   ├── tools.py        ← 工具定义（bash/read_file/write_file/记忆）
│   │   └── memory.py       ← 记忆系统（Markdown + YAML frontmatter）
│   └── data/                ← 数据存储模块
│       ├── skills.py       ← 技能 CRUD（→ data/skills.json）
│       └── chat_sessions.py← 会话 CRUD（→ data/chat_sessions.json）
│
├── data/                    ← 数据文件（持久化）
│   ├── skills.json         ← 技能列表
│   ├── chat_sessions.json  ← AI 对话会话
│   └── memory/             ← 记忆文件（Markdown）
│
├── electron/                ← Electron 桌面应用（待完成）
│   ├── main.js
│   └── preload.js
│
├── .env                     ← 配置（API Key / Model）
└── package.json             ← 根 package.json（Electron 脚本）
```

### 技术栈

| 层级 | 技术 | 原因 |
|------|------|------|
| 前端 | React 18 + TypeScript + Vite | 你是前端，最熟悉；TypeScript 加分 |
| 后端 | FastAPI + Python | 轻量、自动生成 API 文档、Python 生态 |
| AI | Anthropic Claude API（兼容格式，支持 DeepSeek 等） | 灵活切换模型 |
| 存储 | JSON 文件 | 简单、可人工查看、不需要数据库 |
| 桌面应用（计划中） | Electron | 你是前端，零学习成本；打包简单 |

---

## 三、已实现功能

### ✅ 1. 技能管理
- [x] 添加技能（名称 + 目标 + 学习步骤）
- [x] 网格卡片展示（图标 + 名称 + 进度）
- [x] 勾选步骤完成（自动记录完成时间）
- [x] 进度条可视化（%）
- [x] 删除技能（带确认弹窗）
- [x] 编辑技能（弹窗预填当前数据，确定后调用 API）
- [x] 搜索技能名称或目标
- [x] 按状态筛选（全部/进行中/已完成）
- [x] 导出学习记录（Markdown / 打印PDF）
- [x] 数据持久化到 `data/skills.json`

### ✅ 2. 技能详情页
- [x] 点击技能卡片 → 打开独立详情页（非弹窗）
- [x] 显示技能名称、学习目标、完成进度、进度条
- [x] 步骤列表（带 checkbox + 完成时间）
- [x] 点击步骤 → 展开编辑面板
- [x] 编辑面板：修改步骤状态（已完成/进行中）、编辑详细笔记
- [x] 保存步骤修改（调用 `PUT /api/notes` + `POST /api/progress`）

### ✅ 3. AI 对话（类 Claude 风格）
- [x] 多会话管理（New chat / 切换 / 删除）
- [x] 会话按时间分组（Today / Yesterday / 7 Days / Older）
- [x] 自动用首条消息作为会话标题
- [x] 对话历史持久化到 `data/chat_sessions.json`
- [x] 打字动画（●●●）
- [x] 切换 tab 不丢失会话（状态提升到 App 层级）

### ✅ 4. 记忆系统
- [x] 跨会话记忆（写入 `data/memory/*.md`）
- [x] 记忆索引（`MEMORY.md`）
- [x] 记忆查看页面

### ✅ 5. 时间线
- [x] 按日期分组展示学习事件
- [x] 事件类型图标（创建✨ / 完成✅ / 更新📝）

### ✅ 6. UI 风格
- [x] 左侧固定导航 + 右侧内容区
- [x] 简约风格（白底 + 浅灰侧边栏 + 红色主色调 `#e74c3c`）
- [x] 响应式布局
- [x] CSS 按组件拆分（每个 `.tsx` 对应独立 `.css`）

### ✅ 7. 仪表盘
- [x] 欢迎页
- [x] 统计卡片（技能数 / 已完成步骤 / AI 对话次数）
- [x] "去添加技能"按钮（跳转到技能管理）

---

## 四、API 接口列表

### 技能管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills` | 获取所有技能 |
| POST | `/api/skills` | 创建技能 `{name, goal, steps[]}` |
| PUT | `/api/skills/{id}` | 更新技能 `{name, goal, steps[]}` |
| DELETE | `/api/skills/{id}` | 删除技能 |

### 进度管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/progress` | 更新进度 `{skill_id, completed_step, note}` |

### 笔记管理
| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/api/notes` | 保存/更新笔记 `{skill_id, step_id, note}` |

### AI 对话
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sessions` | 获取会话列表（按日期分组） |
| POST | `/api/sessions` | 创建新会话，返回 `{session: {id, title, messages}}` |
| POST | `/api/chat` | 发送消息 `{session_id, message}`，返回更新后的 session |
| DELETE | `/api/sessions/{id}` | 删除会话 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/memories` | 获取记忆列表 `{memories: [{filename, content}]}` |
| GET | `/api/timeline` | 获取时间线 `{events: [{date, type, content, note}]}` |

---

## 五、已知问题与修复记录

| 问题 | 状态 | 修复 |
|------|------|------|
| `main.ts` 包含 JSX 但扩展名是 `.ts` | ✅ 已修复 | 重命名为 `main.tsx` |
| 缺少 React 依赖 | ✅ 已修复 | 安装 react + react-dom + @types |
| 前端显示 Vite 默认页面 | ✅ 已修复 | 重写 `main.tsx` 渲染 `App.tsx` |
| 前后端未联调 | ✅ 已修复 | 前端改为调用后端 API |
| 后端不存储技能数据 | ✅ 已修复 | 创建 `src/data/skills.py` |
| AI 助手无历史记录 | ✅ 已修复 | 创建 `chat_sessions.py` |
| 每次进 AI 助手 tab 都新建会话 | ✅ 已修复 | 状态提升到 App 层级 + `useEffect` 只执行一次 |
| 仪表盘"去添加技能"无反应 | ✅ 已修复 | 传递 `onGoSkills` 回调 |
| 数据文件路径错误 | ✅ 已修复 | 统一改为项目根目录 `data/` |
| `agent_loop` 压缩后 tool_result 报错 | ✅ 已修复 | 添加 `sanitize_tool_results()` |
| Timeline API 500（`'coroutine' object is not iterable`） | ✅ 已修复 | 路由函数名冲突，重命名 `get_timeline` → `get_timeline_api` |
| Timeline API 500（legacy 数据 `NoneType`） | ✅ 已修复 | `skill.get('createdAt') or ''` + `len() >= 10` 防御检查 |
| 编辑技能弹窗不显示数据 | ✅ 已修复 | `editSkillId` 状态提升到 App 层 |
| 编辑技能确定后跳回列表页 | ✅ 已修复 | `onSaved` 回调改为只关闭弹窗，不清除 `detailSkillId` |
| 所有组件堆在 `App.tsx`（803行） | ✅ 已修复 | 按功能拆分到独立 `.tsx` 文件 |
| 所有样式堆在 `App.css` | ✅ 已修复 | 按组件拆分到独立 `.css` 文件 |

---

## 六、前端组件架构

### 6.1 组件树
```
App
├── Sidebar (导航)
├── DashboardPage          (currentPage === 'dashboard')
├── SkillsPage             (currentPage === 'skills' && !detailSkillId)
│   ├── Modal (删除确认)
│   └── Modal (笔记编辑)
├── SkillDetailPage        (currentPage === 'skills' && detailSkillId)
│   └── (步骤展开编辑面板)
├── EditSkillModal         (editSkillId !== null)
├── ChatPage              (currentPage === 'chat')
├── MemoryPage            (currentPage === 'memory')
└── TimelinePage          (currentPage === 'timeline')
```

### 6.2 状态提升策略
- `editSkillId` 提升到 `App` 层 → `SkillsPage` 和 `SkillDetailPage` 都能触发编辑弹窗
- `chatSessions` / `currentSessionId` 提升到 `App` 层 → 切 tab 不丢失对话状态

### 6.3 关键交互设计
| 交互 | 实现方式 |
|------|-----------|
| 点击技能卡片 | `setDetailSkillId(id)` → 切换到 SkillDetailPage |
| 点击"编辑技能" | `setEditSkillId(id)` → 弹出 EditSkillModal |
| 编辑确定 | `onSaved()` → 只关闭弹窗，停留在详情页 |
| 点击步骤名称 | `setEditingStepId(step.id)` → 展开步骤编辑面板 |
| 切换步骤状态 | 调用 `POST /api/progress` → `refreshSkill()` |
| 保存步骤笔记 | 调用 `PUT /api/notes` → `refreshSkill()` |

---

## 七、待完成功能（路线图）

### 阶段 1.5：完善现有功能（下一步）
- [ ] 步骤拖拽排序
- [ ] 技能模板库（预设常见技能的学习计划）
- [ ] 时间线视图优化（添加筛选、搜索）
- [ ] 导出功能优化（支持更多格式：Word、Excel）

### 阶段 2：Electron 桌面应用
- [ ] 配置 Electron 主进程（`electron/main.js` 已创建，需调试）
- [ ] 前端 `npm run build` 后嵌入 Electron
- [ ] 打包成 `.exe` 安装程序
- [ ] 自动启动 Python 后端（打包为 exe）

### 阶段 3：AI 功能增强
- [ ] **RAG**（向量数据库存储记忆，提升检索质量）
- [ ] **LangChain** 集成（更强大的 Agent 框架）
- [ ] **多模态支持**（上传学习笔记图片）
- [ ] **学习分析报告**（AI 生成学习总结）

### 阶段 4：云端与协作
- [ ] 用户账号系统（替代本地文件存储）
- [ ] 云端同步（多设备同步学习进度）
- [ ] 社交功能（分享学习计划给其他用户）

---

## 八、启动指南

### 快速启动（开发模式）

**终端 1：启动后端**
```powershell
cd d:\onlyAlita\skill-record-agent\backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
→ 访问 http://localhost:8000/docs 查看 API 文档

**终端 2：启动前端**
```powershell
cd d:\onlyAlita\skill-record-agent\frontend
npm run dev
```
→ 访问 http://localhost:5173

### 环境变量（`.env`）
```
ANTHROPIC_BASE_URL=https://api.anthropic.com
MODEL_ID=claude-sonnet-4-20250514
# 或者使用兼容 API (如 DeepSeek)
# ANTHROPIC_BASE_URL=https://api.deepseek.com
# MODEL_ID=deepseek-chat
```

---

## 九、给面试官的话术

**"这个项目展示了哪些能力？"**

1. **前端能力**：React + TypeScript + 现代 UI 设计（类 Claude 风格）
2. **后端能力**：FastAPI + Python + RESTful API
3. **AI 集成**：LLM API 调用 + Agent 循环 + 工具调用
4. **系统设计**：记忆系统（类似 RAG 的简化版）
5. **工程能力**：代码重构 + 模块化 + 组件拆分 + CSS 按组件拆分 + 文档

**演示重点**：
1. 打开应用，展示简约风格的界面
2. 在技能管理页创建新技能（如"学雅思"）
3. 添加学习步骤，勾选完成，显示进度条
4. 点击技能卡片，展示详情页和步骤编辑功能
5. 切换到 AI 助手，演示多会话管理
6. 展示记忆系统（AI 记住了之前说的话）

---

## 十、下一步行动

**优先级 1（本周）**：
1. [x] 技能删除功能（已完成）
2. [x] 技能编辑功能（已完成）
3. [x] 学习笔记功能（已完成）
4. [x] 组件按功能拆分（已完成）
5. [x] CSS 按组件拆分（已完成）
6. [ ] 测试所有功能（确保无回归）
7. [ ] 添加步骤拖拽排序

**优先级 2（下周）**：
1. [ ] 开始 Electron 打包
2. [ ] 创建演示视频
3. [ ] 更新 README.md（添加截图和演示视频链接）

**优先级 3（后续）**：
1. [ ] 添加 RAG 功能
2. [ ] 部署到云端（展示在线版本）
3. [ ] 写技术博客（发布到掘金/知乎）

---

## 十一、技术决策记录

### 为什么不用 Streamlit？
- Streamlit 适合快速原型，但不适合做桌面应用
- 界面自定义程度低
- 你是前端，React 更能展示能力

### 为什么不用 PyQt / Tauri？
- **PyQt**：需要学新框架，且界面不如 Web 技术美观
- **Tauri**：需要 Rust，学习曲线陡
- **Electron**：你是前端，零学习成本；打包简单

### 为什么用 JSON 文件而不是数据库？
- 项目规模小，JSON 足够
- 可人工查看/编辑，方便调试
- 后续可迁移到 SQLite（加一层抽象即可）

### 为什么要把所有组件拆分到独立文件？
- **可维护性**：每个文件只负责一个功能，修改时不影响其他组件
- **可读性**：文件短小，快速定位问题
- **复用性**：通用组件（如 `Modal`）可在多个页面复用
- **CSS 隔离**：每个组件对应独立 `.css`，避免样式冲突

---

## 十二、附录

### 参考资料
- [Anthropic Claude API 文档](https://docs.anthropic.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React 文档](https://react.dev/)
- [Vite 文档](https://vitejs.dev/)
- [TypeScript 文档](https://www.typescriptlang.org/docs/)

### 版本历史
- **v2.0** (2026-07-01): 架构重构：FastAPI + React 替代原有 CLI + Streamlit；组件拆分；CSS 按组件拆分；步骤详情编辑功能
- **v1.0** (2026-06-29): 初始版本，支持基本的学习计划创建和进度追踪（CLI + Streamlit）

---

_如有任何问题或需要调整，请随时告诉我！_
