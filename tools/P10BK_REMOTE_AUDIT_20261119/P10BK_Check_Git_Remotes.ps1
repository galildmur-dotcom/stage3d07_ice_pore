param(
    [string]$ProjectRoot = 'G:\ildar\Stage3D07'
)

# Windows PowerShell 5.1, ASCII only, Git read-only operations exclusively.
$ErrorActionPreference = 'Stop'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$expectedParent = 'c0498f6dc98628b62eff996a76844297c7a35094'
$expectedBranch = 'research/p10bi-local-seven-sources-20261119'
$expectedPaths = @(
    'CMakeLists.txt',
    'src/stage3d10p_partial_audit.cpp',
    'src/stage3d10w_analytic_adjoint.cpp',
    'src/stage3d10v_analytic_shape.hpp',
    'src/stage3d10az_probe_export.hpp',
    'src/stage3d10ba_polar_export.hpp',
    'tests/stage3d10v_analytic_shape.cpp'
)
$log = New-Object 'System.Collections.Generic.List[string]'
$reportFile = ''
$exitCode = 0

function Add-Report([string]$Line) {
    [void]$script:log.Add($Line)
    Write-Host $Line
}

function Invoke-ProjectGit([string[]]$Arguments, [switch]$AllowNonzero) {
    # Git may write normal messages to stderr on Windows. Use exit code.
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
        # Do not put raw stderr into this report: URL credentials may be present.
        throw ('Read-only git command failed, exit=' + $gitExit + ', verb=' + $Arguments[0])
    }
    return [pscustomobject]@{ Code = $gitExit; Lines = $lines }
}

function Hide-RemoteCredentials([string]$RemoteUrl) {
    $safe = $RemoteUrl.Trim()
    # Hide any credential-bearing userinfo in ordinary HTTP(S)/SSH URLs.
    $safe = [regex]::Replace($safe, '(?i)^([a-z][a-z0-9+.-]*://)[^/]*@', '$1[USERINFO_HIDDEN]@')
    # Hide the user part of scp-like SSH URLs (e.g. git@host:repo).
    $safe = [regex]::Replace($safe, '^([^@/:]+)@([^:]+):', '[USER_HIDDEN]@${2}:')
    # Do not export query or fragment tokens.
    $safe = [regex]::Replace($safe, '[?#].*$', '[QUERY_OR_FRAGMENT_HIDDEN]')
    return $safe
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw ('Project directory missing: ' + $ProjectRoot)
    }
    $toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $outDir = Join-Path $toolDir ('P10BK_CHECK_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + $PID)
    [void](New-Item -ItemType Directory -Path $outDir -ErrorAction Stop)
    $reportFile = Join-Path $outDir 'P10BK_REMOTE_REPORT.txt'
    Add-Report 'P10BK LOCAL GIT REMOTE READ-ONLY AUDIT'
    Add-Report ('time_local=' + (Get-Date).ToString('o'))
    Add-Report ('project=' + $ProjectRoot)
    $script:gitExe = (Get-Command git.exe -ErrorAction Stop).Source

    $root = (Invoke-ProjectGit @('rev-parse', '--show-toplevel')).Lines | Select-Object -First 1
    $actualRoot = (Resolve-Path -LiteralPath $root).ProviderPath -replace '[\\/]+$', ''
    $givenRoot = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath -replace '[\\/]+$', ''
    if ($actualRoot -ine $givenRoot) { throw ('Unexpected Git root: ' + $root) }
    $branch = (Invoke-ProjectGit @('branch', '--show-current')).Lines | Select-Object -First 1
    $head = (Invoke-ProjectGit @('rev-parse', 'HEAD')).Lines | Select-Object -First 1
    $parentLine = (Invoke-ProjectGit @('show', '-s', '--format=%P', 'HEAD')).Lines | Select-Object -First 1
    $master = (Invoke-ProjectGit @('rev-parse', 'refs/heads/master')).Lines | Select-Object -First 1
    Add-Report ('BRANCH=' + $branch)
    Add-Report ('HEAD=' + $head)
    Add-Report ('COMMIT_PARENTS=' + $parentLine)
    Add-Report ('MASTER_HEAD=' + $master)
    if ($branch -cne $expectedBranch -or $head -cne $expectedHead -or $parentLine -cne $expectedParent) {
        throw 'Git branch/HEAD/parent is not the P10BJ-confirmed state. Stop.'
    }

    $paths = @((Invoke-ProjectGit @('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD')).Lines | Where-Object { $_.Length -gt 0 })
    $actualPaths = [string]::Join('|', @($paths | Sort-Object))
    $plannedPaths = [string]::Join('|', @($expectedPaths | Sort-Object))
    if ($actualPaths -cne $plannedPaths) {
        throw 'HEAD changed paths differ from the seven validated source paths.'
    }
    Add-Report 'COMMIT_PATHS=SEVEN_EXPECTED_SOURCE_FILES'

    $status = @((Invoke-ProjectGit @('status', '--porcelain=v1', '--untracked-files=normal')).Lines | Where-Object { $_.Length -gt 0 })
    $staged = 0
    $unstaged = 0
    $untracked = 0
    foreach ($line in $status) {
        if ($line.Length -lt 3) { throw 'Malformed porcelain status; stop.' }
        if ($line.Substring(0, 2) -ceq '??') { $untracked++ }
        else {
            if ($line[0] -ne ' ') { $staged++ }
            if ($line[1] -ne ' ') { $unstaged++ }
        }
    }
    Add-Report ('INDEX_STAGED_COUNT=' + $staged)
    Add-Report ('WORKTREE_UNSTAGED_COUNT=' + $unstaged)
    Add-Report ('UNTRACKED_ENTRY_COUNT=' + $untracked)
    Add-Report 'Unrelated file names are intentionally omitted for privacy.'

    $upstream = Invoke-ProjectGit @('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}') -AllowNonzero
    if ($upstream.Code -eq 0 -and $upstream.Lines.Count -gt 0) {
        Add-Report ('UPSTREAM=' + $upstream.Lines[0])
    } else {
        Add-Report 'UPSTREAM=NONE'
    }

    $remotes = @((Invoke-ProjectGit @('remote')).Lines | Where-Object { $_.Length -gt 0 })
    Add-Report ('REMOTE_COUNT=' + $remotes.Count)
    foreach ($remoteName in $remotes) {
        $fetchUrl = Invoke-ProjectGit @('remote', 'get-url', '--all', $remoteName) -AllowNonzero
        $pushUrl = Invoke-ProjectGit @('remote', 'get-url', '--all', '--push', $remoteName) -AllowNonzero
        Add-Report ('REMOTE_NAME=' + $remoteName)
        if ($fetchUrl.Code -eq 0 -and $fetchUrl.Lines.Count -gt 0) {
            foreach ($url in $fetchUrl.Lines) { Add-Report ('REMOTE_FETCH=' + (Hide-RemoteCredentials $url)) }
        } else { Add-Report 'REMOTE_FETCH=UNAVAILABLE' }
        if ($pushUrl.Code -eq 0 -and $pushUrl.Lines.Count -gt 0) {
            foreach ($url in $pushUrl.Lines) { Add-Report ('REMOTE_PUSH=' + (Hide-RemoteCredentials $url)) }
        } else { Add-Report 'REMOTE_PUSH=UNAVAILABLE' }
    }
    Add-Report 'NETWORK_COMMANDS=NONE'
    Add-Report 'LOCAL_GIT_MUTATIONS=NONE'
    Add-Report 'RESULT=P10BK_REMOTE_AUDIT_OK'
} catch {
    $exitCode = 2
    Add-Report ('RESULT=P10BK_STOPPED: ' + $_.Exception.Message)
} finally {
    if ($reportFile -ne '') {
        try {
            [System.IO.File]::WriteAllLines($reportFile, $log, [System.Text.UTF8Encoding]::new($false))
            Write-Host ('P10BK report: ' + $reportFile) -ForegroundColor Green
        } catch {
            Write-Host ('Could not write P10BK report: ' + $_.Exception.Message) -ForegroundColor Red
            $exitCode = 2
        }
    }
}
exit $exitCode
