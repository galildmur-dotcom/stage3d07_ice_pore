# P10BZ R2: Windows PowerShell 5.1, 44 exact SHA source checks, two native units.
# No git clone/pull/switch/reset/clean/stash/commit/push; no FEM or mesh reads.
# G:\ildar\Stage3D07 is used solely for optional-lock-free read-only Git facts.
$ErrorActionPreference = 'Stop'
$expectedOriginal = 'G:\ildar\Stage3D07'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$compiler = 'C:\mingw64\bin\g++.exe'
$make = 'C:\mingw64\bin\mingw32-make.exe'
$cmake = 'C:\Program Files\CMake\bin\cmake.exe'
$git = 'C:\Program Files\Git\cmd\git.exe'
$toolRevision = 'P10BZ_R2_BUNDLED_44_SHA_WINDOWS_MEMORY_FIX_NO_FEM'
$report = New-Object 'System.Collections.Generic.List[string]'
$outputRoot = ''
$initialSnapshot = $null
$resultCode = 2
$safeToolRoot = $false
$env:GIT_OPTIONAL_LOCKS = '0'

function Add-Report([string]$Message) {
    [void]$script:report.Add($Message)
    Write-Host $Message
}

function Invoke-Native([string]$Exe, [string[]]$Arguments, [string]$LogFile = '') {
    # Capture stderr as diagnostics, not automatically as an execution failure.
    # Read $LASTEXITCODE IMMEDIATELY after the native process finishes.
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $Exe @Arguments 2>&1
        $nativeExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($LogFile -ne '') {
        [System.IO.File]::WriteAllLines($LogFile, [string[]]$lines,
            [System.Text.UTF8Encoding]::new($false))
    }
    return [pscustomobject]@{ Exit = $nativeExit; Lines = $lines }
}

function Require-Exit0($Response, [string]$What) {
    if ($null -eq $Response.Exit -or $Response.Exit -ne 0) {
        throw ($What + ' returned native exit=' + [string]$Response.Exit)
    }
}

function Hash-Text([string]$Value) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally { $hasher.Dispose() }
}

function Assert-SHA256([string]$File, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
        throw ('P10BZ_STOP missing source file: ' + [System.IO.Path]::GetFileName($File))
    }
    $actual = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne $Expected.ToLowerInvariant()) {
        throw ('P10BZ_STOP SHA256 mismatch: ' + [System.IO.Path]::GetFileName($File))
    }
}

function Get-OriginalSnapshot {
    $headResult = Invoke-Native $git @('-C', $expectedOriginal, 'rev-parse', 'HEAD')
    Require-Exit0 $headResult 'original Git HEAD'
    if ($headResult.Lines.Count -ne 1) { throw 'P10BZ_STOP ambiguous Git HEAD output' }
    $statusResult = Invoke-Native $git @('-C', $expectedOriginal,
        '-c', 'core.fsmonitor=false', 'status', '--porcelain=v1',
        '--untracked-files=normal')
    Require-Exit0 $statusResult 'original Git status'
    $staged = 0; $unstaged = 0; $untracked = 0
    $statusLines = @($statusResult.Lines | Where-Object { $_.Length -ge 2 })
    foreach ($line in $statusLines) {
        if ($line.Substring(0, 2) -ceq '??') { $untracked++ }
        else {
            if ($line[0] -ne ' ') { $staged++ }
            if ($line[1] -ne ' ') { $unstaged++ }
        }
    }
    $fingerprint = Hash-Text ([string]::Join([Environment]::NewLine, [string[]]$statusLines))
    return [pscustomobject]@{
        Head = [string]$headResult.Lines[0]
        Status = ('{0}/{1}/{2}' -f $staged, $unstaged, $untracked)
        StatusSHA256 = $fingerprint
    }
}

function Check-SourcePackage([string]$Root) {
    $pinned = Join-Path $Root 'source\pinned'
    $bx = Join-Path $Root 'source\p10bx'
    $bw = Join-Path $Root 'source\p10bw'
    $by = Join-Path $Root 'source\p10by'
    $manifest = Join-Path $by 'P10BY_PINNED_SHA256.txt'
    Assert-SHA256 $manifest 'bce45c5757796ecc505ca6e0899de912c4ad4441fb05d007f1d2c41192d2f2ce'
    $rows = @(Get-Content -LiteralPath $manifest -Encoding UTF8 |
        Where-Object { $_ -ne '' -and $_ -notmatch '^#' })
    if ($rows.Count -ne 35) { throw 'P10BZ_STOP source manifest needs 35 original files' }
    $seen = @{}
    foreach ($row in $rows) {
        $parts = @($row.Split('|'))
        if ($parts.Count -ne 2 -or $seen.ContainsKey($parts[0]) -or
            $parts[1] -notmatch '^[0-9a-f]{64}$') {
            throw 'P10BZ_STOP malformed or duplicate pinned manifest row'
        }
        $seen[$parts[0]] = $true
        Assert-SHA256 (Join-Path $pinned $parts[0].Replace('/', '\')) $parts[1]
    }
    # The R1 Windows link STOP found this original, omitted Win32-only TU.
    # Require the exact SHA from historical Git 90fd2559 before compilation.
    Assert-SHA256 (Join-Path $pinned 'src\win_process_memory.cpp') 'c299d890b0f3a04f86974fb664120a36681eef464ffbb617eabc8e57e07a5e09'
    # Each entry uses explicit immutable hashes of the published proposals.
    $components = @(
        [pscustomobject]@{ File='p10bx\src\stage3d10p_partial_audit.cpp'; SHA='57754cfaa031fddb391e6b211a6f083346475611d180676c0c4987926ea54b1b' },
        [pscustomobject]@{ File='p10bx\src\stage3d10w_analytic_adjoint.cpp'; SHA='1d769e559aa561817685b56949bf649e6ceddb89da4cfc294cc18738d6d82df8' },
        [pscustomobject]@{ File='p10bx\stage3d10bx_thermal_step_hook.hpp'; SHA='79b716c389a6a9dd466d65d795ad3a67bda206bdd636eec0fb03962dc3155574' },
        [pscustomobject]@{ File='p10bw\stage3d10bw_thermal_qp_partition.hpp'; SHA='71992ba7e8c0b44d7832c5d8566ef8886517bbd87f953b119271746483f0fa23' },
        [pscustomobject]@{ File='p10bw\P10BW_thermal_qp_native_unit.cpp'; SHA='719a9db9f3c3221acdfc096a88cfbb1cdb81307ba931463f3ff62726e10a03c6' },
        [pscustomobject]@{ File='p10by\P10BY_temporal_thermal_qp_native_unit.cpp'; SHA='c06b7245212d7e6d2e1ded93bf4695245b61e51845d882330c73107fb68825ee' },
        [pscustomobject]@{ File='p10by\P10BY_unitonly_entry.cpp'; SHA='080a27aca4bf9d27ba5c245c2dfdd4730a30f185a25df978a3ee3e9c0dfb8024' },
        [pscustomobject]@{ File='p10by\CMakeLists.txt'; SHA='bbf5f43f17f2c607edf4cb12550058d519fc1668354c7b28d57ef6cfee483239' }
    )
    foreach ($component in $components) {
        Assert-SHA256 (Join-Path (Join-Path $Root 'source') $component.File) $component.SHA
    }
    Add-Report 'P10BZ_BUNDLED_SHA256_OK original=36 proposals=8 total=44'
    return [pscustomobject]@{ Pinned=$pinned; BX=$bx; BW=$bw; BY=$by }
}

function Check-Toolchain {
    foreach ($path in @($compiler, $make, $cmake, $git)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw ('P10BZ_STOP missing expected tool: ' + $path)
        }
    }
    $cxxVersion = Invoke-Native $compiler @('--version')
    Require-Exit0 $cxxVersion 'MinGW compiler --version'
    if (-not (($cxxVersion.Lines -join ' ') -match '13\.1\.0')) {
        throw 'P10BZ_STOP expected GNU 13.1.0 from validated P10BP Kit'
    }
    $cmakeVersion = Invoke-Native $cmake @('--version')
    Require-Exit0 $cmakeVersion 'CMake --version'
    Add-Report ('COMPILER=' + $compiler)
    Add-Report 'COMPILER_GNU_VERSION=13.1.0'
    Add-Report ('CMAKE_VERSION_LINE=' + [string]$cmakeVersion.Lines[0])
    Add-Report ('MAKE_PROGRAM=' + $make)
}

function Check-Test([string]$Target, [string]$Marker, [string]$Extra,
                    [string]$Log, [string]$BuildPath) {
    $exe = Join-Path $BuildPath ($Target + '.exe')
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw ('P10BZ_STOP missing built EXE: ' + $Target)
    }
    $sha = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    Add-Report ('EXE_SHA256_' + $Target + '=' + $sha)
    $run = Invoke-Native -Exe $exe -Arguments @() -LogFile $Log
    Add-Report ('TEST_EXIT_' + $Target + '=' + [string]$run.Exit)
    Require-Exit0 $run ($Target + ' unit')
    $output = $run.Lines -join [Environment]::NewLine
    if ($output -notmatch ('(?m)^' + [regex]::Escape($Marker) + '(?:\s|$)')) {
        throw ('P10BZ_STOP required native marker missing: ' + $Marker)
    }
    if ($Extra -ne '' -and $output -notmatch $Extra) {
        throw ('P10BZ_STOP expected unit counts missing: ' + $Target)
    }
    Add-Report ('TEST_MARKER_' + $Target + '=' + $Marker)
}

try {
    Add-Report 'P10BZ R2 TWO FRESH NATIVE WINDOWS UNIT TESTS, NO FEM'
    Add-Report ('TOOL_REVISION=' + $toolRevision)
    Add-Report ('DATE_LOCAL=' + (Get-Date).ToString('o'))
    $toolRoot = [System.IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
    $projectRoot = [System.IO.Path]::GetFullPath($expectedOriginal).TrimEnd('\')
    if ($toolRoot.Equals($projectRoot, [StringComparison]::OrdinalIgnoreCase) -or
        $toolRoot.StartsWith($projectRoot + '\',
            [StringComparison]::OrdinalIgnoreCase)) {
        throw 'P10BZ_STOP tool extracted inside original project; move it outside G:\ildar\Stage3D07'
    }
    $safeToolRoot = $true
    if (-not (Test-Path -LiteralPath $expectedOriginal -PathType Container)) {
        throw 'P10BZ_STOP original project missing; no build attempted'
    }
    $initialSnapshot = Get-OriginalSnapshot
    Add-Report ('ORIGINAL_HEAD_BEFORE=' + $initialSnapshot.Head)
    Add-Report ('ORIGINAL_STATUS_BEFORE=' + $initialSnapshot.Status)
    Add-Report ('ORIGINAL_STATUS_FINGERPRINT_BEFORE=' + $initialSnapshot.StatusSHA256)
    if ($initialSnapshot.Head -cne $expectedHead) {
        throw 'P10BZ_STOP original HEAD differs from historical exact SHA: do not guess'
    }
    $source = Check-SourcePackage $toolRoot
    Check-Toolchain
    Add-Report 'PREFLIGHT=OK_READ_ONLY_SOURCE_TOOLCHAIN_ORIGINAL'
    Write-Host ''
    Write-Host 'ONLY two native selftests will compile in a NEW folder next to this tool.'
    Write-Host 'No mesh, --preflight, physical FEM, patch, git switch or changes in G:\ildar\Stage3D07.'
    $confirmation = Read-Host 'Type exactly TEST P10BZ to start the isolated build (Enter cancels)'
    if ($confirmation -cne 'TEST P10BZ') {
        Add-Report 'CANCELLED_NO_BUILD_NO_FILES_CREATED'
        $resultCode = 0
        return
    }
    Add-Report 'CONFIRMATION=TEST P10BZ'
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outputRoot = Join-Path $toolRoot ('P10BZ_RESULTS_' + $stamp + '_' + $PID)
    if (Test-Path -LiteralPath $outputRoot) { throw 'P10BZ_STOP output folder already exists' }
    [void](New-Item -ItemType Directory -Path $outputRoot)
    $buildPath = Join-Path $outputRoot 'build'
    Add-Report ('OUTPUT_NAME=' + [System.IO.Path]::GetFileName($outputRoot))
    $previousPath = $env:PATH
    try {
        $env:PATH = 'C:\mingw64\bin;' + $env:PATH
        $arguments = @('-S', $source.BY, '-B', $buildPath, '-G', 'MinGW Makefiles',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_CXX_COMPILER=C:/mingw64/bin/g++.exe',
            '-DCMAKE_MAKE_PROGRAM=C:/mingw64/bin/mingw32-make.exe',
            ('-DP10BY_PINNED_ROOT=' + $source.Pinned),
            ('-DP10BY_P10BX_ROOT=' + $source.BX),
            ('-DP10BY_P10BW_ROOT=' + $source.BW))
        $configured = Invoke-Native $cmake $arguments (Join-Path $outputRoot 'cmake_configure.txt')
        Add-Report ('CMAKE_CONFIGURE_EXIT=' + [string]$configured.Exit)
        Require-Exit0 $configured 'P10BZ CMake configure'
        $configureText = $configured.Lines -join [Environment]::NewLine
        if ($configureText -notmatch 'P10BZ_R2_WINDOWS_MEMORY_SOURCE_SHA256_OK') {
            throw 'P10BZ_STOP expected R2 Win32 source SHA gate missing in CMake configure'
        }
        Add-Report 'CMAKE_R2_WIN32_MEMORY_SHA_GATE=PASS'
        $cache = Join-Path $buildPath 'CMakeCache.txt'
        if (-not (Test-Path -LiteralPath $cache -PathType Leaf)) {
            throw 'P10BZ_STOP missing CMakeCache.txt after configure'
        }
        $generator = Select-String -LiteralPath $cache -Pattern '^CMAKE_GENERATOR:INTERNAL=MinGW Makefiles$'
        if ($null -eq $generator) { throw 'P10BZ_STOP unexpected CMake generator' }
        Add-Report 'CACHE_GENERATOR=MinGW Makefiles'
        $built = Invoke-Native $cmake @('--build', $buildPath, '--config',
            'Release', '--parallel', '2', '--target',
            'p10by_temporal_native_unit', 'p10by_optin_dependency_selftest') (Join-Path $outputRoot 'cmake_build.txt')
        Add-Report ('CMAKE_BUILD_EXIT=' + [string]$built.Exit)
        Require-Exit0 $built 'P10BZ two-target unit-only build'
        Check-Test 'p10by_temporal_native_unit' 'P10BY_TEMPORAL_THERMAL_QP_NATIVE_UNIT_OK' 'series=8 steps=144 qp_csv_rows=14544 corruption_stops=2/2' (Join-Path $outputRoot 'temporal_native_unit.txt') $buildPath
        Check-Test 'p10by_optin_dependency_selftest' 'P10I_PRODUCTION_ADJOINT_OK' 'models=6 functionals=3 cases=18' (Join-Path $outputRoot 'dependency_native_unit.txt') $buildPath
    } finally {
        $env:PATH = $previousPath
    }
    Add-Report 'TESTS_PASSED=2/2'
    Add-Report 'PHYSICAL_FEM_RUNS=0'
    $resultCode = 0
} catch {
    Add-Report ('RESULT=P10BZ_STOPPED: ' + $_.Exception.Message)
    $resultCode = 2
    # A preflight STOP may still produce a small evidence package, safely
    # OUTSIDE the original worktree. A user cancellation above creates none.
    if ($outputRoot -eq '' -and $safeToolRoot) {
        try {
            $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
            $outputRoot = Join-Path $toolRoot ('P10BZ_STOP_' + $stamp + '_' + $PID)
            if (Test-Path -LiteralPath $outputRoot) { throw 'STOP folder exists' }
            [void](New-Item -ItemType Directory -Path $outputRoot)
        } catch {
            Write-Host ('STOP_REPORT_WRITE_FAILURE=' + $_.Exception.Message)
            $outputRoot = ''
        }
    }
} finally {
    if ($null -ne $initialSnapshot) {
        try {
            $after = Get-OriginalSnapshot
            Add-Report ('ORIGINAL_HEAD_AFTER=' + $after.Head)
            Add-Report ('ORIGINAL_STATUS_AFTER=' + $after.Status)
            Add-Report ('ORIGINAL_STATUS_FINGERPRINT_AFTER=' + $after.StatusSHA256)
            if ($after.Head -cne $initialSnapshot.Head -or
                $after.StatusSHA256 -cne $initialSnapshot.StatusSHA256 -or
                $after.Status -cne $initialSnapshot.Status) {
                Add-Report 'ORIGINAL_STATE_UNEXPECTED_CHANGE=YES_INVESTIGATE'
                $resultCode = 2
            } else {
                Add-Report 'ORIGINAL_STATE_PRESERVED=YES_BY_READ_ONLY_COMPARISON'
            }
        } catch {
            Add-Report ('ORIGINAL_POSTCHECK_STOP=' + $_.Exception.Message)
            $resultCode = 2
        }
    }
    if ($outputRoot -ne '' -and (Test-Path -LiteralPath $outputRoot)) {
        if ($resultCode -eq 0) {
            Add-Report 'RESULT=P10BZ_WINDOWS_UNIT_ONLY_OK'
        } else {
            $hasStop = $false
            foreach ($line in $report) {
                if ($line.StartsWith('RESULT=P10BZ_STOPPED')) { $hasStop = $true }
            }
            if (-not $hasStop) {
                Add-Report 'RESULT=P10BZ_STOPPED: postcheck or evidence failure'
            }
            Add-Report 'FINAL_STATUS=STOPPED_CHECK_RESULT_AND_LOGS'
        }
        $reportFile = Join-Path $outputRoot 'P10BZ_RESULT.txt'
        [System.IO.File]::WriteAllLines($reportFile, [string[]]$report,
            [System.Text.UTF8Encoding]::new($false))
        $files = @($reportFile)
        foreach ($name in @('cmake_configure.txt', 'cmake_build.txt',
                            'temporal_native_unit.txt', 'dependency_native_unit.txt')) {
            $file = Join-Path $outputRoot $name
            if (Test-Path -LiteralPath $file -PathType Leaf) { $files += $file }
        }
        $archive = Join-Path $outputRoot 'P10BZ_EVIDENCE.zip'
        try {
            Compress-Archive -LiteralPath $files -DestinationPath $archive -CompressionLevel Optimal
            Write-Host ('EVIDENCE_ZIP=' + $archive)
            Write-Host 'Send ONLY P10BZ_EVIDENCE.zip, not EXE, source, build or mesh.'
        } catch {
            Write-Host ('ZIP_STOP=' + $_.Exception.Message)
            Write-Host ('Instead send P10BZ_RESULT.txt from ' + $outputRoot)
            [void]$report.Remove('RESULT=P10BZ_WINDOWS_UNIT_ONLY_OK')
            Add-Report ('RESULT=P10BZ_STOPPED: evidence ZIP creation failed')
            [System.IO.File]::WriteAllLines($reportFile, [string[]]$report,
                [System.Text.UTF8Encoding]::new($false))
            $resultCode = 2
        }
    } else {
        Write-Host 'No build folder was created; preflight or confirmation stopped the run.'
    }
}
exit $resultCode
