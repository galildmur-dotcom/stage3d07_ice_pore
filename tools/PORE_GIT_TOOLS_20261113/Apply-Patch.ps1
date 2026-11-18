#requires -Version 5.1
# One-click patch import into Stage3D07. Does not touch untracked run folders.
param([string]$PatchPath = '')
$ErrorActionPreference = 'Stop'
$Repo = 'G:\ildar\Stage3D07'
$Base = 'G:\ildar\PORE_GIT_TOOLS'
$Logs = Join-Path $Base 'logs'
$Remote = 'origin'
$Branch = 'master'
$logStarted = $false
# Git stash is used ONLY with explicit confirmation to preserve tracked edits.
# A completed stash is never deleted automatically; it remains as a second backup.
$script:PreservedEditsStash = $null
$script:PreservedEditsRestored = $false
Add-Type -AssemblyName System.Windows.Forms
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

function Invoke-Git([string[]]$GitArgs) {
    & $GitExe -C $Repo @GitArgs
    if ($LASTEXITCODE -ne 0) { throw ('Git command failed (code {0}): git {1}' -f $LASTEXITCODE, ($GitArgs -join ' ')) }
}
function Get-GitText([string[]]$GitArgs) {
    $out = & $GitExe -C $Repo @GitArgs
    if ($LASTEXITCODE -ne 0) { throw ('Git command failed (code {0}): git {1}' -f $LASTEXITCODE, ($GitArgs -join ' ')) }
    return ($out | Out-String).Trim()
}
function Ensure-AllowedChanges([string[]]$Names) {
    if ($Names.Count -eq 0) { throw 'Patch made no staged changes.' }
    foreach ($name in $Names) {
        $path = $name.Replace('\','/')
        $allowed = ($path -match '^(docs|article|experiments|gmsh|src|tests|tools|cmake)/') -or
                   ($path -in @('CMakeLists.txt', 'README.md', '.gitignore', '.gitattributes'))
        if (-not $allowed) { throw "Path outside allowed source/doc folders: $path" }
        if ($path -match '(?i)(^|/)(LOCAL_RUNS|LOCAL_RUNS_OPTIMIZED|build|CMakeFiles)(/|$)' -or
            $path -match '(?i)\.(msh|vtu|vtk|exe|dll|pdb|bin|restart)$') {
            throw "Run/binary artifact not allowed in commit: $path"
        }
    }
}
function Restore-PreservedTrackedEdits {
    if (-not $script:PreservedEditsStash -or $script:PreservedEditsRestored) { return }
    # Restore only onto a clean tracked worktree and index; leave stash intact on conflict.
    $current = Get-GitText -GitArgs @('status','--porcelain','--untracked-files=no')
    if ($current) {
        Write-Warning "Preserved local edits remain in Git stash $($script:PreservedEditsStash)."
        Write-Warning 'Automatic restore skipped: the tracked worktree/index has modifications. Send the import log for safe recovery.'
        return
    }
    Write-Host "Restoring original local edits from $($script:PreservedEditsStash)..." -ForegroundColor Cyan
    & $GitExe -C $Repo stash apply $script:PreservedEditsStash
    if ($LASTEXITCODE -eq 0) {
        $script:PreservedEditsRestored = $true
        Write-Host "ORIGINAL LOCAL EDITS RESTORED. Backup retained in stash $($script:PreservedEditsStash)." -ForegroundColor Green
    } else {
        Write-Warning "Could not restore tracked edits cleanly. They remain saved in stash $($script:PreservedEditsStash); do not discard or clean this stash. Send the import log."
    }
}
function Msg([string]$body, [string]$heading, [System.Windows.Forms.MessageBoxButtons]$buttons) {
    return [System.Windows.Forms.MessageBox]::Show($body, $heading, $buttons,
        [System.Windows.Forms.MessageBoxIcon]::Question)
}
try {
    Add-Type -AssemblyName System.Windows.Forms
    if (-not (Test-Path -LiteralPath $Repo -PathType Container)) { throw "Project folder not found: $Repo" }
    New-Item -ItemType Directory -Force -Path $Logs | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    Start-Transcript -Path (Join-Path $Logs "import_$stamp.log") | Out-Null
    $logStarted = $true
    Write-Host '=== PORE GIT: IMPORT PATCH ===' -ForegroundColor Cyan
    Write-Host "Repository: $Repo"

    if ([string]::IsNullOrWhiteSpace($PatchPath)) {
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = 'Select ChatGPT .patch file'
        $dialog.Filter = 'Git patch (*.patch)|*.patch|All files (*.*)|*.*'
        $downloads = Join-Path $env:USERPROFILE 'Downloads'
        if (Test-Path $downloads) { $dialog.InitialDirectory = $downloads }
        if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
            Write-Host 'Cancelled: nothing changed.'; exit 0
        }
        $PatchPath = $dialog.FileName
    }
    $PatchPath = [IO.Path]::GetFullPath($PatchPath)
    if (-not (Test-Path -LiteralPath $PatchPath -PathType Leaf)) { throw "Patch missing: $PatchPath" }
    if ([IO.Path]::GetExtension($PatchPath).ToLowerInvariant() -ne '.patch') { throw 'Only .patch files are accepted.' }
    if ((Get-Item -LiteralPath $PatchPath).Length -gt 25MB) { throw 'Patch larger than 25 MiB; inspect manually.' }

    $currentBranch = Get-GitText -GitArgs @('branch','--show-current')
    if ($currentBranch -ne $Branch) { throw "Wrong branch: $currentBranch (expected $Branch)." }
    # Ignore untracked run directories. Check remote equality before touching any local edit.
    Write-Host 'Fetching remote state (no pull, no rebase)...'
    Invoke-Git -GitArgs @('fetch','--quiet',$Remote,$Branch)
    $head = Get-GitText -GitArgs @('rev-parse','HEAD')
    $remoteHead = Get-GitText -GitArgs @('rev-parse',"refs/remotes/$Remote/$Branch")
    if ($head -ne $remoteHead) { throw 'Local and remote HEAD differ. Please sync/review first; no patch applied.' }

    # Require clean INDEX. Unstaged tracked changes may be preserved in stash
    # after asking; the patch is committed by itself and edits are restored later.
    $staged = Get-GitText -GitArgs @('diff','--cached','--name-only')
    if ($staged) { throw "Staged changes found: preserve/review them first; no patch applied.`n$staged" }
    $tracked = Get-GitText -GitArgs @('status','--porcelain','--untracked-files=no')
    if ($tracked) {
        $answer = Msg "Tracked edits exist (snapshot export includes only committed versions):`n$tracked`n`nSave ALL these edits safely in Git stash, import and push ONLY the selected patch, then restore your edits?`n`nA backup stash will be RETAINED even after restoration. No reset/clean/force-push." 'Preserve local edits before import' ([System.Windows.Forms.MessageBoxButtons]::YesNo)
        if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) {
            Write-Host 'Cancelled: existing local edits were not changed.'; exit 0
        }
        $backupLabel = 'PORE_ONE_CLICK_PREPATCH_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
        Invoke-Git -GitArgs @('stash','push','-m',$backupLabel)
        $script:PreservedEditsStash = Get-GitText -GitArgs @('rev-parse','refs/stash')
        Write-Host "TRACKED EDITS BACKED UP: $($script:PreservedEditsStash)" -ForegroundColor Green
        $after = Get-GitText -GitArgs @('status','--porcelain','--untracked-files=no')
        if ($after) { throw "Some tracked changes remain after stash; stop to avoid mixing:`n$after" }
    }

    Write-Host "`nPatch: $PatchPath" -ForegroundColor Yellow
    Invoke-Git -GitArgs @('apply','--stat',$PatchPath)
    Invoke-Git -GitArgs @('apply','--index','--check',$PatchPath)
    $decision = Msg "Apply the selected patch, commit only its files, and push to GitFlic?`n`n$([IO.Path]::GetFileName($PatchPath))`n`nRepository: $Repo" 'Confirm patch import' ([System.Windows.Forms.MessageBoxButtons]::YesNo)
    if ($decision -ne [System.Windows.Forms.DialogResult]::Yes) { Write-Host 'Cancelled: nothing changed.'; exit 0 }

    Invoke-Git -GitArgs @('apply','--index',$PatchPath)
    $changedText = Get-GitText -GitArgs @('diff','--cached','--name-only')
    $names = @($changedText -split "`r?`n" | Where-Object { $_ })
    Ensure-AllowedChanges $names
    $deleted = Get-GitText -GitArgs @('diff','--cached','--diff-filter=D','--name-only')
    if ($deleted) { throw "Patch deletes files; please review manually before commit:`n$deleted" }
    Invoke-Git -GitArgs @('diff','--cached','--check')
    Write-Host "`nFiles to commit:" -ForegroundColor Cyan
    Invoke-Git -GitArgs @('diff','--cached','--stat')
    $name = [IO.Path]::GetFileNameWithoutExtension($PatchPath)
    if ($name.Length -gt 65) { $name = $name.Substring(0,65) }
    Invoke-Git -GitArgs @('commit','-m',"Research patch: $name")
    Invoke-Git -GitArgs @('push',$Remote,"HEAD:$Branch")
    $newHead = Get-GitText -GitArgs @('rev-parse','HEAD')
    Restore-PreservedTrackedEdits
    Write-Host "`nSUCCESS: commit $newHead pushed to GitFlic." -ForegroundColor Green
    Write-Host 'Tip: click 02_SNAPSHOT_FOR_CHATGPT.cmd, then upload the snapshot in chat.'
} catch {
    Write-Host "`nSTOPPED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'No automatic reset/force-push was performed.' -ForegroundColor Yellow
    Write-Host 'If the patch was already applied, check git status before retrying.'
    exit 1
} finally {
    if ($script:PreservedEditsStash -and -not $script:PreservedEditsRestored) {
        try { Restore-PreservedTrackedEdits } catch {
            Write-Warning "Preserved local edits remain safe in stash $($script:PreservedEditsStash). Restore failed: $($_.Exception.Message)"
        }
    }
    if ($logStarted) { Stop-Transcript | Out-Null }
}
