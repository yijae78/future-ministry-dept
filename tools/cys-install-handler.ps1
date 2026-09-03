# cys-install-handler.ps1 — v2 호환 shim(2026-09-03): 수신 본체는 tools/fm/handler.py 다.
# 기등록 PC(HKCU 가 이 파일을 가리킴)를 위해 남긴다 — install.cmd handle <url> 로 위임하며,
# 그 설치 흐름의 10단계가 수신부를 v2 명령줄("<python3>" -X utf8 cli.py handle "%1")로 재등록한다.
param([string]$Url)
$cmd = Join-Path $PSScriptRoot 'install.cmd'
& $cmd handle $Url
exit $LASTEXITCODE
