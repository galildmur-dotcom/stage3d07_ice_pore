# P10CT R1: one guarded Gmsh mesh-only attempt, outside the Stage3D07 project.
# PowerShell 5.1. This file does NOT call the physical solver or alter source meshes.
$ErrorActionPreference = 'Stop'
$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runBase = Join-Path $toolRoot 'P10CT_RUNS'
$revision = 'P10CT_R1_U0_MESH_ONLY_WINDOWS'
$hMetres = 0.002
$maxSeconds = 900
$maxPrivateBytes = [Int64](8GB)
$maxMeshBytes = [Int64](750MB)
$resultLines = New-Object 'System.Collections.Generic.List[string]'
$resultLines.Add('TOOL_REVISION=' + $revision)
$resultLines.Add('PHYSICAL_FEM_RUNS=0')
$resultLines.Add('GMSH_MESH_ONLY_ATTEMPT_MAX=1')
$resultLines.Add('UNIFORM_SIZE_M=0.002')
$resultLines.Add('GMSH_THREADS=2')
$resultLines.Add('SOFT_CAP_WALL_S=900')
$resultLines.Add('SOFT_CAP_PRIVATE_GIB=8')
$resultLines.Add('SOFT_CAP_MSH_MIB=750')
$status = 'P10CT_STOP_NO_FEM'
$exitNumber = 2
$runDir = $null
$proc = $null

function Test-SourceHash([string] $filename, [string] $expected) {
    $file = Join-Path $toolRoot $filename
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw ('Missing pinned file: ' + $filename) }
    $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw ('SHA-256 mismatch: ' + $filename) }
    $resultLines.Add(('SHA256_' + $filename + '=' + $actual))
    return $file
}

try {
    $userProject = 'G:\ildar\Stage3D07'
    $rootFull = [System.IO.Path]::GetFullPath($toolRoot).TrimEnd('\')
    if ($rootFull.Equals($userProject, [StringComparison]::OrdinalIgnoreCase) -or
        $rootFull.StartsWith($userProject + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Extract this tool OUTSIDE G:\ildar\Stage3D07'
    }
    if (Test-Path -LiteralPath $runBase) {
        if ((@(Get-ChildItem -LiteralPath $runBase -Force)).Count -gt 0) {
            throw 'One-shot attempt already exists here; inspect previous result, no blind rerun'
        }
    } else { New-Item -ItemType Directory -Path $runBase | Out-Null }
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')
    $runDir = Join-Path $runBase ('P10CT_' + $stamp)
    New-Item -ItemType Directory -Path $runDir | Out-Null

    $geo = Test-SourceHash 'P10CS_U0_UNIFORM_VOLUME.geo' 'b4d7682e7c51554d9855044944f4df722a96aa30b9a73db66fba00160fb6b217'
    $base = Test-SourceHash 'sphere_pore_B6_refined.geo' '8029a6ed22bcf312701cd6abc46bbe5575e52df16fd5218dd936b01d5cd6fcf0'
    $audit = Test-SourceHash 'P10CT_u0_mesh_audit.py' '43f1cd5424be6cf8c9f0be40eb64ad0ec1f05a025b26af80fcc86cedc785477c'
    $null = Test-SourceHash 'P10CK_curved_qp_audit.py' '6386d37ade7c6cadcfdfdb511e01a06310ea9c974ee4fd7878a704bcdac9dc90'
    $null = Test-SourceHash 'P10CP_mesh_b6_profile.py' '675bc41523af2013cfdce59ac66c25417e5e7efd9a400c6088b8c454788360f3'
    $resultLines.Add('SOURCE_SHA_GATES=PASS_5_OF_5')

    $gmsh = 'C:\gmsh-4.15.2-Windows64\gmsh.exe'
    if (-not [string]::IsNullOrWhiteSpace($env:P10CT_GMSH_EXE)) { $gmsh = $env:P10CT_GMSH_EXE }
    if (-not (Test-Path -LiteralPath $gmsh -PathType Leaf)) { throw ('Gmsh 4.15.2 not found: ' + $gmsh) }
    $resultLines.Add('GMSH_EXE_SHA256=' + (Get-FileHash -LiteralPath $gmsh -Algorithm SHA256).Hash.ToLowerInvariant())

    $freeMemBytes = [Int64]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory) * 1024
    if ($freeMemBytes -lt [Int64](16GB)) { throw 'Less than 16 GiB currently available RAM' }
    $rootDrive = [System.IO.Path]::GetPathRoot($toolRoot)
    $driveName = $rootDrive.Substring(0, 1)
    $freeDiskBytes = [Int64](Get-PSDrive -Name $driveName).Free
    if ($freeDiskBytes -lt [Int64](4GB)) { throw 'Less than 4 GiB available disk' }
    $resultLines.Add('RAM_DISK_PREFLIGHT=PASS')

    $pythonCmd = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    $pythonPrefix = @()
    if ($null -eq $pythonCmd) {
        $pythonCmd = Get-Command 'python.exe' -ErrorAction SilentlyContinue
        if ($null -eq $pythonCmd) { throw 'Python 3 launcher not available' }
    } else { $pythonPrefix = @('-3') }

    & $pythonCmd.Source @pythonPrefix $audit --selftest *> (Join-Path $runDir 'P10CT_UNIT.txt')
    $unitExit = $LASTEXITCODE
    if ($unitExit -ne 0) { throw ('Python unit test failed with exit ' + $unitExit) }
    $resultLines.Add('SYNTHETIC_UNIT=PASS_EXIT_0')

    $mesh = Join-Path $runDir 'P10CT_U0_h2mm.msh'
    $arguments = '"' + $geo + '" -3 -nt 2 -format msh2 -setnumber uniformSize 0.002 -o "' + $mesh + '"'
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
    $resultLines.Add('GMSH_PROCESS_STARTED=YES')

    while (-not $proc.WaitForExit(1000)) {
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        $proc.Refresh()
        if ($proc.PrivateMemorySize64 -gt $peakPrivate) { $peakPrivate = $proc.PrivateMemorySize64 }
        if ($elapsed -gt $maxSeconds) { $proc.Kill(); $proc.WaitForExit(); throw 'STOP_GMSH_WALL_LIMIT' }
        if ($proc.PrivateMemorySize64 -gt $maxPrivateBytes) { $proc.Kill(); $proc.WaitForExit(); throw 'STOP_GMSH_MEMORY_LIMIT' }
        if ((Test-Path -LiteralPath $mesh) -and ((Get-Item -LiteralPath $mesh).Length -gt $maxMeshBytes)) {
            $proc.Kill(); $proc.WaitForExit(); throw 'STOP_GMSH_MESH_SIZE_LIMIT'
        }
    }
    $proc.WaitForExit()
    $outTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CT_GMSH_STDOUT.txt') -Encoding UTF8
    $errTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CT_GMSH_STDERR.txt') -Encoding UTF8
    $resultLines.Add('GMSH_EXIT=' + $proc.ExitCode)
    $resultLines.Add('GMSH_PEAK_PRIVATE_GIB=' + [Math]::Round($peakPrivate / 1GB, 3))
    $resultLines.Add('GMSH_WALL_SECONDS=' + [Math]::Round(((Get-Date) - $startTime).TotalSeconds, 3))
    if ($proc.ExitCode -ne 0) { throw 'Gmsh native process returned nonzero exit code' }
    if (-not (Test-Path -LiteralPath $mesh -PathType Leaf)) { throw 'Gmsh returned exit0 but no MSH produced' }
    if ((Get-Item -LiteralPath $mesh).Length -gt $maxMeshBytes) { throw 'STOP_GMSH_MESH_SIZE_LIMIT_AFTER_EXIT' }
    $resultLines.Add('U0_MESH_SHA256=' + (Get-FileHash -LiteralPath $mesh -Algorithm SHA256).Hash.ToLowerInvariant())
    $resultLines.Add('U0_MESH_BYTES=' + (Get-Item -LiteralPath $mesh).Length)

    $auditOut = Join-Path $runDir 'QA'
    New-Item -ItemType Directory -Path $auditOut | Out-Null
    & $pythonCmd.Source @pythonPrefix $audit --mesh $mesh --out-dir $auditOut --target-size-mm 2.0 *> (Join-Path $runDir 'P10CT_QA_STDOUT.txt')
    $qaExit = $LASTEXITCODE
    $resultLines.Add('QA_NATIVE_EXIT=' + $qaExit)
    if ($qaExit -ne 0) { throw 'U0 structural/curved-QP mesh QA STOP; inspect QA files' }

    # Do not interpret a mesh-only QA pass as permission or readiness for FEM.
    $status = 'P10CT_U0_GEOMETRY_QA_OK_NO_FEM'
    $exitNumber = 0
} catch {
    $resultLines.Add('STOP_REASON=' + $_.Exception.Message)
    Write-Host ('P10CT stopped safely: ' + $_.Exception.Message)
} finally {
    if ($null -ne $proc) {
        try { if (-not $proc.HasExited) { $proc.Kill(); $proc.WaitForExit() } } catch { }
    }
    if ($null -ne $runDir -and (Test-Path -LiteralPath $runDir)) {
        # Preserve partial Gmsh stdout/stderr even when a safety cap kills it.
        if ($null -ne $proc) {
            try {
                if ($null -ne $outTask -and -not (Test-Path (Join-Path $runDir 'P10CT_GMSH_STDOUT.txt'))) {
                    $outTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CT_GMSH_STDOUT.txt') -Encoding UTF8
                }
                if ($null -ne $errTask -and -not (Test-Path (Join-Path $runDir 'P10CT_GMSH_STDERR.txt'))) {
                    $errTask.GetAwaiter().GetResult() | Set-Content -LiteralPath (Join-Path $runDir 'P10CT_GMSH_STDERR.txt') -Encoding UTF8
                }
            } catch { $resultLines.Add('LOG_CAPTURE_PARTIAL=' + $_.Exception.Message) }
        }
        $resultLines.Add('RESULT=' + $status)
        $resultLines | Set-Content -LiteralPath (Join-Path $runDir 'P10CT_RESULT.txt') -Encoding UTF8
        $paths = @(Get-ChildItem -LiteralPath $runDir -Filter '*.txt' -File | Select-Object -ExpandProperty FullName)
        $qaDir = Join-Path $runDir 'QA'
        if (Test-Path -LiteralPath $qaDir) {
            $paths += @(Get-ChildItem -LiteralPath $qaDir -File | Select-Object -ExpandProperty FullName)
        }
        if ($paths.Count -gt 0) {
            Compress-Archive -LiteralPath $paths -DestinationPath (Join-Path $runDir 'P10CT_EVIDENCE.zip') -CompressionLevel Optimal
        }
        Write-Host ('P10CT RESULT=' + $status)
        Write-Host ('P10CT EVIDENCE=' + (Join-Path $runDir 'P10CT_EVIDENCE.zip'))
        Write-Host ('Large U0 MSH stays locally in ' + $runDir + '; do not upload it.')
    } else {
        Write-Host ('P10CT RESULT=' + $status)
    }
}
exit $exitNumber
