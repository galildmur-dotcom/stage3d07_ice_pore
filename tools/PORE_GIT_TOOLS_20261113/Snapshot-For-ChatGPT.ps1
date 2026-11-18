#requires -Version 5.1
# Portable subset of COMMITTED code and evidence for uploading to ChatGPT.
$ErrorActionPreference = 'Stop'
$Repo = 'G:\ildar\Stage3D07'
$OutDir = 'G:\ildar\PORE_CHATGPT_EXPORTS'
# Find Git for Windows even when it is available in Git Bash but not on the normal PATH.
$GitExe = $null
$cmd = Get-Command git.exe -ErrorAction SilentlyContinue
if ($cmd) { $GitExe = $cmd.Source }
if (-not $GitExe) {
    foreach ($candidate in @('C:\Program Files\Git\cmd\git.exe',
                             'C:\Program Files\Git\bin\git.exe',
                             'C:\msys64\ucrt64\bin\git.exe',
                             'C:\msys64\usr\bin\git.exe')) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { $GitExe = $candidate; break }
    }
}
if (-not $GitExe) { throw 'Git for Windows not found. Install Git for Windows or add git.exe to PATH.' }
function GitText([string[]]$args2) {
    $x = & $GitExe -C $Repo @args2
    if ($LASTEXITCODE -ne 0) { throw "git $($args2 -join ' ') failed" }
    return ($x | Out-String).Trim()
}
try {
    if (-not (Test-Path $Repo)) { throw "Repo missing: $Repo" }
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
    $sha = GitText -args2 @('rev-parse','HEAD')
    $short = $sha.Substring(0,12)
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $zip = Join-Path $OutDir "Stage3D07_CHATGPT_${short}_$stamp.zip"
    $paths = @('docs','src','tests','gmsh','CMakeLists.txt',
       'article/EVIDENCE_REGISTER_CURRENT.md','article/MANUSCRIPT_DRAFT_RU.md',
       'article/LITERATURE_REGISTER.md','experiments/RUN_REGISTRY.csv')
    $existing = @()
    foreach ($p in $paths) {
        & $GitExe -C $Repo cat-file -e ("HEAD:" + $p) 2>$null
        if ($LASTEXITCODE -eq 0) { $existing += $p }
    }
    if ($existing.Count -eq 0) { throw 'No files found for export.' }
    & $GitExe -C $Repo archive --format=zip -o $zip HEAD -- @existing
    if ($LASTEXITCODE -ne 0) { throw 'git archive failed.' }
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $status = GitText -args2 @('status','--short','--untracked-files=no')
    $origin = GitText -args2 @('remote','get-url','origin')
    $info = @(
        'Stage3D07 snapshot for ChatGPT', "HEAD=$sha", "origin=$origin",
        "created_local=$((Get-Date).ToString('o'))", 'Included: committed docs, src, tests, gmsh, selected article and registry files',
        'Untracked calculation directories are not included.',
        'Tracked workspace status at export:', $(if ($status) { $status } else { 'clean' })
    ) -join "`n"
    $zf = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Update)
    try {
        $entry = $zf.CreateEntry('CHATGPT_SNAPSHOT_INFO.txt')
        $w = [System.IO.StreamWriter]::new($entry.Open(), [System.Text.UTF8Encoding]::new($false))
        try { $w.Write($info) } finally { $w.Dispose() }
    } finally { $zf.Dispose() }
    Write-Host "`nSNAPSHOT READY: $zip" -ForegroundColor Green
    Write-Host "HEAD: $sha"
    Write-Host "File size: $([math]::Round((Get-Item $zip).Length / 1MB, 2)) MiB"
    if ($status) { Write-Warning 'Tracked changes not committed; the snapshot contains HEAD, not these changes.' }
    Start-Process explorer.exe -ArgumentList ('/select,"{0}"' -f $zip)
} catch {
    Write-Host "SNAPSHOT FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
