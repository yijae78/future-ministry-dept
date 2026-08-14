# pray-news — 설교기획부 기술자

> 실측 근거: yijae78/pray-news@14b7f43 · README 없음 · 확인 2026-08-14

> **README 부재 — 아래는 리포 파일 구조 실측 기반이다.** 이 리포에는 `README.md`가 없다. 따라서 이 문서의 모든 설명과 실행법은 `package.json`, `vite.config.ts`, `vercel.json`, `index.html`, `api/crawl.ts`, `api/analyze.ts`, `src/App.tsx`, `scripts/*.mjs` 등 **실제 파일에서 읽어낸 내용만** 옮긴 것이다. 리포가 명시하지 않은 절차는 "구조 기반 판단"으로 표시했고 추측 명령을 지어내지 않았다.

## 1. 무엇을 하는가

**한국 기독교 뉴스를 매일 자동 수집·분석해 개혁주의 관점의 요약·전망과 세 종류의 기도문을 생성하는 PWA 웹 앱이다.**

`index.html`의 제목은 "기도로 읽는 뉴스 - AI 분석"이고, `package.json`의 패키지명은 `christian-news-analyzer`다. 이름 그대로 뉴스를 "읽는" 데서 끝나지 않고 **기도로 이어지게** 만드는 것이 이 앱의 목적이다.

동작은 크게 두 단계다. 첫 단계는 수집(`api/crawl.ts`)이다. 국내 기독교 매체 11곳의 RSS를 직접 긁는다 — 한국기독공보, 국민일보, 장로신문, 뉴스앤조이, 시대와목회, 복음과상황, 교회와신앙, 평화교회신문, 기독교한국신문, 크리스천투데이, 기독신문이다. 여기에 Google News 키워드 검색('기독교', '한국교회', '장로교')이 보강된다. 수집 단계에는 **이단 필터**가 내장돼 있다. 이단 계열 매체 도메인 블랙리스트와 이단 관련 키워드 목록을 두어 해당 출처·기사를 걸러낸다. 개혁주의 교회가 쓰는 도구로서 출처 위생을 코드 수준에서 강제한 것이다.

두 번째 단계는 분석(`api/analyze.ts`)이다. Google Gemini(`gemini-2.5-flash`)에 수집된 기사 목록을 넘기고, JSON 스키마를 강제해 7개 항목을 받아낸다.

1. **stats** — 매체별 기사 수 집계
2. **summary** — 주요 이슈 5개 (제목·설명·관련 기사 ID)
3. **categories** — 교단행정·선교·교육·사회참여·신학·이단경보 6개 카테고리 분류
4. **sentiment** — 기사별 긍/부정 + 전체 비율 + 종합 평가
5. **keywords** — 핵심 키워드 Top 10
6. **prediction** — 단기(1~2주)·중기(1~3개월) 전망
7. **prayer** — 기도문 3종

시스템 프롬프트는 분석 관점을 못박아 둔다. "한국 기독교 뉴스 분석 전문가"로서 **개혁주의(칼빈주의) 신학 관점**에서 분석하며 **웨스트민스터 신앙고백을 기준**으로 삼는다고 명시돼 있다.

기도문 3종은 이 앱의 핵심 산출물이며 용도가 각각 다르다. `personal`은 개인 기도제목으로 번호 형식(1. 2. 3. …) 최소 5개·최대 10개를 간결한 한 문장 기도로 나열한다. `communal`은 주일 예배 후 함께 드리는 서술식 공동기도 500자이며, 관련 성경구절을 최소 1개 이상 "(요한복음 3:16)" 형식으로 인용해 자연스럽게 녹여 넣도록 강제된다. `wednesday`는 수요기도회용 700자로, [1부] 목사가 인도하는 서술식 중보기도문 500자와 [2부] "◆ 이번 주 기도제목" 아래 번호 형식 3가지(각 50자 내외)로 구성된다. 세 기도문은 **같은 뉴스 이슈를 다루되 형식만 달라야 한다**는 연결성·통일성 요구가 프롬프트에 걸려 있다.

기도문 작성 원칙도 명문화돼 있다. 삼위일체 하나님께 드리는 기도의 흐름(찬양→감사→고백→중보(뉴스반영)→소망→예수님 이름으로)을 따르고, 뉴스 이슈를 중보기도에 자연스럽게 반영하며, **번영신학·무속적 표현·이단 교리·정치적 편향을 금지**한다. 어투는 "존경스러우면서 따뜻한 한국어"로 지정돼 있다.

API 키 취급 방식이 특기할 만하다. 이 앱은 **서버에 API 키를 두지 않는다(BYOK — Bring Your Own Key)**. 사용자가 브라우저 화면에서 자기 Gemini API 키를 입력하면 `localStorage`의 `gemini-api-key`에 저장되고, 분석 요청마다 요청 본문에 실려 서버 함수로 전달된다. 서버는 그 키로 Gemini를 호출할 뿐 보관하지 않는다. 키 형식은 `AIza`로 시작하고 35자 이상인지 클라이언트에서 1차 검증하며, 화면에는 앞 6자 + `••••••••` + 뒤 4자로 마스킹해 표시한다. 삭제 버튼도 제공된다. 즉 **운영자가 사용자들의 API 비용을 떠안지 않으면서 키 유출 표면도 최소화한 구조**다.

프런트엔드는 React 19 + Vite 6 단일 페이지 앱이며 PWA다. `public/manifest.json`과 `public/sw.js`(서비스 워커)가 있고, `index.html`이 로드 시 서비스 워커를 등록한다. `beforeinstallprompt`를 잡아 설치 배너를 띄우고, iOS에서는 별도 설치 안내 모달을 보여준다. 결과 화면은 Chart.js(`react-chartjs-2`)로 통계·감정 비율을 시각화하고, jsPDF로 PDF 내보내기를 지원하며, 아이콘은 `lucide-react`를 쓴다. 데모 모드가 있어 API 키 없이도 `src/demo-data.json`으로 결과 화면을 둘러볼 수 있다. 이력(History) 패널에 최근/휴지통 탭, 정렬, 검색이 붙어 있고 기도문 글자 크기 조절도 된다.

배포 대상은 Vercel이다. `vercel.json`이 프레임워크를 `vite`로 선언하고, `api/*.ts` 서버리스 함수의 `maxDuration`을 300초로 늘려 두었다(뉴스 수집 + LLM 분석이 오래 걸리기 때문이다). SPA 라우팅을 위해 나머지 경로를 `/index.html`로 rewrite한다.

## 2. 리포·클론

리포: <https://github.com/yijae78/pray-news.git>

```bash
git clone https://github.com/yijae78/pray-news.git \
  "$HOME/Future-Ministry/설교기획부/pray-news"
cd "$HOME/Future-Ministry/설교기획부/pray-news"
```

## 3. 설치·실행법

> README가 없으므로 아래는 전부 `package.json`·`vite.config.ts`·`vercel.json`·소스 실측에서 옮긴 것이다.

### 3.1 요구 환경

`package.json`에 `engines` 선언은 없다. 의존성 실측 기준으로 Vite 6 / React 19 / `@vercel/node@^5`를 쓰므로 **Node.js 18 이상**(Vite 6 요구사항 기준)이 필요하다. 로컬에서 `api/` 서버리스 함수까지 돌리려면 **Vercel CLI**가 필요하다.

분석 기능을 쓰려면 **Google Gemini API 키**가 있어야 한다. 키는 리포나 서버가 아니라 **앱 실행 후 브라우저 화면에서 사용자가 직접 입력**한다.

### 3.2 의존성 설치

```bash
cd "$HOME/Future-Ministry/설교기획부/pray-news"
npm install
```

`package.json` 실측 의존성:

```
dependencies    : @google/genai@^1.37.0, chart.js@^4.5.1, jspdf@^4.2.1,
                  lucide-react@^0.475.0, react@^19.0.0, react-chartjs-2@^5.3.1,
                  react-dom@^19.0.0
devDependencies : @types/node@^22.14.0, @types/react@^19.0.0, @types/react-dom@^19.0.0,
                  @vercel/node@^5.0.0, @vitejs/plugin-react@^5.0.0,
                  typescript@~5.8.2, vite@^6.2.0
```

### 3.3 스크립트 (package.json 선언 그대로)

```bash
npm run dev       # vite
npm run build     # vite build
npm run preview   # vite preview
```

### 3.4 개발 서버 실행

`vite.config.ts` 실측 내용이다.

```ts
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:3000',
      changeOrigin: true,
    },
  },
}
```

즉 프런트는 **5173** 포트에서 뜨고, `/api` 요청은 **localhost:3000**으로 프록시된다.

```bash
npm run dev
# → http://localhost:5173
```

```bash
# 브라우저는 1회만 연다
start "" "http://localhost:5173"
```

> **구조 기반 판단**: `api/crawl.ts`와 `api/analyze.ts`는 `@vercel/node`의 `VercelRequest`/`VercelResponse` 타입을 쓰는 **Vercel 서버리스 함수**다. `npm run dev`(vite 단독)는 이 함수들을 실행하지 않고 3000번 포트로 프록시만 한다. 따라서 수집·분석까지 로컬에서 돌리려면 Vercel CLI의 개발 서버(기본 포트 3000)를 함께 띄워야 한다. 리포에 이 절차를 명시한 문서는 없다.
>
> ```bash
> npm i -g vercel     # 최초 1회
> vercel dev          # api/*.ts 서버리스 함수 로컬 실행 (기본 3000)
> ```
>
> API 키가 없거나 로컬 함수를 띄우기 어려우면 앱의 **데모 모드**로 결과 화면을 확인할 수 있다(`src/demo-data.json` 사용, 네트워크 호출 없음).

### 3.5 API 키 입력 (환경 변수 아님)

이 앱에는 **서버 측 API 키 환경 변수가 없다.** `.env` 파일도 배포에 쓰지 않는다. 실측 흐름은 다음과 같다.

1. 앱 화면에서 API 키 입력란에 Gemini API 키를 넣고 저장한다.
2. 클라이언트가 형식을 검증한다 — `AIza`로 시작하고 길이 35자 이상이어야 한다. 어긋나면 "Gemini API 키 형식이 올바르지 않습니다 (AIza로 시작)"를 띄운다.
3. 통과하면 `localStorage`의 `gemini-api-key` 키로 브라우저에 저장된다.
4. 분석 요청 시 `POST /api/analyze`의 본문에 `apiKey` 필드로 실려 전달된다. 서버는 `new GoogleGenAI({ apiKey })`로 그 키를 그대로 써서 `gemini-2.5-flash`를 호출한다.
5. 화면에는 앞 6자 + `••••••••` + 뒤 4자로 마스킹돼 보인다. 삭제 버튼으로 `localStorage`에서 지울 수 있다.

서버가 반환하는 키 관련 에러 코드는 `NO_API_KEY`, `INVALID_API_KEY_FORMAT`, `INVALID_API_KEY`, `PERMISSION_DENIED`, `QUOTA_EXCEEDED`이며, 프런트는 이 코드를 받으면 키 편집 모드로 자동 전환한다.

> ⚠ **보안**: API 키는 각 사용자의 브라우저에만 저장된다. 키 값을 스크린샷·로그·문서·커밋 어디에도 남기지 않는다. 이 리포는 `.gitignore`에 `.env`, `.env.local`, `.vercel`을 등록해 두었다.

### 3.6 프로덕션 빌드

```bash
npm run build     # dist/ 생성
npm run preview   # 빌드 결과 로컬 미리보기
```

`vercel.json` 실측 내용이다.

```json
{
  "framework": "vite",
  "functions": {
    "api/*.ts": {
      "maxDuration": 300
    }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Vercel에 배포할 때 별도 환경 변수 설정은 필요하지 않다(키는 사용자 브라우저에서 온다).

### 3.7 보조 스크립트 (`scripts/`)

`package.json`에 등록돼 있지 않은 수동 실행용 스크립트다.

```bash
node scripts/gen-icons.mjs         # PWA 아이콘 PNG 생성 (순수 JS, 외부 의존성 없음)
node scripts/gen-gemini-icon.mjs   # 1024×1024 다크 앱 아이콘 생성 (딥 네이비 + 화이트 크로스)
node scripts/generate-demo.mjs     # 실제 크롤링 + Gemini 분석으로 데모 데이터 생성
```

> `scripts/generate-demo.mjs`는 리포 루트의 `.env.local`에서 `GEMINI_API_KEY=` 한 줄을 읽는다. 이 파일은 `.gitignore`에 등록돼 있으며 **절대 커밋하지 않는다**. 개발자 로컬 전용 스크립트다.

### 3.8 리포 구조 (실측)

```
pray-news/
├── api/
│   ├── crawl.ts          ← RSS 11개 매체 + Google News 수집, 이단 도메인·키워드 필터
│   └── analyze.ts        ← Gemini(gemini-2.5-flash) 7항목 분석 + 기도문 3종 생성
├── src/
│   ├── App.tsx           ← 단일 페이지 앱 본체 (키 관리·PWA·이력·결과 화면)
│   ├── main.tsx
│   ├── types.ts
│   ├── demo-data.json    ← 데모 모드 데이터
│   └── config/
│       ├── rss-sources.ts
│       ├── cult-blacklist.ts
│       └── prompts.ts
├── public/
│   ├── manifest.json     ← PWA 매니페스트
│   ├── sw.js             ← 서비스 워커
│   ├── favicon.ico, icon-192*.png, icon-512*.png, app-icon-*.png
├── scripts/
│   ├── gen-icons.mjs
│   ├── gen-gemini-icon.mjs
│   └── generate-demo.mjs
├── index.html
├── vite.config.ts
├── vercel.json
├── tsconfig.json
└── package.json
```

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(설교기획부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지).
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):
  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "pray-news" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\pray-news"
  ```
- 또는 패키지의 `tools/setup.ps1 -Dept fm-sermon -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

## 5. 대표 사용 시나리오

**상황**: 수요기도회가 오늘 저녁이다. 이번 주 한국교회 뉴스를 반영한 수요기도회용 중보기도문과 주보에 넣을 개인 기도제목을 뽑아야 한다.

```powershell
# ① 기술자 패인을 연다 (부서 소켓 번호는 설치 시 발급된 값으로 대체)
$env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
& "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "pray-news" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\pray-news"
```

```bash
# ② 최초 1회 — 의존성 설치
cd "$HOME/Future-Ministry/설교기획부/pray-news"
npm install
npm i -g vercel        # api/ 서버리스 함수를 로컬에서 돌리기 위해
```

```bash
# ③ 서버리스 함수 개발 서버 (패인 1) — 기본 3000 포트
vercel dev
```

```bash
# ④ 프런트 개발 서버 (패인 2) — 5173 포트, /api 는 3000 으로 프록시된다
npm run dev
```

```bash
# ⑤ 브라우저를 1회만 연다
start "" "http://localhost:5173"
```

브라우저에서의 흐름은 다음과 같다.

1. 첫 화면의 API 키 입력란에 Gemini API 키(`AIza…`)를 넣고 저장한다. 저장 후에는 마스킹돼 표시되며, 다음부터는 `localStorage`에 남아 재입력이 필요 없다.
2. 분석 시작 버튼을 누른다. `POST /api/crawl`이 11개 매체 RSS + Google News를 긁고 이단 도메인·키워드를 걸러낸다.
3. 이어서 `POST /api/analyze`가 수집 기사를 `gemini-2.5-flash`에 넘겨 7항목을 받아온다. 서버리스 함수 `maxDuration`이 300초이므로 기사 수가 많으면 수십 초 이상 걸릴 수 있다.
4. 결과 화면에서 매체별 통계·주요 이슈 5개·카테고리 분류·감정 분석·키워드 Top 10·단기/중기 전망을 확인한다. 차트는 Chart.js로 그려진다.
5. **기도문 섹션**에서 세 가지를 각각 받는다.
   - 수요기도회용(`wednesday`) — [1부] 서술식 중보기도문 500자 + [2부] "◆ 이번 주 기도제목" 3가지. 그대로 인도문으로 쓴다.
   - 개인 기도제목(`personal`) — 번호 형식 5~10개. 주보에 옮긴다.
   - 공동기도(`communal`) — 성경구절이 인용된 서술식 500자. 주일 예배 후용으로 보관한다.
   - 글자 크기 조절 기능으로 강대상에서 읽기 좋은 크기로 키운다.
6. jsPDF 내보내기로 PDF를 받아 인쇄하거나, 공유 기능으로 사역자들에게 전달한다.
7. 결과는 이력 패널에 남는다. 다음 주에 "최근" 탭에서 지난 분석과 비교하면 이슈의 흐름이 보인다.

API 키를 아직 발급받지 못했다면 데모 모드로 들어가 결과 화면 구성과 기도문 형식을 먼저 확인한다(네트워크 호출 없이 `src/demo-data.json`을 쓴다).

교회 서버에 상시 올려 두고 쓰려면 Vercel에 배포한다. 별도 서버 환경 변수 설정은 필요 없고, 사용자는 각자 브라우저에서 자기 키를 넣어 쓴다.

```bash
npm run build
vercel deploy --prod
```
