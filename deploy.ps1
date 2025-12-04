# deploy.ps1 - Automates deployment from dev to main

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting deployment from dev to main..." -ForegroundColor Cyan

# 1. Check branch
$currentBranch = git branch --show-current
if ($currentBranch -ne "dev") {
    Write-Error "❌ You must be on the 'dev' branch to run this script."
}

# 2. Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Error "❌ You have uncommitted changes. Please commit or stash them first."
}

# 3. Pull latest dev
Write-Host "⬇️  Pulling latest dev..."
git pull origin dev

# 4. Switch to main
Write-Host "🔀 Switching to main..."
git checkout main
git pull origin main

# 5. Merge dev
Write-Host "🤝 Merging dev into main..."
# We use --no-commit to allow us to remove files before finalizing
# We use --no-ff to create a merge commit, making history clearer
git merge dev --no-commit --no-ff

# 6. Remove test files from staging
Write-Host "🧹 Cleaning up test files..."
$filesToRemove = @("backend/tests", "test_regex.py", "debug_services.py")
foreach ($file in $filesToRemove) {
    if (Test-Path $file) {
        # Remove from index and working directory
        git rm -r -f $file 2>$null
        Write-Host "   - Removed $file from commit" -ForegroundColor Gray
    }
}

# 7. Commit
Write-Host "💾 Committing..."
git commit -m "Deploy: Merge dev into main (excluding tests)"

# 8. Push
Write-Host "⬆️  Pushing to origin/main..."
git push origin main

# 9. Return to dev
Write-Host "🔙 Returning to dev..."
git checkout dev

Write-Host "✅ Deployment complete!" -ForegroundColor Green
