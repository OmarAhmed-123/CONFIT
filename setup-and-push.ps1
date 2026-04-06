# CONFIT Git Setup Script
# Run this script to initialize git and push to GitHub

$ErrorActionPreference = "Continue"
$logFile = "E:\CONFIT\git-setup-log.txt"
$repoPath = "E:\CONFIT"

function Log {
    param([string]$message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    $line = "[$timestamp] $message"
    Write-Host $line
    $line | Out-File -FilePath $logFile -Append
}

# Clear log
"" | Out-File -FilePath $logFile

Log "=== CONFIT Git Setup Started ==="
Log "Working directory: $repoPath"

Set-Location $repoPath

# Check git
Log "Checking git installation..."
try {
    $gitPath = (Get-Command git -ErrorAction Stop).Source
    Log "Git found at: $gitPath"
} catch {
    Log "ERROR: Git not installed. Please install Git for Windows."
    exit 1
}

# Initialize
Log "Initializing git repository..."
$result = git init 2>&1
Log "git init: $result"

# Check .git folder
if (Test-Path ".git" -PathType Container) {
    Log "SUCCESS: .git folder created"
} else {
    Log "ERROR: .git folder not found"
    exit 1
}

# Configure user
Log "Configuring git user..."
git config user.name "OmarAhmed-123" 2>&1 | Out-Null
git config user.email "omar.ahmed@example.com" 2>&1 | Out-Null
Log "User configured"

# Remove old remote
Log "Setting up remote..."
git remote remove origin 2>&1 | Out-Null

# Add remote
$result = git remote add origin https://github.com/OmarAhmed-123/CONFIT.git 2>&1
Log "Remote added: $result"

# Verify remote
$remote = git remote get-url origin 2>&1
Log "Remote URL: $remote"

# Add files
Log "Staging files..."
git add . 2>&1 | Out-Null
Log "Files staged"

# Count files
$stagedFiles = git diff --cached --name-only 2>&1
$count = ($stagedFiles | Measure-Object -Line).Lines
Log "Staged $count files"

# Commit
Log "Creating commit..."
$commitMsg = @"
Initial commit: CONFIT fashion e-commerce platform

Features:
- Virtual try-on with AI integration
- Payment integration (Paymob, PayPal, Stripe)
- User authentication and profiles
- Product catalog and recommendations
- Admin dashboard
- E2E testing with Playwright
- PentAGI security integration

Tech stack:
- Frontend: React, TypeScript, Tailwind CSS
- Backend: Python FastAPI, SQLAlchemy
- Database: SQLite/PostgreSQL
- AI: Gemini, DeepSeek, OpenAI integration
"@
$result = git commit -m $commitMsg 2>&1
Log "Commit result: $result"

# Rename branch
Log "Renaming branch to main..."
git branch -M main 2>&1 | Out-Null
Log "Branch renamed"

# Show status
Log "=== Git Status ==="
$status = git status --short 2>&1
Log $status

Log ""
Log "=== SETUP COMPLETE ==="
Log ""
Log "NEXT STEPS:"
Log "1. Create GitHub repo at: https://github.com/new"
Log "   - Repository name: CONFIT"
Log "   - Owner: OmarAhmed-123"
Log "   - Do NOT add README/gitignore"
Log ""
Log "2. Push to GitHub:"
Log "   git push -u origin main"
Log ""
Log "Log saved to: $logFile"
