param([string]$ProjectRoot = 'G:\ildar\Stage3D07')

# P10BQ: Windows PowerShell 5.1; read-only recovery of tests from an existing P10BP build.
# Never clone, configure, compile, clean, modify Git, run FEM, or touch source files.
$ErrorActionPreference = 'Stop'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$expectedOriginal = 'G:\ildar\Stage3D07'
$p10bpRoot = 'G:\ildar\P10BP_ATTEST_20261119_173658_19404'
$expectedCompiler = 'C:\mingw64\bin\g++.exe'
$expectedFirstExeSha256 = '02f14785ebc5dbe841dbec8b836b163858ff0bcbe311a53eec3dc24bb1da4721'
$targets = @(
    'stage3d10v_analytic_shape_unit',
    'stage3d10y_analytic_shell_unit',
    'stage3d10be_temporal_unit',
    'stage3d10be_temporal_polar_audit'
)
$markers = @(
    'P10V_ANALYTIC_SHAPE_UNIT_OK',
    'P10Y_ANALYTIC_SHELL_UNIT_OK',
    'P10BE_TEMPORAL_UNIT_OK',
    'P10BE_TEMPORAL_BINS_SELFTEST_OK'
)
$report = New-Object 'System.Collections.Generic.List[string]'
$resultCode = 0
$outputRoot = ''
$logsRoot = ''
$reportFile = ''
$git = ''
$resolvedOriginal = ''
$headBefore = ''
$statusBefore = ''

function Add-Report([string]$Message) {
    [void]$script:report.Add($Message)
    Write-Host $Message
}

function Invoke-Native([string]$Exe, [string[]]$Arguments, [string]$LogFile = '') {
    # PS 5.1: execute native EXE directly and read LASTEXITCODE immediately.
    # Do not use Start-Process.ExitCode (was blank in P10BP on this PC).
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $Exe @Arguments 2>&1
        $nativeExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedPreference
    }
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($LogFile -ne '') {
        [System.IO.File]::WriteAllLines($LogFile, [string[]]$lines, [System.Text.UTF8Encoding]::new($false))
    }
    return [pscustomobject]@{ Exit = $nativeExit; Lines = $lines }
}

function Require-Ok($Response, [string]$What) {
    if ($null -eq $Response.Exit -or $Response.Exit -ne 0) {
        throw ($What + ' returned exit=' + [string]$Response.Exit)
    }
}

function Get-SafeStatus([string]$GitExe, [string]$Root) {
    $reply = Invoke-Native $GitExe @('-C', $Root, 'status', '--porcelain=v1', '--untracked-files=normal')
    Require-Ok $reply 'git status'
    $staged = 0; $unstaged = 0; $untracked = 0
    foreach ($line in $reply.Lines) {
        if ($line.Length -lt 2) { continue }
        if ($line.Substring(0, 2) -ceq '??') { $untracked++ }
        else {
            if ($line[0] -ne ' ') { $staged++ }
            if ($line[1] -ne ' ') { $unstaged++ }
        }
    }
    return ('{0}/{1}/{2}' -f $staged, $unstaged, $untracked)
}

function Verify-Checkout([string]$GitExe, [string]$Source, [string]$Phase) {
    $head = Invoke-Native $GitExe @('-C', $Source, 'rev-parse', 'HEAD')
    Require-Ok $head 'isolated source HEAD'
    if ($head.Lines.Count -ne 1 -or $head.Lines[0] -cne $expectedHead) {
        throw ('Isolated P10BP source SHA mismatch: ' + $Phase)
    }
    $dirty = Invoke-Native $GitExe @('-C', $Source, 'status', '--porcelain=v1', '--untracked-files=normal')
    Require-Ok $dirty 'isolated source status'
    if (@($dirty.Lines | Where-Object { $_ -ne '' }).Count -ne 0) {
        throw ('Isolated P10BP source is dirty: ' + $Phase)
    }
    Add-Report ('ISOLATED_SOURCE_' + $Phase + '_SHA=' + $expectedHead)
    Add-Report ('ISOLATED_SOURCE_' + $Phase + '_CLEAN=YES')
}

function Get-Cache([string]$File, [string]$Key) {
    $match = Select-String -LiteralPath $File -Pattern ('^' + [regex]::Escape($Key) + ':[^=]*=(.*)$') |
        Select-Object -First 1
    if ($null -eq $match) { return '' }
    return [string]$match.Matches[0].Groups[1].Value.Trim()
}

function Normalize-Path([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path.Replace('/', '\')).TrimEnd('\')
}

try {
    $resolvedOriginal = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).ProviderPath.TrimEnd('\')
    if ($resolvedOriginal -ine $expectedOriginal) { throw 'Unexpected original project location.' }
    $parent = Split-Path -Parent $resolvedOriginal
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outputRoot = Join-Path $parent ('P10BQ_TESTS_' + $stamp + '_' + $PID)
    if (Test-Path -LiteralPath $outputRoot) { throw 'P10BQ output folder already exists.' }
    $logsRoot = Join-Path $outputRoot 'logs'
    [void](New-Item -ItemType Directory -Path $outputRoot)
    [void](New-Item -ItemType Directory -Path $logsRoot)
    $reportFile = Join-Path $outputRoot 'P10BQ_RESULT.txt'
    Add-Report 'P10BQ FOUR EXISTING WINDOWS TESTS (NO CLONE, BUILD OR FEM)'
    Add-Report 'TOOL_REVISION=P10BQ_R1_DIRECT_NATIVE_LASTEXITCODE'
    Add-Report ('DATE_LOCAL=' + (Get-Date).ToString('o'))
    Add-Report ('OUTPUT_ROOT=' + $outputRoot)
    Add-Report ('EXPECTED_SHA=' + $expectedHead)
    Add-Report ('REUSED_P10BP_ROOT=' + $p10bpRoot)

    $git = (Get-Command git.exe -ErrorAction Stop).Source
    $originalHead = Invoke-Native $git @('-C', $resolvedOriginal, 'rev-parse', 'HEAD')
    Require-Ok $originalHead 'original HEAD'
    if ($originalHead.Lines.Count -ne 1) { throw 'Unexpected original HEAD output.' }
    $headBefore = $originalHead.Lines[0]
    $statusBefore = Get-SafeStatus $git $resolvedOriginal
    Add-Report ('ORIGINAL_HEAD_BEFORE=' + $headBefore)
    Add-Report ('ORIGINAL_STATUS_BEFORE=' + $statusBefore)
    if ($headBefore -cne $expectedHead) { throw 'Original HEAD differs from P10BP expected SHA. Stop.' }

    $sourceRoot = Join-Path $p10bpRoot 'source'
    $buildRoot = Join-Path $p10bpRoot 'build'
    if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) { throw 'Original P10BP isolated SOURCE missing. No rebuild.' }
    if (-not (Test-Path -LiteralPath $buildRoot -PathType Container)) { throw 'Original P10BP isolated BUILD missing. No rebuild.' }
    if ((Normalize-Path $sourceRoot) -ieq (Normalize-Path $resolvedOriginal)) { throw 'Source roots overlap.' }
    Verify-Checkout $git $sourceRoot 'BEFORE_TESTS'

    $inputReport = Join-Path $p10bpRoot 'P10BP_RESULT.txt'
    if (-not (Test-Path -LiteralPath $inputReport -PathType Leaf)) { throw 'P10BP_RESULT.txt missing.' }
    $inputText = [System.IO.File]::ReadAllText($inputReport)
    foreach ($required in @('EXPECTED_SHA=' + $expectedHead, 'SOURCE_BEFORE_BUILD_CLEAN=YES',
        'CONFIGURE_EXIT=0', 'BUILD_EXIT=0', 'RESULT=P10BP_STOPPED: Selftest failed: stage3d10v_analytic_shape_unit')) {
        if (-not $inputText.Contains($required)) { throw ('P10BP report does not confirm: ' + $required) }
    }
    $inputReportHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputReport).Hash.ToLowerInvariant()
    Add-Report ('REUSED_P10BP_RESULT_SHA256=' + $inputReportHash)

    $cacheFile = Join-Path $buildRoot 'CMakeCache.txt'
    if (-not (Test-Path -LiteralPath $cacheFile -PathType Leaf)) { throw 'P10BP build CMakeCache.txt missing.' }
    $generator = Get-Cache $cacheFile 'CMAKE_GENERATOR'
    $type = Get-Cache $cacheFile 'CMAKE_BUILD_TYPE'
    $compiler = Get-Cache $cacheFile 'CMAKE_CXX_COMPILER'
    $homeDirectory = Get-Cache $cacheFile 'CMAKE_HOME_DIRECTORY'
    $openmp = Get-Cache $cacheFile 'STAGE3D06P_OPENMP'
    if ($generator -cne 'MinGW Makefiles') { throw 'P10BP build generator mismatch.' }
    if ($type -cne 'Release') { throw 'P10BP build type mismatch.' }
    if ((Normalize-Path $compiler) -ine (Normalize-Path $expectedCompiler)) { throw 'P10BP compiler mismatch.' }
    if ((Normalize-Path $homeDirectory) -ine (Normalize-Path $sourceRoot)) { throw 'P10BP CMake source directory mismatch.' }
    if ($openmp -cne 'ON') { throw 'P10BP OpenMP setting mismatch.' }
    Add-Report 'P10BP_CACHE_VERIFIED=MinGW Makefiles;Release;GNU13.1.0_EXPECTED_PATH;OPENMP_ON'
    $env:PATH = (Split-Path -Parent $expectedCompiler) + ';' + $env:PATH

    $exePaths = @()
    for ($i = 0; $i -lt $targets.Count; $i++) {
        $exe = Join-Path $buildRoot ($targets[$i] + '.exe')
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw ('Existing compiled EXE missing: ' + $targets[$i]) }
        $sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
        Add-Report ('EXE_SHA256_' + $targets[$i] + '=' + $sha)
        if ($i -eq 0 -and $sha -cne $expectedFirstExeSha256) {
            throw 'P10V EXE SHA differs from primary P10BP evidence; no tests run.'
        }
        $exePaths += $exe
    }
    Add-Report 'PREFLIGHT=OK_FOUR_EXISTING_BINARIES_AND_ISOLATED_SOURCE'
    Write-Host ''
    Write-Host 'No clone, build, FEM, Git write, or deletion. Existing four EXEs only.' -ForegroundColor Yellow
    Write-Host 'Expected time 1-3 min; memory <1 GiB (estimates, not measurements).' -ForegroundColor Yellow
    Write-Host 'Type TEST P10BQ to run four tests. Enter alone makes only a dry-run report.' -ForegroundColor Yellow
    $confirmation = Read-Host 'Confirmation'
    if ($confirmation -cne 'TEST P10BQ') {
        Add-Report 'RESULT=P10BQ_DRY_RUN_ONLY_NO_TESTS'
    } else {
        Add-Report 'CONFIRMATION=TEST P10BQ'
        for ($i = 0; $i -lt $targets.Count; $i++) {
            $argsForTest = @()
            if ($targets[$i] -ceq 'stage3d10be_temporal_polar_audit') { $argsForTest = @('--selftest') }
            $target = $targets[$i]
            Add-Report ('TEST_START=' + $target + ' ARGS=' + [string]::Join(' ', $argsForTest))
            $log = Join-Path $logsRoot ($target + '_combined.txt')
            $result = Invoke-Native $exePaths[$i] $argsForTest $log
            Add-Report ('TEST_EXIT_' + $target + '=' + [string]$result.Exit)
            if ($null -eq $result.Exit -or $result.Exit -ne 0) { throw ('Native process exit is not 0: ' + $target) }
            $exactMarkers = @($result.Lines | Where-Object { $_.Trim() -ceq $markers[$i] })
            if ($exactMarkers.Count -ne 1) { throw ('Expected one exact marker not found: ' + $markers[$i]) }
            Add-Report ('TEST_MARKER_' + $target + '=' + $markers[$i])
            Add-Report ('TEST_LOG_SHA256_' + $target + '=' + (Get-FileHash -Algorithm SHA256 -LiteralPath $log).Hash.ToLowerInvariant())
        }
        Verify-Checkout $git $sourceRoot 'AFTER_TESTS'
        Add-Report 'TESTS_PASSED=4/4'
        Add-Report 'RESULT=P10BQ_FOUR_FRESH_WINDOWS_TESTS_OK'
    }
} catch {
    $resultCode = 2
    Add-Report ('RESULT=P10BQ_STOPPED: ' + $_.Exception.Message)
    Add-Report 'Do not delete files or rerun blindly. Send P10BQ_EVIDENCE.zip for diagnosis.'
} finally {
    if ($reportFile -ne '') {
        try {
            if ($git -ne '' -and $headBefore -ne '') {
                try {
                    $after = Invoke-Native $git @('-C', $resolvedOriginal, 'rev-parse', 'HEAD')
                    Require-Ok $after 'original final HEAD'
                    $statusAfter = Get-SafeStatus $git $resolvedOriginal
                    Add-Report ('ORIGINAL_HEAD_AFTER=' + $after.Lines[0])
                    Add-Report ('ORIGINAL_STATUS_AFTER=' + $statusAfter)
                    if ($after.Lines[0] -cne $headBefore -or $statusAfter -cne $statusBefore) {
                        Add-Report 'ORIGINAL_STATE_CHANGED_DURING_RUN=YES_CHECK_EXTERNAL_ACTIVITY'
                        $resultCode = 2
                    } else { Add-Report 'ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_CHECK' }
                } catch { Add-Report 'ORIGINAL_FINAL_READ_FAILED=YES'; $resultCode = 2 }
            }
            [System.IO.File]::WriteAllLines($reportFile, [string[]]$report, [System.Text.UTF8Encoding]::new($false))
            $items = @($reportFile)
            if (Test-Path -LiteralPath $logsRoot -PathType Container) {
                $items += @(Get-ChildItem -LiteralPath $logsRoot -File | Sort-Object Name | ForEach-Object { $_.FullName })
            }
            $evidenceZip = Join-Path $outputRoot 'P10BQ_EVIDENCE.zip'
            Compress-Archive -LiteralPath $items -DestinationPath $evidenceZip -ErrorAction Stop
            Write-Host ('P10BQ report: ' + $reportFile) -ForegroundColor Green
            Write-Host ('P10BQ evidence ZIP: ' + $evidenceZip) -ForegroundColor Green
        } catch {
            Write-Host ('Could not package P10BQ evidence: ' + $_.Exception.Message) -ForegroundColor Red
            $resultCode = 2
        }
    }
}
exit $resultCode
