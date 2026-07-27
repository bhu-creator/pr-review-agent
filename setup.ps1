# ─────────────────────────────────────────────────────────────────────────────
# setup.ps1 — One-click setup for PR Review Agent (Windows PowerShell)
# Run this once from the pr-review-agent folder:
#   .\setup.ps1
# ─────────────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI PR Review Agent — Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Python is installed ─────────────────────────────────────────────
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Python not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# ── 2. Create virtual environment ────────────────────────────────────────────
Write-Host ""
Write-Host "[2/4] Creating virtual environment (.venv)..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "      .venv already exists, skipping creation." -ForegroundColor Gray
} else {
    python -m venv .venv
    Write-Host "      .venv created." -ForegroundColor Green
}

# ── 3. Install dependencies ───────────────────────────────────────────────────
Write-Host ""
Write-Host "[3/4] Installing dependencies from scripts/requirements.txt..." -ForegroundColor Yellow
& ".venv\Scripts\pip.exe" install -r scripts\requirements.txt --quiet
Write-Host "      Dependencies installed." -ForegroundColor Green

# ── 4. Create .env from .env.example ─────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Setting up .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "      .env already exists. Skipping (your values are safe)." -ForegroundColor Gray
} else {
    Copy-Item ".env.example" ".env"
    Write-Host "      .env created from .env.example." -ForegroundColor Green
    Write-Host "      -> Open .env and fill in your API keys before running!" -ForegroundColor Magenta
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Edit .env with your GEMINI_API_KEY, ADO_ORG_URL, ADO_PROJECT," -ForegroundColor White
Write-Host "     ADO_REPO_NAME, ADO_PR_ID, and SYSTEM_ACCESSTOKEN" -ForegroundColor White
Write-Host "  2. Run the agent locally:" -ForegroundColor White
Write-Host "       .\.venv\Scripts\python.exe scripts\pr_review_agent.py" -ForegroundColor Cyan
Write-Host "  3. Copy files to your Azure DevOps repo and create the pipeline." -ForegroundColor White
Write-Host "     See scripts\README.md for full instructions." -ForegroundColor White
Write-Host ""
