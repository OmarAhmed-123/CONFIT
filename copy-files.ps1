# CONFIT Frontend Migration Script
# Copy all files from E:\CONFIT\src to E:\CONFIT\frontend\src

$srcPath = "E:\CONFIT\src"
$destPath = "E:\CONFIT\frontend\src"

# List of directories to copy
$directories = @(
    "components",
    "hooks", 
    "services",
    "stores",
    "lib",
    "types",
    "context",
    "motion",
    "assets",
    "viewmodels",
    "utils",
    "pages",
    "design-system",
    "integrations",
    "styles"
)

foreach ($dir in $directories) {
    $srcDir = Join-Path $srcPath $dir
    $destDir = Join-Path $destPath $dir
    
    if (Test-Path $srcDir) {
        Write-Host "Copying $dir..."
        
        # Remove existing destination if exists
        if (Test-Path $destDir) {
            Remove-Item $destDir -Recurse -Force
        }
        
        # Copy directory
        Copy-Item -Path $srcDir -Destination $destDir -Recurse -Force
        
        $fileCount = (Get-ChildItem $destDir -Recurse -File -ErrorAction SilentlyContinue).Count
        Write-Host "  Copied $fileCount files"
    } else {
        Write-Host "Skipping $dir (not found)"
    }
}

# Copy individual CSS files
Copy-Item "E:\CONFIT\src\index.css" "E:\CONFIT\frontend\src\styles\index.css" -Force -ErrorAction SilentlyContinue
Copy-Item "E:\CONFIT\src\App.css" "E:\CONFIT\frontend\src\styles\App.css" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Migration Complete ==="
Write-Host ""
Write-Host "Directories in frontend\src:"
Get-ChildItem $destPath -Directory | ForEach-Object { Write-Host "  $($_.Name)" }
