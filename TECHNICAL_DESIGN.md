# 学习管家 (Skill Record Agent) - 技术设计文档

## 1. 项目概述

### 1.1 项目背景
现代人需要并行学习多种技能（如雅思、编程、化妆等），需要一个应用来记录和管理整个学习过程，包括：
- 制定学习计划
- 记录学习进度
- 追踪技能成长轨迹
- 通过 AI 对话辅助学习

### 1.2 项目目标
构建一个智能化的学习管理 Web 应用，帮助用户：
1. 为多个技能创建并行学习计划
2. 记录每次学习的进度和心得
3. 通过 AI 助手提供学习建议和鼓励
4. 持久化记忆用户的学习偏好和目标

### 1.3 核心功能
- **多技能管理**：同时管理多个技能的学习进度
- **学习计划创建**：AI 辅助制定详细的学习步骤
- **进度追踪**：记录每个技能的完成情况和时间线
- **记忆系统**：跨会话记住用户的学习偏好、目标和历史
- **Web UI**：基于 React + TypeScript 的前端界面

---

## 2. 系统架构

### 2.1 整体架构图
```
┌──────────────────────────────────────────────────────┐
│                       前端层                          │
│  ┌──────────────────┐                              │
│  │  React + TypeScript (frontend/src/)           │   │
│  │  App.tsx → 路由到各页面组件                │   │
│  └──────────────────┘                              │
└──────────────────────────────────────────────────────┘
                           │  HTTP (port 8000)
                           ▼
┌──────────────────────────────────────────────────────┐
│                      后端 API 层                       │
│  ┌──────────────────┐  ┌──────────────────┐     │
│  │  FastAPI         │  │  工具系统        │     │
│  │  (backend/      │◄─┼─│  (src/agent/    │     │
│  │   main.py)      │  │   tools.py)     │     │
│  └──────────────────┘  └──────────────────┘     │
│                              │                       │
│                              ▼                       │
│  ┌──────────────────────────────────────────────┐  │
│  │            Agent 核心层 (src/agent/)          │  │
│  │  core.py → memory.py → tools.py             │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                      数据存储层                       │
│  ┌──────────────────┐  ┌──────────────────┐     │
│  │  技能数据        │  │  记忆文件        │     │
│  │  (data/*.json)  │  │  (data/memory/) │     │
│  └──────────────────┘  └──────────────────┘     │
└──────────────────────────────────────────────────────┘
```

### 2.2 技术栈
- **后端**：Python 3.12+ / FastAPI / Uvicorn
- **前端**：React 18 / TypeScript / Vite
- **AI 接口**：Anthropic Claude API（通过 anthropic 库）
- **数据存储**：JSON 文件（技能数据）+ Markdown + YAML frontmatter（记忆）
- **配置管理**：python-dotenv（.env 文件）

---

## 3. 模块设计

### 3.1 后端模块 (backend/ + src/)

#### 3.1.1 backend/main.py - FastAPI 主入口
**职责**：
- 提供 RESTful API 接口
- 处理 CORS 跨域
- 转发 AI 对话请求到 Agent 核心

**主要路由**：
- `GET  /api/skills` - 获取所有技能
- `POST /api/skills` - 创建新技能
- `PUT  /api/skills/{id}` - 更新技能
- `DELETE /api/skills/{id}` - 删除技能
- `POST /api/progress` - 更新学习进度
- `PUT  /api/notes` - 保存步骤笔记
- `GET  /api/sessions` - 获取对话会话列表
- `POST /api/sessions` - 创建新会话
- `POST /api/chat` - 发送聊天消息
- `DELETE /api/sessions/{id}` - 删除会话
- `GET  /api/memories` - 获取记忆列表
- `GET  /api/timeline` - 获取学习时间线

#### 3.1.2 src/agent/core.py - Agent 主循环
**职责**：
- 运行 agent 主循环（agent_loop）
- 管理对话上下文
- 调用 LLM API
- 处理工具调用结果

**关键函数**：
- `agent_loop(messages: list)` - 主循环
- `build_system()` - 构建 system prompt

**压缩管道（Context Compaction）**：
- `tool_result_budget()` - 限制 tool_result 大小
- `snip_compact()` - 裁剪中间消息
- `micro_compact()` - 压缩早期 tool_result
- `compact_history()` - 自动压缩历史
- `reactive_compact()` - 响应式压缩

#### 3.1.3 src/agent/memory.py - 记忆系统
**职责**：
- 提供跨会话的持久化记忆功能
- 记忆存储在 `data/memory/` 目录下

**记忆文件格式**（Markdown + YAML frontmatter）：
```markdown
---
name: skill-ielts
description: 雅思学习计划：考到7分
type: project
---

## 雅思学习计划
- 目标：考到7分
- 总步骤：10步
- 当前进度：3/10
- 创建时间：2026-06-29
```

**关键函数**：
- `write_memory_file()` - 写入记忆文件
- `read_memory_index()` - 读取记忆索引
- `list_memory_files()` - 列出所有记忆
- `select_relevant_memories()` - 选择相关记忆
- `load_memories()` - 加载记忆到上下文
- `extract_memories()` - 从对话提取新记忆
- `consolidate_memories()` - 合并重复记忆

#### 3.1.4 src/agent/tools.py - 工具系统
**职责**：
- 定义 agent 可以使用的所有工具
- 提供工具实现和处理器映射

**工具列表**：
1. **基础工具**：
   - `bash` - 运行 shell 命令
   - `read_file` - 读取文件
   - `write_file` - 写入文件
   - `edit_file` - 编辑文件
   - `glob` - 查找文件
2. **子代理工具**：
   - `task` - 启动子代理处理子任务
3. **学习管家专用工具**：
   - `create_learning_plan` - 创建学习计划
   - `update_progress` - 更新学习进度

### 3.2 前端模块 (frontend/src/)

#### 3.2.1 App.tsx - 主应用组件
**职责**：
- 管理全局状态（当前页面、聊天会话）
- 渲染侧边栏导航
- 根据 `currentPage` 状态切换页面

**状态管理**：
- `currentPage`: 当前页面（'dashboard' | 'skills' | 'chat' | 'memory' | 'timeline'）
- `detailSkillId`: 当前查看的技能 ID（null = 显示列表）
- `editSkillId`: 当前编辑的技能 ID（null = 不显示弹窗）
- `chatSessions` / `currentSessionId`: 聊天会话状态（提升到 App 层，避免切 tab 丢失）

#### 3.2.2 页面组件（frontend/src/pages/）
| 组件 | 文件 | 功能 |
|--------|------|------|
| DashboardPage | `DashboardPage.tsx` | 仪表盘：显示统计卡片，引导用户添加技能 |
| SkillsPage | `SkillsPage.tsx` | 技能管理：网格卡片列表，支持新增/删除/搜索/筛选/导出 |
| SkillDetailPage | `SkillDetailPage.tsx` | 技能详情：进度条、步骤列表、步骤编辑面板 |
| ChatPage | `ChatPage.tsx` | AI 对话：会话列表 + 消息界面 |
| MemoryPage | `MemoryPage.tsx` | 记忆库：查看所有记忆文件内容 |
| TimelinePage | `TimelinePage.tsx` | 时间线：按日期分组展示学习事件 |

#### 3.2.3 通用组件（frontend/src/components/）
| 组件 | 文件 | 功能 |
|--------|------|------|
| Modal | `Modal.tsx` | 通用弹窗：支持 title、width、onClose、children |
| EditSkillModal | `EditSkillModal.tsx` | 编辑技能弹窗：预填表单，调用 PUT /api/skills/{id} |

#### 3.2.4 CSS 拆分（frontend/src/）
每个组件对应独立的 CSS 文件：
```
frontend/src/
├── App.css                     ← 全局变量 + App 布局 + 通用工具类
├── components/
│   ├── Modal.css             ← 弹窗样式
│   └── EditSkillModal.css    ← （复用 Modal.css）
└── pages/
    ├── DashboardPage.css      ← 仪表盘样式
    ├── SkillsPage.css        ← 技能列表样式
    ├── SkillDetailPage.css   ← 技能详情 + 步骤编辑面板样式
    ├── ChatPage.css          ← 聊天页面样式
    ├── MemoryPage.css        ← 记忆库样式
    └── TimelinePage.css     ← 时间线样式
```

---

## 4. 数据流设计

### 4.1 记忆系统数据流
```
用户对话
    │
    ▼
select_relevant_memories()  ← 选择相关记忆
    │
    ▼
load_memories()            ← 注入上下文
    │
    ▼
LLM API 调用
    │
    ▼
extract_memories()         ← 提取新记忆
    │
    ▼
write_memory_file()        ← 写入记忆文件
    │
    ▼
rebuild_index()           ← 更新索引
```

### 4.2 技能创建流程
```
用户: "我想学雅思，目标是7分"
    │
    ▼
Agent 调用 create_learning_plan()
    │
    ▼
POST /api/skills          ← 前端调用后端 API
    │
    ▼
后端写入 data/*.json      ← 持久化到 JSON 文件
    │
    ▼
返回确认消息给用户
```

### 4.3 进度更新流程
```
用户在详情页勾选步骤 checkbox
    │
    ▼
POST /api/progress        ← 前端调用后端 API
    │
    ▼
后端更新 data/*.json      ← 更新步骤 status
    │
    ▼
前端刷新技能数据          ← refreshSkill()
```

### 4.4 步骤详情编辑流程
```
用户点击步骤 → 展开编辑面板
    │
    ▼
修改状态/笔记 → 点击"保存修改"
    │
    ▼
PUT /api/notes           ← 保存笔记
POST /api/progress        ← 如状态变化，更新完成状态
    │
    ▼
前端刷新技能数据          ← refreshSkill()
```

---

## 5. API 设计

### 5.1 技能管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills` | 获取所有技能列表 |
| POST | `/api/skills` | 创建新技能 `{name, goal, steps[]}` |
| PUT | `/api/skills/{id}` | 更新技能 `{name, goal, steps[]}` |
| DELETE | `/api/skills/{id}` | 删除技能 |

### 5.2 进度管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/progress` | 更新进度 `{skill_id, completed_step, note}` |

### 5.3 笔记管理
| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/api/notes` | 保存/更新笔记 `{skill_id, step_id, note}` |

### 5.4 AI 对话
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sessions` | 获取会话列表（按日期分组） |
| POST | `/api/sessions` | 创建新会话，返回 `{session: {id, title, messages}}` |
| POST | `/api/chat` | 发送消息 `{session_id, message}`，返回更新后的 session |
| DELETE | `/api/sessions/{id}` | 删除会话 |

### 5.5 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/memories` | 获取记忆列表 `{memories: [{filename, content}]}` |
| GET | `/api/timeline` | 获取时间线 `{events: [{date, type, content, note}]}` |

### 5.6 Anthropic Claude API 调用
**配置**：
- `base_url`: 从 `ANTHROPIC_BASE_URL` 环境变量读取（支持兼容 API）
- `MODEL_ID`: 从 `MODEL_ID` 环境变量读取（默认：`claude-sonnet-4-20250514`）

**调用示例**：
```python
response = client.messages.create(
    model=MODEL,
    system=system_prompt,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000
)
```

---

## 6. 存储设计

### 6.1 目录结构
```
skill-record-agent/
├── data/
│   ├── skills.json            ← 技能数据（主存储）
│   ├── sessions.json          ← 聊天会话数据
│   └── memory/              ← 记忆文件存储
│       ├── MEMORY.md         ← 记忆索引
│       ├── learning-plan-ielts.md
│       └── ...
├── backend/
│   └── main.py              ← FastAPI 后端入口
├── frontend/
│   └── src/
│       ├── App.tsx           ← React 主组件
│       ├── components/       ← 通用组件
│       └── pages/           ← 页面组件
├── src/
│   └── agent/              ← Agent 核心逻辑
│       ├── core.py
│       ├── tools.py
│       └── memory.py
├── main.py                  ← CLI 入口（保留）
├── .env                     ← 环境变量配置
└── requirements.txt         ← Python 依赖列表
```

### 6.2 技能数据格式（data/skills.json）
```json
[
  {
    "id": "skill-uuid",
    "name": "雅思备考",
    "goal": "雅思 7.5 分",
    "steps": [
      {
        "id": "step-uuid",
        "content": "背单词 3000 个",
        "status": "completed",
        "note": "重点记忆学术词汇",
        "completedAt": "2026-06-30T10:00:00"
      }
    ],
    "createdAt": "2026-06-29T08:00:00"
  }
]
```

### 6.3 记忆文件命名规范
- 学习计划：`learning-plan-{skill}.md`
- 进度更新：`progress-{skill}-{timestamp}.md`
- 用户偏好：`user-reference-{name}.md`

---

## 7. 前端组件架构

### 7.1 组件树
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

### 7.2 状态提升策略
- `editSkillId` 提升到 `App` 层 → `SkillsPage` 和 `SkillDetailPage` 都能触发编辑弹窗
- `chatSessions` / `currentSessionId` 提升到 `App` 层 → 切 tab 不丢失对话状态

### 7.3 关键交互设计
| 交互 | 实现方式 |
|------|-----------|
| 点击技能卡片 | `setDetailSkillId(id)` → 切换到 SkillDetailPage |
| 点击"编辑技能" | `setEditSkillId(id)` → 弹出 EditSkillModal |
| 编辑确定 | `onSaved()` → 只关闭弹窗，停留在详情页 |
| 点击步骤名称 | `setEditingStepId(step.id)` → 展开步骤编辑面板 |
| 切换步骤状态 | 调用 `POST /api/progress` → `refreshSkill()` |
| 保存步骤笔记 | 调用 `PUT /api/notes` → `refreshSkill()` |

---

## 8. 关键技术点

### 8.1 压缩管道（Context Compaction）
**问题**：对话历史过长，超过 LLM 上下文限制。

**解决方案**：
1. **Tool Result Budget**: 限制 tool_result 总大小，超大结果持久化到文件
2. **Snip Compact**: 裁剪中间消息，只保留开头和结尾
3. **Micro Compact**: 压缩早期 tool_result，只保留最近的几个
4. **Auto Compact**: 当上下文超过阈值时，自动总结历史
5. **Reactive Compact**: 当 API 报错 "prompt too long" 时，响应式压缩

### 8.2 孤立 Tool Result 清理
**问题**：压缩管道可能删除包含 tool_use 的消息，导致 tool_result 引用不存在的 tool_use_id。

**解决方案**：
- `sanitize_tool_results()`: 遍历消息，移除没有对应 tool_use 的 tool_result
- 同时删除变空的消息，避免 "non-empty content" 错误

### 8.3 防御性编程
- 后端 `get_timeline()` 对 `skill.get('createdAt')` 做 `or ''` 和 `len() >= 10` 检查，兼容 legacy 数据
- 前端 `SkillsPage` 对 `skill.steps` 做 `|| []` 防御，避免渲染崩溃

### 8.4 CSS 按组件拆分
每个 `.tsx` 组件对应独立的 `.css` 文件，通过 `import './ComponentName.css'` 引入，`App.css` 只保留全局变量和通用工具类。

---

## 9. 部署和运行

### 9.1 环境要求
- Python 3.12+
- Node.js 18+（前端构建）
- Anthropic API Key（或兼容 API）

### 9.2 安装步骤
```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_BASE_URL 和 MODEL_ID

# 3. 启动后端（默认 port 8000）
cd backend && uvicorn main:app --reload

# 4. 启动前端（新终端，默认 port 5173）
cd frontend && npm run dev
```

### 9.3 .env 配置示例
```env
ANTHROPIC_BASE_URL=https://api.anthropic.com
MODEL_ID=claude-sonnet-4-20250514
# 或者使用兼容 API (如 DeepSeek)
# ANTHROPIC_BASE_URL=https://api.deepseek.com
# MODEL_ID=deepseek-chat
```

---

## 10. 未来扩展

### 10.1 功能扩展
- [ ] 支持更多技能类型（编程、音乐、运动等）
- [ ] 数据可视化（学习进度图表）
- [ ] 提醒功能（定期复习提醒）
- [ ] 社交功能（分享学习计划给其他用户）
- [ ] 步骤拖拽排序
- [ ] 技能模板库

### 10.2 技术扩展
- [ ] 使用向量数据库存储记忆（如 ChromaDB）
- [ ] 支持更多 LLM 提供商（OpenAI, Gemini 等）
- [ ] 移动端支持（React Native / Flutter）
- [ ] 云端同步（多设备同步学习进度）
- [ ] Docker 容器化部署
- [ ] 用户账号系统（替代本地文件存储）

---

## 11. 附录

### 11.1 参考资料
- [Anthropic Claude API 文档](https://docs.anthropic.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React 文档](https://react.dev/)
- [Vite 文档](https://vitejs.dev/)

### 11.2 版本历史
- **v2.0** (2026-07-01): 架构重构：FastAPI + React 替代原有 CLI + Streamlit；组件拆分；CSS 按组件拆分
- **v1.0** (2026-06-29): 初始版本，支持基本的学习计划创建和进度追踪（CLI + Streamlit）
