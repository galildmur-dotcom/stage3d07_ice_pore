param([string]$ProjectRoot = 'G:\ildar\Stage3D07')

# Windows PowerShell 5.1. ASCII only. STRICTLY READ ONLY for original project.
# Does not clone, configure, build, run EXE, modify Git, or change Qt Creator.
$ErrorActionPreference = 'Stop'
$expectedRoot = 'G:\ildar\Stage3D07'
$lines = New-Object 'System.Collections.Generic.List[string]'
$reportPath = ''
$resultCode = 0

function Report([string]$Line) {
    [void]$script:lines.Add($Line)
    Write-Host $Line
}

function Cache-Value([string]$CacheFile, [string]$Key) {
    $pattern = '^' + [regex]::Escape($Key) + ':[^=]*=(.*)$'
    $found = Select-String -LiteralPath $CacheFile -Pattern $pattern | Select-Object -First 1
    if ($null -eq $found) { return '<NOT_IN_CACHE>' }
    return [string]$found.Matches[0].Groups[1].Value.Trim()
}

function Show-Tool([string]$Name) {
    $candidates = @(Get-Command $Name -All -ErrorAction SilentlyContinue)
    if ($candidates.Count -eq 0) {
        Report ('PATH_' + $Name + '=NOT_FOUND')
        return
    }
    $uniquePaths = @($candidates | ForEach-Object { [string]$_.Source } | Sort-Object -Unique)
    foreach ($path in $uniquePaths) {
        Report ('PATH_' + $Name + '=' + $path)
    }
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw 'Project folder not found.'
    }
    $actual = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath.TrimEnd('\')
    if ($actual -ine $expectedRoot) { throw 'Unexpected project path. Stop.' }

    # The report is written to a separate sibling, never inside Stage3D07.
    $parent = Split-Path -Parent $actual
    $outDir = Join-Path $parent ('P10BO_TOOLCHAIN_CHECK_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + $PID)
    if (Test-Path -LiteralPath $outDir) { throw 'Output directory already exists.' }
    [void](New-Item -ItemType Directory -Path $outDir)
    $reportPath = Join-Path $outDir 'P10BO_TOOLCHAIN_REPORT.txt'
    Report 'P10BO READ-ONLY QT CREATOR TOOLCHAIN AUDIT'
    Report 'TOOL_REVISION=P10BO_R1'
    Report ('DATE_LOCAL=' + (Get-Date).ToString('o'))
    Report ('PROJECT_ROOT=' + $actual)

    $cacheDir = Join-Path $actual 'build\Desktop_MinGW_Release'
    $cache = Join-Path $cacheDir 'CMakeCache.txt'
    if (-not (Test-Path -LiteralPath $cache -PathType Leaf)) {
        throw 'Existing CMakeCache.txt not found in Qt Creator Release build.'
    }
    Report 'CACHE_FOUND=YES'
    $keys = @(
        'CMAKE_GENERATOR',
        'CMAKE_GENERATOR_PLATFORM',
        'CMAKE_GENERATOR_TOOLSET',
        'CMAKE_HOME_DIRECTORY',
        'CMAKE_BUILD_TYPE',
        'CMAKE_CXX_COMPILER',
        'CMAKE_MAKE_PROGRAM',
        'STAGE3D06P_OPENMP'
    )
    foreach ($key in $keys) {
        $value = Cache-Value $cache $key
        Report ('CACHE_' + $key + '=' + $value)
    }

    $compiler = Cache-Value $cache 'CMAKE_CXX_COMPILER'
    $make = Cache-Value $cache 'CMAKE_MAKE_PROGRAM'
    foreach ($label in @('COMPILER', 'MAKE')) {
        if ($label -ceq 'COMPILER') { $path = $compiler }
        else { $path = $make }
        if ($path -eq '<NOT_IN_CACHE>') {
            Report ('CACHED_' + $label + '_EXISTS=UNKNOWN')
        } else {
            Report ('CACHED_' + $label + '_EXISTS=' + [string][bool](Test-Path -LiteralPath $path -PathType Leaf))
            Report ('CACHED_' + $label + '_BASENAME=' + [System.IO.Path]::GetFileName($path))
        }
    }

    # A CMake generated metadata file records the actual compiler ID even when
    # the executable name or kit label is misleading.
    $cmakeFilesDir = Join-Path $cacheDir 'CMakeFiles'
    $compilerInfo = @()
    if (Test-Path -LiteralPath $cmakeFilesDir -PathType Container) {
        $compilerInfo = @(Get-ChildItem -LiteralPath $cmakeFilesDir -File -Filter 'CMakeCXXCompiler.cmake' -Recurse -ErrorAction SilentlyContinue)
    }
    if ($compilerInfo.Count -eq 0) {
        Report 'CXX_COMPILER_METADATA=NOT_FOUND'
    } else {
        $file = $compilerInfo | Sort-Object FullName | Select-Object -Last 1
        Report 'CXX_COMPILER_METADATA=FOUND'
        foreach ($key in @('CMAKE_CXX_COMPILER_ID', 'CMAKE_CXX_COMPILER_VERSION', 'CMAKE_CXX_PLATFORM_ID')) {
            $match = Select-String -LiteralPath $file.FullName -Pattern ('^set\(' + $key + ' "?([^"\)]+)') | Select-Object -First 1
            if ($null -eq $match) { Report ('METADATA_' + $key + '=UNKNOWN') }
            else { Report ('METADATA_' + $key + '=' + $match.Matches[0].Groups[1].Value) }
        }
    }

    foreach ($toolName in @('cmake.exe', 'git.exe', 'ninja.exe', 'mingw32-make.exe', 'jom.exe', 'g++.exe', 'cl.exe')) {
        Show-Tool $toolName
    }
    Report 'RESULT=P10BO_TOOLCHAIN_AUDIT_OK_NO_BUILD'
} catch {
    $resultCode = 2
    Report ('RESULT=P10BO_STOPPED: ' + $_.Exception.Message)
} finally {
    if ($reportPath -ne '') {
        try {
            [System.IO.File]::WriteAllLines($reportPath, [string[]]$lines, [System.Text.UTF8Encoding]::new($false))
            Write-Host ('P10BO report: ' + $reportPath) -ForegroundColor Green
        } catch {
            Write-Host ('Could not write P10BO report: ' + $_.Exception.Message) -ForegroundColor Red
            $resultCode = 2
        }
    }
}
exit $resultCode
