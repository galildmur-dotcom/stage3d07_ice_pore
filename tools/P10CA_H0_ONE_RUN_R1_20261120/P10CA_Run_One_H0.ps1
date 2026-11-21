# P10CA R1 -- single approved PHYSICAL H0 pilot, never a multi-mesh campaign.
# Exact immutable source bundle and read-only G: original; no git mutation.
# Two explicit confirmations: safe build, then ONE physical run.
$ErrorActionPreference = 'Stop'
$expectedOriginal = 'G:\ildar\Stage3D07'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$mesh = 'G:\ildar\Stage3D07\meshes\H0.msh'
$compiler = 'C:\mingw64\bin\g++.exe'
$make = 'C:\mingw64\bin\mingw32-make.exe'
$cmake = 'C:\Program Files\CMake\bin\cmake.exe'
$git = 'C:\Program Files\Git\cmd\git.exe'
$toolRevision = 'P10CA_R1_ONE_PHYSICAL_H0_BUDGET_GUARD'
$report = New-Object 'System.Collections.Generic.List[string]'
$initialSnapshot = $null
$initialMeshSHA = ''
$outputRoot = ''
$safeToolRoot = $false
$resultCode = 2
$physicalAttempted = $false
$physicalVerified = $false
$safeBuildVerified = $false
$exeSHA = ''
$runElapsed = 0.
$maxResidentBytes = [int64]0
$maxOutputBytes = [int64]0
$toolRoot = ''
$env:GIT_OPTIONAL_LOCKS = '0'

function Add-Report([string]$Message) {
    [void]$script:report.Add($Message)
    Write-Host $Message
}

function Invoke-Native([string]$Exe, [string[]]$Arguments,
                       [string]$LogFile = '') {
    # Verified R2 pattern: read LASTEXITCODE immediately after process exit.
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $Exe @Arguments 2>&1
        $nativeExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    $lines = @($raw | ForEach-Object { [string]$_ })
    if ($LogFile -ne '') {
        [System.IO.File]::WriteAllLines($LogFile, [string[]]$lines,
            [System.Text.UTF8Encoding]::new($false))
    }
    return [pscustomobject]@{ Exit=$nativeExit; Lines=$lines }
}

function Require-Exit0($Result, [string]$Name) {
    if ($null -eq $Result.Exit -or $Result.Exit -ne 0) {
        throw ('P10CA_STOP ' + $Name + ' native exit=' + [string]$Result.Exit)
    }
}

function Assert-SHA([string]$File, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
        throw ('P10CA_STOP missing source: ' + [IO.Path]::GetFileName($File))
    }
    $actual = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne $Expected.ToLowerInvariant()) {
        throw ('P10CA_STOP SHA mismatch: ' + [IO.Path]::GetFileName($File))
    }
}

function Hash-Text([string]$Value) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally { $hasher.Dispose() }
}

function Get-OriginalSnapshot {
    $head = Invoke-Native $git @('-C', $expectedOriginal, 'rev-parse', 'HEAD')
    Require-Exit0 $head 'original Git HEAD'
    if ($head.Lines.Count -ne 1) { throw 'P10CA_STOP ambiguous original HEAD' }
    $status = Invoke-Native $git @('-C', $expectedOriginal, '-c',
        'core.fsmonitor=false', 'status', '--porcelain=v1', '--untracked-files=normal')
    Require-Exit0 $status 'original Git status'
    $lines = @($status.Lines | Where-Object { $_.Length -ge 2 })
    $staged = 0; $unstaged = 0; $untracked = 0
    foreach ($line in $lines) {
        if ($line.Substring(0,2) -ceq '??') { $untracked++ }
        else {
            if ($line[0] -ne ' ') { $staged++ }
            if ($line[1] -ne ' ') { $unstaged++ }
        }
    }
    return [pscustomobject]@{
        Head = [string]$head.Lines[0]
        Counts = ('{0}/{1}/{2}' -f $staged,$unstaged,$untracked)
        StatusSHA256 = Hash-Text ([string]::Join([Environment]::NewLine,
                                               [string[]]$lines))
    }
}

function Check-BundledSources([string]$Root) {
    $source = Join-Path $Root 'source'
    $pinned = Join-Path $source 'pinned'
    $bx = Join-Path $source 'p10bx'
    $bw = Join-Path $source 'p10bw'
    $by = Join-Path $source 'p10by'
    $ca = Join-Path $source 'p10ca'
    $manifest = Join-Path $by 'P10BY_PINNED_SHA256.txt'
    Assert-SHA $manifest 'bce45c5757796ecc505ca6e0899de912c4ad4441fb05d007f1d2c41192d2f2ce'
    $rows = @(Get-Content -LiteralPath $manifest -Encoding UTF8 |
        Where-Object { $_ -ne '' -and $_ -notmatch '^#' })
    if ($rows.Count -ne 35) { throw 'P10CA_STOP original source count not 35' }
    $seen = @{}
    foreach ($row in $rows) {
        $parts = @($row.Split('|'))
        if ($parts.Count -ne 2 -or $seen.ContainsKey($parts[0]) -or
            $parts[1] -notmatch '^[0-9a-f]{64}$') {
            throw 'P10CA_STOP malformed or duplicate historical SHA row'
        }
        $seen[$parts[0]] = $true
        Assert-SHA (Join-Path $pinned $parts[0].Replace('/', '\')) $parts[1]
    }
    Assert-SHA (Join-Path $pinned 'src\win_process_memory.cpp') 'c299d890b0f3a04f86974fb664120a36681eef464ffbb617eabc8e57e07a5e09'
    $components = @(
        [pscustomobject]@{File='p10bx\src\stage3d10p_partial_audit.cpp'; SHA='57754cfaa031fddb391e6b211a6f083346475611d180676c0c4987926ea54b1b'},
        [pscustomobject]@{File='p10bx\src\stage3d10w_analytic_adjoint.cpp'; SHA='1d769e559aa561817685b56949bf649e6ceddb89da4cfc294cc18738d6d82df8'},
        [pscustomobject]@{File='p10bx\stage3d10bx_thermal_step_hook.hpp'; SHA='79b716c389a6a9dd466d65d795ad3a67bda206bdd636eec0fb03962dc3155574'},
        [pscustomobject]@{File='p10bw\stage3d10bw_thermal_qp_partition.hpp'; SHA='71992ba7e8c0b44d7832c5d8566ef8886517bbd87f953b119271746483f0fa23'},
        [pscustomobject]@{File='p10bw\P10BW_thermal_qp_native_unit.cpp'; SHA='719a9db9f3c3221acdfc096a88cfbb1cdb81307ba931463f3ff62726e10a03c6'},
        [pscustomobject]@{File='p10by\P10BY_temporal_thermal_qp_native_unit.cpp'; SHA='c06b7245212d7e6d2e1ded93bf4695245b61e51845d882330c73107fb68825ee'},
        [pscustomobject]@{File='p10by\P10BY_unitonly_entry.cpp'; SHA='080a27aca4bf9d27ba5c245c2dfdd4730a30f185a25df978a3ee3e9c0dfb8024'},
        [pscustomobject]@{File='p10by\CMakeLists.txt'; SHA='bbf5f43f17f2c607edf4cb12550058d519fc1668354c7b28d57ef6cfee483239'}
    )
    foreach ($entry in $components) {
        Assert-SHA (Join-Path $source $entry.File) $entry.SHA
    }
    Assert-SHA (Join-Path $ca 'CMakeLists.txt') 'f37f912c2a68c701ee1cc954739c9fee23bf97b702cb9146f8793d40ffae6369'
    Add-Report 'P10CA_BUNDLED_SHA256_OK original=36 proposals=8 total=44 cmake=1'
    return [pscustomobject]@{Pinned=$pinned;BX=$bx;BW=$bw;BY=$by;CA=$ca}
}

function Check-Toolchain {
    foreach ($path in @($compiler,$make,$cmake,$git)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw ('P10CA_STOP missing validated tool: ' + $path)
        }
    }
    $cxx = Invoke-Native $compiler @('--version')
    Require-Exit0 $cxx 'compiler version'
    if (-not (($cxx.Lines -join ' ') -match '13\.1\.0')) {
        throw 'P10CA_STOP only validated GNU13.1.0 is permitted'
    }
    $cm = Invoke-Native $cmake @('--version')
    Require-Exit0 $cm 'CMake version'
    if (-not (($cm.Lines -join ' ') -match '4\.4\.3')) {
        throw 'P10CA_STOP CMake differs from verified R2 version 4.4.3'
    }
    Add-Report 'TOOLCHAIN=GNU13.1.0_CMAKE4.4.3_MINGW_MAKE'
}

function Get-H0MeshFacts([string]$File) {
    # Strict read-only Gmsh v2.2 ASCII Tet10/Tri6 index audit; no solver.
    $reader = [IO.File]::OpenText($File)
    $format = ''; $nodes = -1; $tets=0; $top=0; $pore=0
    $tri=0; $elements=-1
    try {
        while ($null -ne ($line = $reader.ReadLine())) {
            if ($line -eq '$MeshFormat') {
                $fields = [regex]::Split($reader.ReadLine().Trim(), '\s+')
                if ($fields.Count -lt 2 -or $fields[0] -cne '2.2' -or
                    $fields[1] -cne '0') {
                    throw 'P10CA_STOP H0 mesh must be Gmsh 2.2 ASCII'
                }
                $format = '2.2_ASCII'
            } elseif ($line -eq '$Nodes') {
                $nodes = [int]$reader.ReadLine()
                for ($i=0; $i -lt $nodes; ++$i) {
                    if ($null -eq $reader.ReadLine()) { throw 'P10CA_STOP truncated H0 nodes' }
                }
            } elseif ($line -eq '$Elements') {
                $elements = [int]$reader.ReadLine()
                for ($i=0; $i -lt $elements; ++$i) {
                    $item = $reader.ReadLine()
                    if ($null -eq $item) { throw 'P10CA_STOP truncated H0 elements' }
                    $f = [regex]::Split($item.Trim(), '\s+')
                    if ($f.Count -lt 5) { throw 'P10CA_STOP malformed H0 element' }
                    $type = [int]$f[1]
                    $nTags = [int]$f[2]
                    if ($nTags -lt 1 -or $f.Count -lt 3+$nTags) {
                        throw 'P10CA_STOP missing H0 element physical tag'
                    }
                    if ($type -eq 11) {
                        if ($f.Count -ne 3+$nTags+10) { throw 'P10CA_STOP malformed Tet10' }
                        $tets++
                    } elseif ($type -eq 9) {
                        if ($f.Count -ne 3+$nTags+6) { throw 'P10CA_STOP malformed Tri6' }
                        $tri++
                        $tag = [int]$f[3]
                        if ($tag -eq 2) { $top++ }
                        if ($tag -eq 8) { $pore++ }
                    } else { throw 'P10CA_STOP unexpected H0 element type' }
                }
            }
        }
    } finally { $reader.Dispose() }
    if ($format -cne '2.2_ASCII' -or $nodes -ne 10845 -or
        $tets -ne 7388 -or $pore -ne 136 -or $top -lt 1) {
        $counts = ('{0}/{1}/{2}/{3}' -f $nodes,$tets,$pore,$top)
        throw ('P10CA_STOP H0 geometry not the expected 10845/7388/pore136: ' + $counts)
    }
    return [pscustomobject]@{Format=$format;Nodes=$nodes;Tet10=$tets;
                              Tri6=$tri;TopTri6=$top;PoreTri6=$pore}
}

function Folder-Bytes([string]$Directory) {
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return [int64]0 }
    $files = Get-ChildItem -LiteralPath $Directory -File -Recurse -ErrorAction Stop
    [int64]$total = 0
    foreach ($file in $files) { $total += [int64]$file.Length }
    return $total
}

function Parse-Invariant([string]$Number) {
    return [double]::Parse($Number, [Globalization.CultureInfo]::InvariantCulture)
}

function Check-PhysicalCSV([string]$Dir, [string]$Stdout) {
    $line = $Stdout -split "`n"
    if (-not ($line -match '^P10BX_THERMAL_QP_INTEGRATED_OK .*steps=6 .*bins_per_step=100 .*top_robin_rows=6 .*exported_rows=606 .*original_gradient_unchanged=1')) {
        throw 'P10CA_STOP missing exact P10BX physical all-step marker'
    }
    if (-not ($line -match '^P10W_ANALYTIC_ADJOINT_OK .*geometry_partial=ANALYTIC_TET10 .*central_fd_evaluations=0')) {
        throw 'P10CA_STOP missing P10W analytic derivative marker'
    }
    foreach ($name in @('P10W_ANALYTIC_ADJOINT.csv','P10W_COMPONENTS.csv',
                        'P10W_STEP_COMPONENTS.csv',
                        'P10BX_THERMAL_QP_STEP_BINS.csv',
                        'P10BX_THERMAL_STEP_AUDIT.csv')) {
        if (-not (Test-Path -LiteralPath (Join-Path $Dir $name) -PathType Leaf)) {
            throw ('P10CA_STOP missing physical diagnostic CSV ' + $name)
        }
    }
    $bins = @(Import-Csv -LiteralPath (Join-Path $Dir 'P10BX_THERMAL_QP_STEP_BINS.csv'))
    $audits = @(Import-Csv -LiteralPath (Join-Path $Dir 'P10BX_THERMAL_STEP_AUDIT.csv'))
    if ($bins.Count -ne 606 -or $audits.Count -ne 6) {
        throw 'P10CA_STOP expected 606 local and 6 physical audit rows'
    }
    foreach ($step in 1..6) {
        $b = @($bins | Where-Object { $_.step -eq [string]$step })
        $a = @($audits | Where-Object { $_.step -eq [string]$step })
        if ($b.Count -ne 101 -or $a.Count -ne 1) {
            throw ('P10CA_STOP expected 101 local and 1 audit row at step ' + $step)
        }
        $topRows = @($b | Where-Object { $_.shell_bin -eq '-1' -and $_.polar_bin -eq '-1' })
        if ($topRows.Count -ne 1) { throw 'P10CA_STOP wrong top Robin bin isolation' }
        $sum = 0.
        foreach ($row in $b) {
            $v = Parse-Invariant $row.total_per_m
            if ([double]::IsNaN($v) -or [double]::IsInfinity($v)) {
                throw 'P10CA_STOP nonfinite local thermal bin'
            }
            $sum += $v
        }
        $expected = Parse-Invariant $a[0].qp_total_per_m
        $csr = Parse-Invariant $a[0].csr_total_per_m
        $tol = Parse-Invariant $a[0].allowed_abs_error_per_m
        $qpCount = Parse-Invariant $a[0].thermal_qp_count
        if ($qpCount -ne 472832 -or $tol -lt 0 -or
            [math]::Abs($sum-$expected) -gt $tol -or
            [math]::Abs($csr-$expected) -gt $tol) {
            throw ('P10CA_STOP audit/local/CSR QP mismatch at step ' + $step)
        }
    }
    Add-Report 'P10CA_PHYSICAL_QP_CSV_AUDIT_OK local_rows=606 audit_rows=6 qp_per_step=472832'
}

try {
    Add-Report 'P10CA SINGLE PHYSICAL H0 R/EDV_VAR XI0 6x150s; BUDGET GUARD'
    Add-Report ('TOOL_REVISION=' + $toolRevision)
    Add-Report ('START_LOCAL=' + (Get-Date).ToString('o'))
    $toolRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
    $originalRoot = [IO.Path]::GetFullPath($expectedOriginal).TrimEnd('\')
    if ($toolRoot.Equals($originalRoot,[StringComparison]::OrdinalIgnoreCase) -or
        $toolRoot.StartsWith($originalRoot+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw 'P10CA_STOP tool folder is inside dirty original project'
    }
    $safeToolRoot = $true
    $attemptMarker = Join-Path $toolRoot 'P10CA_PHYSICAL_ATTEMPTED.txt'
    if (Test-Path -LiteralPath $attemptMarker) {
        throw 'P10CA_STOP this extracted package has ALREADY attempted its one H0'
    }
    if (-not (Test-Path -LiteralPath $expectedOriginal -PathType Container)) {
        throw 'P10CA_STOP original Windows project unavailable'
    }
    $initialSnapshot = Get-OriginalSnapshot
    Add-Report ('ORIGINAL_HEAD_BEFORE=' + $initialSnapshot.Head)
    Add-Report ('ORIGINAL_STATUS_BEFORE=' + $initialSnapshot.Counts)
    Add-Report ('ORIGINAL_STATUS_SHA_BEFORE=' + $initialSnapshot.StatusSHA256)
    if ($initialSnapshot.Head -cne $expectedHead) {
        throw 'P10CA_STOP original Git HEAD differs from exact P10BM SHA'
    }
    $source = Check-BundledSources $toolRoot
    Check-Toolchain
    if (-not (Test-Path -LiteralPath $mesh -PathType Leaf)) {
        throw 'P10CA_STOP expected H0 mesh path unavailable; no search or substitution'
    }
    $facts = Get-H0MeshFacts $mesh
    $initialMeshSHA = (Get-FileHash -LiteralPath $mesh -Algorithm SHA256).Hash.ToLowerInvariant()
    Add-Report ('H0_MESH_SHA256=' + $initialMeshSHA)
    Add-Report ('H0_NODES=' + $facts.Nodes)
    Add-Report ('H0_TET10=' + $facts.Tet10)
    Add-Report ('H0_PORE_TRI6=' + $facts.PoreTri6)
    Add-Report ('H0_TOP_TRI6=' + $facts.TopTri6)
    Add-Report ('H0_EXPECTED_THERMAL_VOLUME_QP=2836992')
    Add-Report ('H0_EXPECTED_TOP_ROBIN_QP=' + [string](96*$facts.TopTri6))
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($toolRoot))
    if ($drive.AvailableFreeSpace -lt 2147483648) {
        throw 'P10CA_STOP requires 2 GiB free outside original worktree'
    }
    Add-Report 'READ_ONLY_GATE=PASS'
    Write-Host 'One clean analytic H0 EXE will be built OUTSIDE original project.'
    Write-Host 'No physical FEM until second confirmation. Estimate 2-6 min (low confidence).'
    $prepareAnswer = Read-Host 'Type PREPARE P10CA to build the isolated target (Enter cancels)'
    if ($prepareAnswer -cne 'PREPARE P10CA') {
        Add-Report 'CANCELLED_PREPARE_NO_BUILD_NO_FEM'
        $resultCode = 0
        return
    }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outputRoot = Join-Path $toolRoot ('P10CA_RESULTS_' + $stamp + '_' + $PID)
    if (Test-Path -LiteralPath $outputRoot) { throw 'P10CA_STOP results directory already exists' }
    [void](New-Item -ItemType Directory -Path $outputRoot)
    $build = Join-Path $outputRoot 'build'
    $physicalOut = Join-Path $outputRoot 'H0_PHYSICAL_RUN'
    Add-Report ('RESULT_FOLDER=' + [IO.Path]::GetFileName($outputRoot))
    $oldPath = $env:PATH
    try {
        $env:PATH = 'C:\mingw64\bin;' + $env:PATH
        $args = @('-S', $source.CA, '-B', $build, '-G', 'MinGW Makefiles',
                  '-DCMAKE_BUILD_TYPE=Release',
                  '-DCMAKE_CXX_COMPILER=C:/mingw64/bin/g++.exe',
                  '-DCMAKE_MAKE_PROGRAM=C:/mingw64/bin/mingw32-make.exe',
                  ('-DP10CA_PINNED_ROOT=' + $source.Pinned),
                  ('-DP10CA_P10BX_ROOT=' + $source.BX),
                  ('-DP10CA_P10BW_ROOT=' + $source.BW),
                  ('-DP10CA_P10BY_ROOT=' + $source.BY))
        $config = Invoke-Native $cmake $args (Join-Path $outputRoot 'cmake_configure.txt')
        Add-Report ('CMAKE_CONFIGURE_EXIT=' + [string]$config.Exit)
        Require-Exit0 $config 'P10CA CMake configure'
        if (($config.Lines -join "`n") -notmatch 'P10CA_BUNDLED_SOURCE_SHA256_OK original=36 proposals=8 total=44' -or
            ($config.Lines -join "`n") -notmatch 'P10CA_CONFIGURE_BUILD_ONLY_NO_FEM') {
            throw 'P10CA_STOP missing exact CMake source/build-only gate'
        }
        $cache = Join-Path $build 'CMakeCache.txt'
        if (-not (Test-Path -LiteralPath $cache -PathType Leaf) -or
            $null -eq (Select-String -LiteralPath $cache -Pattern '^CMAKE_GENERATOR:INTERNAL=MinGW Makefiles$')) {
            throw 'P10CA_STOP unexpected or missing CMake cache generator'
        }
        $built = Invoke-Native $cmake @('--build', $build, '--config',
            'Release', '--parallel', '2', '--target', 'p10ca_h0_analytic_qp') (
            Join-Path $outputRoot 'cmake_build.txt')
        Add-Report ('CMAKE_BUILD_EXIT=' + [string]$built.Exit)
        Require-Exit0 $built 'P10CA build-only analytic target'
        $exe = Join-Path $build 'p10ca_h0_analytic_qp.exe'
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
            throw 'P10CA_STOP physical target EXE not built'
        }
        $exeSHA = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
        Add-Report ('P10CA_EXE_SHA256=' + $exeSHA)
        $help = Invoke-Native -Exe $exe -Arguments @('--help') -LogFile (
            Join-Path $outputRoot 'exe_help.txt')
        Require-Exit0 $help 'P10CA --help (NO FEM)'
        if (($help.Lines -join "`n") -notmatch 'no --delta-scan-um is accepted') {
            throw 'P10CA_STOP wrong analytic P10W executable help contract'
        }
        $tiny = Invoke-Native -Exe $exe -Arguments @('--selftest') -LogFile (
            Join-Path $outputRoot 'exe_safe_selftest.txt')
        Add-Report ('BUILD_SELFTEST_EXIT=' + [string]$tiny.Exit)
        Require-Exit0 $tiny 'P10CA native tiny dependency selftest'
        if (($tiny.Lines -join "`n") -notmatch '(?m)^P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18' -or
            ($tiny.Lines -join "`n") -notmatch '(?m)^P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0') {
            throw 'P10CA_STOP missing safe native adjoint markers'
        }
        $safeBuildVerified = $true
        Add-Report 'SAFE_BUILD_AND_SELFTEST=PASS_NO_FEM'
        Write-Host ''
        Write-Host 'READY for ONE approved PHYSICAL H0: R/EDV_VAR xi=0, steps=6 dt=150.'
        Write-Host 'Guard: STOP at ~6 GiB observed process memory, ~0.75 GiB new disk, 9 min wall.'
        Write-Host 'These are conservative polling limits; momentary peaks cannot be guaranteed.'
        Write-Host ('Mesh SHA256: ' + $initialMeshSHA)
        Write-Host ('EXE SHA256: ' + $exeSHA)
        $runAnswer = Read-Host 'Type RUN ONE H0 P10CA to start ONE physical solve (Enter cancels)'
        if ($runAnswer -cne 'RUN ONE H0 P10CA') {
            Add-Report 'CANCELLED_AFTER_SAFE_BUILD_NO_FEM'
            $resultCode = 0
        } else {
            # Recheck immutable inputs immediately before the one physical solve.
            $preRun = Get-OriginalSnapshot
            $preRunMeshSHA = (Get-FileHash -LiteralPath $mesh -Algorithm SHA256).Hash.ToLowerInvariant()
            $preRunExeSHA = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($preRun.Head -cne $initialSnapshot.Head -or
                $preRun.Counts -cne $initialSnapshot.Counts -or
                $preRun.StatusSHA256 -cne $initialSnapshot.StatusSHA256 -or
                $preRunMeshSHA -cne $initialMeshSHA -or
                $preRunExeSHA -cne $exeSHA) {
                throw 'P10CA_STOP input/Git/EXE changed during safe build; no FEM'
            }
            Add-Report 'IMMEDIATE_PRE_PHYSICAL_SHA_AND_GIT_GATE=PASS'
            # One-time token is created BEFORE launching FEM. Never auto-retry.
            $tokenStream = [IO.File]::Open($attemptMarker,[IO.FileMode]::CreateNew,
                [IO.FileAccess]::Write,[IO.FileShare]::None)
            try {
                $writer = [IO.StreamWriter]::new($tokenStream)
                $writer.WriteLine($toolRevision)
                $writer.WriteLine('RUN_ID=' + [IO.Path]::GetFileName($outputRoot))
                $writer.WriteLine('MESH_SHA256=' + $initialMeshSHA)
                $writer.WriteLine('EXE_SHA256=' + $exeSHA)
                $writer.Flush()
                $writer.Dispose()
            } finally { $tokenStream.Dispose() }
            $physicalAttempted = $true
            $stdout = Join-Path $outputRoot 'physical_stdout.txt'
            $stderr = Join-Path $outputRoot 'physical_stderr.txt'
            if (Test-Path -LiteralPath $physicalOut) {
                throw 'P10CA_STOP physical output must be a new directory'
            }
            if ($mesh.Contains('"') -or $physicalOut.Contains('"')) {
                throw 'P10CA_STOP quoted mesh/output paths not supported'
            }
            $physicalArgs = ('--mesh "{0}" --out "{1}" --steps 6 --dt 150 --mode R --cutoff-mm 5 --threads 4' -f $mesh,$physicalOut)
            Add-Report ('PHYSICAL_ARGS=' + $physicalArgs)
            Add-Report 'PHYSICAL_ATTEMPTED=ONE_H0_NO_PREFLIGHT'
            $env:OMP_NUM_THREADS = '4'
            $env:OMP_DYNAMIC = 'FALSE'
            $proc = $null
            $start = Get-Date
            try {
                $proc = Start-Process -FilePath $exe -ArgumentList $physicalArgs -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
                Add-Report ('PHYSICAL_PROCESS_ID=' + $proc.Id)
                $tick = 0
                while ($true) {
                    $proc.Refresh()
                    if ($proc.HasExited) { break }
                    Start-Sleep -Milliseconds 500
                    ++$tick
                    $runElapsed = ((Get-Date) - $start).TotalSeconds
                    $mem = [int64][math]::Max([double]$proc.WorkingSet64,
                                             [double]$proc.PrivateMemorySize64)
                    if ($mem -gt $maxResidentBytes) { $maxResidentBytes = $mem }
                    if ($tick % 4 -eq 0) {
                        $size = Folder-Bytes $physicalOut
                        if ($size -gt $maxOutputBytes) { $maxOutputBytes=$size }
                    }
                    if ($tick % 20 -eq 0) {
                        Write-Host ('H0_RUNNING elapsed_s={0:N0} mem_GiB={1:N2} output_GiB={2:N3}' -f
                            $runElapsed,($maxResidentBytes/1GB),($maxOutputBytes/1GB))
                    }
                    if ($runElapsed -ge 540 -or $mem -ge 6442450944 -or
                        $maxOutputBytes -ge 805306368) {
                        try { Stop-Process -Id $proc.Id -Force -ErrorAction Stop }
                        catch { Write-Host ('PROCESS_STOP_DIAGNOSTIC=' + $_.Exception.Message) }
                        $proc.WaitForExit()
                        throw ('P10CA_BUDGET_STOP time_s=' + [string][int]$runElapsed +
                            ' max_process_bytes=' + [string]$maxResidentBytes +
                            ' max_output_bytes=' + [string]$maxOutputBytes)
                    }
                }
                $proc.WaitForExit()
                $proc.Refresh()
                $runElapsed = ((Get-Date)-$start).TotalSeconds
                $finalBytes = Folder-Bytes $physicalOut
                if ($finalBytes -gt $maxOutputBytes) { $maxOutputBytes=$finalBytes }
                try {
                    $peakWorking = [int64]$proc.PeakWorkingSet64
                    if ($peakWorking -gt $maxResidentBytes) { $maxResidentBytes=$peakWorking }
                } catch { Write-Host 'PEAK_WORKINGSET_UNAVAILABLE_USING_POLLED_VALUES' }
                if ($maxOutputBytes -ge 805306368 -or $maxResidentBytes -ge 6442450944) {
                    throw 'P10CA_BUDGET_STOP final output or peak process memory exceeded guard'
                }
                $nativeExit = $proc.ExitCode
                if ($null -eq $nativeExit) { throw 'P10CA_STOP physical ExitCode unavailable' }
                Add-Report ('PHYSICAL_NATIVE_EXIT=' + [string]$nativeExit)
                Add-Report ('PHYSICAL_WALL_SECONDS=' + [string]([math]::Round($runElapsed,2)))
                if ($nativeExit -ne 0) { throw 'P10CA_STOP physical solver returned nonzero native exit' }
            } finally {
                if ($null -ne $proc) {
                    try {
                        $proc.Refresh()
                        if (-not $proc.HasExited) {
                            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                            $proc.WaitForExit()
                        }
                    } catch { Write-Host ('PROCESS_FINALIZER=' + $_.Exception.Message) }
                    $proc.Dispose()
                }
            }
            if (-not (Test-Path -LiteralPath $stdout -PathType Leaf)) {
                throw 'P10CA_STOP missing physical stdout file'
            }
            $physicalText = [IO.File]::ReadAllText($stdout)
            Check-PhysicalCSV $physicalOut $physicalText
            $physicalVerified = $true
            $resultCode = 0
        }
    } finally {
        $env:PATH = $oldPath
    }
} catch {
    Add-Report ('RESULT=P10CA_STOPPED: ' + $_.Exception.Message)
    $resultCode = 2
    if ($outputRoot -eq '' -and $safeToolRoot) {
        try {
            $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
            $outputRoot = Join-Path $toolRoot ('P10CA_STOP_' + $stamp + '_' + $PID)
            if (-not (Test-Path -LiteralPath $outputRoot)) {
                [void](New-Item -ItemType Directory -Path $outputRoot)
            }
        } catch { Write-Host ('STOP_REPORT_WRITE_FAILED=' + $_.Exception.Message); $outputRoot='' }
    }
} finally {
    if ($null -ne $initialSnapshot) {
        try {
            $now = Get-OriginalSnapshot
            Add-Report ('ORIGINAL_HEAD_AFTER=' + $now.Head)
            Add-Report ('ORIGINAL_STATUS_AFTER=' + $now.Counts)
            Add-Report ('ORIGINAL_STATUS_SHA_AFTER=' + $now.StatusSHA256)
            if ($now.Head -cne $initialSnapshot.Head -or
                $now.Counts -cne $initialSnapshot.Counts -or
                $now.StatusSHA256 -cne $initialSnapshot.StatusSHA256) {
                Add-Report 'ORIGINAL_STATE_CHANGED=STOP_INVESTIGATE'
                $resultCode = 2
            } else { Add-Report 'ORIGINAL_STATE_PRESERVED=YES' }
        } catch { Add-Report ('ORIGINAL_POSTCHECK_STOP=' + $_.Exception.Message);$resultCode=2 }
    }
    if ($initialMeshSHA -ne '') {
        try {
            $afterMesh = (Get-FileHash -LiteralPath $mesh -Algorithm SHA256).Hash.ToLowerInvariant()
            Add-Report ('H0_MESH_SHA256_AFTER=' + $afterMesh)
            if ($afterMesh -cne $initialMeshSHA) { Add-Report 'H0_MESH_CHANGED=STOP';$resultCode=2 }
        } catch { Add-Report ('MESH_POSTCHECK_STOP=' + $_.Exception.Message);$resultCode=2 }
    }
    if ($outputRoot -ne '' -and (Test-Path -LiteralPath $outputRoot -PathType Container)) {
        if ($physicalVerified -and $resultCode -eq 0) {
            Add-Report 'RESULT=P10CA_ONE_H0_PHYSICAL_QP_OK'
        } elseif ($safeBuildVerified -and -not $physicalAttempted -and $resultCode -eq 0) {
            Add-Report 'RESULT=P10CA_BUILD_ONLY_OK_NO_FEM'
        } else {
            Add-Report 'FINAL_STATUS=STOP_OR_INCOMPLETE_CHECK_LOGS'
            $resultCode = 2
        }
        $resultFile = Join-Path $outputRoot 'P10CA_RESULT.txt'
        $manifestFile = Join-Path $outputRoot 'P10CA_RUN_MANIFEST.json'
        $headForManifest = ''
        $statusForManifest = ''
        $statusSHAForManifest = ''
        if ($null -ne $initialSnapshot) {
            $headForManifest = $initialSnapshot.Head
            $statusForManifest = $initialSnapshot.Counts
            $statusSHAForManifest = $initialSnapshot.StatusSHA256
        }
        $manifest = [ordered]@{
            schema='P10CA_R1_LOCAL_EVIDENCE_NOT_OFFICIAL_M01'
            run_id=[IO.Path]::GetFileName($outputRoot)
            tool_revision=$toolRevision
            source_git_commit=$expectedHead
            original_head=$headForManifest
            original_status_before=$statusForManifest
            original_status_fingerprint=$statusSHAForManifest
            mesh_file='meshes/H0.msh'
            mesh_sha256=$initialMeshSHA
            exe_sha256=$exeSHA
            physical_attempted=$physicalAttempted
            physical_verified=$physicalVerified
            mode='R'; law='EDV';modulus='VAR';xi=0
            steps=6;dt_s=150;horizon_s=900;threads=4
            geometry_partial='ANALYTIC_TET10';central_fd_evaluations=0
            wall_seconds=$runElapsed
            max_observed_process_bytes=$maxResidentBytes
            max_observed_output_bytes=$maxOutputBytes
            source_package='P10CA_H0_ONE_RUN_R1_20261120'
            note='New isolated one-H0 run. Not the Stage3D10S M01/M02 register.'
        }
        try {
            [IO.File]::WriteAllText($manifestFile,($manifest | ConvertTo-Json -Depth 4),
                [Text.UTF8Encoding]::new($false))
            [IO.File]::WriteAllLines($resultFile,[string[]]$report,
                [Text.UTF8Encoding]::new($false))
            $files = @($resultFile,$manifestFile)
            foreach ($name in @('cmake_configure.txt','cmake_build.txt','exe_help.txt',
                                'exe_safe_selftest.txt','physical_stdout.txt',
                                'physical_stderr.txt')) {
                $f = Join-Path $outputRoot $name
                if (Test-Path -LiteralPath $f -PathType Leaf) { $files += $f }
            }
            $physicalFolder = Join-Path $outputRoot 'H0_PHYSICAL_RUN'
            foreach ($name in @('P10W_ANALYTIC_ADJOINT.csv','P10W_COMPONENTS.csv',
                                'P10W_STEP_COMPONENTS.csv',
                                'P10BX_THERMAL_QP_STEP_BINS.csv',
                                'P10BX_THERMAL_STEP_AUDIT.csv')) {
                $f = Join-Path $physicalFolder $name
                if (Test-Path -LiteralPath $f -PathType Leaf) { $files += $f }
            }
            $evidence = Join-Path $outputRoot 'P10CA_EVIDENCE.zip'
            Compress-Archive -LiteralPath $files -DestinationPath $evidence -CompressionLevel Optimal
            Add-Report ('EVIDENCE_ZIP=' + $evidence)
            Write-Host 'Send ONLY P10CA_EVIDENCE.zip, never mesh/EXE/bin/checkpoint.'
        } catch {
            [void]$report.Remove('RESULT=P10CA_ONE_H0_PHYSICAL_QP_OK')
            Add-Report ('RESULT=P10CA_STOPPED_EVIDENCE: ' + $_.Exception.Message)
            [IO.File]::WriteAllLines($resultFile,[string[]]$report,
                [Text.UTF8Encoding]::new($false))
            $resultCode=2
        }
    } else {
        Write-Host 'No output folder created; preflight or user confirmation stopped the run.'
    }
}
exit $resultCode
