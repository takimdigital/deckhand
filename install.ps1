# Deckhand installer (Windows) — copies skills\deckhand into every agent harness found and adds a dh.cmd shim.
#   powershell -ExecutionPolicy Bypass -File install.ps1 [-Link] [-Only claude,hermes]
param([switch]$Link, [string]$Only = "")
$ErrorActionPreference = "Stop"
$Src = Join-Path $PSScriptRoot "skills\deckhand"
foreach ($t in @(@("py","Python 3.9+ (the py launcher)"), @("node","Node 18+ (try-on, compose)"), @("git","git"))) {
  if (-not (Get-Command $t[0] -ErrorAction SilentlyContinue)) { Write-Host "missing: $($t[0]) — $($t[1])" }
}
$targets = @(
  @("claude",  "$HOME\.claude\skills"),
  @("codex",   "$HOME\.codex\skills"),
  @("agents",  "$HOME\.agents\skills"),
  @("cursor",  "$HOME\.cursor\skills"),
  @("hermes",  "$env:LOCALAPPDATA\hermes\skills"),
  @("hermes",  "$HOME\.hermes\skills"),
  @("opencode","$HOME\.config\opencode\skills"),
  @("gemini",  "$HOME\.gemini\skills")
)
foreach ($t in $targets) {
  $name, $dir = $t
  if ($Only -and -not ((",$Only,") -like "*,$name,*")) { continue }
  $parent = Split-Path $dir -Parent
  if (-not (Test-Path $parent) -and $name -ne "agents") { continue }
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $dest = Join-Path $dir "deckhand"
  if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
  if ($Link) { New-Item -ItemType Junction -Path $dest -Target $Src | Out-Null } else { Copy-Item -Recurse $Src $dest }
  Write-Host "✓ $name → $dest"
}
$bin = "$HOME\.deckhand\bin"
$stable = "$HOME\.deckhand\skill\deckhand"
New-Item -ItemType Directory -Force -Path $bin, (Split-Path $stable -Parent) | Out-Null
if (Test-Path $stable) { Remove-Item -Recurse -Force $stable }
if ($Link) { New-Item -ItemType Junction -Path $stable -Target $Src | Out-Null } else { Copy-Item -Recurse $Src $stable }
Set-Content -Path "$bin\dh.cmd" -Value "@py `"$stable\dh.py`" %*" -Encoding ASCII
Write-Host "✓ dh shim → $bin\dh.cmd  (add $bin to PATH)"
Write-Host "Next: open your agent and say what you want, e.g. 'Build a website for my bakery. Phased mode.'"
Write-Host "Step by step, copy-a-sentence: docs/USE-CASES.md"
