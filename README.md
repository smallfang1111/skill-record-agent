# 学习管家 (Learning Manager)

记录你的学习过程，追踪成长轨迹。

## 功能特性

✅ **多技能管理** - 同时管理多个技能的学习进度
✅ **学习步骤记录** - 记录每个学习步骤的完成情况和笔记
✅ **进度可视化** - 直观看到每个技能的完成百分比
✅ **AI 助手** - 与 AI 对话，获取学习建议
✅ **跨平台** - 基于 Web 技术，可以轻松打包成桌面应用

## 快速开始

### 1. 安装依赖

**后端（Python）**：
```powershell
pip install fastapi uvicorn anthropic python-dotenv
```

**前端（Node.js）**：
```powershell
cd frontend
npm install
```

### 2. 启动服务

**启动后端**：
```powershell
cd backend
python main.py
```
后端会在 http://localhost:8000 运行

**启动前端**：
```powershell
cd frontend
npm run dev
```
前端会在 http://localhost:5173 运行

### 3. 打开应用

在浏览器访问：http://localhost:5173

## 使用指南

### 添加技能

1. 点击"📋 技能管理"标签页
2. 点击"+ 添加技能"按钮
3. 填写技能名称、学习目标
4. 输入学习步骤（每行一个步骤）
5. 点击"创建"

### 记录进度

1. 在技能卡片中，勾选已完成的步骤
2. 添加备注（可选）
3. 查看进度条更新

### 与 AI 助手对话

1. 点击"💬 AI 助手"标签页
2. 输入你的问题或学习心得
3. 点击"发送"

## 项目结构

```
learning-manager/
├── frontend/          ← React + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx   ← 主组件（包含导航）
│   │   ├── components/
│   │   │   ├── SkillManager.tsx  ← 技能管理
│   │   │   └── SkillManager.css
│   │   └── App.css
│   └── package.json
├── backend/           ← FastAPI 后端
│   └── main.py       ← 主文件（API 接口）
├── src/               ← 现有 Python 代码
│   ├── agent/
│   │   ├── core.py
│   │   ├── memory.py
│   │   └── tools.py
│   └── ui/
├── data/              ← 数据存储
│   └── memory/
├── README.md          ← 本文件
└── .env               ← 环境变量配置
```

## 技术栈

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Fetch API (HTTP 请求)

### 后端
- FastAPI (Python Web 框架)
- Anthropic Claude API
- 现有代码（src/agent/）

## 下一步计划

- [ ] 添加数据持久化（LocalStorage / IndexedDB）
- [ ] 添加时间线视图（看到所有学习记录）
- [ ] 添加学习笔记功能（富文本编辑）
- [ ] 用 Electron 包装成桌面应用
- [ ] 添加用户账号系统
- [ ] 部署到云端

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
