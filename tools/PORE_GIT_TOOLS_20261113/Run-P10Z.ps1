#requires -Version 5.1
# P10Z: read-only quadrature diagnostic for existing H4 & H4W2 meshes.
$ErrorActionPreference = 'Stop'
$Repo = 'G:\ildar\Stage3D07'
$Base = 'G:\ildar\PORE_GIT_TOOLS'
$Logs = Join-Path $Base 'logs'
$Runner = Join-Path $Repo 'tools\p10z_mesh_shell_audit.py'
$OutRoot = Join-Path $Repo 'P10Z_RUNS'
$MeshOne = Join-Path $Repo 'P10M_MESHES\H4.msh'
$MeshTwo = Join-Path $Repo 'P10M_MESHES\H4W2.msh'
$started = $false
Add-Type -AssemblyName System.Windows.Forms
function Need-File([string]$current, [string]$prompt) {
    if (Test-Path -LiteralPath $current -PathType Leaf) { return $current }
    $d = New-Object System.Windows.Forms.OpenFileDialog
    $d.Title = $prompt
    $d.Filter = 'Gmsh MSH files (*.msh)|*.msh|All files (*.*)|*.*'
    $d.CheckFileExists = $true
    if (Test-Path $Repo) { $d.InitialDirectory = $Repo }
    if ($d.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'Mesh selection cancelled; no calculation started.' }
    return $d.FileName
}
try {
    New-Item -ItemType Directory -Force -Path $Logs | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    Start-Transcript -Path (Join-Path $Logs "P10Z_$stamp.log") | Out-Null
    $started = $true
    Write-Host '=== PORE ONE CLICK: P10Z GEOMETRY-ONLY MESH AUDIT ===' -ForegroundColor Cyan
    if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
        throw "P10Z program not found: $Runner. Apply the P10Z Git patch using PORE - 1 first."
    }
    $MeshOne = Need-File $MeshOne 'Select the existing H4.msh (without changing it)'
    $MeshTwo = Need-File $MeshTwo 'Select the existing H4W2.msh (without changing it)'
    if ($MeshOne -eq $MeshTwo) { throw 'H4 and H4W2 are the same file: select two different meshes.' }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    $pythonArgs = @('-3')
    if (-not $py) {
        $py = Get-Command python.exe -ErrorAction SilentlyContinue
        $pythonArgs = @()
    }
    if (-not $py) { throw 'Python 3 not found (py.exe/python.exe). Install Python 3 or provide a Python installation.' }
    $exe = $py.Source
    Write-Host "Python: $exe"
    # Windows PowerShell 5.1 may strip quotes inside native -c arguments.
    # Use a NumPy probe without embedded Python string literals.
    & $exe @pythonArgs -c 'import numpy; print(numpy.__version__)'
    if ($LASTEXITCODE -ne 0) {
        $choice = [System.Windows.Forms.MessageBox]::Show(
            'NumPy is missing for this Python. Install user-local NumPy with pip now? This does not modify the Git repository.',
            'P10Z requires NumPy', [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Question)
        if ($choice -ne [System.Windows.Forms.DialogResult]::Yes) { throw 'NumPy installation declined; no calculation started.' }
        & $exe @pythonArgs -m pip install --user numpy
        if ($LASTEXITCODE -ne 0) { throw 'NumPy installation failed.' }
        & $exe @pythonArgs -c 'import numpy; print(numpy.__version__)'
        if ($LASTEXITCODE -ne 0) { throw 'NumPy remains unavailable after install.' }
    }
    & $exe @pythonArgs $Runner --selftest
    if ($LASTEXITCODE -ne 0) { throw 'P10Z selftest failed; calculations were not started.' }
    New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $output = Join-Path $OutRoot "H4_H4W2_Q3_Q4_$stamp"
    if (Test-Path -LiteralPath $output) { throw "Output folder already exists: $output" }
    Write-Host "H4: $MeshOne"
    Write-Host "H4W2: $MeshTwo"
    Write-Host "New output: $output"
    Write-Host 'Only mesh geometry and quadrature; NO thermo-mechanical/adjoint solve.' -ForegroundColor Yellow
    & $exe @pythonArgs $Runner --mesh "H4=$MeshOne" --mesh "H4W2=$MeshTwo" --out $output --orders 3 4
    if ($LASTEXITCODE -ne 0) { throw 'P10Z diagnostic failed; original meshes were not modified.' }
    Write-Host "`nP10Z FINISHED: $output" -ForegroundColor Green
    Write-Host 'Creating the compact 3-file ZIP using PORE package results...'
    $packager = Join-Path $Base 'Package-Run-Results.ps1'
    if (-not (Test-Path -LiteralPath $packager -PathType Leaf)) { throw "Packaging script missing: $packager" }
    & $packager -ResultsDir $output
    $recent = Get-ChildItem -LiteralPath 'G:\ildar\PORE_CHATGPT_EXPORTS' -Filter ("RUN_{0}_*.zip" -f ([IO.Path]::GetFileName($output))) -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $recent) { throw 'Results ZIP was not found; diagnostic files remain in the output folder. Use PORE - 3 to package manually.' }
    Write-Host 'Send the RUN_H4_H4W2_Q3_Q4_....zip generated in G:\ildar\PORE_CHATGPT_EXPORTS to ChatGPT.' -ForegroundColor Green
} catch {
    Write-Host "`nP10Z STOPPED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'No original mesh, source or existing results were overwritten.' -ForegroundColor Yellow
    exit 1
} finally {
    if ($started) { Stop-Transcript | Out-Null }
}
