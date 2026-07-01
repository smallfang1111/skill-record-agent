#!/usr/bin/env pwsh
"""
启动脚本 - 同时启动前端和后端
"""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  学习管家 - 启动中..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 启动后端 (FastAPI)
Write-Host "[1/2] 启动后端 (FastAPI)..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location "$using:PWD\backend"
    python main.py
}

# 等待后端启动
Start-Sleep -Seconds 3

# 启动前端 (React + Vite)
Write-Host "[2/2] 启动前端 (React + Vite)..." -ForegroundColor Yellow
Set-Location "$PWD\frontend"
npm run dev

# 清理后台任务
Write-Host ""
Write-Host "正在停止服务..." -ForegroundColor Yellow
Stop-Job $backendJob
Remove-Job $backendJob
