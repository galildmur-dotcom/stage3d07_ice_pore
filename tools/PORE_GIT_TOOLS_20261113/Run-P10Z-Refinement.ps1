#requires -Version 5.1
# P10Z-R: geometry-only refined-mesh audit; does not touch FEM states or Git.
# Reads H4W4B2 and, if available/confirmed, H4W2B20.
$ErrorActionPreference = 'Stop'
$Repo = 'G:\ildar\Stage3D07'
$Base = 'G:\ildar\PORE_GIT_TOOLS'
$Logs = Join-Path $Base 'logs'
$Runner = Join-Path $Repo 'tools\p10z_mesh_shell_audit.py'
$OutRoot = Join-Path $Repo 'P10Z_RUNS'
$Export = 'G:\ildar\PORE_CHATGPT_EXPORTS'
$started = $false
Add-Type -AssemblyName System.Windows.Forms

function Find-Candidate([string]$Name) {
    $paths = @(
        (Join-Path $Repo ('P10M_MESHES\' + $Name + '.msh')),
        (Join-Path $Repo ('gmsh\' + $Name + '.msh')),
        (Join-Path $Repo ('meshes\' + $Name + '.msh')),
        (Join-Path $Repo ('LOCAL_MESHES\' + $Name + '.msh'))
    )
    foreach ($p in $paths) {
        if (Test-Path -LiteralPath $p -PathType Leaf) { return $p }
    }
    return ''
}
function Select-Mesh([string]$Name, [bool]$Required) {
    $found = Find-Candidate $Name
    if ($found) {
        Write-Host "Using $Name : $found"
        return $found
    }
    if (-not $Required) {
        $want = [System.Windows.Forms.MessageBox]::Show(
            "Optional control mesh $Name was not found in standard folders. Select it manually? Choose No to audit only H4W4B2.",
            'Optional independent volumetric mesh',
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Question)
        if ($want -ne [System.Windows.Forms.DialogResult]::Yes) { return '' }
    }
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = 'Select existing ' + $Name + '.msh (read-only)'
    $dialog.Filter = 'Gmsh MSH files (*.msh)|*.msh|All files (*.*)|*.*'
    $dialog.CheckFileExists = $true
    if (Test-Path -LiteralPath $Repo) { $dialog.InitialDirectory = $Repo }
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        if ($Required) { throw "Required $Name mesh was not selected; no calculations started." }
        return ''
    }
    $choice = $dialog.FileName
    if ($choice -notmatch ([regex]::Escape($Name))) {
        $confirm = [System.Windows.Forms.MessageBox]::Show(
            "The selected file name does not contain $Name. Continue with this file?`n$choice",
            'Check mesh identity',
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Warning)
        if ($confirm -ne [System.Windows.Forms.DialogResult]::Yes) {
            if ($Required) { throw 'Mesh identity not confirmed; no calculations started.' }
            return ''
        }
    }
    return $choice
}
try {
    New-Item -ItemType Directory -Force -Path $Logs | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    Start-Transcript -Path (Join-Path $Logs "P10Z_REFINED_$stamp.log") | Out-Null
    $started = $true
    Write-Host '=== PORE ONE CLICK: P10Z REFINED MESH AUDIT ===' -ForegroundColor Cyan
    Write-Host 'Target H4W4B2; optional H4W2B20. Only mesh geometry, no FEM.'
    if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
        throw 'P10Z Python script is missing. Apply the original P10Z research patch using PORE - 1 first.'
    }
    $wallMesh = Select-Mesh 'H4W4B2' $true
    $bulkMesh = Select-Mesh 'H4W2B20' $false
    if ($bulkMesh -and ([IO.Path]::GetFullPath($wallMesh) -eq [IO.Path]::GetFullPath($bulkMesh))) {
        throw 'Same input file was selected for two different meshes; nothing executed.'
    }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    $pythonArgs = @('-3')
    if (-not $py) {
        $py = Get-Command python.exe -ErrorAction SilentlyContinue
        $pythonArgs = @()
    }
    if (-not $py) { throw 'Python 3 not found. No changes made.' }
    $exe = $py.Source
    Write-Host "Python: $exe"
    # No nested quotes: native PowerShell 5.1 argument passing is sensitive here.
    & $exe @pythonArgs -c 'import numpy; print(numpy.__version__)'
    if ($LASTEXITCODE -ne 0) { throw 'NumPy is unavailable. No FEM or mesh was changed.' }
    & $exe @pythonArgs $Runner --selftest
    if ($LASTEXITCODE -ne 0) { throw 'P10Z selftest failed; no audit started.' }
    New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $label = 'H4W4B2'
    if ($bulkMesh) { $label = 'H4W4B2_H4W2B20' }
    $output = Join-Path $OutRoot ("${label}_Q3_Q4_$stamp")
    if (Test-Path -LiteralPath $output) { throw "Output folder exists: $output" }
    Write-Host "H4W4B2: $wallMesh" -ForegroundColor Yellow
    if ($bulkMesh) { Write-Host "H4W2B20: $bulkMesh" -ForegroundColor Yellow }
    Write-Host "New output folder: $output"
    $runArgs = @($Runner, '--mesh', "H4W4B2=$wallMesh")
    if ($bulkMesh) { $runArgs += @('--mesh', "H4W2B20=$bulkMesh") }
    $runArgs += @('--out', $output, '--orders', '3', '4')
    & $exe @pythonArgs @runArgs
    if ($LASTEXITCODE -ne 0) { throw 'P10Z failed. Previous evidence and original meshes were not overwritten.' }
    $metricsFile = Join-Path $output 'P10Z_MESH_QP_SHELL_METRICS.csv'
    if (-not (Test-Path -LiteralPath $metricsFile -PathType Leaf)) { throw 'P10Z metrics not generated.' }
    $records = @(Import-Csv -LiteralPath $metricsFile | Where-Object { $_.shell -eq '0' -and $_.quadrature_order -eq '3' })
    foreach ($record in $records) {
        Write-Host "AUDITED: $($record.mesh), tet10=$($record.total_tet10), Q3 first-shell points=$($record.qp_count), mesh_sha256=$($record.mesh_sha256)"
    }
    Write-Host 'Expected previous mesh counts: H4W4B2=261091; H4W2B20=292026.'
    foreach ($r in $records) {
        $expect = if ($r.mesh -eq 'H4W4B2') { 261091 } elseif ($r.mesh -eq 'H4W2B20') { 292026 } else { 0 }
        if ($expect -and ([int]$r.total_tet10 -ne $expect)) {
            Write-Warning "Mesh $($r.mesh) differs from previous count: expected $expect, actual $($r.total_tet10). Preserve SHA for provenance."
        }
    }
    $packager = Join-Path $Base 'Package-Run-Results.ps1'
    if (-not (Test-Path -LiteralPath $packager -PathType Leaf)) { throw 'PORE - 3 packager not found; outputs still in P10Z_RUNS.' }
    & $packager -ResultsDir $output
    $pattern = "RUN_${label}_Q3_Q4_${stamp}_*.zip"
    $recent = Get-ChildItem -LiteralPath $Export -Filter $pattern -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $recent) { throw "Output ZIP not detected. The three result files remain at $output" }
    Write-Host "`nP10Z_REFINED_OK: $output" -ForegroundColor Green
    Write-Host "UPLOAD TO CHATGPT: $($recent.FullName)" -ForegroundColor Green
    Write-Host 'No modification of Git, mesh source, checkpoints or existing results.'
} catch {
    Write-Host "`nP10Z REFINED STOPPED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'No original mesh, source or previous results were overwritten.' -ForegroundColor Yellow
    exit 1
} finally {
    if ($started) { Stop-Transcript | Out-Null }
}
