# Future Ministry(칼빈) — 자비스 부서 패키지

교회·선교 사역을 담당하는 자비스(cys) 부서 **칼빈**을 당신의 PC에 그대로 설치하는 패키지다.
설치하면 부서 4개(칼빈 + 하위 3부)와 기술자 11명이 자비스 터미널 안에 편성된다.

```
Future Ministry(칼빈)
├─ 행정관리부   기술자 3   Church-Admin · frar · Office-Monitor
├─ 예배교육부   기술자 3   worship-setlist-studio · teacher-helper-package · godsaengbook-grace
└─ 설교기획부   기술자 5   Sermon-Assistant · youth-sermon-app · kyle_cardnews · pray-news · 논문시뮬레이터
```

## 먼저 필요한 것

| | 확인 방법 |
|---|---|
| **자비스(cys) 터미널** | `%LOCALAPPDATA%\cys\cys.exe` 가 있으면 된다 |
| **자비스 pack** | `%USERPROFILE%\.cys\pack\bin\cys-dept` 가 있으면 된다 |
| **Git for Windows** | PowerShell에서 `git --version` · `bash --version` 이 나오면 된다 |

셋 중 하나라도 없으면 설치가 중단된다. 자비스 터미널부터 설치하라.

## 설치 3단계

### ① 패키지 받기

```powershell
git clone https://github.com/yijae78/future-ministry-dept.git "$env:USERPROFILE\future-ministry-dept"
cd "$env:USERPROFILE\future-ministry-dept"
```

폴더로 직접 내려받았다면 압축을 풀고 그 폴더로 이동하면 된다.

### ② 먼저 계획만 본다 (아무것도 바뀌지 않는다)

```powershell
.\tools\setup.ps1
```

무엇을 만들고 무엇을 받아올지 전부 출력된다. **이 단계에서는 파일이 하나도 바뀌지 않는다.**
내용을 읽어보고 이상이 없으면 다음으로 간다.

### ③ 실제로 설치한다

```powershell
.\tools\setup.ps1 -Apply
```

이 명령 하나가 아래를 순서대로 처리한다.

1. 부서 선언을 `~/.cys/dept-catalog.json` 에 병합 (기존 파일은 자동 백업)
2. 미션 문서 4개를 `~/.cys/dept-missions/` 에 설치
3. 작업 폴더 `%USERPROFILE%\Future-Ministry\...` 생성
4. `cys-dept create` 로 부서 4개 생성 — **부서 번호는 이 PC에 맞게 새로 발급된다**
5. 헌장(`CHARTER.md`)을 부서 pack에 설치
6. 기술자 리포 11개 클론 (이미 있으면 건너뛴다)
7. 기술자 좌석 편성
8. 결과 검증 출력

한 번 더 실행해도 안전하다(멱등). 중간에 실패한 항목은 마지막 "경고" 목록에 모여 나온다.

## 설치 확인

```powershell
# 부서가 등록됐는지
Get-Content "$env:USERPROFILE\.cys\depts.json" | Select-String "future-ministry|fm-admin|fm-worship|fm-sermon"

# 부서 데몬이 살아 있는지 (N = 위에서 발급된 번호)
$env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
& "$env:LOCALAPPDATA\cys\cys.exe" list

# 기술자 폴더가 받아졌는지
Get-ChildItem "$env:USERPROFILE\Future-Ministry" -Recurse -Depth 1 -Directory
```

자비스 앱을 열면 왼쪽 탭에 **Future Ministry(칼빈)** 이 뜨고, 그 아래로 3개 부가 들여쓰기되어 붙는다.
바로 안 보이면 최대 10초 기다려라 — 앱이 10초 주기로 부서 목록을 다시 맞춘다.

## 자주 쓰는 옵션

```powershell
.\tools\setup.ps1 -Dept fm-admin -Apply   # 행정관리부만 설치
.\tools\setup.ps1 -Apply -SkipClone       # 리포 클론 없이 (네트워크가 없을 때)
```

## 폴더 안내

| 경로 | 내용 |
|---|---|
| `manifest.json` | 부서 위상·기술자 편성의 **정본**. 편성을 바꾸려면 여기를 고친다 |
| `CHARTER.md` | 칼빈 부서 헌장 — 임무·경계의 정본 |
| `missions/` | 부서장 4명의 미션 문서 |
| `techs/` | **기술자 11명 각각의 사용법** — 무엇을 하는지, 설치·실행법, pane 붙이는 법, 사용 시나리오 |
| `tools/setup.ps1` | 설치기 |

기술자를 실제로 쓰려면 `techs/<이름>.md` 를 보면 된다. 리포마다 설치·실행 방법이 다르다.

## 문제가 생기면

| 증상 | 원인·조치 |
|---|---|
| `cys-dept 를 찾을 수 없다` | 자비스 pack 미설치. 자비스 터미널을 먼저 설치하라 |
| `bash 를 찾을 수 없다` | Git for Windows 설치 필요 |
| 특정 리포 클론 실패 | 네트워크·권한 문제다. 경고만 남고 나머지 설치는 끝까지 진행된다. 나중에 그 폴더에서 `git clone` 을 직접 해도 된다 |
| 부서 탭이 안 보임 | 10초 기다려라. 그래도 없으면 `depts.json` 에 등록됐는지부터 확인하라 |
| 되돌리고 싶다 | `~/.cys/dept-catalog.json.bak-<날짜>` 로 카탈로그를 복원하고, `cys-dept down <dept-N>` 으로 부서를 내린다 |

## 주의

- 기술자는 **데몬이 아니라 패인(pane) 노드**다. 데몬 남발은 금지다.
- 각 부서의 작업 폴더에서는 **원격 push 금지 · 로컬 커밋만** 이 규약이다.
- 이 패키지에는 계정 정보·토큰·소켓 경로가 **들어 있지 않다.** 그런 값은 설치 시 당신의 PC에서 새로 만들어진다.
