param([string]$ProjectRoot = 'G:\ildar\Stage3D07')

# Windows PowerShell 5.1 / CMake / Git. ASCII-only script for robust Win encoding.
# Only reads the original project and its existing Qt Creator CMakeCache.
# Clone, build and reports are created in a NEW SIBLING directory.
# The script never runs FEM and never changes original Git refs or working files.
$ErrorActionPreference = 'Stop'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$branch = 'research/p10bi-local-seven-sources-20261119'
$remoteUrl = 'https://github.com/galildmur-dotcom/stage3d07_ice_pore.git'
$expectedOriginalRoot = 'G:\ildar\Stage3D07'
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
$headBefore = ''
$statusBefore = ''

function Add-Report([string]$Message) {
    [void]$script:report.Add($Message)
    Write-Host $Message
}

function Invoke-Native([string]$Exe, [string[]]$Arguments, [string]$LogFile = '') {
    # Native stderr (including routine Git messages) is not a terminating PS 5.1 error.
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $Exe @Arguments 2>&1
        $commandExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedPreference
    }
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($LogFile -ne '') {
        [System.IO.File]::WriteAllLines($LogFile, [string[]]$lines, [System.Text.UTF8Encoding]::new($false))
    }
    return [pscustomobject]@{ Exit = $commandExit; Lines = $lines }
}

function Require-Ok($Response, [string]$What) {
    if ($Response.Exit -ne 0) { throw ($What + ' returned exit=' + $Response.Exit) }
}

function Get-Cache([string]$File, [string]$Key) {
    $match = Select-String -LiteralPath $File -Pattern ('^' + [regex]::Escape($Key) + ':[^=]*=(.*)$') |
        Select-Object -First 1
    if ($null -eq $match) { return '' }
    return [string]$match.Matches[0].Groups[1].Value.Trim()
}

function Find-CMake {
    $found = Get-Command cmake.exe -ErrorAction SilentlyContinue
    if ($null -ne $found -and (Test-Path -LiteralPath $found.Source -PathType Leaf)) {
        return $found.Source
    }
    $candidates = @(
        'C:\Program Files\CMake\bin\cmake.exe',
        'C:\Qt\Tools\CMake_64\bin\cmake.exe',
        'C:\Qt\Tools\CMake\bin\cmake.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw 'cmake.exe not found. Please send the P10BN result; do not modify the old build.'
}

function Get-SafeStatus($GitExe, [string]$Root) {
    $s = Invoke-Native $GitExe @('-C', $Root, 'status', '--porcelain=v1', '--untracked-files=normal')
    Require-Ok $s 'git status'
    $staged = 0; $unstaged = 0; $untracked = 0
    foreach ($line in $s.Lines) {
        if ($line.Length -lt 2) { continue }
        if ($line.Substring(0, 2) -ceq '??') { $untracked++ }
        else {
            if ($line[0] -ne ' ') { $staged++ }
            if ($line[1] -ne ' ') { $unstaged++ }
        }
    }
    return [pscustomobject]@{ Staged = $staged; Unstaged = $unstaged; Untracked = $untracked }
}

function Verify-Checkout($GitExe, [string]$Root, [string]$Phase) {
    $commit = Invoke-Native $GitExe @('-C', $Root, 'rev-parse', 'HEAD')
    Require-Ok $commit 'git rev-parse HEAD'
    if ($commit.Lines.Count -ne 1 -or $commit.Lines[0] -cne $expectedHead) {
        throw ('P10BN source SHA mismatch at ' + $Phase)
    }
    $dirty = Invoke-Native $GitExe @('-C', $Root, 'status', '--porcelain=v1', '--untracked-files=normal')
    Require-Ok $dirty 'git status in isolated source'
    if (@($dirty.Lines | Where-Object { $_ -ne '' }).Count -ne 0) {
        throw ('Isolated source is not clean at ' + $Phase + '; no cleanup attempted.')
    }
    Add-Report ('SOURCE_' + $Phase + '_SHA=' + $expectedHead)
    Add-Report ('SOURCE_' + $Phase + '_CLEAN=YES')
}

function Run-Selftest([string]$Exe, [string]$Target, [string]$Marker, [string]$WorkDir) {
    $stdout = Join-Path $logsRoot ($Target + '_stdout.txt')
    $stderr = Join-Path $logsRoot ($Target + '_stderr.txt')
    $arguments = @()
    if ($Target -ceq 'stage3d10be_temporal_polar_audit') { $arguments = @('--selftest') }
    Add-Report ('TEST_START=' + $Target + ' ARGS=' + [string]::Join(' ', $arguments))
    $options = @{
        FilePath = $Exe
        WorkingDirectory = $WorkDir
        RedirectStandardOutput = $stdout
        RedirectStandardError = $stderr
        NoNewWindow = $true
        PassThru = $true
    }
    if ($arguments.Count -gt 0) { $options.ArgumentList = $arguments }
    $process = Start-Process @options
    if (-not $process.WaitForExit(120000)) {
        try { $process.Kill() } catch {}
        throw ('Short selftest timeout (120 s): ' + $Target)
    }
    $exitCode = $process.ExitCode
    $textOutput = ''
    if (Test-Path -LiteralPath $stdout) {
        $textOutput = [System.IO.File]::ReadAllText($stdout)
    }
    Add-Report ('TEST_EXIT_' + $Target + '=' + $exitCode)
    if ($exitCode -ne 0) { throw ('Selftest failed: ' + $Target) }
    if (-not $textOutput.Contains($Marker)) { throw ('Required marker missing: ' + $Marker) }
    Add-Report ('TEST_MARKER_' + $Target + '=' + $Marker)
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw 'Original project directory was not found.'
    }
    $resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath.TrimEnd('\')
    if ($resolvedRoot -ine $expectedOriginalRoot) { throw 'Unexpected original project path. Stop.' }

    # All outputs are outside the original repository, in a newly named sibling.
    $parent = Split-Path -Parent $resolvedRoot
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outputRoot = Join-Path $parent ('P10BN_ATTEST_' + $stamp + '_' + $PID)
    if (Test-Path -LiteralPath $outputRoot) { throw 'Unique output folder already exists. Stop.' }
    $logsRoot = Join-Path $outputRoot 'logs'
    [void](New-Item -ItemType Directory -Path $outputRoot)
    [void](New-Item -ItemType Directory -Path $logsRoot)
    $reportFile = Join-Path $outputRoot 'P10BN_RESULT.txt'
    Add-Report 'P10BN ISOLATED CLEAN WINDOWS BUILD (NO FEM)'
    Add-Report ('DATE_LOCAL=' + (Get-Date).ToString('o'))
    Add-Report ('EXPECTED_SHA=' + $expectedHead)
    Add-Report ('TARGET_BRANCH=' + $branch)
    Add-Report ('OUTPUT_ROOT=' + $outputRoot)

    $git = (Get-Command git.exe -ErrorAction Stop).Source
    $top = Invoke-Native $git @('-C', $resolvedRoot, 'rev-parse', '--show-toplevel')
    Require-Ok $top 'git root query'
    if ($top.Lines.Count -ne 1 -or
        (Resolve-Path -LiteralPath $top.Lines[0]).ProviderPath.TrimEnd('\') -ine $resolvedRoot) {
        throw 'The original folder is not the expected Git repository root.'
    }
    $originalHead = Invoke-Native $git @('-C', $resolvedRoot, 'rev-parse', 'HEAD')
    Require-Ok $originalHead 'original HEAD query'
    $headBefore = $originalHead.Lines[0]
    Add-Report ('ORIGINAL_HEAD_BEFORE=' + $originalHead.Lines[0])
    $originalStatus = Get-SafeStatus $git $resolvedRoot
    $statusBefore = $originalStatus.Staged + '/' + $originalStatus.Unstaged + '/' + $originalStatus.Untracked
    Add-Report ('ORIGINAL_STATUS_BEFORE=' + $statusBefore)

    $oldCache = Join-Path $resolvedRoot 'build\Desktop_MinGW_Release\CMakeCache.txt'
    if (-not (Test-Path -LiteralPath $oldCache -PathType Leaf)) {
        throw 'Existing Qt Creator Release CMakeCache.txt not found; need toolchain paths from researcher.'
    }
    $oldSource = Get-Cache $oldCache 'CMAKE_HOME_DIRECTORY'
    if ($oldSource -ne '' -and ([System.IO.Path]::GetFullPath($oldSource).TrimEnd('\') -ine $resolvedRoot)) {
        throw 'Old CMakeCache belongs to another source path. Stop.'
    }
    $generator = Get-Cache $oldCache 'CMAKE_GENERATOR'
    $oldBuildType = Get-Cache $oldCache 'CMAKE_BUILD_TYPE'
    $compiler = Get-Cache $oldCache 'CMAKE_CXX_COMPILER'
    $makeProgram = Get-Cache $oldCache 'CMAKE_MAKE_PROGRAM'
    $openmp = Get-Cache $oldCache 'STAGE3D06P_OPENMP'
    if ($generator -cne 'Ninja' -and $generator -cne 'MinGW Makefiles') {
        throw ('Unsupported existing generator: ' + $generator)
    }
    if ($oldBuildType -cne 'Release') { throw 'Existing Qt Creator kit was not configured as Release.' }
    if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) { throw 'Cached MinGW compiler path does not exist.' }
    if (-not (Test-Path -LiteralPath $makeProgram -PathType Leaf)) { throw 'Cached Ninja/MinGW make path does not exist.' }
    if ($openmp -cne 'OFF' -and $openmp -cne 'ON') { $openmp = 'ON' }
    $cmake = Find-CMake
    $compilerBin = Split-Path -Parent $compiler
    $makeBin = Split-Path -Parent $makeProgram
    $env:PATH = $compilerBin + ';' + $makeBin + ';' + $env:PATH
    $cmakeVersion = Invoke-Native $cmake @('--version')
    Require-Ok $cmakeVersion 'cmake --version'
    $compilerVersion = Invoke-Native $compiler @('--version')
    Require-Ok $compilerVersion 'g++ --version'
    Add-Report ('GENERATOR=' + $generator)
    Add-Report ('BUILD_TYPE=' + $oldBuildType)
    Add-Report ('COMPILER=' + $compiler)
    Add-Report ('MAKE_PROGRAM=' + $makeProgram)
    Add-Report ('OPENMP=' + $openmp)
    Add-Report ('CMAKE_VERSION=' + $cmakeVersion.Lines[0])
    Add-Report ('COMPILER_VERSION=' + $compilerVersion.Lines[0])
    Add-Report 'PREFLIGHT=OK_READ_ONLY_ORIGINAL'

    Write-Host ''
    Write-Host 'The original Stage3D07 folder and old build will NOT be changed.' -ForegroundColor Yellow
    Write-Host ('A new GitHub clone + Release build will be created under ' + $outputRoot) -ForegroundColor Yellow
    Write-Host 'Estimated duration 5-20 min, RAM about 2-8 GiB (not measured); no FEM.' -ForegroundColor Yellow
    Write-Host 'Type BUILD P10BN to approve, or Enter to stop after preflight.' -ForegroundColor Yellow
    $answer = Read-Host 'Confirmation'
    if ($answer -cne 'BUILD P10BN') {
        Add-Report 'RESULT=DRY_RUN_ONLY_NO_CLONE_NO_BUILD'
    } else {
        Add-Report 'CONFIRMATION=BUILD P10BN'
        $sourceRoot = Join-Path $outputRoot 'source'
        $buildRoot = Join-Path $outputRoot 'build'
        $env:GIT_TERMINAL_PROMPT = '0'
        Add-Report 'STEP=CLONE_FROM_PUBLIC_GITHUB'
        $clone = Invoke-Native $git @('clone', '--single-branch', '--no-checkout', '--branch', $branch, $remoteUrl, $sourceRoot)
        Require-Ok $clone 'isolated git clone'
        $remoteHead = Invoke-Native $git @('-C', $sourceRoot, 'rev-parse', ('refs/remotes/origin/' + $branch))
        Require-Ok $remoteHead 'remote branch HEAD in clone'
        if ($remoteHead.Lines.Count -ne 1 -or $remoteHead.Lines[0] -cne $expectedHead) {
            throw 'GitHub remote branch SHA differs from the expected P10BM SHA. Stop.'
        }
        $checkout = Invoke-Native $git @('-C', $sourceRoot, 'checkout', '--detach', $expectedHead)
        Require-Ok $checkout 'git checkout only in isolated clone'
        Verify-Checkout $git $sourceRoot 'BEFORE_BUILD'

        Add-Report 'STEP=CMAKE_CONFIGURE'
        $cmakeArgs = @('-S', $sourceRoot, '-B', $buildRoot, '-G', $generator,
            '-DCMAKE_BUILD_TYPE=Release', ('-DCMAKE_CXX_COMPILER=' + $compiler),
            ('-DCMAKE_MAKE_PROGRAM=' + $makeProgram), ('-DSTAGE3D06P_OPENMP=' + $openmp))
        $config = Invoke-Native $cmake $cmakeArgs (Join-Path $logsRoot 'cmake_configure.txt')
        Add-Report ('CONFIGURE_EXIT=' + $config.Exit)
        Require-Ok $config 'CMake configure'

        Add-Report 'STEP=CMAKE_BUILD_FOUR_TARGETS'
        $buildArgs = @('--build', $buildRoot, '--config', 'Release', '--target') + $targets + @('--parallel', '4')
        $build = Invoke-Native $cmake $buildArgs (Join-Path $logsRoot 'cmake_build.txt')
        Add-Report ('BUILD_EXIT=' + $build.Exit)
        Require-Ok $build 'CMake build'

        for ($i = 0; $i -lt $targets.Count; $i++) {
            $target = $targets[$i]
            $exe = Join-Path $buildRoot ($target + '.exe')
            if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
                throw ('Newly compiled EXE not found: ' + $target)
            }
            $digest = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
            Add-Report ('EXE_SHA256_' + $target + '=' + $digest)
            Run-Selftest $exe $target $markers[$i] $buildRoot
        }
        Verify-Checkout $git $sourceRoot 'AFTER_TESTS'
        Add-Report 'RESULT=P10BN_NEW_WINDOWS_BUILD_AND_FOUR_TESTS_OK'
    }
} catch {
    $resultCode = 2
    # Do not embed raw Git/CMake error output in the summary (could contain secrets).
    Add-Report ('RESULT=P10BN_STOPPED: ' + $_.Exception.Message)
    Add-Report 'Do not delete anything or rerun blindly; send the evidence package for diagnosis.'
} finally {
    if ($reportFile -ne '') {
        try {
            if ($git -ne '' -and $headBefore -ne '') {
                try {
                    $originalAfter = Invoke-Native $git @('-C', $resolvedRoot, 'rev-parse', 'HEAD')
                    Require-Ok $originalAfter 'original final HEAD query'
                    $statusAfterObj = Get-SafeStatus $git $resolvedRoot
                    $statusAfter = $statusAfterObj.Staged + '/' + $statusAfterObj.Unstaged + '/' + $statusAfterObj.Untracked
                    Add-Report ('ORIGINAL_HEAD_AFTER=' + $originalAfter.Lines[0])
                    Add-Report ('ORIGINAL_STATUS_AFTER=' + $statusAfter)
                    if ($originalAfter.Lines[0] -cne $headBefore -or $statusAfter -cne $statusBefore) {
                        Add-Report 'ORIGINAL_STATE_CHANGED_DURING_RUN=YES_REVIEW_EXTERNAL_ACTIVITY'
                        $resultCode = 2
                    } else { Add-Report 'ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_CHECK' }
                } catch { Add-Report 'ORIGINAL_FINAL_READ_FAILED=YES' ; $resultCode = 2 }
            }
            if (Test-Path -LiteralPath $logsRoot -PathType Container) {
                foreach ($logFile in (Get-ChildItem -LiteralPath $logsRoot -File | Sort-Object Name)) {
                    $logHash = (Get-FileHash -LiteralPath $logFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                    Add-Report ('LOG_SHA256_' + $logFile.Name + '=' + $logHash)
                }
            }
            [System.IO.File]::WriteAllLines($reportFile, [string[]]$report, [System.Text.UTF8Encoding]::new($false))
            $evidenceZip = Join-Path $outputRoot 'P10BN_EVIDENCE.zip'
            $items = @($reportFile)
            if (Test-Path -LiteralPath $logsRoot -PathType Container) {
                $items += @(Get-ChildItem -LiteralPath $logsRoot -File | ForEach-Object { $_.FullName })
            }
            Compress-Archive -LiteralPath $items -DestinationPath $evidenceZip -ErrorAction Stop
            Write-Host ('P10BN report: ' + $reportFile) -ForegroundColor Green
            Write-Host ('P10BN evidence ZIP: ' + $evidenceZip) -ForegroundColor Green
        } catch {
            Write-Host ('Could not package P10BN evidence: ' + $_.Exception.Message) -ForegroundColor Red
            $resultCode = 2
        }
    }
}
exit $resultCode
