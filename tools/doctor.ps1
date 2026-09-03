# v2에서 fm 패키지로 대체됨(호환용 보존) — 정본: tools/install.cmd + tools/fm/ (docs/install-v2-spec.md)
# doctor.ps1 — 설치 자가 진단. 이 기계 위에서 산출물 전부를 실측해 항목별 PASS/FAIL을 찍는다.
# "설치됐습니다"라는 주장 대신, 각 기계가 스스로 증명하게 하는 장치(오너 결재 2026-09-02).
# 쓰기 0 — 읽기·조회만 한다. 종료코드: 0 = 필수 전항 PASS · 1 = 필수 FAIL 있음.
param([switch]$Quiet)

$ErrorActionPreference = 'SilentlyContinue'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

$PkgRoot = Split-Path -Parent $PSScriptRoot
$rows = @()   # @{name; state(PASS|FAIL|참고); detail; fix; required}

function Add-Row([string]$name, [bool]$ok, [string]$detail, [string]$fix, [bool]$required = $true) {
  $script:rows += @{ name=$name; ok=$ok; detail=$detail; fix=$fix; required=$required }
}

# 1. 자비스(cys) 실행체
$cys = Get-Command cys -ErrorAction SilentlyContinue
Add-Row '자비스(cys) 프로그램' ($null -ne $cys) `
  ($(if ($cys) { $cys.Source } else { '찾을 수 없습니다' })) `
  '자비스 앱을 먼저 설치해 주세요 (설치 안내 1번 화면)'

# 2. git
$git = Get-Command git -ErrorAction SilentlyContinue
Add-Row 'git 도구' ($null -ne $git) `
  ($(if ($git) { (& git --version 2>$null) } else { '찾을 수 없습니다' })) `
  '설치 파일을 다시 실행하면 자동으로 설치를 시도합니다'

# 3. 패키지 클론 무결
$manifest = Join-Path $PkgRoot 'manifest.json'
$pkgOk = (Test-Path (Join-Path $PkgRoot '.git')) -and (Test-Path $manifest)
$mfDetail = '패키지 폴더가 온전하지 않습니다'
if ($pkgOk) {
  # ⚠-Encoding UTF8 필수 — PS5.1 기본 읽기는 cp949 라 BOM 없는 UTF-8 한글 뒤 따옴표를 삼킨다(2026-09-02 실측).
  try { $mf = Get-Content $manifest -Raw -Encoding UTF8 | ConvertFrom-Json; $mfDetail = "manifest v$($mf.version) 정상" }
  catch { $pkgOk = $false; $mfDetail = 'manifest.json 을 읽지 못했습니다' }
}
Add-Row '부서 패키지' $pkgOk $mfDetail '설치 파일을 다시 실행하면 새로 받아옵니다'

# 4. 원클릭 수신부(cys-install:// 프로토콜)
$regCmd = (Get-ItemProperty 'HKCU:\Software\Classes\cys-install\shell\open\command' -ErrorAction SilentlyContinue).'(default)'
$handler = Join-Path $PSScriptRoot 'cys-install-handler.ps1'
$protoOk = ($regCmd -and $regCmd.Contains('cys-install-handler.ps1') -and (Test-Path $handler))
Add-Row '원클릭 수신부 등록' $protoOk `
  ($(if ($protoOk) { '등록되어 있습니다' } elseif ($regCmd) { '등록은 있으나 파일 위치가 다릅니다' } else { '등록되어 있지 않습니다' })) `
  "tools\register-protocol.cmd 를 실행하면 다시 등록됩니다"

# 5. 부서 카탈로그 병합
$cat = Join-Path $HOME '.cys\dept-catalog.json'
$catOk = $false; $catDetail = '카탈로그 파일이 없습니다'
if (Test-Path $cat) {
  try {
    $cj = Get-Content $cat -Raw -Encoding UTF8 | ConvertFrom-Json
    $catOk = ($null -ne $cj.'future-ministry') -or ($null -ne $cj.departments.'future-ministry')
    $catDetail = $(if ($catOk) { 'future-ministry 부서가 등록되어 있습니다' } else { '카탈로그에 future-ministry 항목이 없습니다' })
  } catch { $catDetail = '카탈로그 파일을 읽지 못했습니다' }
}
Add-Row '부서 카탈로그 병합' $catOk $catDetail '설치 파일을 다시 실행해 주세요'

# 6. 미션 이식 — 이 패키지의 미션 파일 각각이 대상 폴더에 실재하는지 파일명 단위로 대조
$missionDir = Join-Path $HOME '.cys\dept-missions'
$srcMissions = @(Get-ChildItem (Join-Path $PkgRoot 'missions') -Filter *.md -ErrorAction SilentlyContinue)
$gotCount = @($srcMissions | Where-Object { Test-Path (Join-Path $missionDir $_.Name) }).Count
$misOk = ($srcMissions.Count -gt 0) -and ($gotCount -eq $srcMissions.Count)
Add-Row '부서 임무 문서' $misOk "$gotCount/$($srcMissions.Count) 이식됨" '설치 파일을 다시 실행해 주세요'

# 7. 작업 폴더
$workDir = Join-Path $HOME 'Future-Ministry'
Add-Row '작업 폴더' (Test-Path $workDir) $workDir '설치 파일을 다시 실행해 주세요'

# 8. 부서 등록(depts.json) — 있으면 확인, 판정 불가면 참고로만
$depts = Join-Path $HOME '.cys\depts.json'
$depOk = $false; $depDetail = '아직 확인할 수 없습니다'
if (Test-Path $depts) {
  try {
    $dj = Get-Content $depts -Raw -Encoding UTF8 | ConvertFrom-Json
    $entries = if ($dj.depts) { @($dj.depts.PSObject.Properties) } else { @($dj.PSObject.Properties) }
    $keys = @($entries | ForEach-Object { $_.Value.mission_key; $_.Value.catalog_key; $_.Name })
    $depOk = ($keys -join ' ') -match 'future-ministry'
    $depDetail = $(if ($depOk) { '부서가 자비스에 등록되어 있습니다' } else { '등록 항목을 찾지 못했습니다' })
  } catch { $depDetail = '등록 파일을 읽지 못했습니다' }
}
Add-Row '부서 등록' $depOk $depDetail '자비스 앱을 켠 뒤 설치 파일을 다시 실행해 주세요' $false

# ── 출력 ─────────────────────────────────────────────
$failReq = @($rows | Where-Object { -not $_.ok -and $_.required })
if (-not $Quiet) {
  Write-Host ''
  Write-Host '──── 설치 자가 진단 ────────────────────────────'
  foreach ($r in $rows) {
    $mark = if ($r.ok) { '[성공]' } elseif ($r.required) { '[실패]' } else { '[참고]' }
    $color = if ($r.ok) { 'Green' } elseif ($r.required) { 'Red' } else { 'Yellow' }
    Write-Host ("{0} {1} — {2}" -f $mark, $r.name, $r.detail) -ForegroundColor $color
    if (-not $r.ok) { Write-Host ("       → {0}" -f $r.fix) -ForegroundColor DarkGray }
  }
  Write-Host '────────────────────────────────────────────────'
  if ($failReq.Count -eq 0) {
    Write-Host '진단 결과: 필수 항목이 모두 정상입니다. 설치가 완료되었습니다.' -ForegroundColor Green
  } else {
    Write-Host ("진단 결과: {0}개 항목이 아직 안 되어 있습니다. 위의 → 안내대로 해 주세요." -f $failReq.Count) -ForegroundColor Red
  }
}
exit $(if ($failReq.Count -eq 0) { 0 } else { 1 })
