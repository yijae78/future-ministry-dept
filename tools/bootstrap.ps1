# bootstrap.ps1 — 퓨처 미니스트리 원버튼 설치기 본체 (오너 결재 2026-09-02 · 설치버튼 전환).
#
# 대시보드가 내려주는 설치 파일(스테이지0)이 패키지를 받은 뒤 이 파일로 넘어온다.
# 모든 단계는 멱등이다 — 언제 어디서 끊겨도, 다시 실행하면 된 것은 건너뛰고 이어서 진행한다.
# 실패는 침묵하지 않는다 — 원인·처방을 화면에 말하고, 전체 로그를 바탕화면에 남긴다.
param(
  [string]$RepoUrl = 'https://github.com/yijae78/future-ministry-dept',
  [string]$PkgDir  = '',
  [switch]$NoApply,        # 시험용: 실제 적용 없이 계획(드라이런)까지만
  [switch]$SkipDoctor
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
if (-not $PkgDir) { $PkgDir = Join-Path $HOME 'Future-Ministry\_pkg\future-ministry-dept' }
# 시험 훅 — 검증 하네스가 스테이지0을 거쳐 올 때 실제 적용 없이 관통만 잰다(FM_NO_APPLY=1).
if ($env:FM_NO_APPLY -eq '1') { $NoApply = $true; $SkipDoctor = $true }

$LogPath = Join-Path $env:TEMP ("fm-install-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
try { Start-Transcript -Path $LogPath -ErrorAction SilentlyContinue | Out-Null } catch {}

function Say([string]$m, [string]$c = 'White') { Write-Host $m -ForegroundColor $c }
function Stage([string]$n, [string]$t) { Say '' ; Say ("[{0}/6] {1}" -f $n, $t) 'Cyan' }

function Bail([string]$why, [string]$fix, [int]$code) {
  Say '' ; Say ("[멈춤] {0}" -f $why) 'Red'
  Say ("→ {0}" -f $fix) 'Yellow'
  try { Stop-Transcript | Out-Null } catch {}
  # 진단 꾸러미 — 바탕화면에 로그를 남긴다. 어떤 실패도 추측 없이 고칠 수 있는 보고서가 된다.
  try {
    $desk = [Environment]::GetFolderPath('Desktop')
    $bundle = Join-Path $desk '퓨처미니스트리-설치로그.txt'
    Copy-Item $LogPath $bundle -Force
    Say ("설치 기록을 바탕화면의 「퓨처미니스트리-설치로그.txt」 에 남겼습니다.") 'Yellow'
    Say '해결이 어려우면 그 파일 하나만 제작자에게 보내 주세요.' 'Yellow'
  } catch {}
  Say ''
  Read-Host '엔터를 누르면 창이 닫힙니다'
  exit $code
}

Say '════════════════════════════════════════════════════'
Say ' 퓨처 미니스트리 설치를 시작합니다'
Say ' 이 창은 스스로 진행합니다 — 끝날 때까지 닫지 말아 주세요.'
Say ' (중간에 꺼져도 괜찮습니다. 다시 실행하면 이어서 진행됩니다.)'
Say '════════════════════════════════════════════════════'

# ── [1/6] 자비스(cys) 확인 ─────────────────────────────
Stage 1 '자비스가 설치되어 있는지 확인합니다'
$cys = Get-Command cys -ErrorAction SilentlyContinue
if (-not $cys) {
  $rel = 'https://github.com/idoforgod/cys-terminal/releases/latest'
  try { Start-Process $rel } catch {}
  Bail '자비스(cys) 앱이 아직 이 컴퓨터에 없습니다.' `
       ("방금 연 페이지에서 자비스를 먼저 설치해 주세요. 끝나면 이 설치 파일을 다시 두 번 눌러 주세요. (페이지가 안 열렸으면: {0})" -f $rel) 2
}
Say ("자비스 확인: {0}" -f $cys.Source) 'Green'

# ── [2/6] git 확인 (없으면 자동 설치 시도) ──────────────
Stage 2 '파일을 받아올 도구(git)를 확인합니다'
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    Say 'git 이 없어 자동으로 설치합니다 — 1~3분 걸릴 수 있습니다.' 'Yellow'
    try {
      & winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements | Out-Host
    } catch { Say '자동 설치 명령이 중단되었습니다.' 'Yellow' }
    # 설치 직후에는 새 PATH 가 이 창에 없다 — 표준 설치 위치를 직접 잇는다.
    $gitCand = @("$env:ProgramFiles\Git\cmd", "${env:ProgramFiles(x86)}\Git\cmd", "$env:LOCALAPPDATA\Programs\Git\cmd")
    foreach ($c in $gitCand) { if (Test-Path (Join-Path $c 'git.exe')) { $env:PATH = "$c;$env:PATH" } }
    $git = Get-Command git -ErrorAction SilentlyContinue
  }
  if (-not $git) {
    $gurl = 'https://git-scm.com/download/win'
    try { Start-Process $gurl } catch {}
    Bail 'git 을 자동으로 설치하지 못했습니다.' `
         ("방금 연 페이지에서 Git 을 설치해 주세요. 끝나면 이 파일을 다시 두 번 눌러 주세요. (페이지: {0})" -f $gurl) 3
  }
}
Say ("git 확인: {0}" -f (& git --version)) 'Green'

# ── [3/6] 패키지 받기 (깨진 폴더 자가복구) ──────────────
Stage 3 '부서 패키지를 받아옵니다'
$parent = Split-Path -Parent $PkgDir
if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force $parent | Out-Null }
# ⚠git 은 정상 진행 메시지를 stderr 로 쓴다 — EAP=Stop+2>&1 은 그걸 치명 예외로 만든다(실측).
#   git 구간만 Continue 로 낮추고, 실패 판정은 $LASTEXITCODE·Test-Path 로 명시한다.
$ErrorActionPreference = 'Continue'
if (Test-Path (Join-Path $PkgDir '.git')) {
  Say '이미 받아 둔 패키지가 있어 최신으로 맞춥니다.'
  & git -C $PkgDir pull --ff-only 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0) { Say '최신화는 건너뜁니다(네트워크 없음?) — 받아 둔 판으로 진행합니다.' 'Yellow' }
} else {
  if (Test-Path $PkgDir) {
    $bak = "$PkgDir.broken-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Say '지난번에 받다 만 폴더가 있어 옆으로 치우고 새로 받습니다.' 'Yellow'
    Move-Item $PkgDir $bak -Force
  }
  & git clone $RepoUrl $PkgDir 2>&1 | Out-Host
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $PkgDir '.git'))) {
    Bail '패키지를 받아오지 못했습니다.' '인터넷 연결을 확인하시고, 이 파일을 다시 두 번 눌러 주세요.' 4
  }
}
$ErrorActionPreference = 'Stop'
Say ("패키지 위치: {0}" -f $PkgDir) 'Green'

# ── [4/6] 원클릭 수신부 등록 ───────────────────────────
Stage 4 '원클릭 수신부를 등록합니다 (관리자 권한 불필요)'
$handler = Join-Path $PkgDir 'tools\cys-install-handler.ps1'
if (-not (Test-Path $handler)) { Bail '패키지 안에서 수신부 파일을 찾지 못했습니다.' '이 파일을 다시 두 번 눌러 새로 받아 주세요.' 5 }
$psexe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$base = 'HKCU:\Software\Classes\cys-install'
New-Item -Path $base -Force | Out-Null
Set-ItemProperty -Path $base -Name '(default)' -Value 'URL:cys-install Protocol'
Set-ItemProperty -Path $base -Name 'URL Protocol' -Value ''
New-Item -Path "$base\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path "$base\shell\open\command" -Name '(default)' `
  -Value ('"{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}" "%1"' -f $psexe, $handler)
Say '등록 완료 — 이제 안내 화면의 모든 설치 버튼이 원클릭으로 작동합니다.' 'Green'

# ── [5/6] 부서 설치 실행 ───────────────────────────────
Stage 5 $(if ($NoApply) { '설치 계획을 확인합니다 (시험 모드 — 실제로 바꾸지 않습니다)' } else { '부서를 설치합니다 — 몇 분 걸릴 수 있습니다' })
Get-ChildItem Env: | Where-Object { $_.Name -like 'CYS_*' } |
  ForEach-Object { Remove-Item "Env:$($_.Name)" -ErrorAction SilentlyContinue }
$setup = Join-Path $PkgDir 'tools\setup.ps1'
if (-not (Test-Path $setup)) { Bail '패키지 안에서 설치기(setup.ps1)를 찾지 못했습니다.' '이 파일을 다시 두 번 눌러 새로 받아 주세요.' 5 }
$setupArgs = @()
if (-not $NoApply) { $setupArgs += '-Apply' }
& $psexe -NoProfile -ExecutionPolicy Bypass -File $setup @setupArgs
$setupExit = $LASTEXITCODE

# ── [6/6] 자가 진단 ───────────────────────────────────
Stage 6 '설치가 잘 되었는지 이 컴퓨터가 스스로 확인합니다'
$doctorExit = 0
if (-not $SkipDoctor) {
  & $psexe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PkgDir 'tools\doctor.ps1')
  $doctorExit = $LASTEXITCODE
}

try { Stop-Transcript | Out-Null } catch {}
Say ''
if ($setupExit -eq 0 -and $doctorExit -eq 0) {
  Say '[OK] install finished — 설치가 끝났습니다. 안내 화면의 「잘 됐는지 확인」과 견주어 보세요.' 'Green'
} else {
  Say ("[확인 필요] 일부 항목이 완료되지 않았습니다 (설치 {0} · 진단 {1}). 위 목록의 → 안내대로 하신 뒤, 이 파일을 다시 두 번 누르면 이어서 진행됩니다." -f $setupExit, $doctorExit) 'Yellow'
  try {
    $desk = [Environment]::GetFolderPath('Desktop')
    Copy-Item $LogPath (Join-Path $desk '퓨처미니스트리-설치로그.txt') -Force
    Say '설치 기록을 바탕화면의 「퓨처미니스트리-설치로그.txt」 에 남겼습니다 — 해결이 어려우면 이 파일만 보내 주세요.' 'Yellow'
  } catch {}
}
Say ''
Read-Host '엔터를 누르면 창이 닫힙니다'
exit $(if ($setupExit -eq 0 -and $doctorExit -eq 0) { 0 } else { 1 })
