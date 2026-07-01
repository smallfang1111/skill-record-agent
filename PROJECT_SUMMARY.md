# 学习管家 (Learning Manager) — 项目总结

> 最后更新：2026-06-30 19:10

---

## 一、项目初衷

**目标用户**：需要并行学习多种技能的人（如学雅思 + 学 AI-Agent + 学化妆）

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
│   │   ├── App.tsx         ← 主组件（所有页面：仪表盘/技能/AI/记忆）
│   │   ├── App.css         ← 全局样式（简约风格）
│   │   └── main.tsx        ← 入口（渲染 App）
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
| AI | DeepSeek API（兼容 Anthropic 格式） | 便宜、国内访问快 |
| 存储 | JSON 文件 | 简单、可人工查看、不需要数据库 |
| 桌面应用（计划中） | Electron | 你是前端，零学习成本；打包简单 |

---

## 三、已实现功能

### ✅ 1. 技能管理
- [x] 添加技能（名称 + 目标 + 学习步骤）
- [x] 查看技能列表
- [x] 勾选步骤完成（自动记录完成时间）
- [x] 进度条可视化（%）
- [x] 删除技能（带确认弹窗）
- [x] 数据持久化到 `data/skills.json`

### ✅ 2. AI 对话（DeepSeek 风格）
- [x] 多会话管理（New chat / 切换 / 删除）
- [x] 会话按时间分组（Today / Yesterday / 7 Days / Older）
- [x] 自动用首条消息作为会话标题
- [x] 对话历史持久化到 `data/chat_sessions.json`
- [x] 打字动画（●●●）
- [x] 切换 tab 不丢失会话（状态提升到 App 层级）

### ✅ 3. 记忆系统
- [x] 跨会话记忆（写入 `data/memory/*.md`）
- [x] 记忆索引（`MEMORY.md`）
- [x] 记忆查看页面

### ✅ 4. UI 风格
- [x] 左侧固定导航 + 右侧内容区
- [x] 简约风格（白底 + 浅灰侧边栏 + 红色主色调 `#e74c3c`）
- [x] 响应式布局

### ✅ 5. 仪表盘
- [x] 欢迎页
- [x] 统计卡片（技能数 / 已完成步骤 / AI 对话次数）
- [x] "去添加技能"按钮（跳转到技能管理）

---

## 四、API 接口列表

### 技能管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills` | 获取所有技能 |
| POST | `/api/skills` | 创建技能 |
| DELETE | `/api/skills/{skill_id}` | 删除技能 |
| POST | `/api/progress` | 更新步骤进度 |

### AI 对话
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sessions` | 获取会话列表（按时间分组） |
| POST | `/api/sessions` | 创建新会话 |
| GET | `/api/sessions/{id}` | 获取会话详情（含消息） |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| POST | `/api/chat` | 发送消息（需要 `session_id`） |

### 记忆系统
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/memories` | 获取所有记忆文件 |
| GET | `/api/memories/{filename}` | 获取单个记忆文件内容 |

### 系统
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

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

---

## 六、待完成功能（路线图）

### 阶段 1.5：完善现有功能（下一步）
- [ ] **技能编辑功能**（修改名称/目标/步骤）
- [ ] **学习笔记**（每个步骤可添加详细笔记，富文本）
- [ ] **时间线视图**（查看学习历史，按日期排序）
- [ ] **导出功能**（导出学习记录为 PDF/Markdown）
- [ ] **技能搜索/筛选**

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

---

## 七、启动指南

### 快速启动（开发模式）

**终端 1：启动后端**
```powershell
cd d:\onlyAlita\skill-record-agent\backend
python main.py
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
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
MODEL_ID=deepseek-chat
ANTHROPIC_API_KEY=your_key_here
```

---

## 八、给面试官的话术

**"这个项目展示了哪些能力？"**

1. **前端能力**：React + TypeScript + 现代 UI 设计（DeepSeek 风格）
2. **后端能力**：FastAPI + Python + RESTful API
3. **AI 集成**：LLM API 调用 + Agent 循环 + 工具调用
4. **系统设计**：记忆系统（类似 RAG 的简化版）
5. **工程能力**：代码重构 + 模块化 + 文档

**演示重点**：
1. 打开应用，展示简约风格的界面
2. 在技能管理页创建新技能（如"学雅思"）
3. 添加学习步骤，勾选完成，显示进度条
4. 切换到 AI 助手，演示多会话管理
5. 展示记忆系统（AI 记住了之前说的话）

---

## 九、下一步行动

**优先级 1（本周）**：
1. ✅ 技能删除功能（已完成）
2. [ ] 技能编辑功能
3. [ ] 学习笔记功能
4. [ ] 测试 AI 对话功能（确保后端正常工作）

**优先级 2（下周）**：
1. [ ] 开始 Electron 打包
2. [ ] 创建演示视频
3. [ ] 更新 README.md（添加截图和演示视频链接）

**优先级 3（后续）**：
1. [ ] 添加 RAG 功能
2. [ ] 部署到云端（展示在线版本）
3. [ ] 写技术博客（发布到掘金/知乎）

---

## 十、技术决策记录

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

---

_如有任何问题或需要调整，请随时告诉我！_
