# 学习管家 - 启动指南

## 阶段 1：React + FastAPI（当前阶段）

### 项目结构
```
learning-manager/
├── frontend/          ← React + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx   ← 主组件
│   │   └── App.css   ← 样式
│   └── package.json
├── backend/           ← FastAPI 后端
│   └── main.py       ← 主文件
├── src/               ← 现有 Python 代码
│   ├── agent/
│   │   ├── core.py
│   │   ├── memory.py
│   │   └── tools.py
│   └── ui/
├── start.ps1          ← 启动脚本
└── START_GUIDE.md    ← 本文件
```

### 启动步骤

#### 方法 1：使用启动脚本（推荐）
```powershell
.\start.ps1
```

#### 方法 2：手动启动

**步骤 1：启动后端**
```powershell
cd backend
python main.py
```
后端会在 http://localhost:8000 运行

**步骤 2：启动前端**（新开一个终端）
```powershell
cd frontend
npm run dev
```
前端会在 http://localhost:5173 运行

**步骤 3：打开浏览器**
访问 http://localhost:5173

### API 接口文档

启动后访问：http://localhost:8000/docs

#### 可用接口：
- `GET /api/memories` - 获取所有记忆
- `GET /api/memories/{filename}` - 获取单个记忆
- `POST /api/skills` - 创建技能
- `POST /api/progress` - 更新进度
- `POST /api/chat` - 与 AI 对话

### 下一步

阶段 1 完成后（功能验证通过），进入阶段 2：
- 用 Electron 包装成桌面应用
- 添加更多功能（技能管理、进度追踪等）

---

## 技术栈

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Fetch API (HTTP 请求)

### 后端
- FastAPI (Python Web 框架)
- Anthropic Claude API
- 现有代码（src/agent/）

### 开发工具
- Node.js 22.14.0
- Python 3.12+
- VSCode
