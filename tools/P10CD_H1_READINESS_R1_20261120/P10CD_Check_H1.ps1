# P10CD R1. SAFE READ-ONLY H1 readiness: hashes, Gmsh v2.2 counts, Git.
# NEVER build, preflight, run EXE, execute FEM, change Git or source files.
# PowerShell 5.1, ASCII, no BOM; outputs written only beside this tool.
$ErrorActionPreference = 'Stop'
$env:GIT_OPTIONAL_LOCKS = '0'
$revision = 'P10CD_R1_H1_MESH_AND_PINNED_EXE_READINESS_NO_FEM'
$root = 'G:\ildar\Stage3D07'
$mesh = 'G:\ildar\Stage3D07\P10M_MESHES\H1.msh'
$exe = 'G:\Downloads\P10CA_H0_ONE_RUN_R1_20261120\P10CA_RESULTS_20261120_151200_8420\build\p10ca_h0_analytic_qp.exe'
$gitExe = 'C:\Program Files\Git\cmd\git.exe'
$runtime = 'C:\mingw64\bin'
$expectedHead = '90fd2559c0224ac0a7d2dbe2fe081a6a319080e4'
$expectedStatus = '0/7/4'
$expectedStatusHash = 'bb376579544e328291674fa91d20c7b8a4b9d4a306fd7a3af47c172cedb75258'
$expectedMeshHash = '394ee339073fe6eacfd58c549ad0b0218a9bdadf8f36a2ca435a1ca3fad0598d'
$expectedExeHash = '17c31f426245317271245e340d68fa5de1e4eb144b7be986167505e14cbed924'
$toolRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$runDir = ''
$before = $null
$passed = $false
$outcome = 2
$log = New-Object 'System.Collections.Generic.List[string]'

function Add-Line([string]$Text) {
    [void]$script:log.Add($Text)
    Write-Host $Text
}

function Hash-Text([string]$Value) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally { $sha.Dispose() }
}

function Invoke-Git([string[]]$ArgsList) {
    $saved = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $raw = & $gitExe @ArgsList 2>&1
        $nativeExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $saved }
    return [pscustomobject]@{Exit=$nativeExit;Lines=@($raw | ForEach-Object { [string]$_ })}
}

function Git-Snapshot {
    $head = Invoke-Git -ArgsList @('-C',$root,'rev-parse','HEAD')
    if ($head.Exit -ne 0 -or $head.Lines.Count -ne 1) {
        throw 'P10CD_STOP cannot read Git HEAD'
    }
    $status = Invoke-Git -ArgsList @('-C',$root,'-c','core.fsmonitor=false','status',
                                     '--porcelain=v1','--untracked-files=normal')
    if ($status.Exit -ne 0) { throw 'P10CD_STOP cannot read Git status' }
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

function Read-H1MeshFacts([string]$File) {
    # Reads exact Gmsh 2.2 ASCII nodes/elements; no geometry computation/solve.
    $reader = [IO.File]::OpenText($File)
    $format=''; $nodes=-1; $tets=0; $tri=0; $pore=0; $top=0
    $elements=-1
    try {
        while ($null -ne ($line = $reader.ReadLine())) {
            if ($line -eq '$MeshFormat') {
                $f = [regex]::Split($reader.ReadLine().Trim(),'\s+')
                if ($f.Count -lt 2 -or $f[0] -cne '2.2' -or $f[1] -cne '0') {
                    throw 'P10CD_STOP mesh is not Gmsh 2.2 ASCII'
                }
                $format='2.2_ASCII'
            } elseif ($line -eq '$Nodes') {
                $nodes=[int]$reader.ReadLine()
                for($i=0;$i -lt $nodes;++$i) {
                    if ($null -eq $reader.ReadLine()) { throw 'P10CD_STOP truncated nodes' }
                }
            } elseif ($line -eq '$Elements') {
                $elements=[int]$reader.ReadLine()
                for($i=0;$i -lt $elements;++$i) {
                    $entry=$reader.ReadLine()
                    if ($null -eq $entry) { throw 'P10CD_STOP truncated elements' }
                    $f=[regex]::Split($entry.Trim(),'\s+')
                    if ($f.Count -lt 5) { throw 'P10CD_STOP malformed element' }
                    $type=[int]$f[1]; $nTags=[int]$f[2]
                    if ($nTags -lt 1 -or $f.Count -lt 3+$nTags) {
                        throw 'P10CD_STOP invalid physical tags'
                    }
                    if ($type -eq 11) {
                        if ($f.Count -ne 3+$nTags+10) { throw 'P10CD_STOP bad Tet10' }
                        ++$tets
                    } elseif ($type -eq 9) {
                        if ($f.Count -ne 3+$nTags+6) { throw 'P10CD_STOP bad Tri6' }
                        ++$tri
                        $tag=[int]$f[3]
                        if ($tag -eq 8) { ++$pore }
                        if ($tag -eq 2) { ++$top }
                    } else { throw 'P10CD_STOP unexpected mesh element type' }
                }
            }
        }
    } finally { $reader.Dispose() }
    if ($format -cne '2.2_ASCII' -or $nodes -ne 27757 -or
        $tets -ne 19412 -or $tri -ne 2536 -or $pore -ne 282 -or
        $elements -ne 21948 -or $top -lt 1) {
        throw ('P10CD_STOP H1 counts differ: nodes/tet/tri/pore/top/records=' +
               ('{0}/{1}/{2}/{3}/{4}/{5}' -f $nodes,$tets,$tri,$pore,$top,$elements))
    }
    return [pscustomobject]@{Format=$format;Nodes=$nodes;Tet10=$tets;
                              Tri6=$tri;PoreTri6=$pore;TopTri6=$top;
                              ElementRecords=$elements}
}

try {
    Add-Line 'P10CD exact H1 readiness. SHA/mesh/Git only. NO FEM, build or preflight.'
    Add-Line ('TOOL_REVISION=' + $revision)
    Add-Line ('START_LOCAL=' + (Get-Date).ToString('o'))
    $sourceRoot = [IO.Path]::GetFullPath($root).TrimEnd('\')
    if ($toolRoot.Equals($sourceRoot,[StringComparison]::OrdinalIgnoreCase) -or
        $toolRoot.StartsWith($sourceRoot+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw 'P10CD_STOP tool must be outside original Windows project'
    }
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
    $runDir=Join-Path $toolRoot ('P10CD_RESULTS_' + $stamp + '_' + $PID)
    if (Test-Path -LiteralPath $runDir) { throw 'P10CD_STOP output already exists' }
    [void](New-Item -ItemType Directory -Path $runDir)
    Add-Line ('P10CD_TOOL_SHA256=' + (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant())
    if (-not (Test-Path -LiteralPath $root -PathType Container) -or
        -not (Test-Path -LiteralPath $gitExe -PathType Leaf)) {
        throw 'P10CD_STOP original Git path unavailable'
    }
    $before=Git-Snapshot
    Add-Line ('ORIGINAL_HEAD_BEFORE=' + $before.Head)
    Add-Line ('ORIGINAL_STATUS_BEFORE=' + $before.Counts)
    Add-Line ('ORIGINAL_STATUS_SHA_BEFORE=' + $before.StatusSHA256)
    if ($before.Head -cne $expectedHead -or
        $before.Counts -cne $expectedStatus -or
        $before.StatusSHA256 -cne $expectedStatusHash) {
        throw 'P10CD_STOP original Git differs from last attested fingerprint'
    }
    if (-not (Test-Path -LiteralPath $mesh -PathType Leaf)) {
        throw 'P10CD_STOP exact H1 mesh path absent; do not substitute'
    }
    $meshSHA=(Get-FileHash -LiteralPath $mesh -Algorithm SHA256).Hash.ToLowerInvariant()
    Add-Line ('H1_MESH_SHA256=' + $meshSHA)
    if ($meshSHA -cne $expectedMeshHash) { throw 'P10CD_STOP H1 mesh SHA mismatch' }
    $facts=Read-H1MeshFacts $mesh
    Add-Line ('H1_MESH_FORMAT=' + $facts.Format)
    Add-Line ('H1_NODES=' + $facts.Nodes)
    Add-Line ('H1_TET10=' + $facts.Tet10)
    Add-Line ('H1_TRI6_TOTAL=' + $facts.Tri6)
    Add-Line ('H1_PORE_TRI6=' + $facts.PoreTri6)
    Add-Line ('H1_TOP_TRI6=' + $facts.TopTri6)
    Add-Line ('H1_ELEMENT_RECORDS=' + $facts.ElementRecords)
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw 'P10CD_STOP exact prior P10CA Windows EXE missing; do not rebuild'
    }
    $exeSHA=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    Add-Line ('PINNED_P10CA_EXE_SHA256=' + $exeSHA)
    if ($exeSHA -cne $expectedExeHash) { throw 'P10CD_STOP pinned EXE SHA mismatch' }
    if (-not (Test-Path -LiteralPath $runtime -PathType Container)) {
        throw 'P10CD_STOP prior MinGW runtime directory missing'
    }
    Add-Line ('MIN_GW_CHILD_RUNTIME_PATH_AVAILABLE=' + $runtime)
    Add-Line ('EXPECTED_VOLUME_QP_PER_STEP=' + [string](64*$facts.Tet10))
    Add-Line ('EXPECTED_VOLUME_QP_ALL_6_STEPS=' + [string](6*64*$facts.Tet10))
    Add-Line ('EXPECTED_TOP_ROBIN_QP_PER_STEP=' + [string](16*$facts.TopTri6))
    Add-Line 'FUTURE_EXPECTED_LOCAL_ROWS=606'
    Add-Line 'FUTURE_EXPECTED_AUDIT_ROWS=6'
    Add-Line 'P10AW_H1_PRIOR_WALL_SECONDS=375.3571844'
    Add-Line 'P10CA_H0_PRIOR_WALL_SECONDS=104.4244299'
    Add-Line 'FUTURE_PHYSICAL_H1_PERMISSION=NOT_GRANTED'
    $afterMeshSHA=(Get-FileHash -LiteralPath $mesh -Algorithm SHA256).Hash.ToLowerInvariant()
    $afterExeSHA=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($afterMeshSHA -cne $meshSHA -or $afterExeSHA -cne $exeSHA) {
        throw 'P10CD_STOP mesh or EXE changed during read-only audit'
    }
    $passed=$true
    $outcome=0
} catch {
    Add-Line ('STOP_REASON=' + $_.Exception.Message)
    $outcome=2
} finally {
    if ($null -ne $before) {
        try {
            $after=Git-Snapshot
            Add-Line ('ORIGINAL_HEAD_AFTER=' + $after.Head)
            Add-Line ('ORIGINAL_STATUS_AFTER=' + $after.Counts)
            Add-Line ('ORIGINAL_STATUS_SHA_AFTER=' + $after.StatusSHA256)
            if ($after.Head -cne $before.Head -or
                $after.Counts -cne $before.Counts -or
                $after.StatusSHA256 -cne $before.StatusSHA256) {
                Add-Line 'ORIGINAL_WORKTREE_CHANGED=STOP_INVESTIGATE'
                $outcome=2
            } else { Add-Line 'ORIGINAL_WORKTREE_PRESERVED=YES' }
        } catch {
            Add-Line ('POSTCHECK_STOP=' + $_.Exception.Message)
            $outcome=2
        }
    }
    if ($passed -and $outcome -eq 0) {
        Add-Line 'RESULT=P10CD_H1_READINESS_OK_NO_FEM'
    } else { Add-Line 'RESULT=P10CD_STOPPED_NO_FEM' }
    Add-Line 'PHYSICAL_FEM_RUNS=0'
    Add-Line ('FINISH_LOCAL=' + (Get-Date).ToString('o'))
    if ($runDir -ne '' -and (Test-Path -LiteralPath $runDir -PathType Container)) {
        try {
            $resultFile=Join-Path $runDir 'P10CD_RESULT.txt'
            [IO.File]::WriteAllLines($resultFile,[string[]]$log,
                                     [Text.UTF8Encoding]::new($false))
            $zip=Join-Path $runDir 'P10CD_EVIDENCE.zip'
            Compress-Archive -LiteralPath $resultFile -DestinationPath $zip -CompressionLevel Optimal
            Write-Host ('SEND_ONE_EVIDENCE_ZIP=' + $zip)
        } catch {
            Write-Host ('EVIDENCE_SAVE_FAILED=' + $_.Exception.Message)
            $outcome=2
        }
    }
}
exit $outcome
