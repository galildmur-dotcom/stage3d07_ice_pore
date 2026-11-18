#requires -Version 5.1
# Package only small diagnostic outputs, never checkpoint/mesh/VTU.
param([string]$ResultsDir = '')
$ErrorActionPreference = 'Stop'
$OutDir = 'G:\ildar\PORE_CHATGPT_EXPORTS'
$patterns = @(
 'P10Y_SHELL_SUMMARY.csv','P10Y_PARTITION_AUDIT.csv',
 'P10W_COMPONENTS.csv','P10W_ANALYTIC_ADJOINT.csv',
 'P10Y_STEP_SHELL_COMPONENTS.csv','P10W_STEP_COMPONENTS.csv',
 'RUN_MANIFEST.json',
 'P10Z_MESH_QP_SHELL_METRICS.csv','P10Z_RADIAL_CUMULATIVE.csv',
 'P10Z_MESH_AUDIT_LOG.txt'
)
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if ([string]::IsNullOrWhiteSpace($ResultsDir)) {
        $d = New-Object System.Windows.Forms.FolderBrowserDialog
        $d.Description = 'Select completed FEM calculation folder'
        $d.ShowNewFolderButton = $false
        if ($d.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
        $ResultsDir = $d.SelectedPath
    }
    $ResultsDir = [IO.Path]::GetFullPath($ResultsDir)
    if (-not (Test-Path -LiteralPath $ResultsDir -PathType Container)) { throw 'Run folder missing.' }
    $picked = @()
    foreach ($name in $patterns) {
        $f = Join-Path $ResultsDir $name
        if (Test-Path -LiteralPath $f -PathType Leaf) {
            if ((Get-Item -LiteralPath $f).Length -gt 15MB) { throw "Unusually large diagnostic file: $name" }
            $picked += $f
        }
    }
    if ($picked.Count -eq 0) { throw 'No matching diagnostic CSV/manifest found. Choose the FULL run folder.' }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $label = [IO.Path]::GetFileName($ResultsDir.TrimEnd('\')) -replace '[^A-Za-z0-9_\-]', '_'
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $zip = Join-Path $OutDir "RUN_${label}_$stamp.zip"
    $z = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        $manifest = @("source_folder=$ResultsDir", "packaged=$((Get-Date).ToString('o'))")
        foreach ($f in $picked) {
            [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z,$f,[IO.Path]::GetFileName($f),[System.IO.Compression.CompressionLevel]::Optimal)
            $sum = (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLowerInvariant()
            $manifest += "$sum  $([IO.Path]::GetFileName($f))"
        }
        $entry = $z.CreateEntry('RESULTS_INFO_SHA256.txt')
        $w = [System.IO.StreamWriter]::new($entry.Open(), [System.Text.UTF8Encoding]::new($false))
        try { $w.Write(($manifest -join "`n")) } finally { $w.Dispose() }
    } finally { $z.Dispose() }
    Write-Host "`nRESULTS PACKAGE READY: $zip" -ForegroundColor Green
    Write-Host ('Included: ' + (($picked | ForEach-Object { [IO.Path]::GetFileName($_) }) -join ', '))
    Start-Process explorer.exe -ArgumentList ('/select,"{0}"' -f $zip)
} catch {
    Write-Host "PACKAGING FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
