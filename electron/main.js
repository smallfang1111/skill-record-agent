const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow
let pythonProcess
let modalOpen = false

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    icon: path.join(__dirname, '../frontend/public/favicon.svg'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  // 开发模式：加载 Vite 开发服务器
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    // 生产模式：加载构建后的文件
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // 有模态框打开时，拦截窗口关闭：不弹提示，改为让模态框抖一下
  mainWindow.on('close', (e) => {
    if (modalOpen) {
      e.preventDefault()
      mainWindow.webContents.send('modal-shake')
    }
  })

  // 有模态框打开时，拦截刷新（Ctrl/Cmd+R）：不弹提示，模态框抖一下
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if ((input.control || input.meta) && input.key.toLowerCase() === 'r' && !input.isAutoRepeat) {
      if (modalOpen) {
        event.preventDefault()
        mainWindow.webContents.send('modal-shake')
      }
    }
  })
}

function startPythonBackend() {
  // 启动 FastAPI 后端
  const pythonPath = 'python'
  const scriptPath = path.join(__dirname, '../backend/main.py')
  
  pythonProcess = spawn(pythonPath, [scriptPath], {
    env: { ...process.env, PYTHONPATH: path.join(__dirname, '..') }
  })

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python backend: ${data}`)
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python backend error: ${data}`)
  })
}

app.whenReady().then(() => {
  // 开发模式下不自动启动 Python 后端（手动启动）
  if (process.env.NODE_ENV !== 'development') {
    startPythonBackend()
  }
  
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill()
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// IPC 通信：前端可以调用后端 API
ipcMain.handle('api-call', async (event, options) => {
  const { url, method, body } = options
  try {
    const response = await fetch(`http://localhost:8000${url}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined
    })
    return await response.json()
  } catch (error) {
    console.error('API call failed:', error)
    throw error
  }
})

// 渲染进程通知：当前是否有模态框打开
ipcMain.on('modal-state', (event, open) => {
  modalOpen = !!open
})

// 打开系统目录选择框，返回选中的绝对路径
ipcMain.handle('dialog:openDirectory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: '选择聊天记录存储目录',
    properties: ['openDirectory', 'createDirectory']
  })
  if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
    return null
  }
  return result.filePaths[0]
})
