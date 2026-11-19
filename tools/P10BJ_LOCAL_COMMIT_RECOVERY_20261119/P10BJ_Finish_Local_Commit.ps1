param(
    [string]$ProjectRoot = 'G:\ildar\Stage3D07'
)

# Windows PowerShell 5.1, ASCII only. Recovery after P10BI emitted the
# ordinary Git switch message on stderr and stopped before git add/commit.
# Never create a branch, push, pull, fetch, reset, stash, clean or run FEM.
$ErrorActionPreference = 'Stop'
$expectedHead = 'c0498f6dc98628b62eff996a76844297c7a35094'
$expectedBranch = 'research/p10bi-local-seven-sources-20261119'
$commitMessage = 'P10BI: record validated P10AZ-P10BE source worktree (7 files)'

$items = @(
    [pscustomobject]@{ Path = 'CMakeLists.txt'; Sha256 = '453f41a086b1284a7c4da4bba2e343b106edae602adc2ee180fa9fd91abbbddf'; Status = ' M' },
    [pscustomobject]@{ Path = 'src/stage3d10p_partial_audit.cpp'; Sha256 = '73cdbf9ee75de9f32ae8490baeedd760b00797670a4c6c869277405e45963f7a'; Status = ' M' },
    [pscustomobject]@{ Path = 'src/stage3d10w_analytic_adjoint.cpp'; Sha256 = '70873515734edaa42ce96366e636fa6c385a114cd08564817b283fadeccdcd46'; Status = ' M' },
    [pscustomobject]@{ Path = 'src/stage3d10v_analytic_shape.hpp'; Sha256 = 'ad9b5f8d24dcbbbd7678a01a32ef5947e198173c779c7e4efe1da48beca4f7e3'; Status = ' M' },
    [pscustomobject]@{ Path = 'src/stage3d10az_probe_export.hpp'; Sha256 = '9bf6b9729da9e2ff698ef8f890fcc88b8d3fb2ef787708992605a72d0ec8e57d'; Status = '??' },
    [pscustomobject]@{ Path = 'src/stage3d10ba_polar_export.hpp'; Sha256 = '92b81c258b11fad8ccd4915d215f567cbdf61b642c61e9dbe47732b294ead373'; Status = '??' },
    [pscustomobject]@{ Path = 'tests/stage3d10v_analytic_shape.cpp'; Sha256 = 'f5c70aba380da9a45c234b33c8ac2f90879d1d59784033a759b7193ab111ca12'; Status = ' M' }
)
$paths = @($items | ForEach-Object { $_.Path })
$log = New-Object 'System.Collections.Generic.List[string]'
$reportFile = ''
$resultCode = 0

function Add-Report([string]$Line) {
    [void]$script:log.Add($Line)
    Write-Host $Line
}

function Invoke-ProjectGit([string[]]$Arguments, [switch]$AllowNonzero) {
    # PowerShell 5.1 may turn ordinary native stderr into a terminating
    # error under ErrorActionPreference=Stop, even if Git exits with code 0.
    # Inspect the native process exit code instead; keep stderr for diagnostics.
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $script:gitExe -C $ProjectRoot @Arguments 2>&1
        $gitExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedPreference
    }
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($gitExit -ne 0 -and -not $AllowNonzero) {
        throw ('git failed exit=' + $gitExit + ': ' + ($Arguments -join ' ') + ' ' + ($lines -join ' '))
    }
    return [pscustomobject]@{ Code = $gitExit; Lines = $lines }
}

function Check-Preflight {
    $head = (Invoke-ProjectGit @('rev-parse', 'HEAD')).Lines | Select-Object -First 1
    $branch = (Invoke-ProjectGit @('branch', '--show-current')).Lines | Select-Object -First 1
    if ($head -cne $expectedHead) { throw ('Unexpected HEAD, stop: ' + $head) }
    if ($branch -cne $expectedBranch) { throw ('Unexpected branch, stop: ' + $branch) }

    $staged = @((Invoke-ProjectGit @('diff', '--cached', '--name-only')).Lines | Where-Object { $_.Length -gt 0 })
    if ($staged.Count -gt 0) {
        throw ('Already staged paths exist; stop: ' + ($staged -join ', '))
    }

    $status = @((Invoke-ProjectGit (@('status', '--porcelain=v1', '--') + $paths)).Lines | Where-Object { $_.Length -gt 0 })
    if ($status.Count -ne $items.Count) {
        throw ('Expected exactly 7 target status lines, got ' + $status.Count)
    }
    $expectedStatuses = @{}
    foreach ($item in $items) { $expectedStatuses[$item.Path] = $item.Status }
    $seen = @{}
    foreach ($line in $status) {
        if ($line.Length -lt 4) { throw ('Malformed status line: ' + $line) }
        $statusCode = $line.Substring(0, 2)
        $path = $line.Substring(3).Trim().Replace('\', '/')
        if (-not $expectedStatuses.ContainsKey($path) -or $statusCode -cne $expectedStatuses[$path]) {
            throw ('Unexpected target path/status, stop: ' + $line)
        }
        if ($seen.ContainsKey($path)) { throw ('Duplicate status path, stop: ' + $path) }
        $seen[$path] = $true
    }

    foreach ($item in $items) {
        $file = Join-Path $ProjectRoot $item.Path
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw ('Source missing: ' + $item.Path) }
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -cne $item.Sha256) { throw ('Source SHA-256 mismatch: ' + $item.Path) }
    }
    return $status
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw ('Project directory missing: ' + $ProjectRoot)
    }
    $toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outDir = Join-Path $toolDir ('P10BJ_CHECK_' + $stamp + '_' + $PID)
    [void](New-Item -ItemType Directory -Path $outDir -ErrorAction Stop)
    $reportFile = Join-Path $outDir 'P10BJ_RESULT.txt'

    Add-Report 'P10BJ SAFE LOCAL COMMIT RECOVERY (NO PUSH)'
    Add-Report ('time_local=' + (Get-Date).ToString('o'))
    Add-Report ('project=' + $ProjectRoot)
    $gitTool = Get-Command git.exe -ErrorAction Stop
    $script:gitExe = $gitTool.Source
    $top = (Invoke-ProjectGit @('rev-parse', '--show-toplevel')).Lines | Select-Object -First 1
    $resolvedTop = (Resolve-Path -LiteralPath $top).ProviderPath -replace '[\\/]+$', ''
    $resolvedProject = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath -replace '[\\/]+$', ''
    if ($resolvedTop -ine $resolvedProject) { throw ('Git root mismatch: ' + $top) }

    $status = Check-Preflight
    $author = Invoke-ProjectGit @('var', 'GIT_AUTHOR_IDENT') -AllowNonzero
    $committer = Invoke-ProjectGit @('var', 'GIT_COMMITTER_IDENT') -AllowNonzero
    if ($author.Code -ne 0 -or $committer.Code -ne 0) {
        throw 'Git author/committer identity is missing; stop before commit.'
    }

    $backupRoot = Join-Path $outDir 'SOURCE_BACKUP'
    [void](New-Item -ItemType Directory -Path $backupRoot -ErrorAction Stop)
    foreach ($item in $items) {
        $original = Join-Path $ProjectRoot $item.Path
        $target = Join-Path $backupRoot $item.Path
        $parent = Split-Path -Parent $target
        if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
            [void](New-Item -ItemType Directory -Path $parent -Force -ErrorAction Stop)
        }
        Copy-Item -LiteralPath $original -Destination $target -ErrorAction Stop
        $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -cne $item.Sha256) { throw ('Backup hash mismatch: ' + $item.Path) }
        Add-Report ('BACKUP_OK ' + $item.Path + ' SHA256=' + $hash)
    }

    Add-Report ('HEAD_BEFORE=' + $expectedHead)
    Add-Report ('BRANCH_BEFORE=' + $expectedBranch)
    Add-Report 'PREVIEW: commit these seven target paths only:'
    foreach ($line in $status) { Add-Report ('  ' + $line) }
    Add-Report ('BACKUP_DIRECTORY=' + $backupRoot)
    Add-Report 'Precheck and backup succeeded. No Git changes have been made by P10BJ.'
    Write-Host ''
    Write-Host 'To make the local commit, type exactly COMMIT 7.' -ForegroundColor Yellow
    Write-Host 'Press Enter for precheck/backup only, without a commit.'
    $answer = Read-Host 'Confirmation'
    if ($answer -cne 'COMMIT 7') {
        Add-Report 'RESULT=DRY_RUN_ONLY_NOT_COMMITTED'
    } else {
        [void](Check-Preflight)
        Add-Report 'CONFIRMATION=COMMIT 7'
        [void](Invoke-ProjectGit (@('add', '--') + $paths))
        $stagedNow = @((Invoke-ProjectGit @('diff', '--cached', '--name-only')).Lines | Where-Object { $_.Length -gt 0 })
        $planned = [string]::Join('|', @($paths | Sort-Object))
        $actual = [string]::Join('|', @($stagedNow | Sort-Object))
        if ($planned -cne $actual) {
            throw ('Unexpected staged paths; commit NOT attempted: ' + ($stagedNow -join ', '))
        }
        Add-Report 'STAGED_EXACTLY_SEVEN=YES'

        # --only with explicit paths limits the commit even if a hook stages extras.
        $commit = Invoke-ProjectGit (@('commit', '--only', '-m', $commitMessage, '--') + $paths)
        foreach ($line in $commit.Lines) { Add-Report ('GIT_COMMIT: ' + $line) }
        $newHead = (Invoke-ProjectGit @('rev-parse', 'HEAD')).Lines | Select-Object -First 1
        $newBranch = (Invoke-ProjectGit @('branch', '--show-current')).Lines | Select-Object -First 1
        if ($newHead -ceq $expectedHead -or $newBranch -cne $expectedBranch) {
            throw 'Post-commit HEAD/branch mismatch; inspect Git before any retry.'
        }
        $committedPaths = @((Invoke-ProjectGit @('show', '--pretty=format:', '--name-only', 'HEAD')).Lines | Where-Object { $_.Length -gt 0 })
        if ([string]::Join('|', @($committedPaths | Sort-Object)) -cne $planned) {
            throw ('Unexpected committed path list: ' + ($committedPaths -join ', '))
        }
        Add-Report ('HEAD_AFTER=' + $newHead)
        Add-Report ('BRANCH_AFTER=' + $newBranch)
        Add-Report 'COMMIT_CONTENTS=SEVEN_VERIFIED_SOURCE_FILES_ONLY'
        Add-Report 'RESULT=LOCAL_COMMIT_OK_NO_PUSH'
    }
} catch {
    $resultCode = 2
    Add-Report ('RESULT=P10BJ_STOPPED: ' + $_.Exception.Message)
    Add-Report 'Do not rerun, reset or push before inspecting this report.'
} finally {
    if ($reportFile -ne '') {
        try {
            [System.IO.File]::WriteAllLines($reportFile, $log, [System.Text.UTF8Encoding]::new($false))
            Write-Host ('P10BJ report: ' + $reportFile) -ForegroundColor Green
        } catch {
            Write-Host ('Could not write report: ' + $_.Exception.Message) -ForegroundColor Red
            $resultCode = 2
        }
    }
}
exit $resultCode
