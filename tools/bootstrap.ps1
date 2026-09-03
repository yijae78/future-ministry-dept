# bootstrap.ps1 — v2 호환 shim(2026-09-03): 설치기 본체는 tools/install.cmd + tools/fm/(Python 1벌)로 옮겨졌다.
# 구 안내·구 Stage0 가 가리키는 이 경로를 보존하기 위해 남긴다. 의미 있는 인자는 -NoApply(드라이런)뿐이다.
param([string]$RepoUrl = '', [string]$PkgDir = '', [switch]$NoApply, [switch]$SkipDoctor)
$cmd = Join-Path $PSScriptRoot 'install.cmd'
if ($NoApply -or $env:FM_NO_APPLY -eq '1') { & $cmd bootstrap --dry-run } else { & $cmd bootstrap }
exit $LASTEXITCODE
