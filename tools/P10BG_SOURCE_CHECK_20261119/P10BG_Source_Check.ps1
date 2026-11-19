param(
    [string]$ProjectRoot = 'G:\ildar\Stage3D07'
)

# P10BG read-only Windows source provenance check. PowerShell 5.1 compatible.
# This program NEVER writes into ProjectRoot, runs no FEM, and changes no Git ref.
$ErrorActionPreference = 'Stop'

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw ('Project directory not found: ' + $ProjectRoot)
    }

    $toolDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outDir = Join-Path $toolDir ('P10BG_SOURCE_CHECK_' + $stamp + '_' + $PID)
    [void](New-Item -ItemType Directory -Path $outDir -ErrorAction Stop)
    $reportFile = Join-Path $outDir 'P10BG_LOCAL_SOURCE_REPORT.txt'
    $hashFile = Join-Path $outDir 'P10BG_SHA256.csv'

    $lines = New-Object 'System.Collections.Generic.List[string]'
    function Add-Report([string]$Line) {
        [void]$lines.Add($Line)
        Write-Host $Line
    }

    Add-Report 'P10BG LOCAL SOURCE CHECK (read-only)'
    Add-Report ('time_local=' + (Get-Date).ToString('o'))
    Add-Report ('project_root=' + $ProjectRoot)
    Add-Report 'expected_set=P10BF archived user source files plus later P10AZ/P10V originals'
    Add-Report 'No source/build/mesh/Local_Runs files were modified.'

    $git = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($null -eq $git) {
        Add-Report 'git_status=UNAVAILABLE (git.exe not found on PATH)'
    } else {
        $gitChecks = @(
            [pscustomobject]@{Label = 'git_HEAD'; Args = @('rev-parse', 'HEAD')},
            [pscustomobject]@{Label = 'git_branch'; Args = @('branch', '--show-current')},
            [pscustomobject]@{Label = 'git_status_seven_paths'; Args = @(
                'status', '--porcelain=v1', '--',
                'CMakeLists.txt',
                'src/stage3d10p_partial_audit.cpp',
                'src/stage3d10w_analytic_adjoint.cpp',
                'src/stage3d10v_analytic_shape.hpp',
                'src/stage3d10az_probe_export.hpp',
                'src/stage3d10ba_polar_export.hpp',
                'tests/stage3d10v_analytic_shape.cpp'
            )}
        )
        foreach ($check in $gitChecks) {
            $gitArgs = @('-C', $ProjectRoot) + $check.Args
            $resultLines = & $git.Source @gitArgs 2>&1
            $gitExit = $LASTEXITCODE
            Add-Report ($check.Label + '_exit=' + $gitExit)
            if (@($resultLines).Count -eq 0) {
                Add-Report ('  ' + $check.Label + '=EMPTY')
            } else {
                foreach ($line in @($resultLines)) {
                    Add-Report ('  ' + [string]$line)
                }
            }
        }
    }

    $expected = @(
        [pscustomobject]@{Path = 'CMakeLists.txt'; Sha256 = '453f41a086b1284a7c4da4bba2e343b106edae602adc2ee180fa9fd91abbbddf'},
        [pscustomobject]@{Path = 'src\stage3d10p_partial_audit.cpp'; Sha256 = '73cdbf9ee75de9f32ae8490baeedd760b00797670a4c6c869277405e45963f7a'},
        [pscustomobject]@{Path = 'src\stage3d10w_analytic_adjoint.cpp'; Sha256 = '70873515734edaa42ce96366e636fa6c385a114cd08564817b283fadeccdcd46'},
        [pscustomobject]@{Path = 'src\stage3d10v_analytic_shape.hpp'; Sha256 = 'ad9b5f8d24dcbbbd7678a01a32ef5947e198173c779c7e4efe1da48beca4f7e3'},
        [pscustomobject]@{Path = 'src\stage3d10az_probe_export.hpp'; Sha256 = '9bf6b9729da9e2ff698ef8f890fcc88b8d3fb2ef787708992605a72d0ec8e57d'},
        [pscustomobject]@{Path = 'src\stage3d10ba_polar_export.hpp'; Sha256 = '92b81c258b11fad8ccd4915d215f567cbdf61b642c61e9dbe47732b294ead373'},
        [pscustomobject]@{Path = 'tests\stage3d10v_analytic_shape.cpp'; Sha256 = 'f5c70aba380da9a45c234b33c8ac2f90879d1d59784033a759b7193ab111ca12'}
    )

    $hashRows = New-Object 'System.Collections.Generic.List[object]'
    $matched = 0
    foreach ($item in $expected) {
        $file = Join-Path $ProjectRoot $item.Path
        $actual = ''
        $status = 'MISSING'
        if (Test-Path -LiteralPath $file -PathType Leaf) {
            $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actual -eq $item.Sha256) {
                $status = 'EXACT_SHA256'
                $matched++
            } else {
                $status = 'DIFFERENT_BYTES'
            }
        }
        [void]$hashRows.Add([pscustomobject]@{
            path = $item.Path
            status = $status
            actual_sha256 = $actual
            archived_sha256 = $item.Sha256
        })
        Add-Report ('source[' + $item.Path + ']=' + $status + ' actual_sha256=' + $actual)
    }

    $hashRows | Export-Csv -LiteralPath $hashFile -NoTypeInformation -Encoding UTF8
    Add-Report ('exact_source_matches=' + $matched + '/7')
    Add-Report 'DIFFERENT_BYTES alone does not prove a numerical difference: compare contents before any replacement.'
    Add-Report 'Do not run git pull, patch import, or CMake reconfigure merely because this check differs.'
    Add-Report ('report=' + $reportFile)
    Add-Report ('hash_csv=' + $hashFile)
    [System.IO.File]::WriteAllLines($reportFile, $lines, [System.Text.UTF8Encoding]::new($false))
    Write-Host 'P10BG_SOURCE_CHECK_OK' -ForegroundColor Green
    exit 0
} catch {
    Write-Host ('P10BG_SOURCE_CHECK_FAILED: ' + $_.Exception.Message) -ForegroundColor Red
    exit 2
}
