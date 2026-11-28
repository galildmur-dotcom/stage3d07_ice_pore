param(
    [string]$ProjectRoot = 'G:\ildar\Stage3D07'
)

# PowerShell 5.1, ASCII-only. No network operations, no source modification.
# Only seven precisely SHA-256-verified source files may enter a local commit.
$ErrorActionPreference = 'Stop'
$expectedHead = 'c0498f6dc98628b62eff996a76844297c7a35094'
$expectedBranch = 'master'
$newBranch = 'research/p10bi-local-seven-sources-20261119'
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
$outDir = ''
$resultCode = 0

function Add-Report([string]$Line) {
    [void]$script:log.Add($Line)
    Write-Host $Line
}

function Invoke-ProjectGit([string[]]$Arguments, [switch]$AllowNonzero) {
    $raw = & $script:gitExe -C $ProjectRoot @Arguments 2>&1
    $code = $LASTEXITCODE
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($code -ne 0 -and -not $AllowNonzero) {
        throw ('git failed, exit=' + $code + ': ' + ($Arguments -join ' ') + ' ' + ($lines -join ' '))
    }
    return [pscustomobject]@{ Code = $code; Lines = $lines }
}

function Check-Preflight {
    $head = (Invoke-ProjectGit @('rev-parse', 'HEAD')).Lines | Select-Object -First 1
    $branch = (Invoke-ProjectGit @('branch', '--show-current')).Lines | Select-Object -First 1
    if ($head -cne $expectedHead) {
        throw ('HEAD changed; expected ' + $expectedHead + ', current ' + $head)
    }
    if ($branch -cne $expectedBranch) {
        throw ('Branch changed; expected master, current ' + $branch)
    }

    $staged = @( (Invoke-ProjectGit @('diff', '--cached', '--name-only')).Lines | Where-Object { $_.Length -gt 0 } )
    if ($staged.Count -ne 0) {
        throw ('Other staged changes exist; commit refused. Paths: ' + ($staged -join ', '))
    }

    $status = @( (Invoke-ProjectGit (@('status', '--porcelain=v1', '--') + $paths)).Lines | Where-Object { $_.Length -gt 0 } )
    if ($status.Count -ne 7) {
        throw ('Expected exactly 7 target status lines, found ' + $status.Count)
    }
    $expectedStatuses = @{}
    foreach ($item in $items) { $expectedStatuses[$item.Path] = $item.Status }
    foreach ($line in $status) {
        if ($line.Length -lt 4) { throw ('Malformed Git status: ' + $line) }
        $code = $line.Substring(0, 2)
        $path = $line.Substring(3).Trim().Replace('\', '/')
        if (-not $expectedStatuses.ContainsKey($path) -or $code -cne $expectedStatuses[$path]) {
            throw ('Unexpected target status: ' + $line)
        }
    }

    foreach ($item in $items) {
        $file = Join-Path $ProjectRoot $item.Path
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw ('Missing source: ' + $item.Path) }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -cne $item.Sha256) { throw ('Source SHA-256 changed: ' + $item.Path) }
    }
    return $status
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw ('Project not found: ' + $ProjectRoot)
    }
    $toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outDir = Join-Path $toolDir ('P10BI_CHECK_' + $stamp + '_' + $PID)
    [void](New-Item -ItemType Directory -Path $outDir -ErrorAction Stop)
    $reportFile = Join-Path $outDir 'P10BI_RESULT.txt'

    Add-Report 'P10BI PRECHECK AND LOCAL COMMIT (no push)'
    Add-Report ('time_local=' + (Get-Date).ToString('o'))
    Add-Report ('project=' + $ProjectRoot)
    $gitTool = Get-Command git.exe -ErrorAction Stop
    $script:gitExe = $gitTool.Source

    $top = (Invoke-ProjectGit @('rev-parse', '--show-toplevel')).Lines | Select-Object -First 1
    $resolvedTop = (Resolve-Path -LiteralPath $top).ProviderPath -replace '[\\/]+$', ''
    $resolvedProject = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath -replace '[\\/]+$', ''
    if ($resolvedTop -ine $resolvedProject) { throw ('Not the expected Git root: ' + $top) }

    $status = Check-Preflight
    $branchExists = Invoke-ProjectGit @('show-ref', '--verify', '--quiet', ('refs/heads/' + $newBranch)) -AllowNonzero
    if ($branchExists.Code -eq 0) { throw ('Local branch already exists: ' + $newBranch) }
    if ($branchExists.Code -ne 1) { throw ('Cannot check branch existence, exit=' + $branchExists.Code) }
    $identity = Invoke-ProjectGit @('var', 'GIT_AUTHOR_IDENT') -AllowNonzero
    if ($identity.Code -ne 0) { throw 'Git author identity is not configured; stop before commit.' }
    $committer = Invoke-ProjectGit @('var', 'GIT_COMMITTER_IDENT') -AllowNonzero
    if ($committer.Code -ne 0) { throw 'Git committer identity is not configured; stop before commit.' }

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
        $backupHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($backupHash -cne $item.Sha256) { throw ('Backup verification failed: ' + $item.Path) }
        Add-Report ('BACKUP_OK ' + $item.Path + ' SHA256=' + $backupHash)
    }

    Add-Report ('HEAD_BEFORE=' + $expectedHead)
    Add-Report ('BRANCH_BEFORE=' + $expectedBranch)
    Add-Report ('NEW_LOCAL_BRANCH=' + $newBranch)
    Add-Report 'PREVIEW: commit precisely these seven paths:'
    foreach ($line in $status) { Add-Report ('  ' + $line) }
    Add-Report ('BACKUP_DIRECTORY=' + $backupRoot)
    Add-Report 'No Git state has been changed yet.'
    Write-Host ''
    Write-Host 'To create the local branch and commit, type exactly COMMIT 7.' -ForegroundColor Yellow
    Write-Host 'Press Enter to stop after the safe preflight and backup.'
    $answer = Read-Host 'Confirmation'
    if ($answer -cne 'COMMIT 7') {
        Add-Report 'RESULT=DRY_RUN_ONLY_NOT_COMMITTED'
    } else {
        [void](Check-Preflight)  # Guard against changes during user confirmation.
        $newRefAgain = Invoke-ProjectGit @('show-ref', '--verify', '--quiet', ('refs/heads/' + $newBranch)) -AllowNonzero
        if ($newRefAgain.Code -ne 1) { throw 'Branch was created or ref check changed; stop.' }
        Add-Report 'CONFIRMATION=COMMIT 7'
        $created = Invoke-ProjectGit @('switch', '-c', $newBranch)
        Add-Report ('BRANCH_SWITCH=' + ($created.Lines -join ' '))
        [void](Invoke-ProjectGit (@('add', '--') + $paths))

        $stagedNow = @( (Invoke-ProjectGit @('diff', '--cached', '--name-only')).Lines | Where-Object { $_.Length -gt 0 } )
        $planned = [string]::Join('|', @($paths | Sort-Object))
        $actualNames = [string]::Join('|', @($stagedNow | Sort-Object))
        if ($planned -cne $actualNames) {
            throw ('Staged path mismatch. Staged: ' + ($stagedNow -join ', ') + '. Commit NOT attempted.')
        }
        Add-Report 'STAGED_EXACTLY_SEVEN=YES'
        # --only plus explicit paths prevents unintended additions if a hook stages other files.
        $commit = Invoke-ProjectGit (@('commit', '--only', '-m', $commitMessage, '--') + $paths)
        foreach ($line in $commit.Lines) { Add-Report ('GIT_COMMIT: ' + $line) }

        $newHead = (Invoke-ProjectGit @('rev-parse', 'HEAD')).Lines | Select-Object -First 1
        $newBranchActual = (Invoke-ProjectGit @('branch', '--show-current')).Lines | Select-Object -First 1
        if ($newHead -ceq $expectedHead -or $newBranchActual -cne $newBranch) {
            throw 'Post-commit HEAD or branch check failed.'
        }
        $committedPaths = @( (Invoke-ProjectGit @('show', '--pretty=format:', '--name-only', 'HEAD')).Lines | Where-Object { $_.Length -gt 0 } )
        if ([string]::Join('|', @($committedPaths | Sort-Object)) -cne $planned) {
            throw ('Post-commit file list differs: ' + ($committedPaths -join ', '))
        }
        Add-Report ('HEAD_AFTER=' + $newHead)
        Add-Report ('BRANCH_AFTER=' + $newBranchActual)
        Add-Report 'COMMIT_CONTENTS=SEVEN_VERIFIED_SOURCE_FILES_ONLY'
        Add-Report 'RESULT=LOCAL_COMMIT_OK_NO_PUSH'
    }
} catch {
    $resultCode = 2
    Add-Report ('RESULT=P10BI_STOPPED: ' + $_.Exception.Message)
    Add-Report 'No automatic rollback, reset, clean or remote action was executed.'
} finally {
    if ($reportFile -ne '') {
        try {
            [System.IO.File]::WriteAllLines($reportFile, $log, [System.Text.UTF8Encoding]::new($false))
            Write-Host ('P10BI report: ' + $reportFile) -ForegroundColor Green
        } catch {
            Write-Host ('Could not write P10BI report: ' + $_.Exception.Message) -ForegroundColor Red
            $resultCode = 2
        }
    }
}
exit $resultCode
