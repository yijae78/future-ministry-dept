# cys-install-handler.ps1 — 대시보드 설치버튼(cys-install:// 프로토콜)의 수신부.
#
# 브라우저가 cys-install://dept/future-ministry 또는 cys-install://tech/<id> 를 열면
# 레지스트리(HKCU\Software\Classes\cys-install)가 이 스크립트를 부른다
# (등록은 bootstrap.ps1 4단계 · 수동 재등록은 register-protocol.cmd).
# 받은 URL을 해석해 이 패키지의 tools/setup.ps1 을 실행하고, 끝나면 doctor.ps1 로
# 자가 진단까지 찍는다 — 사용자는 버튼만 누르면 된다.
#
# 안전 원칙:
#   · URL 의 kind/key 만 읽고, 그 밖의 문자열은 어떤 명령에도 넣지 않는다(인젝션 차단).
#   · key 는 소문자·숫자·하이픈 슬러그만 통과시킨다(manifest id 형식).
#   · CYS_* 환경변수를 지운 청정 환경에서 돌린다(cys-dept 거버넌스 가드 exit 7 회피).
#   · 실패는 침묵하지 않는다 — 원인·처방을 말하고 로그를 바탕화면에 남긴다.
param([string]$Url)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

$PkgRoot = Split-Path -Parent $PSScriptRoot   # tools\ 의 부모 = 패키지 루트
$Setup   = Join-Path $PSScriptRoot 'setup.ps1'
$Doctor  = Join-Path $PSScriptRoot 'doctor.ps1'
$LogPath = Join-Path $env:TEMP ("fm-oneclick-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
try { Start-Transcript -Path $LogPath -ErrorAction SilentlyContinue | Out-Null } catch {}

function Fail([string]$msg, [string]$fix) {
  Write-Host ''
  Write-Host "[멈춤] $msg" -ForegroundColor Red
  if ($fix) { Write-Host "→ $fix" -ForegroundColor Yellow }
  try { Stop-Transcript | Out-Null } catch {}
  try {
    $desk = [Environment]::GetFolderPath('Desktop')
    Copy-Item $LogPath (Join-Path $desk '퓨처미니스트리-설치로그.txt') -Force
    Write-Host '기록을 바탕화면의 「퓨처미니스트리-설치로그.txt」 에 남겼습니다 — 해결이 어려우면 이 파일만 보내 주세요.' -ForegroundColor Yellow
  } catch {}
  Write-Host ''
  Read-Host '엔터를 누르면 창이 닫힙니다'
  exit 1
}

# PowerShell 이 제한 모드면 표준 동작을 보장할 수 없다 — 정직하게 말하고 멈춘다.
if ($ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') {
  Fail ('이 컴퓨터의 PowerShell 이 제한 모드({0})라 자동 설치를 진행할 수 없습니다.' -f $ExecutionContext.SessionState.LanguageMode) `
       '회사·기관 보안 정책이 걸린 컴퓨터입니다. 관리자에게 문의해 주세요.'
}

# ── 1. URL 해석 (화이트리스트) ──────────────────────────
if (-not $Url) { Fail '설치 대상 주소가 오지 않았습니다.' '안내 화면의 설치 버튼으로 다시 시도해 주세요.' }
$m = [regex]::Match($Url, '^cys-install://(dept|tech)/([a-z0-9][a-z0-9-]*)/?$')
if (-not $m.Success) { Fail "알 수 없는 설치 주소입니다: $Url" '안내 화면의 설치 버튼으로 다시 시도해 주세요.' }
$kind = $m.Groups[1].Value
$key  = $m.Groups[2].Value

# ── 2. 전제 점검 ────────────────────────────────────────
if (-not (Test-Path $Setup)) {
  Fail "설치기(setup.ps1)를 찾을 수 없습니다: $Setup" '2번(부서 설치)의 설치 파일을 다시 실행해 패키지를 새로 받아 주세요.'
}

Write-Host '════════════════════════════════════════════════════'
Write-Host ' 원클릭 설치 — 자비스가 받아서 진행합니다'
Write-Host ("  대상: {0} / {1}" -f $kind, $key)
Write-Host ' 이 창은 스스로 진행합니다 — 끝날 때까지 닫지 말아 주세요.'
Write-Host '════════════════════════════════════════════════════'

# 패키지 최신화 — 실패해도 설치는 계속한다(오프라인 허용). 배포 후 수리는 이 통로로 배달된다.
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git -and (Test-Path (Join-Path $PkgRoot '.git'))) {
  Write-Host '[준비] 패키지를 최신으로 맞춥니다…'
  # ⚠git 정상 메시지가 stderr 로 온다 — Stop+2>&1 치명 예외 지뢰라 이 구간만 Continue(실측 2026-09-02).
  $ErrorActionPreference = 'Continue'
  & git -C $PkgRoot pull --ff-only 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) { Write-Host '[준비] 최신화는 건너뜁니다(네트워크 없음?) — 받아 둔 판으로 진행합니다.' -ForegroundColor Yellow }
  $ErrorActionPreference = 'Stop'
}

# ── 3. 청정 환경에서 setup.ps1 실행 ─────────────────────
Get-ChildItem Env: | Where-Object { $_.Name -like 'CYS_*' } |
  ForEach-Object { Remove-Item "Env:$($_.Name)" -ErrorAction SilentlyContinue }

$setupArgs = @('-Apply')
if ($kind -eq 'tech') { $setupArgs += @('-Only', $key) }
elseif ($key -ne 'future-ministry') { $setupArgs += @('-Dept', $key) }

Write-Host ("[실행] setup.ps1 {0}" -f ($setupArgs -join ' '))
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Setup @setupArgs
$code = $LASTEXITCODE

# ── 4. 자가 진단 ────────────────────────────────────────
$doctorExit = 0
if (Test-Path $Doctor) {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Doctor
  $doctorExit = $LASTEXITCODE
}

try { Stop-Transcript | Out-Null } catch {}
Write-Host ''
if ($code -eq 0 -and $doctorExit -eq 0) {
  Write-Host '[완료] 설치가 끝났습니다. 안내 화면의 「잘 됐는지 확인」과 견주어 보세요.' -ForegroundColor Green
} else {
  Write-Host ("[확인 필요] 일부 항목이 완료되지 않았습니다 (설치 {0} · 진단 {1}). 위 목록의 → 안내를 따라 주세요. 같은 버튼을 다시 누르면 이어서 진행됩니다." -f $code, $doctorExit) -ForegroundColor Yellow
  try {
    $desk = [Environment]::GetFolderPath('Desktop')
    Copy-Item $LogPath (Join-Path $desk '퓨처미니스트리-설치로그.txt') -Force
    Write-Host '기록을 바탕화면의 「퓨처미니스트리-설치로그.txt」 에 남겼습니다 — 해결이 어려우면 이 파일만 보내 주세요.' -ForegroundColor Yellow
  } catch {}
}
Read-Host '엔터를 누르면 창이 닫힙니다'
exit $(if ($code -eq 0 -and $doctorExit -eq 0) { 0 } else { 1 })
