# Stage 3D-06: CPU-only reproducible local Windows run (Windows PowerShell / PowerShell 7).
param(
  [ValidateSet('H0','H1','H2')][string]$Mesh = 'H0',
  [ValidateSet('ALL','E','ED','EDV')][string]$Law = 'ALL',
  [ValidateSet('ALL','CONST','VAR')][string]$Modulus = 'ALL',
  [switch]$ReuseTemperature
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $root
try {
  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
  if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed' }
  cmake --build build --config Release --parallel 4 --target stage3d02_thermal stage3d06_spatial
  if ($LASTEXITCODE -ne 0) { throw 'CMake build failed' }
  function Binary([string]$Name) {
    foreach ($p in @("build/Release/$Name.exe","build/$Name.exe","build/RelWithDebInfo/$Name.exe")) {
      if (Test-Path $p) { return (Resolve-Path $p).Path }
    }
    throw "Cannot locate executable $Name.exe"
  }
  $heat = Binary 'stage3d02_thermal'
  $mech = Binary 'stage3d06_spatial'
  $temperature = "results/G06_thermal_${Mesh}_dt300"
  $output = "results/G06_${Mesh}_dt300"
  if (!$ReuseTemperature) {
    & $heat --mesh "meshes/$Mesh.msh" --out $temperature --dt 300 --tend 3600 --xi 0 --every-step
    if ($LASTEXITCODE -ne 0) { throw 'Thermal solver failed' }
  }
  $times = (1..12 | ForEach-Object { $_ * 300 }) -join ','
  & $mech --mesh "meshes/$Mesh.msh" --temp-dir $temperature --out $output --law $Law --modulus $Modulus --times $times --quad 3 --cg-tol 1e-7 --resume
  if ($LASTEXITCODE -ne 0) { throw 'Mechanical solver failed; inspect last checkpoint' }
  Write-Host "Finished. Summary: $output/G06_campaign.csv"
}
finally { Pop-Location }
