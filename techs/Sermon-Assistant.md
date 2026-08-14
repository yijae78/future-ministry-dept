# Sermon-Assistant — 설교기획부 기술자

> 실측 근거: idoforgod/Sermon-Assistant-AgenticWorkflow@ab75428 · README 있음 · 확인 2026-08-14

## 1. 무엇을 하는가

**본문 선정부터 최종 원고까지, 11개 박사급 전문 에이전트가 설교 연구 전 과정을 체계적으로 수행하는 AI 설교 비서 자동화 시스템이다.**

이 시스템은 `AgenticWorkflow`라는 부모 프레임워크(리포 자체 표현으로 "만능줄기세포")에서 분화된 자식 시스템이다. 부모의 전체 DNA — 절대 기준, 품질 보장 체계, 안전장치, 기억 체계 — 를 구조적으로 내장한 채, 설교 연구 도메인에 특화된 GRA(Grounded Research Architecture)를 얹어 할루시네이션을 원천 차단하도록 설계돼 있다. 즉 "설교문을 그럴듯하게 써주는 도구"가 아니라, **연구의 근거성 자체를 검증 대상으로 삼는 연구 파이프라인**이다.

연구 영역은 11개로 나뉜다. 원문 분석(히브리어/헬라어), 사본학, 구조 분석, 평행 본문, 신학, 문학 비평, 수사학, 역사 맥락, 핵심 단어, 성경지리, 문화 배경이다. 이 영역들은 독립적으로 흩어져 실행되지 않고 4개의 Wave로 묶여 순차·병렬 혼합으로 진행되며, Wave 사이마다 Cross-Validation Gate가 놓여 앞 Wave의 산출물이 다음 Wave로 넘어가도 되는지를 판정한다.

품질 보증은 3계층으로 구성된다. 첫째 Agent Self-Verification — 각 에이전트가 자기 산출물을 자체 검증한다. 둘째 Cross-Validation Gates — Wave 간 교차 검증이다. 셋째 SRCS 4축 평가 — Source·Rigor·Confidence·Specificity 네 축으로 최종 점수를 매긴다. 이와 별도로 **Hallucination Firewall**이 생성 시점에서 "모든 학자가 동의한다" 같은 과잉 일반화 패턴을 차단하고, **GroundedClaim 스키마**가 모든 연구 결과에 출처·신뢰도·불확실성을 구조화해 붙이도록 강제한다. 근거 없는 단정이 구조적으로 통과할 수 없게 만든 것이 이 시스템의 핵심 설계 의도다.

사람의 개입 지점은 7개 HITL(Human-In-The-Loop) 체크포인트로 명시돼 있다. 본문 선정 → 연구 검토 → 스타일/메시지 확정 → 아웃라인 승인 → 포맷/최종 승인의 흐름이며, 각 지점은 전용 슬래시 커맨드로 대응된다. 설교자가 흐름을 잃지 않으면서도 매 단계 결정권을 쥐도록 설계된 구조다.

입력 모드는 3가지다. 주제 기반(Theme) — 본문이 아직 정해지지 않았을 때, 본문 직접 입력(Passage) — 본문이 이미 정해졌을 때, 설교 시리즈(Series) — 연속 강해 중일 때다. 여기에 기존 설교 샘플을 분석해 문체·어조를 반영하는 **스타일 학습** 기능과, 세션이 끊기거나 컨텍스트가 리셋돼도 `/sermon-resume`으로 복구되는 **Context Reset Recovery**가 붙는다.

컨텍스트 보존 체계는 부모 프레임워크에서 상속받았다. `save_context.py`(SessionEnd/PreCompact 전체 스냅샷), `restore_context.py`(SessionStart 복원), `update_work_log.py`(PostToolUse 작업 로그 누적), `generate_context_summary.py`(Stop 증분 스냅샷) 등 22개 Hook이 자동으로 작업 내역을 저장·복원한다. 안전 계열로는 `output_secret_filter.py`(시크릿 25종 이상 패턴 탐지)와 `block_destructive_commands.py`(위험 명령 차단)가 함께 등록돼 있다. 테스트는 4계층 216개(L1 Unit + L2 E2E + L3 Integration + L4 Structural)에 더해 설교 워크플로우 222개, Safety Hook 131개 자동화 테스트가 리포에 명시돼 있다.

AI 도구 호환성은 Hub-and-Spoke 패턴으로 처리된다. Claude Code는 `CLAUDE.md`, Gemini CLI는 `GEMINI.md`, Codex CLI는 `AGENTS.md`, Copilot CLI는 `.github/copilot-instructions.md`, Cursor는 `.cursor/rules/agenticworkflow.mdc`를 각각 읽어 동일한 방법론이 자동 적용된다. 자비스 부서에서 클로드·AGY·Codex 어느 노드에 붙여도 같은 규약으로 굴러간다는 뜻이다.

## 2. 리포·클론

리포: <https://github.com/idoforgod/Sermon-Assistant-AgenticWorkflow.git>

```bash
git clone https://github.com/idoforgod/Sermon-Assistant-AgenticWorkflow.git \
  "$HOME/Future-Ministry/설교기획부/Sermon-Assistant-AgenticWorkflow"
cd "$HOME/Future-Ministry/설교기획부/Sermon-Assistant-AgenticWorkflow"
```

## 3. 설치·실행법

README와 `SERMON-ASSISTANT-USER-MANUAL.md`가 명시한 절차를 원문 수준으로 옮긴다.

### 3.1 사전 준비

| 항목 | 필수 여부 | 설명 |
|------|----------|------|
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | 필수 | `npm install -g @anthropic-ai/claude-code` |
| Python 3.10+ | 필수 | GRA 검증 라이브러리 실행 |
| PyYAML | 필수 | `pip install pyyaml` |
| GitHub 계정 | 권장 | 저장소 clone |

```bash
npm install -g @anthropic-ai/claude-code
pip install pyyaml
```

> 리포의 `pyproject.toml`은 `requires-python = ">=3.8"`로 선언돼 있으나, 사용자 매뉴얼은 Python 3.10+를 요구한다. 더 엄격한 쪽(3.10+)을 따른다.

### 3.2 설치 및 실행

```bash
git clone https://github.com/idoforgod/Sermon-Assistant-AgenticWorkflow.git
cd Sermon-Assistant-AgenticWorkflow
claude          # Claude Code 실행
```

Claude Code가 실행되면 `CLAUDE.md`를 자동으로 읽고, 시스템의 절대 기준·GRA 프로토콜·22개 Hook이 자동 적용된다.

### 3.3 인프라 검증

첫 실행 시 자동으로 `setup_init.py`가 인프라 건강을 검증한다. 수동 검증이 필요하면 Claude Code 안에서 다음을 입력한다.

```
/install
```

`/install`은 `.claude/hooks/setup.init.log`를 읽어 CRITICAL / WARNING / INFO로 분류하고 문제를 해결한다. 로그 파일이 없으면 `claude --init`으로 Setup Hook을 먼저 실행해야 한다.

### 3.4 워크플로우 시작

```
시작하자
```

또는 직접 커맨드를 쓴다.

```
# 주제 기반 (Mode A)
/sermon-start theme 고난 중에도 하나님을 신뢰하는 것

# 본문 직접 입력 (Mode B)
/sermon-start passage 시편 23:1-6

# 설교 시리즈 (Mode C)
/sermon-start series 요한복음 강해 시리즈 - 3주차 (요 3:1-21)
```

### 3.5 입력 모드 3종

| Mode | 입력 | 사용 시기 | 예시 |
|------|------|---------|------|
| **Mode A** (기본) | 주제/테마 | 본문이 정해지지 않았을 때 | `고난 중에도 하나님을 신뢰하는 것` |
| **Mode B** | 본문(Pericope) | 본문이 이미 정해졌을 때 | `시편 23:1-6` |
| **Mode C** | 설교시리즈 | 시리즈 설교 중일 때 | `요한복음 강해 시리즈 - 3주차 (요 3:1-21)` |

### 3.6 커맨드 레퍼런스

| 커맨드 | 설명 | HITL |
|--------|------|------|
| `/sermon-start` | 설교연구 워크플로우 시작 | - |
| `/sermon-select-passage` | 본문 선정 및 연구 옵션 설정 | HITL-1 |
| `/sermon-review-research` | 연구 결과 검토 | HITL-2 |
| `/sermon-set-style` | 설교 유형 및 청중 설정 | HITL-3a |
| `/sermon-confirm-message` | 핵심 메시지 확정 | HITL-3b |
| `/sermon-approve-outline` | 아웃라인 승인 | HITL-4 |
| `/sermon-set-format` | 원고 형식 및 분량 설정 | HITL-5a |
| `/sermon-finalize` | 최종 검토 및 완료 | HITL-5b |
| `/sermon-status` | 진행 상태 확인 | - |
| `/sermon-resume` | 컨텍스트 리셋 후 재개 | - |
| `/sermon-learn-style` | 설교 스타일 수동 분석 | - |
| `/sermon-evaluate-srcs` | SRCS 평가 수동 실행 | - |

### 3.7 사용자 참고 자료 우선순위

`user-resource/` 폴더에 주석서·논문 등을 넣으면 최우선으로 참조된다.

| 우선순위 | 소스 | 설명 |
|---------|------|------|
| 1 (최우선) | `user-resource/` | 사용자 제공 자료 (주석서, 논문 등) |
| 2 | 웹 검색 | 학술 논문, 주석서 |
| 3 | 기본 지식 | AI 내장 지식 |

### 3.8 워크플로우 구조

```
Phase 0: 초기화 → 3-File Architecture 설정
    │
Phase 1: Research
    ├── Wave 1 (병렬): 원문 분석, 사본 비교, 성경지리, 역사문화 배경
    │       └── Cross-Validation Gate 1
    ├── Wave 2 (병렬): 구조 분석, 평행 본문, 핵심 단어
    │       └── Cross-Validation Gate 2
    ├── Wave 3 (병렬): 신학적 분석, 문학적 분석, 역사/문화 맥락
    │       └── Cross-Validation Gate 3
    ├── Wave 4 (순차): 플롯/수사학적 분석
    │       └── SRCS 4축 평가
    └── 연구 종합 (2000-2500자 압축)
    │
Phase 2: Planning → 스타일 선택 → 핵심 메시지 도출 → 아웃라인 설계
    │
Phase 2.5: Style Analysis (조건부) → 사용자 설교 스타일 반영
    │
Phase 3: Implementation → 원고 작성 → 품질 검토 → 최종 원고
```

### 3.9 문제 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| "PyYAML not found" | Python 패키지 미설치 | `pip install pyyaml` |
| Hook 에러 | 인프라 검증 실패 | `/install` 실행 |
| 연구 결과가 나오지 않음 | 에이전트 실패 | `/sermon-status`로 확인 후 해당 Wave 재실행 |
| 컨텍스트 리셋 | 토큰 한계 초과 | `/sermon-resume`으로 복구 |

### 3.10 테스트 (선택)

```bash
python -m pytest        # pyproject.toml의 pytest 설정을 따른다 (testpaths = ["tests"])
```

> ⚠ 이 리포는 API 키를 요구하는 `.env` 파일을 사용하지 않는다(Claude Code 구독 인증을 그대로 쓴다). 어떤 문서에도 실제 키·토큰을 적지 않는다.

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(설교기획부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지).
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):
  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "Sermon-Assistant" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\Sermon-Assistant-AgenticWorkflow"
  ```
- 또는 패키지의 `tools/setup.ps1 -Dept fm-sermon -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

## 5. 대표 사용 시나리오

**상황**: 이번 주일 설교 본문이 시편 23편으로 이미 정해져 있고, 원문 분석까지 포함한 연구 패키지와 최종 원고를 만들어야 한다.

```powershell
# ① 기술자 패인을 연다 (부서 소켓 번호는 설치 시 발급된 값으로 대체)
$env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
& "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "Sermon-Assistant" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\Sermon-Assistant-AgenticWorkflow"
```

```bash
# ② 최초 1회 — 의존성 설치
npm install -g @anthropic-ai/claude-code
pip install pyyaml

# ③ 리포로 이동해 Claude Code 기동
cd "$HOME/Future-Ministry/설교기획부/Sermon-Assistant-AgenticWorkflow"
claude
```

Claude Code 안에서 진행한다.

```
# ④ 인프라 검증 (최초 1회)
/install

# ⑤ 본문 직접 입력 모드로 시작
/sermon-start passage 시편 23:1-6

# ⑥ HITL-1 — 원문 분석 수준을 Expert(본문비평 포함), 연구 범위를 전체 11개 영역으로 설정
/sermon-select-passage

# ⑦ Wave 1~4 + Gate 1~3 + SRCS 자동 진행. 완료 후 연구 결과 검토
/sermon-review-research

# ⑧ 설교 유형·청중 설정 → 핵심 메시지 확정 → 아웃라인 승인
/sermon-set-style
/sermon-confirm-message
/sermon-approve-outline

# ⑨ 원고 형식·분량 지정 후 최종화
/sermon-set-format
/sermon-finalize
```

산출물은 `sermon-output/[passage-YYYY-MM-DD]/` 아래에 쌓인다. `research-package/`에 11개 영역 연구 결과가, `pacs-logs/`에 품질 평가 로그가, `session.json`에 도메인 상태 SOT가 저장된다.

작업 도중 컨텍스트가 초과돼 세션이 끊어졌다면 다시 `claude`를 띄우고 다음 한 줄로 복귀한다.

```
/sermon-resume
```

기존 설교 원고를 참고 자료로 먹여 문체를 학습시키려면, 원고 파일을 `user-resource/`에 넣은 뒤 다음을 실행한다.

```
/sermon-learn-style
```
