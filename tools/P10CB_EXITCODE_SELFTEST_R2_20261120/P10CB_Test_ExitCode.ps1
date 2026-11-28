# P10CB R2: read-only, unit-only native exit-code diagnostic.
# NEVER invokes FEM, --mesh, --out, --preflight, any build, or Git mutation.
# PowerShell 5.1; ASCII-only script; isolated output alongside this tool.
$ErrorActionPreference = 'Stop'
$toolRevision = 'P10CB_R2_NATIVE_EXITCODE_MIN_GW_CHILD_PATH_FIX_NO_FEM'
$expectedRoot = 'G:\ildar\Stage3D07'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$expectedExe = 'G:\Downloads\P10CA_H0_ONE_RUN_R1_20261120\P10CA_RESULTS_20261120_151200_8420\build\p10ca_h0_analytic_qp.exe'
$expectedExeSHA = '17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924'
$minGWBin = 'C:\mingw64\bin'
$gitExe = 'C:\Program Files\Git\cmd\git.exe'
$cmdExe = Join-Path $env:WINDIR 'System32\cmd.exe'
$toolRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$runDir = ''
$snapshot = $null
$outcome = 2
$testsPassed = $false
$report = New-Object 'System.Collections.Generic.List[string]'
$logs = New-Object 'System.Collections.Generic.List[string]'
$env:GIT_OPTIONAL_LOCKS = '0'

function Log-Line([string]$Line) {
    [void]$script:report.Add($Line)
    Write-Host $Line
}

function Write-Lines([string]$File, [string[]]$Lines) {
    [IO.File]::WriteAllLines($File, $Lines, [Text.UTF8Encoding]::new($false))
    [void]$script:logs.Add($File)
}

function Hash-Text([string]$Value) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally { $hash.Dispose() }
}

function Invoke-Direct([string]$Executable, [string[]]$Arguments) {
    # The exact P10BZ native pattern: capture LASTEXITCODE before ANY other call.
    $old = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $Executable @Arguments 2>&1
        $nativeExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $old }
    $lines = @($raw | ForEach-Object { [string]$_ })
    return [pscustomobject]@{Exit=$nativeExit;Lines=$lines}
}

function Get-OriginalSnapshot {
    $head = Invoke-Direct $gitExe @('-C',$expectedRoot,'rev-parse','HEAD')
    if ($head.Exit -ne 0 -or $head.Lines.Count -ne 1) {
        throw 'P10CB_STOP: cannot attest original Git HEAD'
    }
    $status = Invoke-Direct $gitExe @('-C',$expectedRoot,'-c','core.fsmonitor=false',
                                     'status','--porcelain=v1','--untracked-files=normal')
    if ($status.Exit -ne 0) { throw 'P10CB_STOP: cannot attest original Git status' }
    $lines = @($status.Lines | Where-Object { $_.Length -ge 2 })
    $staged=0; $unstaged=0; $untracked=0
    foreach ($line in $lines) {
        if ($line.Substring(0,2) -ceq '??') { ++$untracked }
        else {
            if ($line[0] -ne ' ') { ++$staged }
            if ($line[1] -ne ' ') { ++$unstaged }
        }
    }
    return [pscustomobject]@{
        Head=[string]$head.Lines[0]
        Counts=('{0}/{1}/{2}' -f $staged,$unstaged,$untracked)
        StatusSHA256=Hash-Text ([string]::Join([Environment]::NewLine,[string[]]$lines))
    }
}

function Invoke-BoundedDotNet([string]$Executable, [string]$Arguments,
                              [int]$TimeoutMs) {
    # .NET Process owns the handle; exit code is read BEFORE Dispose().
    # Both pipes are drained asynchronously to avoid full-pipe deadlock.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Executable
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $toolRoot
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    # P10CA R1 had exactly this MinGW runtime prefix during physical launch.
    # Set it ONLY in the child's environment; never mutate the host PATH.
    $psi.EnvironmentVariables['PATH'] = $minGWBin + ';' + $env:PATH
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    try {
        if (-not $proc.Start()) { throw 'P10CB_STOP: .NET Start returned false' }
        $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
        $stderrTask = $proc.StandardError.ReadToEndAsync()
        if (-not $proc.WaitForExit($TimeoutMs)) {
            try { $proc.Kill(); $proc.WaitForExit() } catch {}
            throw ('P10CB_STOP: safe process timeout >' + [string]$TimeoutMs + 'ms')
        }
        $proc.WaitForExit()
        $exitValue = $proc.ExitCode
        if ($null -eq $exitValue) { throw 'P10CB_STOP: .NET ExitCode returned NULL' }
        $nativeExit = [int]$exitValue
        $standardOutput = $stdoutTask.GetAwaiter().GetResult()
        $standardError = $stderrTask.GetAwaiter().GetResult()
        return [pscustomobject]@{Exit=$nativeExit;Out=$standardOutput;Err=$standardError}
    } finally { $proc.Dispose() }
}

try {
    Log-Line 'P10CB native ExitCode check. SAFE UNIT ONLY. No FEM, mesh, or preflight.'
    Log-Line ('TOOL_REVISION=' + $toolRevision)
    Log-Line ('START_LOCAL=' + (Get-Date).ToString('o'))
    $sourceRoot = [IO.Path]::GetFullPath($expectedRoot).TrimEnd('\')
    if ($toolRoot.Equals($sourceRoot,[StringComparison]::OrdinalIgnoreCase) -or
        $toolRoot.StartsWith($sourceRoot+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw 'P10CB_STOP: tool folder cannot be within original Git project'
    }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $runDir = Join-Path $toolRoot ('P10CB_RESULTS_' + $stamp + '_' + $PID)
    if (Test-Path -LiteralPath $runDir) { throw 'P10CB_STOP: result folder exists' }
    [void](New-Item -ItemType Directory -Path $runDir)
    $scriptSHA = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Log-Line ('P10CB_TOOL_PS1_SHA256=' + $scriptSHA)
    if (-not (Test-Path -LiteralPath $gitExe -PathType Leaf) -or
        -not (Test-Path -LiteralPath $expectedRoot -PathType Container)) {
        throw 'P10CB_STOP: original Git or git.exe unavailable'
    }
    $snapshot = Get-OriginalSnapshot
    Log-Line ('ORIGINAL_HEAD_BEFORE=' + $snapshot.Head)
    Log-Line ('ORIGINAL_STATUS_BEFORE=' + $snapshot.Counts)
    Log-Line ('ORIGINAL_STATUS_SHA_BEFORE=' + $snapshot.StatusSHA256)
    if ($snapshot.Head -cne $expectedHead) { throw 'P10CB_STOP: unexpected original HEAD' }
    if (-not (Test-Path -LiteralPath $expectedExe -PathType Leaf)) {
        throw 'P10CB_STOP: exact existing P10CA R1 EXE missing. Do not build a replacement.'
    }
    $actualExeSHA = (Get-FileHash -LiteralPath $expectedExe -Algorithm SHA256).Hash.ToLowerInvariant()
    Log-Line ('P10CA_EXISTING_EXE_SHA256=' + $actualExeSHA)
    if ($actualExeSHA -cne $expectedExeSHA) {
        throw 'P10CB_STOP: existing EXE SHA differs from P10CA physical evidence'
    }
    if (-not (Test-Path -LiteralPath $minGWBin -PathType Container) -or
        -not (Test-Path -LiteralPath (Join-Path $minGWBin 'g++.exe') -PathType Leaf)) {
        throw 'P10CB_STOP: exact MinGW runtime directory absent'
    }
    Log-Line ('CHILD_PATH_PREFIX=' + $minGWBin)
    if (-not (Test-Path -LiteralPath $cmdExe -PathType Leaf)) {
        throw 'P10CB_STOP: Windows cmd.exe unavailable'
    }
    Log-Line 'INPUT_GATE=PASS_READ_ONLY'

    # Exactly one known nonzero synthetic native process through each safe method.
    $commandArgs = '/d /c exit 7'
    $probe = Invoke-BoundedDotNet $cmdExe $commandArgs 10000
    Log-Line ('DOTNET_SYNTHETIC_EXIT=' + [string]$probe.Exit)
    if ($probe.Exit -ne 7) { throw 'P10CB_STOP: .NET failed to capture synthetic exit 7' }
    $simple = Invoke-Direct $cmdExe @('/d','/c','exit','7')
    Log-Line ('DIRECT_SYNTHETIC_EXIT=' + [string]$simple.Exit)
    if ($simple.Exit -ne 7) { throw 'P10CB_STOP: direct LASTEXITCODE failed to capture exit 7' }

    # The historical Start-Process method is DIAGNOSTIC ONLY; null is expected on some PS5.1 versions.
    try {
        $legacy = Start-Process -FilePath $cmdExe -ArgumentList $commandArgs -NoNewWindow -Wait -PassThru
        $legacyExit = $legacy.ExitCode
        if ($null -eq $legacyExit) { Log-Line 'START_PROCESS_SYNTHETIC_EXIT=NULL' }
        else { Log-Line ('START_PROCESS_SYNTHETIC_EXIT=' + [string]$legacyExit) }
        $legacy.Dispose()
    } catch { Log-Line ('START_PROCESS_DIAGNOSTIC_EXCEPTION=' + $_.Exception.Message) }

    # Only safe, short, non-physical options of the existing SHA-gated EXE.
    $help = Invoke-BoundedDotNet $expectedExe '--help' 20000
    Log-Line ('DOTNET_HELP_EXIT=' + [string]$help.Exit)
    Write-Lines (Join-Path $runDir 'exe_dotnet_help_stdout.txt') @($help.Out)
    if ($help.Exit -ne 0 -or $help.Out -notmatch 'no --delta-scan-um is accepted') {
        throw 'P10CB_STOP: safe --help failed'
    }
    $native = Invoke-BoundedDotNet $expectedExe '--selftest' 60000
    Log-Line ('DOTNET_SELFTEST_EXIT=' + [string]$native.Exit)
    Write-Lines (Join-Path $runDir 'exe_dotnet_selftest_stdout.txt') @($native.Out)
    Write-Lines (Join-Path $runDir 'exe_dotnet_selftest_stderr.txt') @($native.Err)
    if ($native.Exit -ne 0 -or
        $native.Out -notmatch '(?m)^P10I_PRODUCTION_ADJOINT_OK models=6 functionals=3 cases=18' -or
        $native.Out -notmatch '(?m)^P10W_DEPENDENCY_SELFTEST_OK analytic_coupling_verified=0') {
        throw 'P10CB_STOP: .NET native --selftest exit or marker failed'
    }
    # No unbounded direct invocation of the real scientific EXE. The direct
    # LASTEXITCODE path above was exercised only with immediate cmd exit 7.
    $afterExeSHA=(Get-FileHash -LiteralPath $expectedExe -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($afterExeSHA -cne $actualExeSHA) { throw 'P10CB_STOP: existing EXE changed during safe tests' }
    $testsPassed = $true
    $outcome = 0
} catch {
    Log-Line ('STOP_REASON=' + $_.Exception.Message)
    $outcome = 2
} finally {
    if ($null -ne $snapshot) {
        try {
            $post=Get-OriginalSnapshot
            Log-Line ('ORIGINAL_HEAD_AFTER=' + $post.Head)
            Log-Line ('ORIGINAL_STATUS_AFTER=' + $post.Counts)
            Log-Line ('ORIGINAL_STATUS_SHA_AFTER=' + $post.StatusSHA256)
            if ($post.Head -cne $snapshot.Head -or
                $post.Counts -cne $snapshot.Counts -or
                $post.StatusSHA256 -cne $snapshot.StatusSHA256) {
                Log-Line 'ORIGINAL_WORKTREE_CHANGED=STOP_INVESTIGATE'
                $outcome=2
            } else { Log-Line 'ORIGINAL_WORKTREE_PRESERVED=YES' }
        } catch { Log-Line ('POSTCHECK_STOP=' + $_.Exception.Message); $outcome=2 }
    }
    if ($testsPassed -and $outcome -eq 0) {
        Log-Line 'RESULT=P10CB_NATIVE_EXITCODE_SELFTEST_OK_NO_FEM'
    } else { Log-Line 'RESULT=P10CB_STOPPED_NO_FEM' }
    Log-Line 'PHYSICAL_FEM_RUNS=0'
    Log-Line ('FINISH_LOCAL=' + (Get-Date).ToString('o'))
    if ($runDir -ne '' -and (Test-Path -LiteralPath $runDir -PathType Container)) {
        try {
            $resultFile = Join-Path $runDir 'P10CB_RESULT.txt'
            Write-Lines $resultFile ([string[]]$report)
            $evidence = Join-Path $runDir 'P10CB_EVIDENCE.zip'
            Compress-Archive -LiteralPath ([string[]]$logs.ToArray()) -DestinationPath $evidence -CompressionLevel Optimal
            Write-Host ('SEND_ONE_EVIDENCE_ZIP=' + $evidence)
        } catch {
            Write-Host ('EVIDENCE_SAVE_FAILED=' + $_.Exception.Message)
            $outcome=2
        }
    }
}
exit $outcome
