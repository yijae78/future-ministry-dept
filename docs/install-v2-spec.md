# 설치기 v2 계약(SPEC) — 맥·윈도우 "설치 버튼 하나" · 2026-09-03

> 목표: **공식 자비스(upstream cys 0.14.x)만 깔린 목사님 PC(Windows 11 / macOS Apple Silicon·Intel)에서 대시보드의 설치 버튼만으로 부서·기술자 설치가 예외 없이 완주**한다.
> 원칙: ①유저 환경(PATH·시스템 Git·winget·brew·pwsh·코드페이지)을 믿지 않는다 — 아는 것은 자비스 설치 위치 하나 ②관문 = 실행 환경 ③실패는 원문과 함께 로그에 ④거짓 성공 금지(실물로만 판정) ⑤안내는 목사님 언어, 판단은 기계 ⑥로직은 **1벌**(Python) — OS별 차이는 얇은 런처·수신부에만.

## 1. 구조

```
tools/
  install.cmd              # Windows 런처(더블클릭·Stage0). 번들 python3 로 fm.cli 실행
  install.sh               # macOS 런처(curl | bash · .command). 번들 python3 로 fm.cli 실행
  bootstrap.ps1            # ★호환 shim: install.cmd 로 위임(구 수신부·구 안내가 가리키는 경로 보존)
  cys-install-handler.ps1  # ★호환 shim: fm.cli handle <url> 로 위임(이지현 PC 등 기등록 레지스트리 보존)
  setup.ps1 / doctor.ps1 / setup.sh  # 삭제(로직 이중화 금지). 필요 시 shim 1줄만
  fm/                      # Python 패키지(정본 · 1벌)
    __init__.py
    cli.py        # 서브커맨드: bootstrap | install [--dept K] [--only ID] [--deps] | doctor | handle <url> | receiver-register | env
    resolve.py    # 자비스 런타임 해석기(OS별 절대경로) + 실행 환경(PATH·env) 구성
    steps.py      # 설치 단계 ①~⑪ (setup.ps1 이식 · 멱등)
    doctor.py     # 실물 검사 + last-result.json
    handler.py    # cys-install://(dept|tech)/<id> 화이트리스트 → install 호출 → 알림
    receiver.py   # Windows HKCU 등록 / macOS osacompile 수신부 앱 생성 + lsregister
    log.py        # UTF-8 로그(파일·콘솔) · 바탕화면 사본 · 자기진단 헤더 · 최종 배너
    manifest.py   # manifest.json 로드·검증(스키마 고정)
```

## 2. 자비스 런타임 해석기(resolve.py) — 유일한 진실
| 항목 | Windows | macOS |
|---|---|---|
| 앱 루트 | `%LOCALAPPDATA%\cys` (폴백: 레지스트리 Uninstall 키 `cys` InstallLocation → `Get-Command cys` 부모) | `/Applications/cys.app` → `~/Applications/cys.app` → `mdfind "kMDItemCFBundleIdentifier == '<cys bundle id>'"` |
| cys / cysd | `<루트>\cys.exe`, `<루트>\cysd.exe` | `<앱>/Contents/MacOS/cys`, `…/cysd` |
| python3 | `<루트>\runtime\python\python3.exe` | `<앱>/Contents/Resources/runtime/python/bin/python3` |
| git | `<루트>\runtime\git\cmd\git.exe` | `<앱>/Contents/Resources/runtime/git/bin/git` |
| bash | `<루트>\runtime\git\usr\bin\bash.exe` (MSYS 실물) | `/bin/bash` (3.2 · cys-dept 호환 명시됨) |
| node/npm | `<루트>\runtime\node\{node.exe,npm.cmd}` | `<앱>/Contents/Resources/runtime/node/bin/{node,npm}` |
| cys-dept | `%USERPROFILE%\.cys\pack\bin\cys-dept` (없으면 `cys init-pack`) | `$HOME/.cys/pack/bin/cys-dept` (동일) |
| 실행 env | PATH 선두 = [루트, runtime\python, runtime\git\cmd, runtime\git\usr\bin, runtime\node] · `MSYS_NO_PATHCONV=1` · `PYTHONUTF8=1` · `CYS_*` 전삭제 · `ORIGINAL_PATH` 삭제 | PATH 선두 = [MacOS, runtime/python/bin, runtime/git/bin, runtime/node/bin, /usr/bin:/bin] · `CYS_*` 전삭제 |
| bash 호출 | `bash <script> args` (비로그인 · `-l` 금지) | 동일 |
| 자비스 없음 | 한 줄: "자비스가 아직 설치되지 않았습니다 → 내려받기" + 브라우저 열기 · exit 10 | 동일 |
| HOME 정합 | `cys`가 쓰는 홈(`~/.cys` 실제 위치)과 Python `Path.home()` 비교, 다르면 cys 쪽을 채택하고 로그에 명시 | 동일 |

관문(`fm env`)은 **위 절대경로 각각을 실행**(`--version`)하고 없는 것을 경로별로 출력한다. 로그인 셸·`command -v` 의존 금지.

macOS 실측 보강(2026-09-03 분석·CI): ①DMG는 드래그형이 아니라 `Install cys.app` 도우미가 숨은 `.support/cys.app`을 **`/Applications/cys.app`(고정)** 에 설치한다 → 해석기 1순위 경로가 그것 ②`/usr/local/bin/cys` 심볼릭은 앱의 「셸에 cys 설치」 버튼(관리자 승인)으로만 생기므로 **없다고 가정**(cys-dept:26-27의 `command -v`는 PATH 선두 주입으로 만족) ③맥 런타임에 bash는 동봉되지 않는다 → `/bin/bash`(3.2) 사용, cys-dept·런처는 3.2 호환 확인됨(bash4 전용 구문 0건·flock은 python fcntl) ④`~/.cys/pack`은 앱 첫 기동 온보딩 또는 `cys init-pack`으로 생기며 `init-pack`은 env HOME을 무시하고 실제 홈에 쓴다 ⑤시스템 `/usr/bin/python3`·`git`은 CLT 셔틀(실행 시 개발도구 설치 다이얼로그) → **절대 호출 금지**, 번들만 ⑥Terminal에서 `~/Desktop` 쓰기는 TCC 프롬프트 가능 → 실패 시 `~/Downloads`로 폴백 ⑦URL 수신부 = osacompile 로컬 앱 + `CFBundleURLTypes`(cys-install) + `lsregister -f` — GitHub macOS 러너에서 발화·수신 **검증 완료**(mac-probe run 33736709058 job ①).

## 3. 설치 단계(steps.py · 멱등 · 각 단계는 "이미 됨/새로 함/실패"를 로그)
0. 자기진단 헤더: OS·버전·아키텍처·해석된 경로 5종·버전 5종·PATH 선두·HOME·패키지 커밋
1. 카탈로그 `~/.cys/dept-catalog.json` 등록(manifest → departments/accounts 병합, 기존 사용자 값 보존, `.bak-<ts>` 3개 회전)
2. 미션 `missions/*.md` → `~/.cys/dept-missions/<mission_key>.md`
3. 작업 폴더 `cwd_template` 생성(한글 경로는 Python이 처리 · bash로 넘길 때 UTF-8 유지)
4. 부서 생성: `cys-dept create <key>` 루트→하위 순, stdout 마지막 `dept-N` 파싱, REUSE 정상, exit 3/4/5/6/7/8 별 목사님 언어 메시지 매핑. 계정 폴더(`~/.cys/claude` 등) 없으면 **선행 생성**. 상한(`CYS_DEPT_CAP`) 사전 계산·안내
5. `~/.cys/depts.json` parent 백필 — **부서 키**로(표시명 금지)
6. `CHARTER.md` → `~/.cys/pack-dept-<dept-N>/`
7. 기술자 클론(번들 git · `--depth 1` · `visibility:public`은 필수, `optional:true`는 경고) · `.git` 없는 폴더는 `.broken-<ts>`로 치우고 재클론
8. 의존성(`--deps` 또는 `delivery:install` 기본 on): 번들 node/python으로 `npm install`/`pip install` · 실패는 **실패**로 계상(기술자 단위)
9. 좌석(surface) 정합: 데몬 `ping` 최대 30s 재시도 후 판정
10. 수신부 등록: Windows HKCU `cys-install` → `install.cmd handle "%1"` 경로 / macOS `~/Applications/자비스 설치 수신부.app`(osacompile · CFBundleURLTypes `cys-install` · `lsregister -f`)
11. doctor → `~/.cys/fm-install/last-result.json` + 바탕화면 `퓨처미니스트리-설치로그.txt`(UTF-8) + 최종 배너 한 줄(성공/실패 + 로그 경로 + "이 파일을 보내주세요")

## 4. doctor.py — 실물 검사(필수 항목 하나라도 실패 = exit 1)
카탈로그 키 · 미션 파일 · 작업 폴더 · `depts.json`의 4개 키 · `pack-dept-*` 디렉터리 · 부서 데몬 소켓 `ping` · 필수 기술자 `.git` · 수신부 등록(Windows: 레지스트리 명령줄이 가리키는 파일 실재 / macOS: `lsregister -dump`에 스킴 + 앱 실재) · 런타임 버전 5종. 결과 JSON: `{ok, checks:[{id,required,ok,detail}], log, os, ts}`.

## 5. 런처·수신부·Stage0
- **Windows** `install.cmd`: `chcp 65001`, 번들 python3 탐색(없으면 자비스 안내), `python3 -X utf8 -m fm.cli bootstrap`. Stage0(대시보드 다운로드 `.cmd`)은 같은 내용에 "패키지 클론(번들 git)" 1단계가 앞에 붙는다. 시스템 Git·winget·UAC **사용 금지**.
- **macOS** `install.sh`: `curl -fsSL …/tools/install.sh | bash` 로 진입(격리 표시 없음). 번들 python3 탐색 → 패키지 클론(번들 git) → `python3 -X utf8 -m fm.cli bootstrap`. 같은 파일을 `퓨처미니스트리-설치.command`로도 제공(우클릭→열기 안내 동봉).
- **수신부**: Windows = HKCU 등록(관리자 불필요). macOS = 로컬 생성 AppleScript 앱(격리 없음 → 경고 없음) — `on open location` → `install.sh handle <url>` → `display notification` + 실패 시 로그 열기.
- **핸들러**: 화이트리스트 `^cys-install://(dept|tech)/([a-z0-9][a-z0-9-]*)/?$` 유지, 패키지 `git pull --ff-only`(번들 git), 대상 설치, 결과 알림.
- **구 경로 호환**: `bootstrap.ps1`·`cys-install-handler.ps1`은 shim(각 5줄)으로 남긴다 — 기등록 PC(이지현)가 재실행하면 `[3/6] pull`로 새 코드를 받고 그대로 동작.

## 6. 대시보드 계약(cys-dashboard)
- 단계: ① 부서 설치 ② 잘 됐는지 확인 ③ 기술자 골라 넣기 ④ 틀로 다른 부서 (자비스 점검 단계 삭제)
- 버튼은 OS 무관 **하나**: 첫 한 번 = Windows `.cmd` 다운로드 / macOS 한 줄 복사(+`.command` 대안) · 그 다음부터 = `cys-install://…`
- 오너 스캔값 표시 제거(요약 타일·메타바·푸터·상세의 브랜치/커밋/파일수/경로/폴더존재/준비점검) → manifest 정적 카탈로그
- ② 확인 = 설치기 최종 배너 모형 + 자비스 사이드바 모형 + "네, 이렇게 보여요" + 실패 시 로그 보내기 안내
- 문제 해결 항목: 자비스 미설치 / 인터넷 / Windows SmartScreen·Edge 다운로드 차단 / macOS 우클릭→열기 / 로그 보내기

## 7. 검증(CI · 부서 저장소 `.github/workflows/install-e2e.yml`)
matrix: `windows-latest`(setup.exe `/S`) · `macos-latest`(arm64 DMG) · `macos-13`(x64 DMG). 각: 공식 자비스 설치 → Stage0 진입(`.cmd` / `install.sh`) → `doctor` JSON `ok:true` 단언 → 수신부 발화(`cys-install://tech/frar`)로 핸들러 경로 검증 → 2회 재실행 멱등 단언 → 로그 아티팩트. 로컬 V1(한글 콘솔 렌더) + 실유저 수락(Windows 이지현 · macOS 지원자 1인).

## 8. 합격 기준(V0)
ⓐ 부서 4개 생성(depts.json·pack-dept·ping) ⓑ 필수 기술자 전량 클론 ⓒ doctor ok ⓓ 한글 로그 정상 ⓔ 2회 재실행 동일 결과 ⓕ 수신부 발화 성공 ⓖ 대시보드 ② 확인 완료 — 3개 러너 + 실유저 2명.
