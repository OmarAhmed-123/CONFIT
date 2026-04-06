<#
.SYNOPSIS
    CONFIT - Cleanup Windows user temp and tool caches WITHOUT touching project source by default.

.DESCRIPTION
    DEFAULT (Scope=Disk): cleans npm/pip caches + safe OS/user temp folders only.
    This targets files on the system/user profile and temp drives — not your repo tree.

    Scope=Project: OPTIONAL — removes regenerable build folders (.next, dist, etc.) INSIDE the repo.
    Use only when you intentionally want to reclaim space from build outputs.

    SystemSafe skips any path under the repo EXCEPT dedicated folders like .tmp and .npm-cache
    (so README-recommended TEMP locations can still be cleaned).

.PARAMETER Scope
    Disk       - DEFAULT: UserCaches + SystemSafe (no project files).
    Project    - Only build/cache dirs under the CONFIT repo (explicit opt-in).
    UserCaches - npm cache clean, pip cache purge only.
    SystemSafe - User TEMP, LocalAppData Temp, INetCache, old CrashDumps (respects project protection).
    Both       - Disk + Project (full clean including repo build artifacts).

.PARAMETER Root
    CONFIT repository root (parent of scripts/). Used for Project scope and protection checks.

.PARAMETER DryRun
    List actions without deleting.

.PARAMETER CopyToDesktop
    Copy this script to Desktop as CONFIT-windows-cleanup.ps1.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-cleanup.ps1 -Scope Disk -DryRun

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-cleanup.ps1 -Scope Project
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $Root = "",
    [ValidateSet("Disk", "Project", "UserCaches", "SystemSafe", "Both")]
    [string] $Scope = "Disk",
    [switch] $DryRun,
    [switch] $RemoveEmptyFiles,
    [switch] $RemoveEmptyDirs,
    # DANGER: With -Scope Project, removes every `node_modules` under the repo (not used by default Scope=Disk).
    [switch] $RemoveNodeModules,
    [string] $LogPath = "",
    [switch] $CopyToDesktop
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    param([string] $ExplicitRoot)
    if ($ExplicitRoot -and (Test-Path -LiteralPath $ExplicitRoot)) {
        return (Resolve-Path -LiteralPath $ExplicitRoot).Path
    }
    $here = $PSScriptRoot
    if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path -LiteralPath (Join-Path $here "..")).Path
}

$RepoRoot = Get-RepoRoot -ExplicitRoot $Root
$started = Get-Date
$stats = @{ DirsRemoved = 0; FilesRemoved = 0; BytesFreedApprox = [int64]0 }

function Write-CleanupLog {
    param([string] $Message)
    $line = "[{0:u}] {1}" -f (Get-Date), $Message
    Write-Host $line
    if ($LogPath) {
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    }
}

function Test-IsBlockedSystemPath {
    param([string] $FullPath)
    $lower = $FullPath.ToLowerInvariant()
    $blocked = @(
        "\windows\system32", "\windows\syswow64", "\windows\winsxs",
        "\program files\", "\program files (x86)\",
        "\programdata\microsoft\windows defender"
    )
    foreach ($b in $blocked) {
        if ($lower -like "*${b}*") { return $true }
    }
    return $false
}

function Test-IsProtectedRepoPath {
    param(
        [string] $FullPath,
        [string] $Repo
    )
    if (-not $Repo) { return $false }
    try {
        $f = (Resolve-Path -LiteralPath $FullPath -ErrorAction Stop).Path
        $r = (Resolve-Path -LiteralPath $Repo -ErrorAction Stop).Path
    } catch {
        return $false
    }
    if (-not $f.StartsWith($r, [StringComparison]::OrdinalIgnoreCase)) { return $false }
    $allowedUnderRepo = @(
        (Join-Path $r ".tmp"),
        (Join-Path $r ".npm-cache")
    )
    foreach ($a in $allowedUnderRepo) {
        if ($f.StartsWith($a, [StringComparison]::OrdinalIgnoreCase)) { return $false }
    }
    return $true
}

function Remove-PathSafe {
    param(
        [string] $LiteralPath,
        [string] $Kind,
        [switch] $SkipRepoProtection
    )
    if (-not (Test-Path -LiteralPath $LiteralPath)) { return }
    if (Test-IsBlockedSystemPath -FullPath $LiteralPath) {
        Write-Warning "Skipped (protected system path): $LiteralPath"
        return
    }
    if (-not $SkipRepoProtection -and ($Kind -eq "system-temp") -and (Test-IsProtectedRepoPath -FullPath $LiteralPath -Repo $RepoRoot)) {
        Write-CleanupLog "Skipped (inside project tree, not .tmp/.npm-cache): $LiteralPath"
        return
    }
    try {
        $item = Get-Item -LiteralPath $LiteralPath -Force
        if ($item.PSIsContainer) {
            if ($DryRun) {
                Write-CleanupLog "[DRY-RUN] Would remove dir ${Kind}: $LiteralPath"
                return
            }
            if ($PSCmdlet.ShouldProcess($LiteralPath, "Remove directory")) {
                Remove-Item -LiteralPath $LiteralPath -Recurse -Force -ErrorAction Stop
                $script:stats.DirsRemoved++
                Write-CleanupLog "Removed dir ${Kind}: $LiteralPath"
            }
        } else {
            $len = $item.Length
            if ($DryRun) {
                Write-CleanupLog "[DRY-RUN] Would remove file ${Kind}: $LiteralPath ($len bytes)"
                return
            }
            if ($PSCmdlet.ShouldProcess($LiteralPath, "Remove file")) {
                Remove-Item -LiteralPath $LiteralPath -Force -ErrorAction Stop
                $script:stats.FilesRemoved++
                $script:stats.BytesFreedApprox += $len
                Write-CleanupLog "Removed file ${Kind}: $LiteralPath"
            }
        }
    } catch {
        Write-Warning ("Failed: {0} - {1}" -f $LiteralPath, $_.Exception.Message)
    }
}

function Get-ProjectScanRoots {
    param([string] $Base)
    $roots = @($Base)
    foreach ($child in @("apps", "services", "packages", "backend", "src", "scripts", "tools")) {
        $p = Join-Path $Base $child
        if (Test-Path -LiteralPath $p) { $roots += (Resolve-Path -LiteralPath $p).Path }
    }
    return $roots
}

function Clear-ProjectCaches {
    param([string] $Base)

    $dirPatterns = @(
        ".next", "dist", "build", ".turbo", "coverage", ".pytest_cache", "__pycache__",
        ".mypy_cache", ".parcel-cache", ".vite", ".eslintcache", "storybook-static",
        ".swc", ".tsc-cache", "htmlcov", ".nyc_output", "cypress/videos", "cypress/screenshots"
    )

    $scanRoots = Get-ProjectScanRoots -Base $Base
    foreach ($root in $scanRoots) {
        foreach ($name in $dirPatterns) {
            Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -eq $name -and $_.FullName -notmatch '[\\/]\.git[\\/]' } |
                ForEach-Object { Remove-PathSafe -LiteralPath $_.FullName -Kind "cache/build" -SkipRepoProtection }
        }
        Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '[\\/]node_modules[\\/]\.cache$' } |
            ForEach-Object { Remove-PathSafe -LiteralPath $_.FullName -Kind "node_modules/.cache" -SkipRepoProtection }
        if ($RemoveNodeModules) {
            Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -eq "node_modules" -and $_.FullName -notmatch '[\\/]\.git[\\/]' } |
                ForEach-Object { Remove-PathSafe -LiteralPath $_.FullName -Kind "node_modules" -SkipRepoProtection }
        }
        Get-ChildItem -LiteralPath $root -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Extension -eq ".log" -and
                $_.FullName -notmatch '[\\/]\.git[\\/]' -and
                $_.FullName -notmatch '[\\/]node_modules[\\/]'
            } |
            ForEach-Object { Remove-PathSafe -LiteralPath $_.FullName -Kind "log" -SkipRepoProtection }
        Get-ChildItem -LiteralPath $root -Filter "*.tsbuildinfo" -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' } |
            ForEach-Object { Remove-PathSafe -LiteralPath $_.FullName -Kind "tsbuildinfo" -SkipRepoProtection }
    }
}

function Remove-EmptyFilesUnder {
    param([string] $Base)
    foreach ($scan in (Get-ProjectScanRoots -Base $Base)) {
        Get-ChildItem -LiteralPath $scan -File -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Length -eq 0 -and
                $_.FullName -notmatch '[\\/]\.git[\\/]'
            } |
            ForEach-Object { Remove-PathSafe -LiteralPath $_.FullName -Kind "empty-file" -SkipRepoProtection }
    }
}

function Remove-EmptyDirsUnder {
    param([string] $Base)
    foreach ($scan in (Get-ProjectScanRoots -Base $Base)) {
        $dirs = Get-ChildItem -LiteralPath $scan -Directory -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '[\\/]\.git([\\/]|$)' } |
            Sort-Object { $_.FullName.Length } -Descending
        foreach ($d in $dirs) {
            $any = Get-ChildItem -LiteralPath $d.FullName -Force -ErrorAction SilentlyContinue
            if (-not $any) {
                Remove-PathSafe -LiteralPath $d.FullName -Kind "empty-dir" -SkipRepoProtection
            }
        }
    }
}

function Get-SafeSystemTempRoots {
    $list = New-Object System.Collections.Generic.List[string]
    foreach ($p in @($env:TEMP, $env:TMP)) {
        if ($p -and (Test-Path -LiteralPath $p)) { $list.Add((Resolve-Path -LiteralPath $p).Path) }
    }
    $localTemp = Join-Path $env:LOCALAPPDATA "Temp"
    if (Test-Path -LiteralPath $localTemp) { $list.Add((Resolve-Path -LiteralPath $localTemp).Path) }
    $inet = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\INetCache"
    if (Test-Path -LiteralPath $inet) { $list.Add((Resolve-Path -LiteralPath $inet).Path) }
    $crash = Join-Path $env:LOCALAPPDATA "CrashDumps"
    if (Test-Path -LiteralPath $crash) { $list.Add((Resolve-Path -LiteralPath $crash).Path) }
    $winTemp = Join-Path $env:SystemRoot "Temp"
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin -and (Test-Path -LiteralPath $winTemp)) {
        $list.Add((Resolve-Path -LiteralPath $winTemp).Path)
    }
    return $list | Select-Object -Unique
}

function Clear-SystemSafeJunk {
    param([int] $OlderThanDays = 7)

    $roots = Get-SafeSystemTempRoots
    Write-CleanupLog ("SystemSafe: {0} temp root(s). Repo tree is protected except .tmp and .npm-cache under repo." -f $roots.Count)

    $cutoff = (Get-Date).AddDays(-$OlderThanDays)
    $extOk = @(".tmp", ".temp", ".log", ".bak", ".old", ".dmp")

    foreach ($root in $roots) {
        if (Test-IsBlockedSystemPath -FullPath $root) { continue }
        try {
            Get-ChildItem -LiteralPath $root -File -Recurse -Force -ErrorAction SilentlyContinue |
                Where-Object {
                    -not (Test-IsBlockedSystemPath -FullPath $_.FullName) -and
                    (
                        ($_.Length -eq 0) -or
                        ($_.Extension -in $extOk -and $_.LastWriteTime -lt $cutoff)
                    )
                } |
                ForEach-Object { Remove-PathSafe -LiteralPath $_.FullName -Kind "system-temp" }
        } catch {
            Write-Warning ("Scan failed for {0}: {1}" -f $root, $_.Exception.Message)
        }
    }

    Write-CleanupLog "Note: Prefetch and Windows Update caches are not modified."
}

function Clear-UserCaches {
    Write-CleanupLog "Running npm cache clean..."
    if ($DryRun) {
        Write-CleanupLog "[DRY-RUN] Would run: npm cache clean --force"
        return
    }
    try {
        & npm cache clean --force 2>&1 | ForEach-Object { Write-CleanupLog ("npm: {0}" -f $_) }
    } catch {
        Write-Warning ("npm cache clean failed: {0}" -f $_.Exception.Message)
    }
    $pip = Get-Command pip -ErrorAction SilentlyContinue
    if ($pip) {
        Write-CleanupLog "Running pip cache purge..."
        try {
            & pip cache purge 2>&1 | ForEach-Object { Write-CleanupLog ("pip: {0}" -f $_) }
        } catch {
            Write-Warning ("pip cache purge failed: {0}" -f $_.Exception.Message)
        }
    } else {
        Write-CleanupLog "pip not found; skipped."
    }
}

function Copy-ScriptToDesktop {
    try {
        $desktop = [Environment]::GetFolderPath("Desktop")
        if (-not $desktop) { return }
        $dest = Join-Path $desktop "CONFIT-windows-cleanup.ps1"
        $src = $PSCommandPath
        if (-not $src) { $src = $MyInvocation.MyCommand.Path }
        if (-not $src -or -not (Test-Path -LiteralPath $src)) {
            $src = Join-Path $PSScriptRoot "windows-cleanup.ps1"
        }
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination $dest -Force
            Write-CleanupLog ("Copied script to Desktop: {0}" -f $dest)
        } else {
            Write-Warning "Could not resolve script path for Desktop copy."
        }
    } catch {
        Write-Warning ("Could not copy to Desktop: {0}" -f $_.Exception.Message)
    }
}

# --- main ---
Write-CleanupLog "=== CONFIT windows-cleanup.ps1 ==="
Write-CleanupLog ("RepoRoot={0} Scope={1} DryRun={2}" -f $RepoRoot, $Scope, $DryRun)
Write-CleanupLog "Default Scope=Disk cleans OS/user caches only — not apps/web/node_modules unless you use -Scope Project."

if ($LogPath -and (Split-Path -Parent $LogPath) -and -not (Test-Path -LiteralPath (Split-Path -Parent $LogPath))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $LogPath) -Force | Out-Null
}

$runProject = ($Scope -eq "Project") -or ($Scope -eq "Both")

if ($runProject) {
    if (-not (Test-Path -LiteralPath $RepoRoot)) {
        throw ("Root path does not exist: {0}" -f $RepoRoot)
    }
    Clear-ProjectCaches -Base $RepoRoot
    if ($RemoveEmptyFiles) {
        Remove-EmptyFilesUnder -Base $RepoRoot
    }
    if ($RemoveEmptyDirs) {
        Remove-EmptyDirsUnder -Base $RepoRoot
    }
}

if ($Scope -eq "Disk" -or $Scope -eq "Both") {
    Clear-UserCaches
    Clear-SystemSafeJunk -OlderThanDays 7
} elseif ($Scope -eq "UserCaches") {
    Clear-UserCaches
} elseif ($Scope -eq "SystemSafe") {
    Clear-SystemSafeJunk -OlderThanDays 7
}

$elapsed = (Get-Date) - $started
$summary = "Done in {0:mm\:ss}. Dirs removed: {1}, files removed: {2}, approx bytes: {3}." -f `
    $elapsed, $stats.DirsRemoved, $stats.FilesRemoved, $stats.BytesFreedApprox
Write-CleanupLog $summary
Write-CleanupLog "Tip: set TEMP, TMP, npm_config_cache to E:\CONFIT\.tmp and E:\CONFIT\.npm-cache (see README). For broken node_modules after ENOSPC run: scripts\repair-node-modules.ps1"
Write-Output $summary

if ($CopyToDesktop) {
    Copy-ScriptToDesktop
}
