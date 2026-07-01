# Electron 桌面应用启动指南

## 开发模式

### 步骤 1：启动前端开发服务器
```powershell
cd frontend
npm run dev
```

### 步骤 2：启动 Electron（新终端）
```powershell
cd d:\onlyAlita\skill-record-agent
set NODE_ENV=development
electron .
```

或者一键启动（推荐）：
```powershell
npm run dev
```

## 生产模式（打包）

### 构建前端
```powershell
npm run build
```

### 打包成 Windows 安装程序
```powershell
npm run dist
```

打包后的安装程序在 `dist-installer/` 目录。

## 目录结构

```
electron/
  main.js      ← Electron 主进程
  preload.js   ← 预加载脚本（安全桥接）
frontend/
  dist/        ← 构建后的前端文件
backend/
  main.py      ← FastAPI 后端
```

## 注意事项

1. **开发模式**下，Electron 会加载 `http://localhost:5173`，并自动打开开发者工具
2. **生产模式**下，Electron 会自动启动 Python 后端，并加载本地 HTML 文件
3. 打包时需要确保 Python 环境已打包（或使用 PyInstaller 打包成 exe）

## 下一步优化

- [ ] 使用 PyInstaller 将 Python 后端打包成 exe
- [ ] 配置 electron-builder 自动打包 Python 运行时
- [ ] 添加自动更新功能
