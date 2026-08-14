# Church-Admin — 행정관리부 기술자

> 실측 근거: yijae78/Church-Admin-AgenticWorkflow@e551dea · README 있음 · 확인 2026-08-14

## 1. 무엇을 하는가

한국 중소형 교회(100~500명)의 반복 행정 업무를 AI 에이전트가 대신 수행하는 에이전틱 워크플로우 시스템이다.

이 리포는 두 겹 구조다. 바깥쪽은 **AgenticWorkflow** 프레임워크(부모)이고, 안쪽 `church-admin/` 디렉터리가 그 프레임워크에서 분화되어 나온 **교회 행정 시스템**(자식)이다. README는 이 관계를 "만능줄기세포(Pluripotent Stem Cell) 프레임워크에서 분화되었다"고 표현하며, 자식이 부모의 DNA — 절대 기준, 품질 보장, 안전장치, 기억 체계 — 를 구조적으로 내장한다고 명시한다. 따라서 실제 교회 업무를 돌리는 작업 디렉터리는 리포 루트가 아니라 `church-admin/`이다.

해결 대상은 README가 표로 명시한 6개 업무다. 주보 제작(주당 약 4시간 → 약 15분), 새신자 등록·관리(약 3시간 → 약 30분), 재정 기록·보고(약 6시간 → 약 2시간, 이중 검토는 유지), 증명서·공문 발급(약 3시간 → 약 15분), 일정 관리(약 2시간 → 약 15분, 충돌 자동 감지), 기타 데이터 정리(약 5시간 → 약 1시간). 합계로 주당 약 23시간이 약 4시간 15분으로 줄어든다는 것이 리포가 내건 수치다.

시스템 구성은 다음과 같다. **5개 독립 워크플로우**(주보 생성, 새신자 파이프라인, 월별 재정 보고, 문서 발급, 일정 관리)가 `workflows/`에 영문·한국어 쌍으로 들어 있다. **8개 전문 에이전트**(`bulletin-generator`, `data-ingestor`, `document-generator`, `finance-recorder`, `member-manager`, `newcomer-tracker`, `schedule-manager`, `template-scanner`)가 각자 담당 데이터 파일에 대해 **단독 쓰기 권한**을 갖는다 — 두 에이전트가 같은 파일을 건드리는 상황을 구조적으로 없애 데이터 충돌을 원천 차단하는 설계다.

품질 쪽은 **29개 결정론적 검증 규칙**이 뼈대다. P1 검증 스크립트 5개가 각각 Members M1~M7, Finance F1~F7, Schedule S1~S6, Newcomers N1~N6, Bulletin B1~B3을 담당한다. 이 검증은 LLM의 판단이 아니라 Python 스크립트가 수행하므로 할루시네이션이 끼어들 여지가 없다. 그 위로 4계층 품질 보장 스택 — L0 Anti-Skip Guard(파일 존재 + 100 bytes 이상), L1 Verification Gate(기능적 목표 100% 달성 자기검증), L1.5 pACS Self-Rating(F/C/L 3차원 신뢰도, min-score 원칙, GREEN ≥70 자동 진행 / YELLOW 50~69 플래그 후 진행 / RED <50 재작업), L2 Adversarial Review(`@reviewer` + `@fact-checker` 서브에이전트 독립 검토) — 가 얹힌다.

인터페이스는 셋이다. 첫째, **한국어 자연어** — 41개 한국어 명령 패턴이 8개 카테고리로 매핑되어 "주보 만들어줘", "새신자 등록", "이번 달 재정 보고서" 같은 말이 그대로 명령이 된다. 둘째, **5개 Slash Command** — `/start`(대화형 시작 메뉴), `/generate-bulletin`, `/generate-finance-report`, `/system-status`(건강 검사), `/validate-all`(검증). 셋째, **Streamlit 대시보드** — 비기술 사용자인 행정 간사를 위한 웹 UI로, 기능 카드 클릭·실시간 진행 표시·HitL 승인 패널을 제공하며, 무엇보다 **대시보드가 LLM 바깥에서 Python으로 직접 P1 검증을 수행**해 할루시네이션을 원천봉쇄한다.

데이터 입력은 **3계층 수신함 파이프라인**이 받는다. Tier A는 Excel/CSV, Tier B는 Word/PDF, Tier C는 이미지이며 각각 자동 파싱 후 신뢰도 점수를 매긴다. 문서 출력은 **스캔-복제 엔진**이 담당해 7종 교회 문서(주보, 영수증, 순서지, 공문, 회의록, 증서, 초청장)를 템플릿화한다. 한국 교회 용어 사전은 직분·치리·예배·재정·성례·새신자·문서 7개 축에 걸쳐 50개 이상 용어를 정규화한다.

안전장치 중 특히 중요한 것은 **재정 Autopilot 영구 비활성화**다. SOT + 에이전트 + 워크플로우 3중으로 강제되어, 재정 관련 단계는 어떤 경우에도 사람의 승인 없이 자동 진행되지 않는다. Hook 인프라는 `.claude/settings.json`에 등록된 3개 Hook(PreToolUse 단독작성자 강제, PostToolUse YAML 검증, Setup 건강검사)으로 구성된다.

데이터 민감도 정책도 명시적이다. `members.yaml`·`newcomers.yaml`(HIGH — PII)과 `finance.yaml`(HIGH — 금융)은 `.gitignore`로 공개 금지이며 삭제 방식도 각각 Soft-delete only, Void-only로 제한된다. `schedule.yaml`·`bulletin-data.yaml`·`church-glossary.yaml`(LOW)만 버전 관리 대상이다. 실제로 리포의 `church-admin/data/`에는 LOW 3종만 커밋되어 있음을 파일 트리에서 확인했다.

Hub-and-Spoke 패턴으로 AI CLI 도구 호환성을 확보한 점도 특징이다. `AGENTS.md`가 방법론 SOT(Hub)이고, Claude Code는 `CLAUDE.md`, Gemini CLI는 `GEMINI.md` + `.gemini/settings.json`, Codex CLI는 `AGENTS.md` 직독, Copilot CLI는 `.github/copilot-instructions.md`, Cursor는 `.cursor/rules/agenticworkflow.mdc`를 각각 Spoke로 읽는다. 절대 기준과 설계 원칙은 전부 동일하고 도구별 구현 매핑의 구체성만 다르다.

## 2. 리포·클론

- 리포: https://github.com/yijae78/Church-Admin-AgenticWorkflow.git
- 대상 경로: `$HOME/Future-Ministry/행정관리부/Church-Admin-AgenticWorkflow`

```bash
mkdir -p "$HOME/Future-Ministry/행정관리부"
git clone https://github.com/yijae78/Church-Admin-AgenticWorkflow.git \
  "$HOME/Future-Ministry/행정관리부/Church-Admin-AgenticWorkflow"
cd "$HOME/Future-Ministry/행정관리부/Church-Admin-AgenticWorkflow"
```

> ⚠ README 본문의 빠른 시작에는 `git clone https://github.com/idoforgod/AgenticWorkflow.git` 이 적혀 있다(개발 당시 원본 주소). 행정관리부 배포 기준 주소는 위의 `yijae78/Church-Admin-AgenticWorkflow.git` 이다.

## 3. 설치·실행법

### 3-1. 사전 준비 사항 점검표

`church-admin/docs/installation-guide.ko.md` 가 명시한 요구 사항이다.

| 요구 사항 | 버전 | 확인 명령 | 비고 |
|----------|------|----------|------|
| Python | 3.10+ | `python3 --version` | macOS: 기본 설치 또는 `brew install python3` |
| PyYAML | 최신 | `pip3 install pyyaml` | 핵심 데이터 형식 라이브러리 |
| openpyxl | 최신 | `pip3 install openpyxl` | inbox/ 1단계 Excel 파일 파싱용 |
| pandas | 최신 | `pip3 install pandas` | 보고서 데이터 처리용 |
| python-docx | 최신 | `pip3 install python-docx` | 문서 생성(증서, 공문 등) |
| Git | 2.0+ | `git --version` | 저장소 관리 |
| Claude Code | 최신 | `claude --version` | AI 에이전트 런타임 — Anthropic 구독 필요 |

**Claude Code 구독** — 이 시스템은 활성화된 Claude Code 구독이 필요하다. 구독을 통해 ①Claude AI 모델 접근(Opus/Sonnet)을 통한 에이전트 실행 ②검증 및 안전을 위한 Hook 인프라 ③서브에이전트 및 팀 조율 기능을 사용한다.

### 3-2. 1단계: 저장소 복제

```bash
# Navigate to your preferred installation directory
cd "$HOME/Future-Ministry/행정관리부"

# Clone the repository
git clone https://github.com/yijae78/Church-Admin-AgenticWorkflow.git Church-Admin-AgenticWorkflow
cd Church-Admin-AgenticWorkflow
```

### 3-3. 2단계: Python 의존성 설치

```bash
# Install all required packages
pip3 install pyyaml openpyxl pandas python-docx

# Verify installations
python3 -c "import yaml; import openpyxl; import pandas; import docx; print('All dependencies OK')"
```

예상 출력: `All dependencies OK`

### 3-4. 3단계: 교회 행정 디렉터리로 이동

```bash
cd church-admin
```

이 디렉터리가 모든 교회 행정 작업의 기본 작업 디렉터리다.

### 3-5. 4단계: 초기 설정 검증 실행

```bash
claude --init
```

이 명령은 `setup_init.py` Hook을 실행하여 다음 항목을 검증한다.

1. **Python 버전** — 3.10 이상 확인
2. **스크립트 구문** — 19개 이상의 Hook 스크립트가 오류 없이 파싱되는지 확인
3. **디렉터리 구조** — 필요한 디렉터리가 존재하거나 자동 생성: `verification-logs/`, `pacs-logs/`, `review-logs/`, `autopilot-logs/`, `translations/`, `diagnosis-logs/`
4. **PyYAML 사용 가능 여부** — 모든 데이터 작업에 필수
5. **SOT 무결성** — `state.yaml` 구조 검증 (파일이 존재하는 경우)

예상 출력:

```
Setup Init — Infrastructure Health Check
✓ Python 3.12.x
✓ 19/19 scripts OK
✓ Runtime directories OK
✓ PyYAML available
✓ SOT schema valid
```

검사 항목 중 하나라도 실패하면 출력에 해당 문제가 구체적으로 표시된다. 해결 방법은 `docs/troubleshooting.ko.md` 를 참조한다.

### 3-6. 5단계: 데이터 파일 확인

```bash
# Check data file existence
ls -la data/

# Expected files:
# members.yaml       (sample member records)
# finance.yaml        (sample financial data)
# schedule.yaml       (sample worship schedule)
# newcomers.yaml      (sample newcomer records)
# bulletin-data.yaml  (bulletin configuration)
# church-glossary.yaml (church terminology reference)
```

모든 데이터 파일에 대해 P1 검증을 실행한다.

```bash
# Validate member data (M1-M7)
python3 .claude/hooks/scripts/validate_members.py --data-dir data/

# Validate finance data (F1-F7)
python3 .claude/hooks/scripts/validate_finance.py --data-dir data/

# Validate schedule data (S1-S6)
python3 .claude/hooks/scripts/validate_schedule.py --data-dir data/

# Validate newcomer data (N1-N6)
python3 .claude/hooks/scripts/validate_newcomers.py --data-dir data/
```

모든 스크립트가 오류 없이 `X/X checks passed`를 보고해야 한다.

> 참고 — `members.yaml`·`finance.yaml`·`newcomers.yaml` 은 PII/금융 데이터라 `.gitignore` 대상이므로 클론 직후에는 존재하지 않는다. 시드 데이터가 필요하면 `python3 scripts/generate_seed_data.py` 로 생성한다(리포에 실재하는 스크립트).

### 3-7. 6단계: 에이전트 구성 확인

```bash
# List all agents
ls .claude/agents/

# Expected agents:
# bulletin-generator.md
# data-ingestor.md
# document-generator.md
# finance-recorder.md
# member-manager.md
# newcomer-tracker.md
# schedule-manager.md
# template-scanner.md
```

### 3-8. 7단계: Inbox 인프라 확인

```bash
# Check inbox directories
ls inbox/

# Expected subdirectories:
# documents/   — Word/PDF files for parsing
# errors/      — Invalid files quarantined here
# images/      — Namecard/document images
# processed/   — Successfully processed files
# staging/     — Files awaiting processing
# templates/   — Template images for scan-and-replicate
```

### 3-9. 8단계: 첫 실행 테스트

Claude Code를 시작하여 시스템이 정상적으로 응답하는지 확인한다.

```bash
claude
```

Claude Code가 시작되면 간단한 명령을 입력해 본다.

```
주보 미리보기
```

자연어 인터페이스가 정상 작동하면 Claude가 `data/bulletin-data.yaml`을 읽어 현재 주보 데이터 요약을 표시한다.

### 3-10. 설치 후 점검표

- [ ] Python 3.10 이상 설치 및 확인 완료
- [ ] Python 패키지 모두 설치 완료 (pyyaml, openpyxl, pandas, python-docx)
- [ ] 저장소 복제 및 `church-admin/` 디렉터리 접근 가능
- [ ] `claude --init` 모든 검사 통과
- [ ] `data/`에 데이터 파일 6개 존재
- [ ] 모든 P1 검증 스크립트 통과 (29/29 규칙)
- [ ] `.claude/agents/`에 에이전트 파일 8개 존재
- [ ] inbox 디렉터리 6개 존재
- [ ] Claude Code가 시작되고 한국어 명령에 응답

### 3-11. 실행 — 자연어 / Slash Command

```bash
claude                     # 시스템 시작

# 대화창에서:
"시작"                      # → 상태 수집 + 환영 배너 + 대화형 메뉴
"주보 만들어줘"              # 주보 생성
"새신자 등록"                # 새신자 파이프라인 시작
"이번 달 재정 보고서"         # 월별 재정 보고서
```

Slash Command 5종: `/start`, `/generate-bulletin`, `/generate-finance-report`, `/system-status`, `/validate-all`.

### 3-12. 실행 — Streamlit 대시보드

대시보드 전용 의존성(`church-admin/dashboard/requirements.txt` 실측):

```
streamlit>=1.30.0
pyyaml>=6.0
```

```bash
cd "$HOME/Future-Ministry/행정관리부/Church-Admin-AgenticWorkflow/church-admin"
pip3 install -r dashboard/requirements.txt
streamlit run dashboard/app.py     # 웹 UI에서 모든 기능 사용
```

> 자비스 규약 — Streamlit 실행 시 브라우저가 두 번 뜨지 않도록 `--server.headless true` 를 붙이고 브라우저는 수동으로 1회만 연다.
> `streamlit run dashboard/app.py --server.headless true --server.port 8501`

### 3-13. 민감 데이터 주의사항

다음 파일에는 개인 식별 정보(PII)가 포함되어 있으며 git에서 제외되어 있다.

- `data/members.yaml` — 교인 이름, 전화번호, 주소
- `data/finance.yaml` — 기부자 이름이 포함된 헌금 기록
- `data/newcomers.yaml` — 새신자 개인 정보

이 파일들은 `.gitignore`에 등록되어 있으며 공개 저장소에 **절대** 커밋해서는 안 된다. 데이터 보호를 위해 반드시 백업 시스템(`scripts/daily-backup.sh`)을 사용한다.

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(행정관리부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지).
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):

  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "Church-Admin-AgenticWorkflow" --cwd "$env:USERPROFILE\Future-Ministry\행정관리부\Church-Admin-AgenticWorkflow"
  ```

- 또는 패키지의 `tools/setup.ps1 -Dept fm-admin -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

## 5. 대표 사용 시나리오

### 시나리오 — 이번 주 주보를 30분 안에 만든다

`church-admin/docs/quick-start.ko.md` 의 흐름을 그대로 따른다.
`Prepare Data (10 min) → Start Claude (2 min) → Generate Bulletin (5 min) → Review & Approve (10 min) → Done!`

**1단계 — 데이터 준비 (10분).** 기술자 pane에서 작업 디렉터리로 들어간다.

```bash
cd "$HOME/Future-Ministry/행정관리부/Church-Admin-AgenticWorkflow/church-admin"
```

`data/bulletin-data.yaml` 을 열어 이번 주 설교 정보를 수정한다.

```yaml
sermon:
  title: "은혜의 능력"           # This week's sermon title
  scripture: "에베소서 2:8-10"    # Bible passage
  pastor: "이성훈"               # Preaching pastor
```

같은 파일에서 공지사항을 수정한다.

```yaml
announcements:
  - title: "수요예배 안내"
    content: "이번 주 수요예배는 오후 7시 30분에 진행됩니다."
  - title: "교회 소풍"
    content: "5월 첫째 주 토요일 교회 소풍이 있습니다. 참가 신청서를 제출해주세요."
```

찬송가 번호를 수정한다.

```yaml
hymns:
  opening: 21         # Opening hymn number
  offertory: 94       # Offertory hymn number
  closing: 370        # Closing hymn number
```

저장하면 시스템이 `data/members.yaml`에서 생일·기념일 해당 교인을, `data/schedule.yaml`에서 이번 주 일정을, `data/newcomers.yaml`에서 새신자 요약을 자동으로 끌어온다.

**2단계 — Claude Code 시작 (2분).**

```bash
claude
```

**3단계 — 주보 생성 (5분).** 대화창에 한국어로 입력한다.

```
이번 주 주보 만들어줘
```

또는 Slash Command를 쓴다.

```
/generate-bulletin
```

`bulletin-generator` 에이전트가 `data/bulletin-data.yaml`의 단독 쓰기 권한자로서 작업하고, B1~B3 결정론 검증(`validate_bulletin.py`)이 산출물을 검사한다. 결과는 `bulletins/YYYY-MM-DD-bulletin.md` 와 `bulletins/YYYY-MM-DD-worship-order.md` 로 떨어진다(리포에 2026-03-01·03-15·03-22·03-29 실물 예시가 커밋되어 있다).

**4단계 — 검토·승인 (10분).** 생성 결과를 P1 검증으로 독립 확인한다.

```bash
python3 .claude/hooks/scripts/validate_bulletin.py --data-dir data/
python3 scripts/validate_all.py
```

또는 대화창에서 `/validate-all` 을 실행한다. 전체 시스템 건강 상태가 궁금하면 `/system-status` 를 쓴다.

**대안 경로 — 행정 간사용 웹 UI.** CLI가 부담스러운 담당자에게는 대시보드를 띄워 준다.

```bash
pip3 install -r dashboard/requirements.txt
streamlit run dashboard/app.py --server.headless true --server.port 8501
```

브라우저에서 `http://localhost:8501` 을 1회만 연다. 기능 카드를 클릭하면 실행되고, 진행 상황이 실시간 표시되며, HitL 승인 패널에서 사람이 최종 확인한다. 대시보드는 LLM 밖에서 Python으로 직접 P1 검증을 돌리므로 결과 표시 자체가 할루시네이션되지 않는다.

**주의 — 재정은 절대 자동 확정되지 않는다.** `"이번 달 재정 보고서"` / `/generate-finance-report` 를 돌리더라도 재정 Autopilot은 SOT·에이전트·워크플로우 3중으로 영구 비활성화되어 있어 사람의 이중 검토 승인 단계를 반드시 거친다. 이는 버그가 아니라 설계다.
