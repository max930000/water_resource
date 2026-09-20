<#
    城市水路 —— 一鍵啟動開發環境

    用法：
        .\start.ps1          啟動後端 + 前端，並自動開瀏覽器
        .\start.ps1 -Stop    停掉兩個服務
        .\start.ps1 -NoOpen  啟動但不開瀏覽器

    為什麼需要這個腳本：
      後端和前端是兩個獨立的程式，各自要佔住一個終端機視窗。
      每次開發都要開兩個視窗、打六行指令，還常常忘記啟動 venv 或站錯資料夾。
      比賽當天四五個人各自啟動環境，有這個腳本可以省掉一堆
      「我這邊跑不起來」的時間。
#>

param(
    [switch]$Stop,
    [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'

# 腳本自己的所在位置，不管你從哪裡執行都能找到專案
$Root     = $PSScriptRoot
$Backend  = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$ApiPort  = 8000
$WebPort  = 5173

function Stop-Port([int]$Port) {
    # 注意：埠被占用時，Windows 回報的錯誤是
    #   [WinError 10013] 嘗試存取通訊端被拒絕，因為存取權限不足
    # 它講「權限」，但真正原因是埠已經被別的程式握著。
    # 用系統管理員開沒有用，要先把占住的程序關掉。
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($p) {
            Write-Host "  停止 $Port 上的 $($p.ProcessName) (PID $($p.Id))" -ForegroundColor DarkGray
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

function Start-InNewWindow([string]$Title, [string]$Command) {
    # -NoExit 讓視窗跑完指令後不要關閉，這樣你才看得到 log。
    # 服務掛掉時錯誤訊息會留在那個視窗裡 —— 那永遠是除錯的第一站。
    Start-Process powershell -ArgumentList @(
        '-NoExit', '-Command',
        "`$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
    ) | Out-Null
}

# ── 停止模式 ─────────────────────────────────────────────
if ($Stop) {
    Write-Host "停止服務..." -ForegroundColor Yellow
    Stop-Port $ApiPort
    Stop-Port $WebPort
    Write-Host "已停止。" -ForegroundColor Green
    return
}

# ── 啟動前檢查 ───────────────────────────────────────────
if (-not (Test-Path (Join-Path $Backend '.venv\Scripts\Activate.ps1'))) {
    Write-Host "找不到後端的虛擬環境。請先在 backend 資料夾執行：" -ForegroundColor Red
    Write-Host "  py -3.13 -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    return
}
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) {
    Write-Host "前端套件還沒安裝。請先在 frontend 資料夾執行： npm install" -ForegroundColor Red
    return
}

# ── 先清埠，避免撞到上一次沒關乾淨的程序 ──────────────────
Write-Host "清理連接埠..." -ForegroundColor DarkGray
Stop-Port $ApiPort
Stop-Port $WebPort
Start-Sleep -Milliseconds 800

# ── 啟動 ────────────────────────────────────────────────
Write-Host "啟動後端 (port $ApiPort)..." -ForegroundColor Cyan
Start-InNewWindow 'TownQuest 後端' "cd '$Backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port $ApiPort"

Write-Host "啟動前端 (port $WebPort)..." -ForegroundColor Cyan
Start-InNewWindow 'TownQuest 前端' "cd '$Frontend'; npm run dev"

# ── 等後端真的就緒，而不是死等固定秒數 ────────────────────
Write-Host "等待後端就緒" -NoNewline -ForegroundColor DarkGray
$ready = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline -ForegroundColor DarkGray
    try {
        if ((Invoke-RestMethod "http://127.0.0.1:$ApiPort/health" -TimeoutSec 2).status -eq 'UP') {
            $ready = $true
            break
        }
    } catch { }
}
Write-Host ""

if ($ready) {
    Write-Host ""
    Write-Host "  服務       http://127.0.0.1:$WebPort/"    -ForegroundColor Green
    Write-Host "  API 文件   http://127.0.0.1:$ApiPort/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "  停止：.\start.ps1 -Stop" -ForegroundColor DarkGray
    if (-not $NoOpen) { Start-Process "http://127.0.0.1:$WebPort/" }
} else {
    Write-Host "後端沒有在 30 秒內就緒。" -ForegroundColor Red
    Write-Host "去看標題是「TownQuest 後端」的那個視窗，錯誤訊息在裡面。" -ForegroundColor Yellow
}
