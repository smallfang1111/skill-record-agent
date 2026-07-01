const { contextBridge, ipcRenderer } = require('electron')

// 安全地暴露 API 到渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  callApi: (options) => ipcRenderer.invoke('api-call', options)
})
