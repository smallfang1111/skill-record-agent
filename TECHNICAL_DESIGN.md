# 学习管家 (Learning Manager) - 技术设计文档

## 1. 项目概述

### 1.1 项目背景
现代人需要并行学习多种技能（如雅思、AI-Agent开发、化妆等），需要一个应用来记录和管理整个学习过程，包括：
- 制定学习计划
- 记录学习进度
- 追踪技能成长轨迹
- 跨会话记忆学习偏好和目标

### 1.2 项目目标
构建一个智能化的学习管理应用，帮助用户：
1. 为多个技能创建并行学习计划
2. 记录每次学习的进度和心得
3. 通过 AI 助手提供学习建议和鼓励
4. 持久化记忆用户的学习偏好和目标

### 1.3 核心功能
- **多技能管理**：同时管理多个技能的学习进度
- **学习计划创建**：AI 辅助制定详细的学习步骤
- **进度追踪**：记录每个技能的完成情况和时间线
- **记忆系统**：跨会话记住用户的学习偏好、目标和历史
- **双端支持**：终端 CLI + Web UI (Streamlit)

---

## 2. 系统架构

### 2.1 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面层                          │
│  ┌──────────────────┐              ┌──────────────────┐   │
│  │  终端 CLI        │              │  Web UI          │   │
│  │  (src/ui/cli.py) │              │ (src/ui/web.py)  │   │
│  └──────────────────┘              └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        核心逻辑层                          │
│  ┌──────────────────┐              ┌──────────────────┐   │
│  │  Agent 主循环    │              │  工具系统        │   │
│  │  (src/agent/     │◄─────────────│ (src/agent/      │   │
│  │   core.py)       │              │  tools.py)       │   │
│  └──────────────────┘              └──────────────────┘   │
│                              │                             │
│                              ▼                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │               记忆系统 (src/agent/memory.py)         │  │
│  │  - 读写记忆文件                                      │  │
│  │  - 选择相关记忆                                      │  │
│  │  - 提取新记忆                                        │  │
│  │  - 合并重复记忆                                      │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        数据存储层                          │
│  ┌──────────────────┐              ┌──────────────────┐   │
│  │  记忆文件        │              │  技能数据        │   │
│  │  (data/memory/)  │              │  (skills/)       │   │
│  └──────────────────┘              └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈
- **编程语言**：Python 3.12+
- **AI 接口**：Anthropic Claude API (通过 anthropic 库)
- **Web 框架**：Streamlit (可选，用于 Web UI)
- **数据存储**：Markdown 文件 + YAML frontmatter
- **配置管理**：python-dotenv (.env 文件)

---

## 3. 模块设计

### 3.1 核心模块 (src/agent/)

#### 3.1.1 core.py - Agent 主循环
**职责**：
- 运行 agent 主循环 (agent_loop)
- 管理对话上下文
- 调用 LLM API
- 处理工具调用结果

**关键函数**：
- `agent_loop(messages: list)` - 主循环
- `sanitize_tool_results(msgs: list)` - 清理孤立的 tool_result 块
- `build_system()` - 构建 system prompt

**压缩管道**：
- `tool_result_budget()` - 限制 tool_result 大小
- `snip_compact()` - 裁剪中间消息
- `micro_compact()` - 压缩早期 tool_result
- `compact_history()` - 自动压缩历史
- `reactive_compact()` - 响应式压缩

#### 3.1.2 memory.py - 记忆系统
**职责**：
- 提供跨会话的持久化记忆功能
- 记忆存储在 `data/memory/` 目录下

**记忆文件格式** (Markdown + YAML frontmatter)：
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

#### 3.1.3 tools.py - 工具系统
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

**关键数据结构**：
- `TOOLS` - 工具定义列表 (Anthropic API 格式)
- `TOOL_HANDLERS` - 工具名称到处理函数的映射

### 3.2 UI 模块 (src/ui/)

#### 3.2.1 cli.py - 终端入口
**职责**：
- 提供交互式 REPL 循环
- 提供单次查询模式
- 支持内部命令 (?help, ?history, ?memories 等)

**使用方式**：
```bash
python main.py                              # 交互模式
python main.py "帮我制定雅思学习计划"       # 单次查询
python main.py --history                     # 查看记忆索引
```

#### 3.2.2 web.py - Streamlit Web 入口
**职责**：
- 提供美观的 Web 界面
- 支持多技能管理、进度追踪、记忆可视化

**使用方式**：
```bash
streamlit run src/ui/web.py
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
_rebuild_index()           ← 更新索引
```

### 4.2 学习计划创建流程
```
用户: "我想学雅思，目标是7分"
    │
    ▼
create_learning_plan(skill="雅思", goal="7分", steps=[...])
    │
    ▼
write_memory_file()  ← 写入学习计划到记忆系统
    │
    ▼
返回确认消息给用户
```

### 4.3 进度更新流程
```
用户: "我今天完成了听力练习"
    │
    ▼
update_progress(skill="雅思", completed="听力练习")
    │
    ▼
write_memory_file()  ← 写入进度记录到记忆系统
    │
    ▼
返回确认消息给用户
```

---

## 5. API 设计

### 5.1 Anthropic Claude API 调用
**配置**：
- `base_url`: 从 `ANTHROPIC_BASE_URL` 环境变量读取 (支持兼容 API)
- `MODEL_ID`: 从 `MODEL_ID` 环境变量读取 (默认: `claude-sonnet-4-20250514`)

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

### 5.2 工具定义格式 (Anthropic API)
```python
{
    "name": "create_learning_plan",
    "description": "为某个技能创建学习计划",
    "input_schema": {
        "type": "object",
        "properties": {
            "skill": {"type": "string"},
            "goal": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["skill", "goal", "steps"]
    }
}
```

---

## 6. 存储设计

### 6.1 目录结构
```
learning-manager/
├── data/
│   └── memory/              ← 记忆文件存储
│       ├── MEMORY.md        ← 记忆索引
│       ├── learning-plan-ielts.md
│       ├── progress-ielts-xxx.md
│       └── ...
├── skills/                  ← 技能相关数据
├── src/
│   ├── agent/
│   │   ├── core.py
│   │   ├── tools.py
│   │   └── memory.py
│   └── ui/
│       ├── cli.py
│       └── web.py
├── main.py                 ← 主入口
├── .env                    ← 环境变量配置
└── requirements.txt        ← 依赖列表
```

### 6.2 记忆文件命名规范
- 学习计划: `learning-plan-{skill}.md`
- 进度更新: `progress-{skill}-{timestamp}.md`
- 用户偏好: `user-preference-{name}.md`

---

## 7. 关键技术点

### 7.1 压缩管道 (Context Compaction)
**问题**：对话历史过长，超过 LLM 上下文限制

**解决方案**：
1. **Tool Result Budget**: 限制 tool_result 总大小，超大结果持久化到文件
2. **Snip Compact**: 裁剪中间消息，只保留开头和结尾
3. **Micro Compact**: 压缩早期 tool_result，只保留最近的几个
4. **Auto Compact**: 当上下文超过阈值时，自动总结历史
5. **Reactive Compact**: 当 API 报错 "prompt too long" 时，响应式压缩

### 7.2 孤立 Tool Result 清理
**问题**：压缩管道可能删除包含 tool_use 的消息，导致 tool_result 引用不存在的 tool_use_id

**解决方案**：
- `sanitize_tool_results()`: 遍历消息，移除没有对应 tool_use 的 tool_result
- 同时删除变空的消息，避免 "non-empty content" 错误

### 7.3 记忆系统
**设计理念**：
- 每个记忆是一个独立的 Markdown 文件
- 使用 YAML frontmatter 存储元数据 (name, description, type)
- `MEMORY.md` 作为索引，列出所有记忆的摘要
- 每次 turn 注入相关记忆到上下文

**记忆类型**：
- `user` - 用户偏好
- `feedback` - 反馈和指导
- `project` - 项目事实 (如学习计划)
- `reference` - 外部参考

---

## 8. 部署和运行

### 8.1 环境要求
- Python 3.12+
- Anthropic API Key (或兼容 API)
- (可选) Streamlit for Web UI

### 8.2 安装步骤
```bash
# 1. 克隆项目
cd learning-manager

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_BASE_URL 和 MODEL_ID

# 4. 运行终端模式
python main.py

# 5. (可选) 运行 Web UI
streamlit run src/ui/web.py
```

### 8.3 .env 配置示例
```env
ANTHROPIC_BASE_URL=https://api.anthropic.com
MODEL_ID=claude-sonnet-4-20250514
# 或者使用兼容 API (如 DeepSeek)
# ANTHROPIC_BASE_URL=https://api.deepseek.com
# MODEL_ID=deepseek-chat
```

---

## 9. 未来扩展

### 9.1 功能扩展
- [ ] 支持更多技能类型 (编程、音乐、运动等)
- [ ] 数据可视化 (学习进度图表)
- [ ] 提醒功能 (定期复习提醒)
- [ ] 社交功能 (分享学习计划给其他用户)

### 9.2 技术扩展
- [ ] 使用向量数据库存储记忆 (如 ChromaDB)
- [ ] 支持更多 LLM 提供商 (OpenAI, Gemini 等)
- [ ] 移动端支持 (React Native / Flutter)
- [ ] 云端同步 (多设备同步学习进度)

---

## 10. 附录

### 10.1 参考资料
- [Anthropic Claude API 文档](https://docs.anthropic.com/)
- [Streamlit 文档](https://docs.streamlit.io/)
- [Python-dotenv 文档](https://github.com/theskumar/python-dotenv)

### 10.2 版本历史
- **v1.0** (2026-06-29): 初始版本，支持基本的学习计划创建和进度追踪
