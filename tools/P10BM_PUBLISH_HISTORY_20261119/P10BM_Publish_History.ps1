param(
    [string]$ProjectRoot = 'G:\ildar\Stage3D07'
)

# Windows PowerShell 5.1, ASCII only. The researcher explicitly approved
# publication of all 56 reachable local commits as one NEW GitHub branch.
# Non-force push with exactly one refspec. Never pushes tags or other branches.
$ErrorActionPreference = 'Stop'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$expectedParent = 'c0498f6dc98628b62eff996a76844297c7a35094'
$expectedBranch = 'research/p10bi-local-seven-sources-20261119'
$remoteRef = 'refs/heads/research/p10bi-local-seven-sources-20261119'
$expectedRemoteUrl = 'https://github.com/galildmur-dotcom/stage3d07_ice_pore.git'
$expectedFiles = @(
    'CMakeLists.txt',
    'src/stage3d10p_partial_audit.cpp',
    'src/stage3d10v_analytic_shape.hpp',
    'src/stage3d10w_analytic_adjoint.cpp',
    'src/stage3d10az_probe_export.hpp',
    'src/stage3d10ba_polar_export.hpp',
    'tests/stage3d10v_analytic_shape.cpp'
)
$log = New-Object 'System.Collections.Generic.List[string]'
$reportFile = ''
$resultCode = 0

function Add-Report([string]$Line) {
    [void]$script:log.Add($Line)
    Write-Host $Line
}

function Invoke-ProjectGit([string[]]$Arguments, [switch]$AllowNonzero) {
    # Native Git can send ordinary messages to stderr on Windows PowerShell.
    # Use the process exit code, not the stderr stream, for success/failure.
    $saved = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $script:gitExe -C $ProjectRoot @Arguments 2>&1
        $gitExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $saved }
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($gitExit -ne 0 -and -not $AllowNonzero) {
        # Do not report raw Git error lines: they may contain URL credentials.
        throw ('Git command returned exit=' + $gitExit + ', verb=' + $Arguments[0])
    }
    return [pscustomobject]@{ Code = $gitExit; Lines = $lines }
}

function Get-RemoteBranchStatus {
    $response = Invoke-ProjectGit @('ls-remote', '--exit-code', '--heads', 'origin', $remoteRef) -AllowNonzero
    if ($response.Code -eq 2) { return [pscustomobject]@{ Exists = $false; Sha = '' } }
    if ($response.Code -ne 0) {
        throw ('Cannot verify remote branch with git ls-remote; exit=' + $response.Code)
    }
    $shaLines = @($response.Lines | Where-Object { $_ -match '^[0-9a-fA-F]{40}\s+refs/heads/' })
    if ($shaLines.Count -ne 1) { throw 'Unexpected remote branch response. Stop.' }
    $line = $shaLines[0]
    if ($line -match '^([0-9a-fA-F]{40})\s+refs/heads/research/p10bi-local-seven-sources-20261119$') {
        return [pscustomobject]@{ Exists = $true; Sha = $Matches[1].ToLowerInvariant() }
    }
    throw 'Remote branch name mismatch. Stop.'
}

function Check-LocalState {
    $branch = (Invoke-ProjectGit @('branch', '--show-current')).Lines | Select-Object -First 1
    $head = (Invoke-ProjectGit @('rev-parse', 'HEAD')).Lines | Select-Object -First 1
    $parent = (Invoke-ProjectGit @('show', '-s', '--format=%P', 'HEAD')).Lines | Select-Object -First 1
    $master = (Invoke-ProjectGit @('rev-parse', 'refs/heads/master')).Lines | Select-Object -First 1
    if ($branch -cne $expectedBranch -or $head -cne $expectedHead -or
        $parent -cne $expectedParent -or $master -cne $expectedParent) {
        throw 'Local branch, HEAD, parent or master changed since P10BK/P10BL. Stop.'
    }
    $ncommits = (Invoke-ProjectGit @('rev-list', '--count', 'HEAD')).Lines | Select-Object -First 1
    if ($ncommits -cne '56') { throw ('Reachable commit count changed: ' + $ncommits) }

    $files = @((Invoke-ProjectGit @('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD')).Lines | Where-Object { $_.Length -gt 0 })
    if ([string]::Join('|', @($files | Sort-Object)) -cne [string]::Join('|', @($expectedFiles | Sort-Object))) {
        throw 'The HEAD commit is not the seven-source commit. Stop.'
    }
    $allRemotes = @((Invoke-ProjectGit @('remote')).Lines | Where-Object { $_.Length -gt 0 })
    if ($allRemotes.Count -ne 1 -or $allRemotes[0] -cne 'origin') {
        throw 'Unexpected number or name of Git remotes. Stop.'
    }
    $fetchUrls = @((Invoke-ProjectGit @('remote', 'get-url', '--all', 'origin')).Lines)
    $pushUrls = @((Invoke-ProjectGit @('remote', 'get-url', '--all', '--push', 'origin')).Lines)
    if ($fetchUrls.Count -ne 1 -or $pushUrls.Count -ne 1 -or
        $fetchUrls[0] -cne $expectedRemoteUrl -or $pushUrls[0] -cne $expectedRemoteUrl) {
        throw 'Configured origin URL changed or has unexpected multiple targets. Stop.'
    }

    $mirror = Invoke-ProjectGit @('config', '--bool', '--get', 'remote.origin.mirror') -AllowNonzero
    if ($mirror.Code -ne 0 -and $mirror.Code -ne 1) { throw 'Cannot inspect remote mirror setting. Stop.' }
    if ($mirror.Code -eq 0 -and $mirror.Lines.Count -gt 0 -and $mirror.Lines[0] -ceq 'true') {
        throw 'Remote origin has mirror mode enabled. Stop.'
    }
    $pushSpec = Invoke-ProjectGit @('config', '--get-all', 'remote.origin.push') -AllowNonzero
    if ($pushSpec.Code -ne 0 -and $pushSpec.Code -ne 1) { throw 'Cannot inspect remote push refspec. Stop.' }
    if ($pushSpec.Code -eq 0 -and $pushSpec.Lines.Count -gt 0) {
        throw 'A custom remote.origin.push refspec is configured. Stop.'
    }
    # Do not run a potentially mutating or user-configured pre-push hook.
    $hooksConfig = Invoke-ProjectGit @('config', '--get', 'core.hooksPath') -AllowNonzero
    if ($hooksConfig.Code -ne 0 -and $hooksConfig.Code -ne 1) { throw 'Cannot inspect hook configuration. Stop.' }
    if ($hooksConfig.Code -eq 0 -and $hooksConfig.Lines.Count -gt 0) {
        throw 'Custom core.hooksPath configured. Stop for review.'
    }
    $gitDir = (Invoke-ProjectGit @('rev-parse', '--absolute-git-dir')).Lines | Select-Object -First 1
    $prePushHook = Join-Path $gitDir 'hooks/pre-push'
    if (Test-Path -LiteralPath $prePushHook -PathType Leaf) {
        throw 'Active pre-push hook exists. Stop for review.'
    }

    $status = @((Invoke-ProjectGit @('status', '--porcelain=v1', '--untracked-files=normal')).Lines | Where-Object { $_.Length -gt 0 })
    $staged = 0
    $unstaged = 0
    $untracked = 0
    foreach ($line in $status) {
        if ($line.Length -lt 3) { throw 'Malformed Git status. Stop.' }
        if ($line.Substring(0, 2) -ceq '??') { $untracked++ }
        else {
            if ($line[0] -ne ' ') { $staged++ }
            if ($line[1] -ne ' ') { $unstaged++ }
        }
    }
    if ($staged -ne 0 -or $unstaged -ne 7 -or $untracked -ne 4) {
        throw ('Git status changed: staged=' + $staged + ', unstaged=' + $unstaged + ', untracked=' + $untracked)
    }
    return [pscustomobject]@{ Commits = $ncommits; Staged = $staged; Unstaged = $unstaged; Untracked = $untracked }
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw ('Project directory not found: ' + $ProjectRoot)
    }
    $toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $outDir = Join-Path $toolDir ('P10BM_CHECK_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + $PID)
    [void](New-Item -ItemType Directory -Path $outDir -ErrorAction Stop)
    $reportFile = Join-Path $outDir 'P10BM_PUSH_RESULT.txt'
    Add-Report 'P10BM CONTROLLED GITHUB NEW-BRANCH PUSH (NO FORCE)'
    Add-Report ('time_local=' + (Get-Date).ToString('o'))
    Add-Report ('project=' + $ProjectRoot)
    $script:gitExe = (Get-Command git.exe -ErrorAction Stop).Source
    $top = (Invoke-ProjectGit @('rev-parse', '--show-toplevel')).Lines | Select-Object -First 1
    $actualRoot = (Resolve-Path -LiteralPath $top).ProviderPath -replace '[\\/]+$', ''
    $givenRoot = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath -replace '[\\/]+$', ''
    if ($actualRoot -ine $givenRoot) { throw ('Git root mismatch: ' + $top) }

    $state = Check-LocalState
    Add-Report ('HEAD=' + $expectedHead)
    Add-Report ('BRANCH=' + $expectedBranch)
    Add-Report ('PARENT=' + $expectedParent)
    Add-Report ('COMMITS=' + $state.Commits)
    Add-Report ('STAGED=' + $state.Staged)
    Add-Report ('UNSTAGED_PRESERVED=' + $state.Unstaged)
    Add-Report ('UNTRACKED_PRESERVED=' + $state.Untracked)
    Add-Report ('REMOTE=origin ' + $expectedRemoteUrl)
    Add-Report ('TARGET_REMOTE_REF=' + $remoteRef)

    $remoteBefore = Get-RemoteBranchStatus
    if ($remoteBefore.Exists) {
        Add-Report ('REMOTE_HEAD_BEFORE=' + $remoteBefore.Sha)
        if ($remoteBefore.Sha -ceq $expectedHead) {
            Add-Report 'RESULT=ALREADY_PUBLISHED_VERIFIED_NO_PUSH'
        } else {
            throw 'Target remote branch already exists at a different SHA. No push attempted.'
        }
    } else {
        Add-Report 'REMOTE_HEAD_BEFORE=ABSENT'
        Add-Report 'PREVIEW: this operation publishes the full reachable 56-commit history.'
        Add-Report 'P10BL_AUDIT: reachable blobs 818, uncompressed bytes 15217564, max blob bytes 1450900.'
        Add-Report 'Only ONE NEW branch will be created. No GitHub master, research branch or tag update.'
        Write-Host ''
        Write-Host 'The 56 historical commits will become visible in the PUBLIC GitHub repo.' -ForegroundColor Yellow
        Write-Host 'To approve exactly this ONE remote branch push, type PUSH 56.' -ForegroundColor Yellow
        Write-Host 'Press Enter to stop with no push.'
        $answer = Read-Host 'Confirmation'
        if ($answer -cne 'PUSH 56') {
            Add-Report 'RESULT=DRY_RUN_ONLY_NO_PUSH'
        } else {
            [void](Check-LocalState)
            $remoteAgain = Get-RemoteBranchStatus
            if ($remoteAgain.Exists) { throw 'Remote branch appeared during confirmation. No push attempted.' }
            Add-Report 'CONFIRMATION=PUSH 56'
            Add-Report 'GIT_PUSH_ATTEMPT=ONE_REFSPEC_NO_FORCE_NO_TAGS'
            Write-Host 'Uploading the approved 56-commit history; please wait. Do not close this window.' -ForegroundColor Yellow
            # Explicit refspec; config overrides prohibit automatic tag/submodule pushes.
            $pushResult = Invoke-ProjectGit @('-c', 'push.followTags=false', '-c', 'push.recurseSubmodules=no', 'push', '--porcelain', '--no-follow-tags', '--recurse-submodules=no', 'origin', ('HEAD:' + $remoteRef)) -AllowNonzero
            Add-Report ('GIT_PUSH_EXIT=' + $pushResult.Code)
            if ($pushResult.Code -ne 0) {
                throw 'git push did not exit successfully. Remote state may be uncertain; do not retry.'
            }
            $remoteAfter = Get-RemoteBranchStatus
            if (-not $remoteAfter.Exists -or $remoteAfter.Sha -cne $expectedHead) {
                throw 'Push returned success but GitHub branch SHA was not verified. Do not retry.'
            }
            Add-Report ('REMOTE_HEAD_AFTER=' + $remoteAfter.Sha)
            Add-Report 'RESULT=P10BM_REMOTE_BRANCH_PUBLISHED_AND_VERIFIED'
        }
    }
} catch {
    $resultCode = 2
    Add-Report ('RESULT=P10BM_STOPPED: ' + $_.Exception.Message)
    Add-Report 'Do not run old PORE push, force-push, or repeat P10BM before reviewing this report.'
} finally {
    if ($reportFile -ne '') {
        try {
            [System.IO.File]::WriteAllLines($reportFile, $log, [System.Text.UTF8Encoding]::new($false))
            Write-Host ('P10BM report: ' + $reportFile) -ForegroundColor Green
        } catch {
            Write-Host ('Could not write report: ' + $_.Exception.Message) -ForegroundColor Red
            $resultCode = 2
        }
    }
}
exit $resultCode
