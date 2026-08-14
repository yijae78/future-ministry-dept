<#
.SYNOPSIS
  칼빈(Future Ministry) 부서 패키지를 이 PC의 자비스(cys) 터미널에 설치한다 — 멱등 · 기본 드라이런.

.DESCRIPTION
  이 스크립트는 manifest.json 의 선언(desired)을 이 PC의 실제 상태(actual)에 수렴(reconcile)시킨다.

  왜 이런 구조인가:
    부서 데몬(cysd)이 재기동되면 좌석 테이블이 비고, phoenix 가 desired_roster.json 대로만 복원한다.
    그런데 로스터는 **role 을 키로 하는 맵**이라 role 미등록인 기술자(유닛) 좌석은 담길 자리가 없다.
    즉 기술자는 구조적으로 phoenix 보호 밖이며, 데몬이 한 번만 튀어도 전멸한다.
    따라서 편성의 재현성은 phoenix 가 아니라 **manifest.json + 이 스크립트**가 책임진다.

  실행 순서 (★의존 순서라 바꾸면 안 된다):
    ① 전제 점검      — cys 실행체(버전 >=0.13.0) · git · bash · cys-dept · bash PATH 의 cys·cysd·python3
    ② 매니페스트 병합 — manifest.json → ~/.cys/dept-catalog.json  (백업 후 병합)
    ③ 미션 이식      — missions/*.md → ~/.cys/dept-missions/
    ④ 작업 폴더 생성  — $HOME/Future-Ministry/... 4개
    ⑤ 부서 생성      — cys-dept create <key>  (루트 → 하위 순. 카탈로그에 키가 있어야 하므로 반드시 ② 다음)
    ⑤b parent 백필   — depts.json 의 부서 엔트리에 parent 기록 (UI 부서 트리의 진실원)
    ⑥ 헌장 이식      — CHARTER.md → ~/.cys/pack-dept-<발급번호>/CHARTER.md
    ⑦ 기술자 리포 클론 — 11개 (이미 있으면 skip)
    ⑧ 기술자 좌석 수렴 — 카탈로그 techs 선언대로 pane 좌석 생성·정리
    ⑨ 검증 보고      — 부서별 선언(techs) vs 실좌석(비exited) 정확 비교

  종료코드: 0 = 성공(드라이런 포함) · 1 = 실패 누적 있음(개별 실패는 끝까지 진행 후 목록 보고).

  ★dept 번호(dept-N)·소켓·계정 디렉터리는 이 PC의 cys-dept 가 새로 발급한다.
    매니페스트에는 들어 있지 않다(그래야 어느 PC에서든 그대로 돈다).

.PARAMETER Apply
  실제로 설치한다. 생략하면 계획만 출력(드라이런 · 쓰기 0).

.PARAMETER Dept
  대상 부서 키만 처리(future-ministry · fm-admin · fm-worship · fm-sermon). 생략 시 전부.

.PARAMETER SkipClone
  기술자 리포 클론 단계를 건너뛴다(네트워크 없는 환경).

.PARAMETER RemoveMaster
  ⚠위험. 하위 부의 role 좌석을 제거한다. close-surface 는 자손 프로세스 트리를 통째로 죽이는데,
  부서 cysd 가 그 좌석의 자손으로 기동돼 있으면 **데몬까지 죽는다**. 반드시 로스터 정리와
  한 호흡으로만 쓰라. 평상시에는 쓰지 마라.

.EXAMPLE
  .\setup.ps1                          # 전체 계획만 본다 (쓰기 0)
  .\setup.ps1 -Apply                   # 실제 설치
  .\setup.ps1 -Dept fm-admin -Apply    # 행정관리부만
#>
[CmdletBinding()]
param(
  [switch]$Apply,
  [string]$Dept,
  [switch]$SkipClone,
  [switch]$RemoveMaster,
  [string]$CysExe   = "$env:LOCALAPPDATA\cys\cys.exe"
)

$ErrorActionPreference = 'Stop'
# ★경로 고정(파라미터 제거 사유): cys-dept 는 env(CYS_DEPT_CATALOG·CYS_DEPTS_JSON·CYS_DEPT_MISSIONS)
#   미전달 시 $HOME/.cys 고정 경로만 읽는다(cys-dept:31,635-636). CysHome 을 파라미터로 받으면
#   병합은 A 경로에 쓰고 create 는 B 경로를 읽는 분기 결함이 되므로 기본 경로로 고정한다.
#   WorkRoot 파라미터도 제거 — 작업 폴더는 매니페스트 cwd_template + Expand-HomeTemplate 로만 결정된다.
$CysHome  = Join-Path $env:USERPROFILE '.cys'
$PkgDir   = Split-Path -Parent $PSScriptRoot           # .../departments/future-ministry
$Manifest = Join-Path $PkgDir 'manifest.json'
$Catalog  = Join-Path $CysHome 'dept-catalog.json'
$DeptsMap = Join-Path $CysHome 'depts.json'
$MissDir  = Join-Path $CysHome 'dept-missions'
$DeptTool = Join-Path $CysHome 'pack\bin\cys-dept'

$script:Warnings = @()
$script:Failures = @()
function Warn($m) { $script:Warnings += $m; Write-Host "  ⚠ $m" -ForegroundColor Yellow }
function Fail($m) { $script:Failures += $m; Write-Host "  ✗ $m" -ForegroundColor Red }
function Step($n, $t) { Write-Host ""; Write-Host ("[$n] $t") -ForegroundColor Cyan }
function Act($m) { if ($Apply) { Write-Host "  · $m" } else { Write-Host "  (계획) $m" -ForegroundColor DarkGray } }
# PS 5.1 은 EAP=Stop + `2>&1` 조합에서 native 명령의 stderr 첫 줄이 NativeCommandError 로 터진다.
# native 호출 동안만 EAP 를 완화한다(버전 무관 동작). $LASTEXITCODE 는 전역이라 호출부에서 그대로 검사.
function Invoke-Native([scriptblock]$sb) {
  $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try { & $sb } finally { $ErrorActionPreference = $eap }
}

# ── 호출자 env 보호: 원값 보관 → finally 에서 복원 (CYS_NO_AUTOSTART·CYS_SOCKET) ──
# ★아래 본문은 try 블록 안이지만 외과적 변경 최소화를 위해 원래 들여쓰기를 유지한다.
$__origNoAutostart = $env:CYS_NO_AUTOSTART
$__origSocket      = $env:CYS_SOCKET
try {

# 실패한 호출이 좀비 데몬을 낳는 것을 막는다.
$env:CYS_NO_AUTOSTART = '1'

# ── ① 전제 점검 ───────────────────────────────────────────────────────────────
Step 1 '전제 점검'
if (-not (Test-Path $Manifest)) { throw "manifest.json 을 찾을 수 없다: $Manifest" }
if (-not (Test-Path $CysExe))   { throw "cys 실행체를 찾을 수 없다: $CysExe  (자비스 터미널을 먼저 설치하라)" }
if (-not (Test-Path $DeptTool)) { throw "cys-dept 를 찾을 수 없다: $DeptTool  (자비스 pack 이 설치돼 있어야 한다)" }

# ★`?.Source`(PS7 전용 null-conditional)는 PS 5.1 에서 파싱 즉시 실패 — 5.1 호환 문법으로 분리.
$bashCmd = Get-Command bash -ErrorAction SilentlyContinue
$bash = if ($bashCmd) { $bashCmd.Source } else { $null }
if (-not $bash) { throw "bash 를 찾을 수 없다. Git for Windows 를 설치하라 — cys-dept 는 bash 스크립트다." }
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
$git = if ($gitCmd) { $gitCmd.Source } else { $null }
if (-not $git -and -not $SkipClone) { Warn "git 이 없다 — 기술자 리포 클론을 건너뛴다."; $SkipClone = $true }

# ★cys-dept 는 Bash PATH 의 cys·cysd·python3 에 의존한다(cys-dept:35-43,237,639) — 없으면 즉시 중단.
Invoke-Native { & $bash -lc 'command -v cys >/dev/null 2>&1 && command -v cysd >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1' } | Out-Null
if ($LASTEXITCODE -ne 0) { throw "bash PATH 에서 cys·cysd·python3 를 모두 찾지 못했다 — cys-dept 가 실행될 수 없다. Git Bash 의 PATH 를 확인하라." }

# ★cys 버전 확인 — manifest requires: >=0.13.0
$verRaw = (Invoke-Native { & $CysExe --version 2>&1 }) -join ' '
if ($LASTEXITCODE -ne 0 -or $verRaw -notmatch '(\d+\.\d+\.\d+)') { throw "cys 버전을 확인할 수 없다: $verRaw" }
$cysVer = [version]$Matches[1]
if ($cysVer -lt [version]'0.13.0') { throw "cys $cysVer 는 요구 버전(>=0.13.0)보다 낮다 — 자비스 터미널을 업데이트하라." }

Write-Host "  cys      : $CysExe ($cysVer)"
Write-Host "  cys-dept : $DeptTool"
Write-Host "  bash     : $bash"

$mf = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$targets = @($mf.departments | Where-Object { -not $Dept -or $_.key -eq $Dept })
if (-not $targets.Count) { throw "대상 부서가 없다: '$Dept'" }
Write-Host ("  대상 부서 : {0}" -f (($targets | ForEach-Object { $_.key }) -join ', '))

# HOME 템플릿 전개 — 매니페스트의 "$HOME/..." 를 이 PC 경로로 바꾼다.
function Expand-HomeTemplate([string]$t) {
  if (-not $t) { return $null }
  return ($t -replace '^\$HOME', [regex]::Escape($env:USERPROFILE).Replace('\\','\')) -replace '/', '\'
}

# JSON 원자 저장 — 임시파일 + 원자 교체 · UTF-8(BOM 없음. PS5.1 Set-Content UTF8 은 BOM 을 붙여
# cys-dept 의 python json.load 를 깨뜨린다 — 버전 무관 동작을 위해 .NET 으로 직접 쓴다).
function Save-JsonAtomic([string]$path, [string]$json) {
  $tmp = Join-Path (Split-Path -Parent $path) ((Split-Path -Leaf $path) + ".tmp-$PID")
  [System.IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding($false)))
  Move-Item -Force $tmp $path
}

# ── ② 매니페스트 → 카탈로그 병합 ──────────────────────────────────────────────
# ★반드시 부서 생성보다 먼저다. cys-dept create <key> 는 카탈로그에서 키를 찾지 못하면
#   exit 4 로 죽는다(카탈로그가 선언의 진실원이기 때문).
Step 2 '매니페스트 → dept-catalog.json 병합'
if (-not (Test-Path $CysHome)) { Act "폴더 생성: $CysHome"; if ($Apply) { New-Item -ItemType Directory -Force $CysHome | Out-Null } }

if (Test-Path $Catalog) {
  $cat = Get-Content $Catalog -Raw -Encoding UTF8 | ConvertFrom-Json
  $bak = "$Catalog.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
  Act "백업: $bak"
  if ($Apply) { Copy-Item $Catalog $bak -Force }
} else {
  Act "카탈로그 신규 생성: $Catalog"
  $cat = [pscustomobject]@{ accounts = [pscustomobject]@{}; departments = [pscustomobject]@{} }
}
if (-not $cat.accounts)    { $cat | Add-Member -NotePropertyName accounts    -NotePropertyValue ([pscustomobject]@{}) -Force }
if (-not $cat.departments) { $cat | Add-Member -NotePropertyName departments -NotePropertyValue ([pscustomobject]@{}) -Force }

# accounts: 'owner'(기본 primary)만 쓴다 — cys-dept 가 부서별 config dir 를 자동 생성하므로
# 별도 계정 포크를 요구하지 않는다(배포 안전).
foreach ($ap in $mf.accounts.PSObject.Properties) {
  if ($ap.Name -eq '_comment') { continue }
  if (-not $cat.accounts.PSObject.Properties[$ap.Name]) {
    Act "accounts['$($ap.Name)'] = $($ap.Value)"
    if ($Apply) { $cat.accounts | Add-Member -NotePropertyName $ap.Name -NotePropertyValue $ap.Value -Force }
  }
}

foreach ($d in $targets) {
  $entry = [ordered]@{
    display     = $d.display
    account     = $d.account
    mission_key = $d.mission_key
    cwd         = $d.cwd_template
  }
  if ($d.parent) { $entry['parent'] = $d.parent }
  if ($d.techs -and @($d.techs).Count) {
    # 카탈로그 techs 는 좌석 수렴기가 읽는 형식(name·repo·cwd)이다.
    $entry['techs'] = @($d.techs | ForEach-Object {
      [ordered]@{ name = $_.name; repo = $_.repo; cwd = $_.cwd_template }
    })
  }
  $existed = [bool]$cat.departments.PSObject.Properties[$d.key]
  Act ("departments['{0}'] {1} (기술자 {2})" -f $d.key, $(if ($existed) { '갱신' } else { '추가' }), @($d.techs).Count)
  if ($Apply) {
    $cat.departments | Add-Member -NotePropertyName $d.key -NotePropertyValue ([pscustomobject]$entry) -Force
  }
}
if ($Apply) {
  Save-JsonAtomic $Catalog ($cat | ConvertTo-Json -Depth 12)
  Write-Host "  → 병합 완료: $Catalog" -ForegroundColor Green
}

# ── ③ 미션 이식 ───────────────────────────────────────────────────────────────
Step 3 '미션 파일 이식 → ~/.cys/dept-missions/'
if ($Apply -and -not (Test-Path $MissDir)) { New-Item -ItemType Directory -Force $MissDir | Out-Null }
foreach ($d in $targets) {
  if (-not $d.mission_file) { continue }
  $src = Join-Path $PkgDir ($d.mission_file -replace '/','\')
  if (-not (Test-Path $src)) { Warn "미션 파일 없음: $src"; continue }
  $dst = Join-Path $MissDir "$($d.mission_key).md"
  Act "$($d.mission_key).md → $dst"
  if ($Apply) { Copy-Item $src $dst -Force }
}

# ── ④ 작업 폴더 ───────────────────────────────────────────────────────────────
Step 4 '작업 폴더 생성'
foreach ($d in $targets) {
  $cwd = Expand-HomeTemplate $d.cwd_template
  if (Test-Path $cwd) { Write-Host "  = 이미 있음: $cwd" }
  else { Act "생성: $cwd"; if ($Apply) { New-Item -ItemType Directory -Force $cwd | Out-Null } }
}

# ── ⑤ 부서 생성 (cys-dept create) ─────────────────────────────────────────────
# 루트(tier 0) → 하위(tier 1) 순서. cys-dept create 는 멱등이다:
#   같은 mission_key 엔트리가 이미 있으면 REUSE 로 기존 부서를 그대로 돌려준다.
Step 5 '부서 생성 — cys-dept create (멱등)'
$deptIdOf = @{}
foreach ($d in ($targets | Sort-Object tier)) {
  Act "cys-dept create $($d.key)"
  if (-not $Apply) { continue }
  $toolPosix = $DeptTool -replace '\\','/'
  $out = Invoke-Native { & $bash $toolPosix create $d.key 2>&1 }
  $code = $LASTEXITCODE
  $name = (@($out) | Where-Object { "$_" -match '^dept-\d+$' } | Select-Object -Last 1)
  if ($code -ne 0 -or -not $name) {
    # 부서 생성 실패는 설치 실패다 — 성공으로 위장하지 않는다(누적 후 최종 종료코드 비0).
    Fail "부서 생성 실패 [$($d.key)] exit=$code : $((@($out) | Select-Object -Last 3) -join ' / ')"
    continue
  }
  $deptIdOf[$d.key] = "$name"
  Write-Host ("  + {0} → {1}" -f $d.key, $name) -ForegroundColor Green
  Start-Sleep -Milliseconds 1200   # 백신 락 회피 — cys 호출은 간격을 두고 하나씩
}

# ── ⑤b parent 백필 → depts.json ──────────────────────────────────────────────
# ★cys-dept create 는 카탈로그에서 display/account/mission_key/cwd 만 읽고 depts.json 신규
#   엔트리에 parent 를 쓰지 않는다(cys-dept:639-647,705-715). 그런데 UI 부서 트리(계층)의
#   진실원은 depts.json 의 parent 다(main.ts:3235-3238,6559,6575-6579) — 백필이 없으면 하위 부가
#   루트로 평면화된다. create 성공 후 여기서 직접 기록한다(기존 키 보존·임시파일+원자 교체·UTF-8).
Step '5b' 'parent 백필 → depts.json'
foreach ($d in ($targets | Where-Object { $_.parent })) {
  Act "depts.json: <발급번호>.parent = '$($d.parent)'  [$($d.key)]"
}
if ($Apply) {
  $needParent = @($targets | Where-Object { $_.parent -and $deptIdOf.ContainsKey($_.key) })
  if ($needParent.Count) {
    if (-not (Test-Path $DeptsMap)) {
      Fail "depts.json 이 없어 parent 백필 불가: $DeptsMap"
    } else {
      $dj = Get-Content $DeptsMap -Raw -Encoding UTF8 | ConvertFrom-Json
      $djChanged = $false
      foreach ($d in $needParent) {
        $id = $deptIdOf[$d.key]
        $ep = $dj.depts.PSObject.Properties[$id]
        if (-not $ep) { Fail "depts.json 에 $id 엔트리가 없다 — parent 백필 실패 [$($d.key)]"; continue }
        $cur = $ep.Value.PSObject.Properties['parent']
        if ($cur -and "$($cur.Value)" -eq "$($d.parent)") { Write-Host "  = 이미 일치: $id.parent" ; continue }
        $ep.Value | Add-Member -NotePropertyName parent -NotePropertyValue $d.parent -Force
        $djChanged = $true
        Write-Host ("  + {0}.parent = '{1}'  [{2}]" -f $id, $d.parent, $d.key) -ForegroundColor Green
      }
      if ($djChanged) {
        Save-JsonAtomic $DeptsMap ($dj | ConvertTo-Json -Depth 12)
        Write-Host "  → 백필 완료: $DeptsMap" -ForegroundColor Green
      }
    }
  }
}

# ── ⑥ 헌장 이식 ───────────────────────────────────────────────────────────────
Step 6 '헌장(CHARTER.md) 이식 → 부서 pack'
$charterSrc = Join-Path $PkgDir 'CHARTER.md'
$rootKey = ($mf.departments | Where-Object { $_.tier -eq 0 }).key
if ((Test-Path $charterSrc) -and ($targets.key -contains $rootKey)) {
  if ($Apply -and $deptIdOf.ContainsKey($rootKey)) {
    $packDir = Join-Path $CysHome "pack-dept-$($deptIdOf[$rootKey])"
    New-Item -ItemType Directory -Force $packDir | Out-Null
    Copy-Item $charterSrc (Join-Path $packDir 'CHARTER.md') -Force
    Write-Host "  → $packDir\CHARTER.md" -ForegroundColor Green
  } else {
    Act "CHARTER.md → ~/.cys/pack-dept-<발급번호>/CHARTER.md"
  }
}

# ── ⑦ 기술자 리포 클론 ────────────────────────────────────────────────────────
Step 7 '기술자 리포 클론'
if ($SkipClone) {
  Write-Host "  (건너뜀 — -SkipClone)" -ForegroundColor DarkGray
} else {
  foreach ($d in $targets) {
    foreach ($t in @($d.techs)) {
      $dest = Expand-HomeTemplate $t.cwd_template
      if (Test-Path (Join-Path $dest '.git')) {
        Write-Host ("  = 이미 있음: {0}  (최신화하려면: git -C `"{0}`" pull)" -f $dest)
        continue
      }
      if (Test-Path $dest) { Warn "폴더가 있으나 git 리포가 아니다 — 클론 생략: $dest"; continue }
      Act "clone $($t.repo) → $dest"
      if (-not $Apply) { continue }
      New-Item -ItemType Directory -Force (Split-Path -Parent $dest) | Out-Null
      Invoke-Native { & $git clone --depth 1 $t.repo $dest 2>&1 } | Out-Null
      if ($LASTEXITCODE -ne 0) {
        # ★비공개 리포는 치명 오류가 아니다 — 경고만 남기고 나머지 셋업을 완주한다.
        if ($t.visibility -eq 'private') {
          Warn "[$($t.name)] 클론 실패 — 이 리포는 비공개(PRIVATE)다. 소유자 공개 전환 또는 접근 권한이 필요하다. 나머지 설치는 계속한다."
        } else {
          Warn "[$($t.name)] 클론 실패 (네트워크·권한 확인): $($t.repo)"
        }
      } else {
        Write-Host ("  + {0}" -f $dest) -ForegroundColor Green
      }
    }
  }
}

# ── ⑧ 기술자 좌석 수렴 ────────────────────────────────────────────────────────
# 카탈로그가 선언(desired), 여기가 수렴(reconcile)이다.
Step 8 '기술자 좌석 수렴'
$socketOf = @{}
if (Test-Path $DeptsMap) {
  $depts = Get-Content $DeptsMap -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($p in $depts.depts.PSObject.Properties) {
    $mk = $p.Value.mission_key
    if ($mk) { $socketOf[$mk] = @{ socket = $p.Value.socket; id = $p.Name } }
  }
} elseif ($Apply) {
  Warn "depts.json 이 없다 — 좌석 수렴을 건너뛴다."
}

function Get-Seats($socket) {
  # env 는 함수 안에서만 바꾸고 반드시 원복한다(호출자 오염 금지).
  $prevSock = $env:CYS_SOCKET
  try {
    $env:CYS_SOCKET = $socket
    $raw = Invoke-Native { & $CysExe list 2>&1 }
    if ($LASTEXITCODE -ne 0) { return $null }                        # 데몬 무응답 — 판정 보류
    if ("$raw" -match 'cannot connect|not running') { return $null } # 데몬 무응답 — 판정 보류
    $seats = @()
    foreach ($line in $raw) {
      $f = "$line" -split "`t"
      if ($f.Count -ge 5 -and $f[0] -match '^surface:(\d+)$') {
        # ★cys list 의 4번째 탭 필드 = exited (cys.rs:1503-1513).
        #   exited=true(죽은 좌석)는 좌석 집합에서 제외 — 죽은 동일제목 좌석이 재생성을 막으면 안 된다.
        if (($f[3] -replace '^exited=','') -eq 'true') { continue }
        $seats += [pscustomobject]@{ Id = [int]$Matches[1]; Role = ($f[1] -replace '^role=',''); Title = $f[4] }
      }
    }
    return ,$seats
  } finally { $env:CYS_SOCKET = $prevSock }
}

$plan = @()
foreach ($d in $targets) {
  if (-not @($d.techs).Count) { continue }
  if (-not $socketOf.ContainsKey($d.mission_key)) { Warn "[$($d.key)] depts.json 에 소켓 매핑이 없다 — 건너뛴다"; continue }

  $socket = $socketOf[$d.mission_key].socket
  $seats  = Get-Seats $socket
  if ($null -eq $seats) { Warn "[$($d.key)] 데몬 무응답 — 판정 보류(좌석을 지우지 않는다)"; continue }

  $want = @($d.techs | ForEach-Object { $_.name })
  $have = @($seats | Where-Object { $_.Role -eq '-' })
  $mast = @($seats | Where-Object { $_.Role -ne '-' })

  Write-Host ""
  Write-Host ("  === {0} [{1}] {2} ===" -f $d.display, $socketOf[$d.mission_key].id, $d.key) -ForegroundColor Cyan
  Write-Host ("    목표 기술자 {0} : {1}" -f $want.Count, ($want -join ', '))
  Write-Host ("    현재 기술자 {0} : {1}" -f $have.Count, (($have | ForEach-Object { "$($_.Title)#$($_.Id)" }) -join ', '))

  # ① 누락 — 선언에 있는데 좌석이 없다
  foreach ($t in $want) {
    if (-not ($have | Where-Object { $_.Title -eq $t })) {
      $plan += [pscustomobject]@{ Dept=$d.key; Socket=$socket; Act='create'; Title=$t; Id=$null
                                  Cwd=(Expand-HomeTemplate ($d.techs | Where-Object { $_.name -eq $t }).cwd_template)
                                  Why='선언에 있으나 좌석 없음' }
    }
  }
  # ② 중복 — 같은 제목이 둘 이상. 가장 최근 것(높은 id) 하나만 남긴다
  foreach ($g in ($have | Group-Object Title | Where-Object { $_.Count -gt 1 })) {
    foreach ($dup in ($g.Group | Sort-Object Id | Select-Object -SkipLast 1)) {
      $plan += [pscustomobject]@{ Dept=$d.key; Socket=$socket; Act='reap'; Title=$dup.Title; Id=$dup.Id; Cwd=$null
                                  Why="중복 $($g.Count)좌석 중 구본" }
    }
  }
  # ③ 잉여 — 선언에 없는 기술자 좌석
  foreach ($h in $have) {
    if ($want -notcontains $h.Title) {
      $plan += [pscustomobject]@{ Dept=$d.key; Socket=$socket; Act='reap'; Title=$h.Title; Id=$h.Id; Cwd=$null
                                  Why='선언에 없는 좌석' }
    }
  }
  # ④ 역할 좌석 — 하위 부는 기술자만 둔다(칼빈 본진 단일 함대 원칙)
  foreach ($m in $mast) {
    if ($RemoveMaster) {
      $plan += [pscustomobject]@{ Dept=$d.key; Socket=$socket; Act='reap-role'; Title=$m.Role; Id=$m.Id; Cwd=$null
                                  Why='하위 부 함대 금지 — ⚠데몬 동반 사망 위험' }
    } else {
      Write-Host "    · 역할 좌석은 -RemoveMaster 없이는 건드리지 않는다" -ForegroundColor DarkGray
    }
  }
}

if ($plan.Count) {
  Write-Host ""
  Write-Host "  ── 좌석 계획 ──" -ForegroundColor Cyan
  $plan | Format-Table Dept, Act, Title, Id, Why -AutoSize
  if ($Apply) {
    # env 는 finally 로 원복(호출자 오염 금지). 각 native 호출은 exit 검사 — 실패를 성공으로 위장하지 않는다.
    $prevSock = $env:CYS_SOCKET
    try {
      foreach ($p in $plan) {
        $env:CYS_SOCKET = $p.Socket
        switch ($p.Act) {
          'create' {
            $cwd = if ($p.Cwd -and (Test-Path $p.Cwd)) { $p.Cwd } else { $env:USERPROFILE }
            $r = Invoke-Native { & $CysExe new-surface --title $p.Title --cwd $cwd 2>&1 }
            if ($LASTEXITCODE -ne 0) {
              Fail ("[{0}] 좌석 생성 실패 '{1}' exit={2} : {3}" -f $p.Dept, $p.Title, $LASTEXITCODE, ($r -join ' '))
            } else {
              Write-Host ("    + [{0}] '{1}' → {2}" -f $p.Dept, $p.Title, ($r -join ' ')) -ForegroundColor Green
            }
          }
          'reap' {
            # --reap 필수: 기본값(OwnerClose)은 묘비를 심는다. 묘비는 부서를 폐역시킨다.
            $r = Invoke-Native { & $CysExe close-surface --reap $p.Id 2>&1 }
            if ($LASTEXITCODE -ne 0) {
              Fail ("[{0}] 좌석 제거 실패 '{1}'#{2} exit={3} : {4}" -f $p.Dept, $p.Title, $p.Id, $LASTEXITCODE, ($r -join ' '))
            } else {
              Write-Host ("    - [{0}] '{1}'#{2} → {3}" -f $p.Dept, $p.Title, $p.Id, ($r -join ' ')) -ForegroundColor Yellow
            }
          }
          'reap-role' {
            Write-Host ("    ⚠[{0}] 역할 좌석 {1}#{2} 제거 — 데몬 동반 사망 가능" -f $p.Dept, $p.Title, $p.Id) -ForegroundColor Red
            $r = Invoke-Native { & $CysExe close-surface --reap $p.Id 2>&1 }
            if ($LASTEXITCODE -ne 0) {
              Fail ("[{0}] 역할 좌석 제거 실패 {1}#{2} exit={3} : {4}" -f $p.Dept, $p.Title, $p.Id, $LASTEXITCODE, ($r -join ' '))
            } else {
              Write-Host ("       → {0}" -f ($r -join ' '))
            }
            Start-Sleep -Seconds 3
          }
        }
        Start-Sleep -Milliseconds 1200   # 백신 락 회피
      }
    } finally { $env:CYS_SOCKET = $prevSock }
  }
} else {
  Write-Host "  수렴 완료 — 편차 없음." -ForegroundColor Green
}

# ── ⑨ 검증 보고 ───────────────────────────────────────────────────────────────
Step 9 '검증'
if (-not $Apply) {
  Write-Host "  드라이런이다. 실제로 설치하려면 -Apply 를 붙여라." -ForegroundColor Yellow
} else {
  # ★총수 비교가 아니라 부서별 선언(desired 기술자 title 집합) vs 실좌석(live·비exited) 정확 비교.
  #   누락·잉여·중복 어느 하나라도 있으면 실패로 누적 → 최종 종료코드 비0.
  foreach ($d in $targets) {
    if (-not $socketOf.ContainsKey($d.mission_key)) {
      if (@($d.techs).Count) { Fail "[$($d.key)] depts.json 소켓 매핑 없음 — 기술자 좌석 검증 불가" }
      continue
    }
    $seats = Get-Seats $socketOf[$d.mission_key].socket
    if ($null -eq $seats) {
      Write-Host ("  {0,-24} {1,-10} 무응답" -f $d.display, $socketOf[$d.mission_key].id)
      if (@($d.techs).Count) { Fail "[$($d.key)] 데몬 무응답 — 기술자 좌석 검증 불가" }
      continue
    }
    $want = @($d.techs | ForEach-Object { $_.name })
    $live = @($seats | Where-Object { $_.Role -eq '-' } | ForEach-Object { $_.Title })
    $missing = @($want | Where-Object { $live -notcontains $_ })
    $extra   = @($live | Where-Object { $want -notcontains $_ })
    $dupes   = @($live | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Name })
    if ($missing.Count -or $extra.Count -or $dupes.Count) {
      Fail ("[{0}] 좌석 불일치 — 누락:[{1}] 잉여:[{2}] 중복:[{3}]" -f $d.key, ($missing -join ', '), ($extra -join ', '), ($dupes -join ', '))
    } else {
      Write-Host ("  {0,-24} {1,-10} 일치 — 기술자 {2}/{3}" -f $d.display, $socketOf[$d.mission_key].id, $live.Count, $want.Count) -ForegroundColor Green
    }
  }
}
if ($script:Warnings.Count) {
  Write-Host ""
  Write-Host "── 경고 $($script:Warnings.Count)건 ──" -ForegroundColor Yellow
  $script:Warnings | ForEach-Object { Write-Host "  · $_" -ForegroundColor Yellow }
}
if ($script:Failures.Count) {
  Write-Host ""
  Write-Host "── 실패 $($script:Failures.Count)건 ──" -ForegroundColor Red
  $script:Failures | ForEach-Object { Write-Host "  ✗ $_" -ForegroundColor Red }
  Write-Host ""
  Write-Host "끝(실패 있음). 위 실패 목록을 해결한 뒤 다시 실행하라 — 이 스크립트는 멱등이다." -ForegroundColor Red
  exit 1
}
Write-Host ""
Write-Host "끝. 자비스 앱에서 부서 탭이 보이는지 확인하라(최대 10초 내 자동 정합)." -ForegroundColor Cyan
exit 0

} finally {
  # 호출자 env 복원 — 원값이 없었으면 제거된다($null 대입 = 삭제).
  $env:CYS_NO_AUTOSTART = $__origNoAutostart
  $env:CYS_SOCKET       = $__origSocket
}
