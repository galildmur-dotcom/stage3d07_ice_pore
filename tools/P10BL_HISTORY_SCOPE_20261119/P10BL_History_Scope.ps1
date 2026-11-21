param(
    [string]$ProjectRoot = 'G:\ildar\Stage3D07'
)

# Windows PowerShell 5.1, ASCII only, read-only local history audit.
# GitHub does not currently recognize parent c0498f6... . A regular push
# of child 90fd255... may transfer many ancestors and their historical blobs.
$ErrorActionPreference = 'Stop'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$expectedParent = 'c0498f6dc98628b62eff996a76844297c7a35094'
$expectedBranch = 'research/p10bi-local-seven-sources-20261119'
$expectedRemote = 'https://github.com/galildmur-dotcom/stage3d07_ice_pore.git'
$maxObjects = 100000
$log = New-Object 'System.Collections.Generic.List[string]'
$reportFile = ''
$resultCode = 0

function Add-Report([string]$Line) {
    [void]$script:log.Add($Line)
    Write-Host $Line
}

function Invoke-ProjectGit([string[]]$Arguments, [switch]$AllowNonzero) {
    $saved = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $script:gitExe -C $ProjectRoot @Arguments 2>&1
        $gitExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $saved }
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($gitExit -ne 0 -and -not $AllowNonzero) {
        # Never echo full Git stderr (it could contain remote credentials).
        throw ('Read-only Git command failed, exit=' + $gitExit + ', verb=' + $Arguments[0])
    }
    return [pscustomobject]@{ Code = $gitExit; Lines = $lines }
}

function Invoke-ObjectSizes([string[]]$Ids) {
    $saved = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = @($Ids | & $script:gitExe -C $ProjectRoot 'cat-file' '--batch-check=%(objectname) %(objecttype) %(objectsize)' 2>&1)
        $gitExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $saved }
    if ($gitExit -ne 0) { throw ('git cat-file batch-check failed, exit=' + $gitExit) }
    return @($raw | ForEach-Object { [string]$_ })
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw ('Project not found: ' + $ProjectRoot)
    }
    $toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $outDir = Join-Path $toolDir ('P10BL_CHECK_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + $PID)
    [void](New-Item -ItemType Directory -Path $outDir -ErrorAction Stop)
    $reportFile = Join-Path $outDir 'P10BL_HISTORY_SCOPE.txt'
    Add-Report 'P10BL READ-ONLY HISTORY SCOPE BEFORE GITHUB PUSH'
    Add-Report ('time_local=' + (Get-Date).ToString('o'))
    Add-Report ('project=' + $ProjectRoot)
    $script:gitExe = (Get-Command git.exe -ErrorAction Stop).Source

    $root = (Invoke-ProjectGit @('rev-parse', '--show-toplevel')).Lines | Select-Object -First 1
    $actualRoot = (Resolve-Path -LiteralPath $root).ProviderPath -replace '[\\/]+$', ''
    $givenRoot = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath -replace '[\\/]+$', ''
    if ($actualRoot -ine $givenRoot) { throw ('Unexpected Git root: ' + $root) }
    $head = (Invoke-ProjectGit @('rev-parse', 'HEAD')).Lines | Select-Object -First 1
    $branch = (Invoke-ProjectGit @('branch', '--show-current')).Lines | Select-Object -First 1
    $parents = (Invoke-ProjectGit @('show', '-s', '--format=%P', 'HEAD')).Lines | Select-Object -First 1
    Add-Report ('HEAD=' + $head)
    Add-Report ('BRANCH=' + $branch)
    Add-Report ('COMMIT_PARENTS=' + $parents)
    if ($head -cne $expectedHead -or $branch -cne $expectedBranch -or $parents -cne $expectedParent) {
        throw 'Current Git branch/HEAD/parent differs from P10BK. Stop.'
    }
    $fetch = Invoke-ProjectGit @('remote', 'get-url', 'origin')
    $push = Invoke-ProjectGit @('remote', 'get-url', '--push', 'origin')
    if ($fetch.Lines.Count -ne 1 -or $push.Lines.Count -ne 1 -or
        $fetch.Lines[0] -cne $expectedRemote -or $push.Lines[0] -cne $expectedRemote) {
        throw 'Git remote URL changed or is not the expected GitHub repository. Stop.'
    }
    Add-Report 'REMOTE=origin (verified GitHub URL; credentials not reported)'

    $status = @((Invoke-ProjectGit @('status', '--porcelain=v1', '--untracked-files=normal')).Lines | Where-Object { $_.Length -gt 0 })
    $staged = 0
    $unstaged = 0
    $untracked = 0
    foreach ($line in $status) {
        if ($line.Length -lt 3) { throw 'Malformed Git status line.' }
        if ($line.Substring(0, 2) -ceq '??') { $untracked++ }
        else {
            if ($line[0] -ne ' ') { $staged++ }
            if ($line[1] -ne ' ') { $unstaged++ }
        }
    }
    Add-Report ('STAGED_COUNT=' + $staged)
    Add-Report ('UNSTAGED_COUNT=' + $unstaged)
    Add-Report ('UNTRACKED_COUNT=' + $untracked)
    if ($staged -ne 0) { throw 'Staged changes appeared since P10BK; stop.' }

    $commitCount = (Invoke-ProjectGit @('rev-list', '--count', 'HEAD')).Lines | Select-Object -First 1
    Add-Report ('REACHABLE_COMMIT_COUNT=' + $commitCount)
    $objects = @((Invoke-ProjectGit @('rev-list', '--objects', 'HEAD')).Lines | Where-Object { $_.Length -gt 0 })
    Add-Report ('REACHABLE_OBJECT_COUNT=' + $objects.Count)

    $ids = New-Object 'System.Collections.Generic.List[string]'
    $top = @{}
    $riskFlagCount = 0
    foreach ($line in $objects) {
        if ($line -notmatch '^[0-9a-fA-F]{40}($| )') { throw 'Unexpected Git object listing; stop.' }
        [void]$ids.Add($line.Substring(0, 40))
        if ($line.Length -gt 41) {
            $path = $line.Substring(41).Replace('\', '/')
            $group = ($path -split '/')[0]
            if ($group -notmatch '^[A-Za-z0-9._-]+$') { $group = '[OTHER_OR_NONASCII]' }
            if (-not $top.ContainsKey($group)) { $top[$group] = 0 }
            $top[$group]++
            if ($path -match '(?i)(^|/)(\.env|id_rsa|id_ed25519|[^/]*\.(pem|pfx|key|kdbx)|[^/]*secret[^/]*|[^/]*password[^/]*|[^/]*token[^/]*)(/|\.|$)') {
                $riskFlagCount++
            }
        }
    }
    Add-Report ('SENSITIVE_NAME_PATTERNS=' + $riskFlagCount)
    Add-Report 'Historical file paths are not exported; only top-level group counts are shown.'
    foreach ($group in @($top.Keys | Sort-Object)) {
        Add-Report ('PATH_GROUP=' + $group + ' COUNT=' + $top[$group])
    }

    if ($objects.Count -gt $maxObjects) {
        Add-Report ('OBJECT_SIZE_SCAN=SKIPPED_LIMIT_' + $maxObjects)
        Add-Report 'RESULT=P10BL_HISTORY_LARGE_REQUIRES_REVIEW'
    } else {
        $sizeLines = @(Invoke-ObjectSizes -Ids ($ids.ToArray()))
        if ($sizeLines.Count -ne $objects.Count) { throw 'Git object size scan did not return the full object count.' }
        $totalBlob = [Int64]0
        $maxBlob = [Int64]0
        $blobCount = 0
        $commitObjects = 0
        $treeObjects = 0
        $tagObjects = 0
        foreach ($line in $sizeLines) {
            if ($line -match '^([0-9a-fA-F]{40}) (blob|tree|commit|tag) ([0-9]+)$') {
                $type = $matches[2]
                $size = [Int64]::Parse($matches[3])
            } else {
                throw 'Unexpected git cat-file object size record.'
            }
            if ($type -ceq 'blob') {
                $blobCount++
                $totalBlob += $size
                if ($size -gt $maxBlob) { $maxBlob = $size }
            } elseif ($type -ceq 'commit') { $commitObjects++ }
            elseif ($type -ceq 'tree') { $treeObjects++ }
            elseif ($type -ceq 'tag') { $tagObjects++ }
        }
        Add-Report ('REACHABLE_BLOB_COUNT=' + $blobCount)
        Add-Report ('REACHABLE_COMMIT_OBJECTS=' + $commitObjects)
        Add-Report ('REACHABLE_TREE_OBJECTS=' + $treeObjects)
        Add-Report ('REACHABLE_TAG_OBJECTS=' + $tagObjects)
        Add-Report ('REACHABLE_TOTAL_BLOB_BYTES_UNCOMPRESSED=' + $totalBlob)
        Add-Report ('REACHABLE_LARGEST_BLOB_BYTES=' + $maxBlob)
        Add-Report 'Note: these are reachable-history upper-bound metrics, not the actual push pack size.'
        Add-Report 'RESULT=P10BL_HISTORY_SCOPE_OK_NO_PUSH'
    }
    Add-Report 'NO_NETWORK_NO_PUSH_NO_GIT_MUTATION'
} catch {
    $resultCode = 2
    Add-Report ('RESULT=P10BL_STOPPED: ' + $_.Exception.Message)
    Add-Report 'No push was attempted. Share this report for analysis.'
} finally {
    if ($reportFile -ne '') {
        try {
            [System.IO.File]::WriteAllLines($reportFile, $log, [System.Text.UTF8Encoding]::new($false))
            Write-Host ('P10BL report: ' + $reportFile) -ForegroundColor Green
        } catch {
            Write-Host ('Could not write report: ' + $_.Exception.Message) -ForegroundColor Red
            $resultCode = 2
        }
    }
}
exit $resultCode
