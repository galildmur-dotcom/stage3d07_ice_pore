# Stage3D07 P10BS: Windows PowerShell 5.1. Read ONLY original four CSVs.
# Creates a new independent evidence folder OUTSIDE the original project.
# NO commands modify source files, Git, CMake, Qt, FEM, meshes or checkpoints.
param([string]$ProjectRoot = 'G:\ildar\Stage3D07')

$ErrorActionPreference = 'Stop'
$revision = 'P10BS_R1_EXISTING_FOUR_RAW_POLAR_CSV'
$report = New-Object 'System.Collections.Generic.List[string]'
$outDir = ''
$exitCode = 2
$filesForZip = New-Object 'System.Collections.Generic.List[string]'

function Add-Report([string]$line) {
    [void]$script:report.Add($line)
    Write-Host $line
}

$runs = @(
    @{ Label = 'DT150'; Dt = 150; Steps = 6; Dir = 'P10BD_H2_DT150_20261118_145403' },
    @{ Label = 'DT75'; Dt = 75; Steps = 12; Dir = 'P10BD_H2_DT75_20261118_145403' },
    @{ Label = 'DT50'; Dt = 50; Steps = 18; Dir = 'P10BD_H2_DT50_20261118_145403' },
    @{ Label = 'DT25'; Dt = 25; Steps = 36; Dir = 'P10BE_H2_DT25_20261118_182525' }
)

try {
    $expectedRoot = 'G:\ildar\Stage3D07'
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw 'Stage3D07 project directory not found.'
    }
    $actualRoot = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath.TrimEnd('\')
    if ($actualRoot -ine $expectedRoot) { throw 'Unexpected project directory; stop.' }
    $parentDir = Split-Path -Parent $actualRoot
    $outDir = Join-Path $parentDir ('P10BS_EXPORT_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + $PID)
    if (Test-Path -LiteralPath $outDir) { throw 'Evidence output directory already exists.' }
    [void](New-Item -ItemType Directory -Path $outDir)

    Add-Report 'P10BS FOUR EXISTING RAW POLAR CSV EXPORT (READ-ONLY SOURCE, NO FEM)'
    Add-Report ('TOOL_REVISION=' + $revision)
    Add-Report ('DATE_LOCAL=' + (Get-Date).ToString('o'))
    Add-Report ('ORIGINAL_PROJECT=' + $actualRoot)
    Add-Report ('OUTPUT_ROOT=' + $outDir)
    Add-Report 'EXPECTED_ROWS=1200,2400,3600,7200'

    $preflight = New-Object 'System.Collections.Generic.List[object]'
    $expectedColumns = @('mesh', 'time_step', 'time_s', 'radial_subbin',
        'polar_band', 'qp_count', 'positive_qp', 'negative_qp', 'qp_volume_m3',
        'explicit_per_m', 'equilibrium_per_m', 'history_per_m', 'total_mechanical_per_m')
    foreach ($r in $runs) {
        $source = Join-Path (Join-Path $actualRoot ('LOCAL_RUNS\' + $r.Dir)) 'P10BD_QP_POLAR_RADIAL.csv'
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
            throw ('Expected existing CSV missing: ' + $source)
        }
        $entries = @(Import-Csv -LiteralPath $source)
        $expectedRows = 200 * [int]$r.Steps
        if ($entries.Count -ne $expectedRows) {
            throw ('Wrong row count in ' + $r.Label + ': ' + $entries.Count + ' expected ' + $expectedRows)
        }
        $presentColumns = @($entries[0].PSObject.Properties.Name)
        foreach ($col in $expectedColumns) {
            if ($presentColumns -cnotcontains $col) { throw ('Missing column in ' + $r.Label + ': ' + $col) }
        }
        $seen = @{}
        foreach ($entry in $entries) {
            $n = [int]$entry.time_step
            if ($entry.mesh -cne 'H2' -or $n -lt 1 -or $n -gt [int]$r.Steps -or
                [int]$entry.time_s -ne ($n * [int]$r.Dt)) {
                throw ('Wrong mesh/step/time at ' + $r.Label + ' step ' + $n)
            }
            if ([int]$entry.qp_count -ne ([int]$entry.positive_qp + [int]$entry.negative_qp)) {
                throw ('QP partition mismatch in ' + $r.Label)
            }
            $slot = [string]$n
            if (-not $seen.ContainsKey($slot)) { $seen[$slot] = 0 }
            $seen[$slot]++
        }
        for ($step = 1; $step -le [int]$r.Steps; $step++) {
            if ($seen[[string]$step] -ne 200) { throw ('Step row count is not 200 in ' + $r.Label) }
        }
        $sha = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
        [void]$preflight.Add(@{ Run = $r; Source = $source; Sha = $sha; Count = $entries.Count })
        Add-Report ('PREFLIGHT_' + $r.Label + '=OK rows=' + $entries.Count +
            ' steps=' + $r.Steps + ' dt=' + $r.Dt + ' sha256=' + $sha)
    }
    Add-Report 'ALL_FOUR_PREFLIGHT=OK'

    foreach ($item in $preflight) {
        $destName = ([string]$item.Run.Label) + '_P10BD_QP_POLAR_RADIAL.csv'
        $dest = Join-Path $outDir $destName
        Copy-Item -LiteralPath ([string]$item.Source) -Destination $dest -ErrorAction Stop
        $copySha = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($copySha -cne [string]$item.Sha) { throw ('Copied CSV SHA mismatch: ' + $destName) }
        $sourceAfter = (Get-FileHash -LiteralPath ([string]$item.Source) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($sourceAfter -cne [string]$item.Sha) { throw ('Source changed during export: ' + $item.Run.Label) }
        [void]$filesForZip.Add($dest)
        Add-Report ('COPIED_' + $item.Run.Label + '=SHA256_MATCH name=' + $destName +
            ' sha256=' + $copySha)
    }
    Add-Report 'SOURCE_FOUR_SHA256_UNCHANGED=YES'
    Add-Report 'RESULT=P10BS_FOUR_EXISTING_RAW_POLAR_CSV_READY_NO_FEM'
    $exitCode = 0
} catch {
    Add-Report ('RESULT=P10BS_STOPPED: ' + $_.Exception.Message)
    Add-Report 'DO_NOT_RERUN_BLINDLY=YES'
} finally {
    if ($outDir -ne '') {
        try {
            $reportPath = Join-Path $outDir 'P10BS_RESULT.txt'
            [System.IO.File]::WriteAllLines($reportPath, [string[]]$report,
                (New-Object System.Text.UTF8Encoding($false)))
            [void]$filesForZip.Add($reportPath)
            $zipPath = Join-Path $outDir 'P10BS_EVIDENCE.zip'
            Compress-Archive -LiteralPath ([string[]]$filesForZip.ToArray()) -DestinationPath $zipPath -CompressionLevel Optimal
            Write-Host ('P10BS report: ' + $reportPath)
            Write-Host ('P10BS evidence ZIP: ' + $zipPath)
        } catch {
            Write-Host ('Could not package P10BS evidence: ' + $_.Exception.Message)
            $exitCode = 2
        }
    }
}
exit $exitCode
