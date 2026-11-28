#requires -Version 5.1
# Installs only local helper scripts outside the Git repository.
$ErrorActionPreference = 'Stop'
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dest = 'G:\ildar\PORE_GIT_TOOLS'
try {
    if (-not (Test-Path 'G:\ildar\Stage3D07\.git')) { throw 'Repository G:\ildar\Stage3D07\.git not found.' }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    if ([IO.Path]::GetFullPath($Source).TrimEnd('\') -ne [IO.Path]::GetFullPath($Dest).TrimEnd('\')) {
        Get-ChildItem -LiteralPath $Source -File | Where-Object { $_.Extension -in @('.ps1','.cmd','.txt') } |
            Copy-Item -Destination $Dest -Force
    }
    # Validate exact UTF-8 BOM and Windows PowerShell 5.1 parsing of every installed script.
    # A duplicated BOM (EF BB BF EF BB BF) breaks #requires and param() at startup.
    $installedScripts = @(Get-ChildItem -LiteralPath $Source -File -Filter '*.ps1')
    foreach ($sourceScript in $installedScripts) {
        $target = Join-Path $Dest $sourceScript.Name
        $bytes = [System.IO.File]::ReadAllBytes($target)
        if ($bytes.Length -lt 13 -or
            $bytes[0] -ne 0xEF -or $bytes[1] -ne 0xBB -or $bytes[2] -ne 0xBF -or
            $bytes[3] -ne 0x23) {
            throw "Invalid UTF-8 BOM / #requires in installed file: $target"
        }
        $tokens = $null
        $parseErrors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile(
            $target, [ref]$tokens, [ref]$parseErrors)
        if ($parseErrors.Count -gt 0) {
            $details = ($parseErrors | ForEach-Object { $_.Message }) -join '; '
            throw "PowerShell syntax check failed for $target : $details"
        }
    }
    Write-Host "Verified PowerShell scripts: $($installedScripts.Count)" -ForegroundColor Green
    New-Item -ItemType Directory -Force -Path (Join-Path $Dest 'logs') | Out-Null
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shell = New-Object -ComObject WScript.Shell
    $buttons = @(
        @('01_APPLY_PATCH_AND_PUSH.cmd','PORE - 1 Apply patch and push'),
        @('02_SNAPSHOT_FOR_CHATGPT.cmd','PORE - 2 Export source snapshot'),
        @('03_PACKAGE_RUN_RESULTS.cmd','PORE - 3 Package run results'),
        @('04_RUN_P10Z.cmd','PORE - 4 Run P10Z mesh audit'),
        @('05_RUN_P10Z_REFINED.cmd','PORE - 5 Audit refined H4W4B2')
    )
    foreach ($b in $buttons) {
        $shortcut = $shell.CreateShortcut((Join-Path $desktop ($b[1] + '.lnk')))
        $shortcut.TargetPath = Join-Path $Dest $b[0]
        $shortcut.WorkingDirectory = $Dest
        $shortcut.Description = 'Stage3D07 helper; does not change Git unless patch import is confirmed'
        $shortcut.Save()
    }
    Write-Host "`nINSTALLED: $Dest" -ForegroundColor Green
    Write-Host "Desktop shortcuts created: $desktop"
    Write-Host 'This installer did NOT modify the Git repository.'
} catch {
    Write-Host "INSTALL FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
