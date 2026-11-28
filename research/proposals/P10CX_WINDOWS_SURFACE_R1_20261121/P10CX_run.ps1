# P10CX R1: exactly one Gmsh4.15.2 2D-only surface run. NO FEM/3D.
$ErrorActionPreference = 'Stop'
$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runBase = Join-Path $toolRoot 'P10CX_RUNS'
$revision = 'P10CX_R1_GMSH4152_SURFACE_ONLY_ONE_SHOT'
$maxSeconds = 180
$maxPrivateBytes = [Int64](2GB)
$maxMeshBytes = [Int64](150MB)
$resultLines = New-Object 'System.Collections.Generic.List[string]'
$resultLines.Add('TOOL_REVISION=' + $revision)
$resultLines.Add('PHYSICAL_FEM_RUNS=0')
$resultLines.Add('VOLUME_3D_MESH_RUNS=0')
$resultLines.Add('MESH_SURFACE_ONLY_ATTEMPT_MAX=1')
$resultLines.Add('GMSH_THREADS=2')
$resultLines.Add('CAP_WALL_SECONDS=180')
$resultLines.Add('CAP_PRIVATE_GIB=2')
$resultLines.Add('CAP_MSH_MIB=150')
$status = 'P10CX_STOP_NO_3D_NO_FEM'
$exitNumber = 2
$runDir = $null
$proc = $null
$outTask = $null
$errTask = $null

function Test-SourceHash([string] $filename, [string] $expected) {
    $path = Join-Path $toolRoot $filename
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw ('Missing source: ' + $filename) }
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $expected) { throw ('SHA-256 mismatch: ' + $filename) }
    $resultLines.Add(('SHA256_' + $filename + '=' + $hash))
    return $path
}

try {
    $userProject = 'G:\ildar\Stage3D07'
    $rootFull = [System.IO.Path]::GetFullPath($toolRoot).TrimEnd('\')
    if ($rootFull.Equals($userProject,[StringComparison]::OrdinalIgnoreCase) -or
        $rootFull.StartsWith($userProject + '\',[StringComparison]::OrdinalIgnoreCase)) {
        throw 'STOP: extract tool OUTSIDE G:\ildar\Stage3D07'
    }
    if (Test-Path -LiteralPath $runBase) {
        if ((@(Get-ChildItem -LiteralPath $runBase -Force)).Count -gt 0) {
            throw 'STOP_ONE_SHOT_ALREADY_USED: do not repeat the same extracted tool'
        }
    } else { New-Item -ItemType Directory -Path $runBase | Out-Null }
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')
    $runDir = Join-Path $runBase ('P10CX_' + $stamp)
    New-Item -ItemType Directory -Path $runDir | Out-Null

    $geo = Test-SourceHash 'P10CV_U1_GEO_ANGULAR_NEUTRAL_CANDIDATE.geo' '85ee63351ff8e7c1b7720f8ba360aac1d4e6c381f776e3fa66f130e73f17aca7'
    $null = Test-SourceHash 'sphere_pore_B6_refined.geo' '8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0'
    $audit = Test-SourceHash 'P10CX_surface_audit.py' '165d59ff1b05f45478008c6498a0b5ddfde19ca4538816439a3a530f70cc0f50'
    $resultLines.Add('SOURCE_SHA_GATES=PASS_3_OF_3')

    $gmsh = 'C:\gmsh-4.15.2-Windows64\gmsh.exe'
    if (-not [string]::IsNullOrWhiteSpace($env:P10CX_GMSH_EXE)) { $gmsh = $env:P10CX_GMSH_EXE }
    if (-not (Test-Path -LiteralPath $gmsh -PathType Leaf)) { throw ('STOP: Gmsh not found: ' + $gmsh) }
    $resultLines.Add('GMSH_EXE_SHA256=' + (Get-FileHash -LiteralPath $gmsh -Algorithm SHA256).Hash.ToLowerInvariant())
    $versionText = @(& $gmsh -version 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw ('STOP: Gmsh -version native exit ' + $LASTEXITCODE) }
    $resultLines.Add('GMSH_VERSION=' + ($versionText.Trim() -replace "`r|`n", ' '))
    if ($versionText.Trim() -notmatch '(?m)^4\.15\.2\s*$') { throw 'STOP: require Gmsh 4.15.2' }

    $freeMemBytes = [Int64]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory) * 1024
    if ($freeMemBytes -lt [Int64](4GB)) { throw 'STOP: less than 4 GiB available RAM' }
    $rootDrive = [System.IO.Path]::GetPathRoot($toolRoot)
    $driveName = $rootDrive.Substring(0, 1)
    $freeDiskBytes = [Int64](Get-PSDrive -Name $driveName).Free
    if ($freeDiskBytes -lt [Int64](1GB)) { throw 'STOP: less than 1 GiB free disk' }
    $resultLines.Add('RAM_DISK_PREFLIGHT=PASS')

    $pythonCmd = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    $pythonPrefix = @()
    if ($null -eq $pythonCmd) {
        $pythonCmd = Get-Command 'python.exe' -ErrorAction SilentlyContinue
        if ($null -eq $pythonCmd) { throw 'STOP: Python 3 not found' }
    } else { $pythonPrefix = @('-3') }
    & $pythonCmd.Source @pythonPrefix $audit --selftest *> (Join-Path $runDir 'P10CX_UNIT.txt')
    $unitExit = $LASTEXITCODE
    $resultLines.Add('PYTHON_UNIT_EXIT=' + $unitExit)
    if ($unitExit -ne 0) { throw ('STOP: Python unit native exit ' + $unitExit) }

    $mesh = Join-Path $runDir 'P10CX_U1_SURFACE_ONLY.msh'
    $arguments = '"' + $geo + '" -2 -nt 2 -format msh2 -o "' + $mesh + '" -nopopup'
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $gmsh
    $psi.Arguments = $arguments
    $psi.WorkingDirectory = $toolRoot
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $outTask = $proc.StandardOutput.ReadToEndAsync()
    $errTask = $proc.StandardError.ReadToEndAsync()
    $startTime = Get-Date
    $peakPrivate = [Int64]0
    $resultLines.Add('GMSH_STARTED=YES')
    while (-not $proc.WaitForExit(500)) {
        $proc.Refresh()
        if ($proc.PrivateMemorySize64 -gt $peakPrivate) { $peakPrivate = $proc.PrivateMemorySize64 }
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        if ($elapsed -gt $maxSeconds) { $proc.Kill(); $proc.WaitForExit(); throw 'STOP_GMSH_WALL_LIMIT' }
        if ($proc.PrivateMemorySize64 -gt $maxPrivateBytes) { $proc.Kill(); $proc.WaitForExit(); throw 'STOP_GMSH_MEMORY_LIMIT' }
        if ((Test-Path -LiteralPath $mesh) -and ((Get-Item -LiteralPath $mesh).Length -gt $maxMeshBytes)) {
            $proc.Kill(); $proc.WaitForExit(); throw 'STOP_GMSH_OUTPUT_LIMIT'
        }
    }
    $proc.WaitForExit()
    $outTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CX_GMSH_STDOUT.txt') -Encoding UTF8
    $errTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CX_GMSH_STDERR.txt') -Encoding UTF8
    $resultLines.Add('GMSH_EXIT=' + $proc.ExitCode)
    $resultLines.Add('GMSH_PEAK_PRIVATE_GIB=' + [Math]::Round($peakPrivate / 1GB, 4))
    $resultLines.Add('GMSH_WALL_S=' + [Math]::Round(((Get-Date)-$startTime).TotalSeconds, 3))
    if ($proc.ExitCode -ne 0) { throw 'STOP: Gmsh native nonzero exit' }
    if (-not (Test-Path -LiteralPath $mesh -PathType Leaf)) { throw 'STOP: no output MSH' }
    if ((Get-Item -LiteralPath $mesh).Length -gt $maxMeshBytes) { throw 'STOP: output MSH exceeds 150MiB' }
    $resultLines.Add('MSH_BYTES=' + (Get-Item -LiteralPath $mesh).Length)
    $resultLines.Add('MSH_SHA256=' + (Get-FileHash -LiteralPath $mesh -Algorithm SHA256).Hash.ToLowerInvariant())

    $qaDir = Join-Path $runDir 'QA'
    New-Item -ItemType Directory -Path $qaDir | Out-Null
    & $pythonCmd.Source @pythonPrefix $audit --mesh $mesh --out-dir $qaDir *> (Join-Path $runDir 'P10CX_QA_STDOUT.txt')
    $qaExit = $LASTEXITCODE
    $resultLines.Add('QA_NATIVE_EXIT=' + $qaExit)
    if ($qaExit -ne 0) { throw ('STOP: surface QA native exit ' + $qaExit) }
    $qa = Get-Content -LiteralPath (Join-Path $qaDir 'P10CX_SURFACE_QA.json') -Raw | ConvertFrom-Json
    $resultLines.Add('PORE_TRI6=' + [string]$qa.pore_tri6)
    $resultLines.Add('WORST_CORNER_Q=' + [string]$qa.min_corner_quality)
    $resultLines.Add('BAD_Q0P1_COUNT=' + [string]$qa.below_q0p1)
    $resultLines.Add('WORST_MU_BIN=' + [string]$qa.worst_tri6.mu_bin)
    $resultLines.Add('WORST_PHI_BIN=' + [string]$qa.worst_tri6.phi_bin)

    if ($qa.below_q0p1 -gt 0) {
        $status = 'P10CX_STOP_SURFACE_POLE_SLIVER_NO_3D_NO_FEM'
        $exitNumber = 0
    } else {
        $status = 'P10CX_SURFACE_QA_NO_SLIVER_NO_3D_NO_FEM'
        $exitNumber = 0
    }
} catch {
    $resultLines.Add('STOP_REASON=' + $_.Exception.Message)
    Write-Host ('P10CX safely stopped: ' + $_.Exception.Message)
} finally {
    if ($null -ne $proc) {
        try { if (-not $proc.HasExited) { $proc.Kill(); $proc.WaitForExit() } } catch { }
    }
    if ($null -ne $runDir -and (Test-Path -LiteralPath $runDir)) {
        if ($null -ne $proc) {
            try {
                if ($null -ne $outTask -and -not (Test-Path -LiteralPath (Join-Path $runDir 'P10CX_GMSH_STDOUT.txt'))) {
                    $outTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CX_GMSH_STDOUT.txt') -Encoding UTF8
                }
                if ($null -ne $errTask -and -not (Test-Path -LiteralPath (Join-Path $runDir 'P10CX_GMSH_STDERR.txt'))) {
                    $errTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CX_GMSH_STDERR.txt') -Encoding UTF8
                }
            } catch { $resultLines.Add('LOG_CAPTURE_PARTIAL=' + $_.Exception.Message) }
        }
        $resultLines.Add('RESULT=' + $status)
        $resultLines | Set-Content -LiteralPath (Join-Path $runDir 'P10CX_RESULT.txt') -Encoding UTF8
        $paths = @(Get-ChildItem -LiteralPath $runDir -Filter '*.txt' -File | Select-Object -ExpandProperty FullName)
        $qaDir = Join-Path $runDir 'QA'
        if (Test-Path -LiteralPath $qaDir) { $paths += @(Get-ChildItem -LiteralPath $qaDir -File | Select-Object -ExpandProperty FullName) }
        if ($paths.Count -gt 0) { Compress-Archive -LiteralPath $paths -DestinationPath (Join-Path $runDir 'P10CX_EVIDENCE.zip') -CompressionLevel Optimal }
        Write-Host ('P10CX RESULT=' + $status)
        Write-Host ('P10CX EVIDENCE=' + (Join-Path $runDir 'P10CX_EVIDENCE.zip'))
        Write-Host 'Keep MSH locally; only send small P10CX_EVIDENCE.zip.'
    } else { Write-Host ('P10CX RESULT=' + $status) }
}
exit $exitNumber
