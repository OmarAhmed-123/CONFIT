# CONFIT Git Push Script
# This script initializes git and pushes to GitHub

$logFile = "git-setup-log.txt"
function Log {
    param($message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $logFile -Append
    Write-Host $message
}

Log "=== CONFIT Git Setup Started ==="

# Check git
try {
    $gitPath = (Get-Command git).Source
    Log "Git found at: $gitPath"
} catch {
    Log "ERROR: Git not found. Please install Git for Windows."
    exit 1
}

# Initialize
Log "Initializing git repository..."
git init 2>&1 | Out-File -FilePath $logFile -Append

# Check if .git folder exists
if (Test-Path ".git") {
    Log "SUCCESS: .git folder created"
} else {
    Log "ERROR: .git folder not found after git init"
}

# Configure user
Log "Configuring git user..."
git config user.name "OmarAhmed-123" 2>&1 | Out-Null
git config user.email "omar.ahmed@example.com" 2>&1 | Out-Null

# Add remote
Log "Adding remote origin..."
$existingRemote = git remote get-url origin 2>&1
if ($LASTEXITCODE -ne 0) {
    git remote add origin https://github.com/OmarAhmed-123/CONFIT.git 2>&1 | Out-File -FilePath $logFile -Append
    Log "Remote origin added"
} else {
    Log "Remote already exists: $existingRemote"
}

# Add files
Log "Staging files..."
git add . 2>&1 | Out-File -FilePath $logFile -Append

# Count staged files
$stagedCount = (git diff --cached --name-only 2>&1 | Measure-Object -Line).Lines
Log "Files staged: $stagedCount"

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

Tech stack:
- Frontend: React, TypeScript, Tailwind CSS
- Backend: Python FastAPI, SQLAlchemy
- Database: SQLite/PostgreSQL
- AI: Gemini, DeepSeek, OpenAI integration
"@
git commit -m $commitMsg 2>&1 | Out-File -FilePath $logFile -Append

# Check commit status
$commitHash = git rev-parse HEAD 2>&1
if ($LASTEXITCODE -eq 0) {
    Log "SUCCESS: Commit created: $commitHash"
} else {
    Log "ERROR: Commit failed"
}

# Rename branch to main
Log "Renaming branch to main..."
git branch -M main 2>&1 | Out-File -FilePath $logFile -Append

# Final status
Log "=== Final Git Status ==="
git status 2>&1 | Out-File -FilePath $logFile -Append

Log ""
Log "=== SETUP COMPLETE ==="
Log "Log file saved to: $logFile"
Log ""
Log "NEXT STEPS:"
Log "1. Create GitHub repo at: https://github.com/new"
Log "   - Repository name: CONFIT"
Log "   - Owner: OmarAhmed-123"
Log "   - Do NOT add README/gitignore (we have them)"
Log ""
Log "2. After creating repo, run:"
Log "   git push -u origin main"
