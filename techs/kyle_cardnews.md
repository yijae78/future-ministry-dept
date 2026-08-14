# kyle_cardnews — 설교기획부 기술자

> 실측 근거: yijae78/kyle_cardnews@fb85487 · README 있음 · 확인 2026-08-14

## 1. 무엇을 하는가

**설교 자료를 인스타그램 카드뉴스 10장(1080×1350·4:5) + 캡션 + 카카오톡 공유 메시지로 전자동 변환하는 Claude Code 스킬 스위트다(v2.0).**

리포 자체의 설명에 따르면 디딤교회 주간 콘텐츠 자동화 시스템에서 실운영으로 검증된 워크플로우를 범용화해 공개한 것이다. 즉 이론적 템플릿이 아니라 매주 실제로 돌아간 파이프라인을 추출한 산출물이다.

아키텍처는 **대표 1 + 하위 5** 구조다. 사용자는 대표 스킬(`sns-cardnews`)과만 대화한다. 대표 스킬이 하위 스킬 5종을 목적에 맞게 스스로 호출하고, 전 과정을 Orchestration Trace로 보여준다.

```
사용자 ── sns-cardnews (대표 · 단일 창구)
              ├─ sns-cardnews-context   설교 자료에서 CMT·FCF·HP 자동 추출
              ├─ sns-cardnews-design    슬라이드별 디자인 브리프 (트렌드 리서치 포함)
              ├─ sns-cardnews-copy      10장 텍스트 + 캡션 + 카톡 메시지
              ├─ sns-cardnews-build     HTML 조립 + Puppeteer PNG 캡처
              └─ sns-cardnews-verify    독립 검증 (성경 인용 대조·복음 비트·규격)
```

이 설계에는 세 가지 방어 장치가 박혀 있다.

첫째, 하위 스킬은 전부 `disable-model-invocation: true`로 선언돼 있다. 대표 스킬의 오케스트레이션으로만 실행되며 직접 발동이 불가능하다. 모델이 임의로 하위 단계를 건너뛰거나 순서를 뒤집는 것을 막고, 동시에 모델 부담을 줄인다.

둘째, **작성자·검증자 분리**다. 성경 인용의 정확성, 복음 비트(Gospel Point)의 생존 여부, 규격 준수는 콘텐츠를 만든 스킬이 아니라 `sns-cardnews-verify`가 독립적으로 판정한다. 검증을 통과하기 전에는 완성으로 인정되지 않는다. 자기가 만든 것을 자기가 채점하지 않는다는 원칙이 구조로 강제돼 있다.

셋째, **선택 지점에서의 강제 질문**이다. 표지 제목 2안, 디자인 방향 분기, 브랜드 미설정처럼 선택이 결과를 가르는 지점에서는 대표 스킬이 진행 전에 사용자에게 묻는다. 임의 확정이나 하드코딩이 금지돼 있다.

콘텐츠 설계의 신학적 뼈대는 Bryan Chapell의 그리스도 중심 설교학 용어 체계를 따른다.

| 약어 | 뜻 |
|------|-----|
| CMT | Central Message of the Text — 본문의 중심 진리 |
| FCF | Fallen Condition Focus — 본문이 다루는 인간의 문제 |
| HP | Hope/Gospel Point — 그리스도 안에서의 복음적 해답 |

중요한 실용적 특징은 **입력의 관대함**이다. 설교 요약(`sermon-context.md`)이 미리 준비돼 있지 않아도 된다. `sns-cardnews-context`가 원고 전문·요약·구두 전사 무엇이 들어오든 판별해 CMT·FCF·HP를 자동 추출한다. 사용자에게 수동 입력을 요구하지 않는 것이 명시된 설계 원칙이다.

출력 채널별 규칙은 `rules/`에 분리돼 있다. `instagram.md`가 캡션 세부 규칙(300자·해시태그)을, `kakaotalk.md`가 카톡 세부 규칙(150자)을 담당한다. 교회별 브랜드는 `config/brand-guide.md` 템플릿에 교회명·주일예배 시간·SNS 계정·고정 해시태그·색상 팔레트·슬라이드별 배색을 채워 넣는 방식으로 주입한다.

최종 이미지 산출은 `scripts/capture-cardnews.js`가 담당한다. Puppeteer로 HTML을 열어 `.slide` 클래스 요소를 하나씩 스크린샷하며, 540×675 뷰포트에 `deviceScaleFactor: 2`를 걸어 정확히 1080×1350 PNG를 뽑는다. 웹폰트 로딩 완료(`document.fonts.ready`)를 기다린 뒤 추가로 1.5초를 더 대기해 폰트 깨짐을 방지한다.

v1(단일 SKILL.md + 참조 문서)은 커밋 이력에 보존돼 있다. v2는 대표/하위 스킬 분리, 자동 컨텍스트 추출, 독립 검증 스킬, Orchestration Trace가 추가된 전면 재설계다. 라이선스는 MIT다.

## 2. 리포·클론

리포: <https://github.com/yijae78/kyle_cardnews.git>

```bash
git clone https://github.com/yijae78/kyle_cardnews.git \
  "$HOME/Future-Ministry/설교기획부/kyle_cardnews"
cd "$HOME/Future-Ministry/설교기획부/kyle_cardnews"
```

## 3. 설치·실행법

README의 "빠른 시작"을 원문 수준으로 옮긴다.

### 3.1 요구 환경

- Claude Code (또는 SKILL.md 스킬 체계를 지원하는 LLM 에이전트)
- Node.js 18+ (PNG 캡처 시)

### 3.2 빠른 시작 (4단계)

**1단계 — `skills/` 아래 6개 폴더를 프로젝트의 `.claude/skills/`로 복사한다.**

```bash
cp -r skills/* <프로젝트>/.claude/skills/
```

**2단계 — `config/`·`scripts/`를 프로젝트로 복사하고 `config/brand-guide.md`를 자기 교회 값으로 채운 뒤 `config/logo.png`를 추가한다.**

```bash
cp -r config scripts <프로젝트>/
```

**3단계 — PNG 캡처 의존성을 설치한다.**

```bash
npm install
```

(루트 `package.json`의 의존성은 `puppeteer@^24.0.0` 하나다.)

**4단계 — Claude Code에서 다음과 같이 요청한다.**

```
이 설교로 카드뉴스 만들어줘
```

+ 설교 원고(전문·요약·전사 무엇이든)를 함께 준다.

설교 요약(`sermon-context.md`)이 없어도 된다 — `sns-cardnews-context`가 원고에서 자동 추출한다.

### 3.3 브랜드 설정 (`config/brand-guide.md`)

템플릿에 자기 교회 값을 채운다. 실측 기준 템플릿 항목은 다음과 같다.

```markdown
## 기본 정보

| 항목 | 값 |
|------|-----|
| 교회명 | {교회명} |
| 주일예배 시간 | {예: 주일 오전 11시} |
| SNS 계정 | {예: @church_instagram} |
| 고정 해시태그 | {예: #우리교회} #주일설교 #말씀카드 |

## 로고

- `config/logo.png` — 기본 로고 (마지막 슬라이드 필수)
- `config/logo-white.png` — 흰색 버전 (어두운 배경용·선택)
```

색상 팔레트도 템플릿에 예시 값이 들어 있으며 자유롭게 교체한다.

| 용도 | 색상 | HEX | 사용처 |
|------|------|-----|--------|
| Primary | 네이비 블루 | `#1B2A4A` | 제목, 헤더, 주요 텍스트 |
| Secondary | 올리브 그린 | `#6B7B3A` | 보조 배경 |
| Accent | 골드 | `#C4A35A` | 강조, 구분선, 아이콘 |
| Background | 크림 | `#FAF8F5` | 본문 배경 |
| Text | 차콜 | `#333333` | 기본 텍스트 |

슬라이드별 배색 예시도 함께 선언돼 있다.

| 슬라이드 | 배경색 | 텍스트 색 |
|----------|--------|----------|
| 표지 | Primary | `#FFFFFF` |
| 공감 | Background | Text |
| 핵심 메시지 | `#FFFFFF` | Primary |
| 적용/초대 | Secondary | `#FFFFFF` |
| 인용구 | 연한 Background | Primary |
| 마무리 | Primary | Accent |

### 3.4 PNG 캡처 스크립트 직접 실행

빌드 단계에서 생성된 `slide-preview.html`을 PNG로 굽는 명령이다. 스크립트 헤더에 적힌 사용법을 그대로 옮긴다.

```bash
node scripts/capture-cardnews.js <slide-preview.html 경로>
```

또는 `package.json`의 스크립트를 쓴다.

```bash
npm run capture -- <slide-preview.html 경로>
```

동작 사양(스크립트 실측):

- 출력: HTML과 **같은 폴더**에 `slide-1.png`, `slide-2.png`, … 개별 파일 생성
- 크기: 1080×1350 (4:5) — `.slide` 요소를 540×675 뷰포트 × `deviceScaleFactor: 2`로 캡처
- 대기: `networkidle0`(타임아웃 30초) → `document.fonts.ready` → 추가 1.5초
- `.slide` 클래스 요소가 하나도 없으면 에러를 내고 종료한다
- 완료 시 성공 장수와 저장 위치를 콘솔에 출력한다

### 3.5 리포 구조

```
kyle_cardnews/
├── skills/
│   ├── sns-cardnews/            ← 대표 (여기에만 명령)
│   ├── sns-cardnews-context/
│   ├── sns-cardnews-design/
│   ├── sns-cardnews-copy/
│   ├── sns-cardnews-build/
│   └── sns-cardnews-verify/
├── rules/
│   ├── instagram.md             ← 캡션 세부 규칙 (300자·해시태그)
│   └── kakaotalk.md             ← 카톡 세부 규칙 (150자)
├── config/
│   └── brand-guide.md           ← 교회 브랜드 템플릿 (교회명·색상·해시태그·로고)
├── scripts/
│   └── capture-cardnews.js      ← HTML → 1080×1350 PNG (Puppeteer)
└── package.json
```

> ⚠ 이 리포는 API 키나 `.env`를 요구하지 않는다. 브랜드 가이드에 SNS 계정명을 적을 때도 비밀번호·토큰류는 넣지 않는다.

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(설교기획부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지).
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):
  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "kyle_cardnews" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\kyle_cardnews"
  ```
- 또는 패키지의 `tools/setup.ps1 -Dept fm-sermon -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

## 5. 대표 사용 시나리오

**상황**: 이번 주일 설교 원고가 완성됐다. 이것을 인스타그램 카드뉴스 10장 + 캡션 + 카톡 공유 메시지로 만들어 주중에 배포해야 한다.

```powershell
# ① 기술자 패인을 연다 (부서 소켓 번호는 설치 시 발급된 값으로 대체)
$env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
& "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "kyle_cardnews" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\kyle_cardnews"
```

```bash
# ② 최초 1회 — 스킬 스위트를 작업 프로젝트에 이식한다
cd "$HOME/Future-Ministry/설교기획부/kyle_cardnews"
npm install                       # puppeteer 설치

WORK="$HOME/Future-Ministry/설교기획부/주간콘텐츠"
mkdir -p "$WORK/.claude/skills"
cp -r skills/* "$WORK/.claude/skills/"
cp -r config scripts "$WORK/"

# ③ 브랜드 값을 채운다
#    $WORK/config/brand-guide.md 를 열어 교회명·예배시간·SNS계정·해시태그·색상을 기입
#    $WORK/config/logo.png 에 교회 로고를 넣는다 (마지막 슬라이드에 필수)
```

```bash
# ④ 작업 프로젝트에서 Claude Code를 띄운다
cd "$WORK"
claude
```

Claude Code 안에서 대표 스킬에만 말을 건다.

```
이 설교로 카드뉴스 만들어줘

(설교 원고 파일을 첨부하거나 sermons/20260816-주일설교/manuscript.md 경로를 알려준다)
```

이후 진행은 대표 스킬이 자동으로 오케스트레이션한다.

1. **입력 분류** — 원고 전문/요약/구두 전사 중 무엇이 들어왔는지 판별한다. CMT·FCF·HP가 없으면 `sns-cardnews-context`를 호출해 자동 추출한다.
2. **선택 질문** — 표지 제목 2안, 디자인 방향 분기, 브랜드 미설정 항목이 있으면 진행 전에 물어본다. 여기서 답을 준다.
3. `sns-cardnews-design` — 슬라이드별 디자인 브리프를 만든다(트렌드 리서치 포함).
4. `sns-cardnews-copy` — 10장 텍스트 + 인스타 캡션(300자·해시태그) + 카톡 메시지(150자)를 쓴다.
5. `sns-cardnews-build` — HTML을 조립하고 Puppeteer로 PNG를 캡처한다.
6. `sns-cardnews-verify` — 성경 인용 대조, 복음 비트 생존, 규격, 과장 표현을 독립 검증한다. 실패 항목은 해당 하위 스킬로 되돌려 수정 후 1회 재검증한다.

빌드 산출 HTML만 있고 PNG를 다시 굽고 싶으면 스크립트를 직접 돌린다.

```bash
node scripts/capture-cardnews.js "$WORK/output/20260816/slide-preview.html"
# → 같은 폴더에 slide-1.png ~ slide-10.png (각 1080×1350) 생성
```

결과 확인 항목은 다음 세 가지다. 10장 PNG가 모두 1080×1350인지, 마지막 슬라이드에 로고가 들어갔는지, `sns-cardnews-verify`가 통과 판정을 냈는지다. 검증 통과 전에는 완성으로 취급하지 않는다.
