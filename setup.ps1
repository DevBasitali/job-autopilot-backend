Write-Host "Starting setup for Job Autopilot..." -ForegroundColor Cyan

# 1. Create venv
Write-Host "Creating virtual environment..."
python -m venv .venv

# Activate venv
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Could not find virtual environment activation script." -ForegroundColor Red
    exit
}

# 2. Install dependencies
Write-Host "Installing Python dependencies..."
pip install -r requirements.txt

# Install frontend dependencies
Write-Host "Installing Frontend dependencies..."
Set-Location frontend
npm.cmd install
Set-Location ..

# 3. Install Playwright chromium
Write-Host "Installing Playwright Chromium browser..."
playwright install chromium

# 4. Pull Ollama model
Write-Host "Pulling Ollama llama3 model..."
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama pull llama3
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Could not pull llama3. Is Ollama running?" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️ Ollama is not installed or not in your PATH." -ForegroundColor Yellow
    Write-Host "Please download and install it from https://ollama.com/download to use the AI features." -ForegroundColor Yellow
}

# 5. Create empty directories
Write-Host "Creating sessions/ and resumes/ directories..."
New-Item -ItemType Directory -Force -Path "sessions" | Out-Null
New-Item -ItemType Directory -Force -Path "resumes" | Out-Null

# 6. Print success message
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Setup complete. Run .\run.ps1 to start" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
