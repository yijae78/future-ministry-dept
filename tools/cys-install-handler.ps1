# cys-install-handler.ps1 — 대시보드 설치버튼(cys-install:// 프로토콜)의 수신부.
#
# 브라우저가 cys-install://dept/future-ministry 또는 cys-install://tech/<id> 를 열면
# 레지스트리(HKCU\Software\Classes\cys-install)가 이 스크립트를 부른다(register-protocol.cmd가 등록).
# 받은 URL을 해석해 이 패키지의 tools/setup.ps1 을 실행한다 — 유저는 버튼만 누르면 된다.
#
# 안전 원칙:
#   · URL 의 kind/key 만 읽고, 그 밖의 문자열은 어떤 명령에도 넣지 않는다(인젝션 차단).
#   · key 는 setup.ps1 -ListTechs 가 아는 id 형식(소문자·숫자·하이픈)만 통과시킨다.
#   · CYS_* 환경변수를 지운 청정 환경에서 돌린다(cys-dept 거버넌스 가드 exit 7 회피 —
#     자식 프로세스만 청정. 이 창은 브라우저가 새로 띄우므로 부모 오염 없음).
param([string]$Url)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

$PkgRoot = Split-Path -Parent $PSScriptRoot   # tools\ 의 부모 = 패키지 루트
$Setup   = Join-Path $PSScriptRoot 'setup.ps1'

function Fail([string]$msg) {
  Write-Host ''
  Write-Host "[중단] $msg" -ForegroundColor Red
  Write-Host ''
  Read-Host '엔터를 누르면 창이 닫힙니다'
  exit 1
}

# ── 1. URL 해석 ─────────────────────────────────────────────
# 형태: cys-install://<kind>/<key>  (브라우저에 따라 끝에 / 가 붙을 수 있다)
if (-not $Url) { Fail '설치 대상 URL이 오지 않았습니다. 대시보드의 설치 버튼으로 다시 시도하세요.' }
$m = [regex]::Match($Url, '^cys-install://(dept|tech)/([a-z0-9][a-z0-9-]*)/?$')
if (-not $m.Success) { Fail "알 수 없는 설치 주소입니다: $Url" }
$kind = $m.Groups[1].Value
$key  = $m.Groups[2].Value

# ── 2. 전제 점검 ────────────────────────────────────────────
if (-not (Test-Path $Setup)) { Fail "설치기(setup.ps1)를 찾을 수 없습니다: $Setup`n패키지가 옮겨졌으면 2번(부서 설치)을 다시 실행하세요." }

Write-Host '════════════════════════════════════════════════'
Write-Host ' 퓨처 미니스트리 설치 — 자비스가 받아서 진행합니다'
Write-Host "  대상: $kind / $key"
Write-Host "  패키지: $PkgRoot"
Write-Host '════════════════════════════════════════════════'

# 패키지 최신화 — 실패해도 설치는 계속한다(오프라인 허용).
try {
  $git = Get-Command git -ErrorAction SilentlyContinue
  if ($git -and (Test-Path (Join-Path $PkgRoot '.git'))) {
    Write-Host '[준비] 패키지 최신화(git pull)…'
    & git -C $PkgRoot pull --ff-only 2>&1 | Out-Host
  }
} catch { Write-Host '[준비] 최신화 생략(네트워크 없음?) — 현재 판으로 진행' }

# ── 3. 청정 환경에서 setup.ps1 실행 ─────────────────────────
# cys-dept 는 CYS_ROLE 이 비어 있을 때만 launch 를 허용한다(가드 exit 7).
Get-ChildItem Env: | Where-Object { $_.Name -like 'CYS_*' } |
  ForEach-Object { Remove-Item "Env:$($_.Name)" -ErrorAction SilentlyContinue }

$setupArgs = @('-Apply')
if ($kind -eq 'tech') { $setupArgs += @('-Only', $key) }
elseif ($key -ne 'future-ministry') { $setupArgs += @('-Dept', $key) }

Write-Host "[실행] setup.ps1 $($setupArgs -join ' ')"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Setup @setupArgs
$code = $LASTEXITCODE

Write-Host ''
if ($code -eq 0) {
  Write-Host '[완료] 설치가 끝났습니다. 대시보드의 「잘 됐는지 확인」 화면과 견주어 보세요.' -ForegroundColor Green
} else {
  Write-Host "[실패 있음] 종료코드 $code — 위 목록에서 실패 항목을 확인하세요." -ForegroundColor Yellow
}
Read-Host '엔터를 누르면 창이 닫힙니다'
exit $code
