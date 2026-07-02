const { contextBridge, ipcRenderer } = require('electron')

// 安全地暴露 API 到渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  callApi: (options) => ipcRenderer.invoke('api-call', options),

  // 通知主进程：当前是否有模态框打开
  setModalOpen: (open) => ipcRenderer.send('modal-state', open),

  // 监听主进程发来的「抖动」指令（窗口被尝试关闭/刷新时）
  onShake: (cb) => {
    ipcRenderer.on('modal-shake', () => cb())
  },

  // 打开系统目录选择框，返回选中的绝对路径
  selectDirectory: () => ipcRenderer.invoke('dialog:openDirectory')
})
