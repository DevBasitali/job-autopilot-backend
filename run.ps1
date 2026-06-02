Write-Host "Starting Job Autopilot..." -ForegroundColor Cyan

# 1. Activate Python venv
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found. Run .\setup.ps1 first." -ForegroundColor Red
    exit
}

# 2. Start FastAPI backend on port 8000 in background
Write-Host "Starting FastAPI backend on port 8000..."
$backendProcess = Start-Process -NoNewWindow -PassThru -FilePath "uvicorn" -ArgumentList "backend.main:app", "--host", "0.0.0.0", "--port", "8000"

# 3. Start Next.js frontend on port 3000
Write-Host "Starting Next.js frontend on port 3000..."
Set-Location frontend
$frontendProcess = Start-Process -NoNewWindow -PassThru -FilePath "npm.cmd" -ArgumentList "run dev"
Set-Location ..

# 4. Print URLs for both
Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "🚀 Job Autopilot is running!" -ForegroundColor Green
Write-Host "Backend API: http://localhost:8000"
Write-Host "Frontend UI: http://localhost:3000"
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers." -ForegroundColor Yellow
Write-Host ""

try {
    # Keep script running to allow Ctrl+C to be caught
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nStopping servers..." -ForegroundColor Yellow
    if ($backendProcess -and !$backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
    if ($frontendProcess -and !$frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force
    }
    Write-Host "Servers stopped." -ForegroundColor Green
}
