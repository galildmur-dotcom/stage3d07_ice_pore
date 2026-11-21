#requires -Version 5.1
# P10CP R1: launch only a pinned READ-ONLY Python audit, no build/mesher/FEM.
$ErrorActionPreference = 'Stop'
$toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = 'G:\ildar\Stage3D07\P10M_MESHES'
$projectRoot = 'G:\ildar\Stage3D07'
$pyScript = Join-Path $toolDir 'P10CP_mesh_b6_profile.py'
$expectedScriptSha256 = '675bc41523af2013cfdce59ac66c25417e5e7efd9a400c6088b8c454788360f3'

try {
    if (-not (Test-Path -LiteralPath $pyScript -PathType Leaf)) {
        throw 'Missing P10CP_mesh_b6_profile.py; extract the complete package.'
    }
    $actualScriptSha256 = (Get-FileHash -LiteralPath $pyScript -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualScriptSha256 -ne $expectedScriptSha256) {
        throw 'Pinned P10CP Python script SHA-256 mismatch. STOP; do not modify the package.'
    }
    $targetToolDir = [System.IO.Path]::GetFullPath($toolDir).TrimEnd('\')
    $targetProjectRoot = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\')
    $toolVolume = [System.IO.Path]::GetPathRoot($targetToolDir).TrimEnd('\')
    if (($toolVolume -eq 'G:') -or ($toolVolume -eq 'F:')) {
        throw 'Unpack the tool on C: (or another non-G:/F: drive). No G:/F: outputs are allowed.'
    }
    if (($targetToolDir -eq $targetProjectRoot) -or $targetToolDir.StartsWith($targetProjectRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Tool must be extracted OUTSIDE the user project G:\ildar\Stage3D07.'
    }
    if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
        throw 'The original G:\ildar\Stage3D07\P10M_MESHES directory is missing. Do not copy/rename the source meshes.'
    }
    $launcher = $null
    $cmdArgs = @()
    $candidate = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($null -ne $candidate) {
        & $candidate.Source -3 -V | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $launcher = $candidate.Source
            $cmdArgs = @('-3')
        }
    }
    if ($null -eq $launcher) {
        $candidate = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -ne $candidate) {
            & $candidate.Source -V | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $launcher = $candidate.Source
            }
        }
    }
    if ($null -eq $launcher) {
        throw 'Python 3 cannot be started. No mesh access was attempted.'
    }
    Write-Host 'P10CP: checking the exact pinned script against in-memory unit tests.'
    & $launcher @cmdArgs $pyScript --selftest
    $unitExit = $LASTEXITCODE
    if ($null -eq $unitExit -or $unitExit -ne 0) {
        throw 'P10CP selftest did not return native exit 0. STOP.'
    }
    Write-Host 'P10CP: reading three original mesh files, no changes to G: or F:.'
    $cmdArgs += @($pyScript, '--mesh-root', $sourceRoot)
    & $launcher @cmdArgs
    $nativeExit = $LASTEXITCODE
    if ($null -eq $nativeExit) {
        throw 'Native Python exit code was unavailable; STOP.'
    }
    if ($nativeExit -ne 0) {
        Write-Host ('RESULT=P10CP_STOP_NATIVE_EXIT_' + $nativeExit)
        exit 2
    }
    Write-Host 'P10CP: native exit=0. Verify RESULT.txt before sending one evidence ZIP.'
    exit 0
}
catch {
    Write-Host ('RESULT=P10CP_STOP_LAUNCH ' + $_.Exception.Message)
    Write-Host 'No Gmsh, remesh, or FEM was started.'
    exit 2
}
