# worship-setlist-studio — 예배교육부 기술자

> 실측 근거: https://github.com/yijae78/worship-setlist-studio.git@ef8539c · README 있음 · 확인 2026-08-14

---

## 1. 무엇을 하는가

**주제·성경본문·예배유형을 입력하면 찬양콘티(설교 예배의 찬양 순서) 초안을 자동 생성하고, 사람이 손으로 다듬은 뒤 Word/PDF로 뽑아 현장에 들고 나갈 수 있게 하는 Next.js 웹앱이다.**

이 기술자는 예배 준비의 가장 반복적이고 소모적인 구간 — "이번 주 주제가 이건데 어떤 곡을 어떤 순서로 붙일까"를 백지에서 시작하지 않게 만드는 도구다. README가 밝히는 제품 정의는 "주제, 성경본문, 예배유형을 바탕으로 찬양콘티 초안을 생성하고, 수정·저장·출력까지 할 수 있는 Next.js 웹앱"이며, `docs/01_PRD.md`가 명시한 핵심 가치는 세 가지다. ①빠른 초안 생성 ②사람 중심 수정 ③현장용 출력. 즉 이 앱은 AI가 콘티를 확정해 주는 도구가 아니라, **초안을 던져 주고 최종 판단은 인도자가 하도록 설계된 도구**다.

동작 구조는 4단 위저드다. `components/step-progress-bar.tsx`에 실제로 박혀 있는 단계 라벨은 `1. 새 콘티 → 2. 편집 → 3. 내보내기 → 4. 최종본`이며, `docs/00_PROJECT_WORKFLOW.md`가 서술하는 전체 흐름은 "입력 → 추천 → 편집 → 저장 → 출력"이다. 사용자는 홈 화면(`components/home-screen.tsx`)에서 시작해 입력 패널(`components/input-panel.tsx`)에 주제·본문·예배유형·분위기를 넣고, 추천 엔진이 초안을 만들면 편집 패널(`components/editor-panel.tsx`)에서 곡을 갈아끼우거나(`components/song-picker-modal.tsx`) 곡 정보를 직접 고치고(`components/song-editor-modal.tsx`), 내보내기 패널(`components/export-panel.tsx`)에서 문서로 뽑고, 최종본 패널(`components/final-panel.tsx`)에서 확정본을 확인한다. 예배일 선택은 `components/calendar-picker.tsx`가 담당하며 `lib/korean-holidays.ts`가 한국 절기·공휴일을 함께 물려 준다.

콘티의 골격은 5개 섹션으로 고정되어 있다. `lib/constants.ts`의 `SECTION_LABELS`가 실측 근거다 — `opening(도입) / confession(고백) / grace(은혜) / response(결단) / sending(파송)`. 추천 엔진(`lib/recommendation.ts`)은 이 5단 구조에 곡을 배치하며, README의 "구현 메모"가 밝히듯 **룰 기반 + 선택적 AI 보정 구조**다. 서버 라우트 `app/api/recommend/route.ts`를 실제로 읽어 보면 현재 구현은 외부 API 호출 없이 `buildRecommendation(input, songCatalog, referenceTeams)`만 호출하는 **순수 룰 기반**이다(입력 정규화·검증은 `lib/validators.ts`). 즉 지금 이 리포를 그대로 돌리면 외부 AI 비용 없이 완전히 로컬로 작동한다.

곡 데이터는 `data/song-catalog.json`에 들어 있고 실측 곡 수는 **36곡**이다. README가 정직하게 고지하듯 "현재 샘플 곡 메타데이터는 시작용 카탈로그이며, 실제 운영 시 교회 상황에 맞게 보강해야" 한다 — 즉 이 파일을 우리 교회 찬양팀 레퍼토리로 갈아끼우는 것이 도입 1순위 작업이다. 참고 예배팀 데이터는 `data/reference-teams.json`에 **7개 항목**이 들어 있으며, README가 명시한 기준팀은 피아워십(F.I.A Worship)·예람워십·마커스워십·아이자야씩스티원이다. 이 부분에도 README는 방어선을 쳐 두었다 — "앱은 참고 예배팀의 공개적으로 확인 가능한 흐름·소개·메타정보를 참고하지만, 공식 제휴/공식 데이터 제공을 의미하지 않습니다."

저장과 출력의 전제도 README가 못 박아 두었다. **DB가 없다.** 모든 콘티는 브라우저 LocalStorage에 저장된다(`lib/constants.ts`의 `STORAGE_KEYS` = `worship:setlist:current` / `worship:setlist:saved` / `worship:setlist:settings`, 저장 슬롯 상한 `MAX_SAVED_DRAFTS = 20`, 용량 경고선 `MAX_STORAGE_WARNING_MB = 4`). 상태 관리는 Zustand(`state/use-setlist-store.ts`)다. 출력은 `lib/exporters.ts`가 담당하는데 Word(.docx)는 `docx` 패키지로, PDF는 `jspdf` + `html-to-image`로 생성한다. 실제 Word 출력물에는 교회명·예배일 머리글, "찬양콘티" 제목, 주제·본문·예배유형·분위기, 그리고 곡마다 `순번. [섹션] 곡제목 (Key: · BPM: )` + 추천 이유 + 메모가 실린다. 악보는 앱이 만들어 주지 않고 **사용자가 가진 이미지/PDF를 첨부**하는 방식이며 첨부 상한은 `MAX_ATTACHMENT_MB = 1`(=1MB, `lib/file-utils.ts`가 처리)이다.

운영·배포 측면에서는 GitHub Actions CI(`.github/workflows/ci.yml`)가 `main`·`dev` 푸시와 모든 PR에서 lint → typecheck → build를 돌리고, `vercel.json`은 GitHub 연동 배포를 켜 두었다. 요약하면 이 기술자는 **비용 0·DB 0·계정 0으로 굴러가는 예배 준비 로컬 도구**이며, 예배교육부 기술자 pane에 붙여 두면 매주 콘티 초안을 30초 안에 뽑아 편집만 하면 되는 상태가 된다.

---

## 2. 리포·클론

- 리포: `https://github.com/yijae78/worship-setlist-studio.git`
- 커밋(실측): `ef8539c`
- 표준 설치 경로: `$HOME/Future-Ministry/예배교육부/worship-setlist-studio`

```bash
mkdir -p "$HOME/Future-Ministry/예배교육부"
git clone https://github.com/yijae78/worship-setlist-studio.git \
  "$HOME/Future-Ministry/예배교육부/worship-setlist-studio"
cd "$HOME/Future-Ministry/예배교육부/worship-setlist-studio"
```

PowerShell에서는 다음과 같다.

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Future-Ministry\예배교육부" | Out-Null
git clone https://github.com/yijae78/worship-setlist-studio.git `
  "$env:USERPROFILE\Future-Ministry\예배교육부\worship-setlist-studio"
Set-Location "$env:USERPROFILE\Future-Ministry\예배교육부\worship-setlist-studio"
```

---

## 3. 설치·실행법

### 3-1. 권장 Node 버전

README 원문: **Node.js 20.9 이상.** CI(`.github/workflows/ci.yml`)도 `node-version: 20.9`로 고정되어 있으므로 로컬도 이 선을 맞춘다.

```bash
node -v   # v20.9.0 이상이어야 한다
```

### 3-2. 빠른 시작 (README 원문 그대로)

```bash
npm install
npm run dev
```

개발 서버가 뜨면 브라우저에서 `http://localhost:3000` 을 연다(Next.js 기본 포트).

### 3-3. package.json이 제공하는 전체 스크립트 (실측)

```bash
npm run dev         # next dev      — 개발 서버
npm run build       # next build    — 프로덕션 빌드
npm run start       # next start    — 빌드 결과 구동
npm run lint        # eslint .      — 린트
npm run typecheck   # tsc --noEmit  — 타입 검사
```

CI가 도는 순서와 동일하게 로컬에서 사전 검증하려면 다음을 그대로 돌린다.

```bash
npm install
npm run lint
npm run typecheck
npm run build
```

### 3-4. 의존성 (실측 · package.json)

- dependencies: `docx ^9.5.1`, `html-to-image ^1.11.13`, `jspdf ^3.0.3`, `next ^16.1.6`, `react latest`, `react-dom latest`, `zustand ^5.0.8`
- devDependencies: `@types/node ^24.7.0`, `@types/react ^19.2.2`, `@types/react-dom ^19.2.2`, `eslint ^9.38.0`, `eslint-config-next ^16.1.6`, `typescript ^5.9.3`

별도의 시스템 패키지(ffmpeg 등)나 DB는 필요 없다. `npm install` 한 번이면 끝난다.

### 3-5. 환경변수 (`.env.example` 원문)

리포에 `.env.example`이 들어 있고 내용은 다음 3줄이다.

```env
OPENAI_API_KEY=
NEXT_PUBLIC_APP_NAME=찬양콘티 스튜디오
MAX_ATTACHMENT_MB=1
```

★실측 고지 — **현재 코드베이스에는 `process.env`를 읽는 지점이 하나도 없다**(`.ts`/`.tsx` 전수 grep 결과 0건). 즉 위 세 값은 README의 "추천 로직은 룰 기반 + 선택적 AI 보정 구조"라는 설계 여지에 대응하는 **예비 슬롯**이며, `.env.local` 없이도 앱은 완전히 정상 동작한다. README의 Cursor handoff 5항이 밝히듯 "OpenAI API를 연결할 경우 `.env.local`에 `OPENAI_API_KEY`를 추가"하는 것은 **AI 보정을 실제로 구현할 때의 절차**다.

AI 보정을 붙일 계획이라면 다음과 같이 로컬 파일을 만든다.

```bash
cp .env.example .env.local
# 편집기로 .env.local 을 열어 값을 채운다
```

> ⚠ **보안 경고**: `OPENAI_API_KEY=` 는 **자리표시자(placeholder)다. 실제 키 값을 이 문서나 저장소 어디에도 적지 마라.** 키는 `.env.local`(gitignore 대상) 또는 Windows Credential Manager 같은 자격 증명 저장소에만 둔다. 키를 커밋·로그·대화창·스크린샷에 남기지 않는다. 유출이 의심되면 즉시 발급처에서 revoke 후 재발급한다.

### 3-6. 배포 (실측 · vercel.json + CI)

`vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "github": {
    "enabled": true
  }
}
```

GitHub 연동이 켜져 있으므로 Vercel에 리포를 연결하면 `main` 푸시 시 Production, PR 시 Preview 배포가 자동으로 돈다. `docs/00_PROJECT_WORKFLOW.md`의 8~9단계("GitHub Actions / Vercel 설정" → "Preview / Production 배포")가 이 흐름이다. 다만 **DB가 없고 LocalStorage 저장이므로, 배포본에서 만든 콘티는 그 브라우저에만 남는다** — 여러 사람이 같은 콘티를 공유하려면 Word/PDF로 내보내서 돌린다.

### 3-7. README의 Cursor handoff 절차 (원문 그대로 이식)

1. 이 폴더를 Cursor로 엽니다.
2. `npm install`
3. `npm run dev`
4. UI 확인 후 `data/song-catalog.json`부터 실제 운영용 메타데이터로 확장합니다.
5. OpenAI API를 연결할 경우 `.env.local`에 `OPENAI_API_KEY`를 추가합니다.

`docs/08_CURSOR_HANDOFF.md`는 여기에 한 항목을 더 붙인다 — 3번과 4번 사이에 **"입력 → 추천 → 편집 → 저장 → 출력 플로우 점검"**을 넣고, 마지막에 **"UI 미세 조정 및 배포"**로 닫는다.

### 3-8. 주요 구조 (README 원문)

- `app/` : App Router
- `components/` : 화면 컴포넌트
- `state/` : Zustand store
- `lib/` : 추천/출력/유틸 로직
- `data/` : 메타데이터 JSON
- `docs/` : 설계 문서

설계 문서는 `docs/00_PROJECT_WORKFLOW.md`(워크플로우), `01_PRD.md`(제품 정의), `02_TRD.md`(기술 요구), `03_DESIGN_SPEC.md`(디자인), `04_CODING_PLAN.md`(구현 계획), `05_PIPELINE_PLAN.md`(파이프라인), `06_DATA_MODEL.md`(데이터 모델), `07_SOURCE_NOTES.md`(출처 노트), `08_CURSOR_HANDOFF.md`(핸드오프) 9본이 실려 있다.

---

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(예배교육부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지). → `worship-setlist-studio`
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):
  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "worship-setlist-studio" --cwd "$env:USERPROFILE\Future-Ministry\예배교육부\worship-setlist-studio"
  ```
- 또는 패키지의 `tools/setup.ps1 -Dept fm-worship -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

---

## 5. 대표 사용 시나리오

### 시나리오 — "이번 주 주일예배 찬양콘티를 30분 안에 확정하고 팀에 Word로 돌린다"

**상황**: 주제 "내가 너를 지명하여 불렀나니", 본문 이사야 43:1-7, 주일 오전 예배. 찬양팀 리허설이 토요일 저녁이라 금요일까지 콘티를 확정해 단톡방에 뿌려야 한다.

**① 기술자 pane을 연다** (예배교육부 탭에서 `worship-setlist-studio` pane 선택). 최초 1회라면 클론부터.

```bash
mkdir -p "$HOME/Future-Ministry/예배교육부"
git clone https://github.com/yijae78/worship-setlist-studio.git \
  "$HOME/Future-Ministry/예배교육부/worship-setlist-studio"
cd "$HOME/Future-Ministry/예배교육부/worship-setlist-studio"
node -v          # v20.9 이상 확인
npm install
```

**② 개발 서버를 띄운다.**

```bash
npm run dev
```

출력에 `http://localhost:3000` 이 뜨면 브라우저로 연다.

**③ 1단계 「새 콘티」** — 입력 패널에 다음을 넣는다.
- 주제: `내가 너를 지명하여 불렀나니`
- 성경본문: `이사야 43:1-7`
- 예배유형: `주일예배`
- 예배일: 캘린더 피커에서 해당 주일 선택(`lib/korean-holidays.ts`가 절기를 함께 표시해 준다)
- 분위기: 원하는 태그 선택

추천을 실행하면 `POST /api/recommend`가 호출되고, `lib/recommendation.ts`가 `data/song-catalog.json`(36곡)과 `data/reference-teams.json`(7팀)을 근거로 **도입 → 고백 → 은혜 → 결단 → 파송** 5단 초안을 돌려준다. 외부 API를 타지 않으므로 오프라인에서도 즉시 나온다.

API를 직접 두드려 응답 형태만 확인하고 싶으면 다음과 같이 한다.

```bash
curl -X POST http://localhost:3000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"topic":"내가 너를 지명하여 불렀나니","scripture":"이사야 43:1-7","worshipType":"주일예배","moods":["은혜","결단"]}'
```

**④ 2단계 「편집」** — 초안을 사람이 손본다.
- 「은혜」 섹션 곡이 우리 팀 음역에 안 맞으면 곡 선택 모달에서 교체한다.
- 곡 편집 모달에서 Key를 팀 기준으로 바꾸고(예: `A` → `G`), 메모에 "간주 2마디 늘림 / 인도자 멘트 자리" 같은 현장 지시를 적는다.
- 추천 이유 칸은 그대로 두면 출력물에 함께 실려, 왜 이 곡인지 팀원들이 알 수 있다.
- 편집 중 상태는 Zustand store를 거쳐 LocalStorage(`worship:setlist:current`)에 자동 보존되므로 브라우저를 닫아도 이어서 작업할 수 있다. 저장 슬롯은 최대 20개(`MAX_SAVED_DRAFTS`)다.

**⑤ 3단계 「내보내기」** — 악보를 첨부하고 문서로 뽑는다.
- 보유한 악보 이미지/PDF를 첨부한다(**개당 1MB 상한** — `MAX_ATTACHMENT_MB=1`. 초과하면 이미지 압축 후 재첨부).
- 교회명·예배일·하단 안내문을 채우고 **Word(.docx)** 를 내보낸다. `lib/exporters.ts`가 `교회명 · 예배일` 머리글 → `찬양콘티` 제목 → 주제/본문/예배유형/분위기 → `1. [도입] 곡제목 (Key: G / BPM: 72)` + 추천 이유 + 메모 순으로 조립해 준다.
- 인쇄용이 필요하면 **PDF**도 함께 내보낸다(`jspdf` + `html-to-image`).

**⑥ 4단계 「최종본」** — 확정본을 확인하고 파일을 찬양팀 단톡방·인도자에게 전달한다. LocalStorage에는 남지만 **다른 사람 브라우저에는 없다** — 공유는 반드시 내보낸 파일로 한다.

**⑦ 운영 정착 작업(도입 첫 달 1회)** — 샘플 카탈로그를 우리 교회 레퍼토리로 바꾼다.

```bash
code "$HOME/Future-Ministry/예배교육부/worship-setlist-studio/data/song-catalog.json"
# 우리 팀이 실제로 쓰는 곡의 제목/Key/BPM/섹션 적합도/분위기 태그로 확장·교체
npm run typecheck   # JSON 스키마와 타입 정합 확인
npm run dev         # 다시 추천을 돌려 초안 품질이 올라갔는지 확인
```

**⑧ 팀 전체가 쓰게 하려면** Vercel에 리포를 연결한다. `vercel.json`의 GitHub 연동이 켜져 있어 `main` 푸시마다 Production이 갱신되고, 각 인도자는 자기 브라우저 LocalStorage에 자기 콘티를 쌓는다. 배포 전 CI와 동일한 검증을 로컬에서 먼저 돌린다.

```bash
npm run lint && npm run typecheck && npm run build
```
