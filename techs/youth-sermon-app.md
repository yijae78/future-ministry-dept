# youth-sermon-app — 설교기획부 기술자

> 실측 근거: yijae78/youth-sermon-app@f0ec74a · README 없음 · 확인 2026-08-14

> **README 부재 — 아래는 리포 파일 구조 실측 기반이다.** 이 리포에는 최상위 `README.md`가 존재하지 않는다(마크다운 파일은 `prompts/system/*.v1.md` 8개뿐이다). 따라서 이 문서의 설치·실행법은 `package.json`(루트·backend·frontend), `.env.example`, `packages/backend/src/config/env.ts`, `packages/frontend/vite.config.ts` 등 **실제 파일에서 읽어낸 내용만** 옮긴 것이다. 리포가 문서화하지 않은 부분은 "미검증"으로 명시했고 추측으로 채우지 않았다.

## 1. 무엇을 하는가

**청소년 설교 지원 — 청소년 설교 원고를 자동으로 작성하고 시각자료(슬라이드·PPT)까지 제작하는 웹 애플리케이션이다.**

한 줄 역할 규정은 리포 자체의 선언을 그대로 따른다. 루트 `package.json`의 `description` 필드가 "청소년 설교 원고 자동 작성 및 시각자료 제작 앱"으로 적혀 있다.

구조는 npm workspaces + Turborepo 기반 모노레포다. `packages/shared`(공용 타입·enum·상수), `packages/backend`(Express API 서버), `packages/frontend`(React 웹 앱) 3개 워크스페이스로 나뉜다. 루트 스크립트는 전부 `turbo run <task>` 형태로 하위 워크스페이스에 위임한다.

백엔드의 핵심은 **에이전트 오케스트레이션**이다. `packages/backend/src/agents/` 아래에 `orchestrator.ts`를 중심으로 8개 전문 에이전트가 배치돼 있다 — `leader.agent.ts`(총괄), `text-analyzer.agent.ts`(본문 분석), `method-selector.agent.ts`(설교 방법론 선택), `style-analyzer.agent.ts`(설교자 문체 분석), `sermon-generator.agent.ts`(원고 생성), `youth-adapter.agent.ts`(청소년 눈높이 변환), `visual-generator.agent.ts`(시각자료 생성), `edit-support.agent.ts`(편집 지원)이다. 각 에이전트의 시스템 프롬프트는 코드가 아니라 `prompts/system/` 아래에 `*.v1.md`로 분리·버전 관리돼 있어, 프롬프트를 코드 배포 없이 교체할 수 있는 구조다. LLM 호출은 `@anthropic-ai/sdk`를 쓰며 설정은 `src/config/claude.ts`에 있다.

도메인 데이터는 `database/seeds/`에 시드로 준비돼 있다. `preacher-styles.seed.ts`(설교자 문체), `youth-minister-styles.seed.ts`(청소년 사역자 문체), `method-templates.seed.ts`(설교 방법론 템플릿), `theological-standards.seed.ts`(신학 기준)이다. 즉 "어떤 설교자의 문체로, 어떤 방법론으로, 어떤 신학 기준 안에서" 원고를 만들지가 데이터로 선언돼 있고 에이전트가 그것을 참조하는 설계다.

API 표면은 넓다. `src/routes/` 기준으로 인증(`auth`), 성경 본문(`bible`), 상호참조(`cross-reference`), 편집 지원(`edit-support`), 내보내기(`export`), 피드백(`feedback`), 소그룹 가이드(`group-guide`), 전례력(`liturgical`), 설교 방법론(`method`), 설교자(`preacher`), 시리즈(`series`), 설교(`sermon`), 사용자(`user`), 버전(`version`), 시각자료(`visual`), 청소년 사역자(`youth-minister`) 16개 라우트가 있다. 원고 생성처럼 오래 걸리는 작업은 동기 응답으로 처리하지 않고 Bull 큐(`src/queues/sermon-generation.processor.ts`)에 넣은 뒤, Socket.IO 웹소켓(`src/websocket/generation.handler.ts`)으로 진행 상황을 프런트에 실시간 푸시한다.

내보내기는 서버에서 실제 파일을 굽는다. 의존성에 `docx`(워드), `pptxgenjs`(파워포인트), `puppeteer`(HTML 렌더링/캡처)가 들어 있고, `src/services/ppt.service.ts`와 `export.service.ts`가 이를 담당한다. 설교 원고에서 곧바로 PPT와 문서가 나오는 파이프라인이다.

프런트엔드는 React 19 + Vite 6 + Zustand(상태) + React Router 7 구성이다. 원고 편집기는 Tiptap 기반이며(`src/editor/SermonEditor.tsx`), `SermonSection`·`InteractionMark` 같은 커스텀 확장을 두어 설교 원고의 구조(섹션)와 상호작용 지점을 문서 모델 수준에서 다룬다. 슬라이드 미리보기는 `reveal.js`를 쓴다(`src/slides/`). 입력 화면에는 성경 본문 입력, 상호참조 패널, 전례력 절기 선택, 설교 방법론 탭, 설교자 선택, 설교 길이 슬라이더, 대상 그룹 선택, 청소년 사역자 선택 컴포넌트가 각각 분리돼 있다. 자동 저장(`useAutoSave.ts`)과 버전 관리(`useEditorVersions.ts`) 훅도 존재한다.

보안·운영 측면에서는 Helmet, CORS, rate limiter, 입력 sanitize(DOMPurify + jsdom), Zod 검증기, Winston 로거, JWT 액세스/리프레시 토큰(15분/7일)이 미들웨어와 설정에 배치돼 있다.

## 2. 리포·클론

리포: <https://github.com/yijae78/youth-sermon-app.git>

```bash
git clone https://github.com/yijae78/youth-sermon-app.git \
  "$HOME/Future-Ministry/설교기획부/youth-sermon-app"
cd "$HOME/Future-Ministry/설교기획부/youth-sermon-app"
```

## 3. 설치·실행법

> README가 없으므로 아래는 전부 `package.json`·`.env.example`·`config/env.ts`·`vite.config.ts` 실측에서 옮긴 것이다. 리포에 없는 단계는 만들어 넣지 않았다.

### 3.1 요구 환경

루트 `package.json`의 `engines` 선언이다.

```
Node.js >= 20.0.0
npm     >= 10.0.0
```

외부 서비스는 `.env.example`과 `src/config/env.ts` 기준으로 **MongoDB**(mongoose)와 **Redis**(ioredis / Bull 큐)가 필요하다.

### 3.2 의존성 설치

npm workspaces 모노레포이므로 루트에서 한 번만 설치한다.

```bash
cd "$HOME/Future-Ministry/설교기획부/youth-sermon-app"
npm install
```

### 3.3 환경 변수

`.env.example`을 `.env`로 복사해 값을 채운다. `src/config/env.ts`가 **리포 루트의 `.env`** 를 읽는다(`path.resolve(__dirname, '../../../../.env')`).

```bash
cp .env.example .env
```

`.env.example` 원문(키 이름과 자리표시자만 — **실제 값은 절대 이 문서나 리포에 적지 않는다**):

```dotenv
# Server
NODE_ENV=development
PORT=4000

# MongoDB
MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/youth-sermon?retryWrites=true&w=majority

# Redis (Upstash)
REDIS_URL=redis://default:<password>@<host>:<port>

# JWT
JWT_ACCESS_SECRET=your-access-secret-key-min-32-chars
JWT_REFRESH_SECRET=your-refresh-secret-key-min-32-chars

# Claude API (Anthropic)
ANTHROPIC_API_KEY=<발급받은 키를 여기에>

# Image Generation
OPENAI_API_KEY=<발급받은 키를 여기에>
# or STABILITY_API_KEY=<발급받은 키를 여기에>

# Cloud Storage (Cloudflare R2)
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=youth-sermon-assets
R2_PUBLIC_URL=https://your-r2-url.com

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Sentry
SENTRY_DSN=https://xxxx@sentry.io/xxxx

# Frontend URL (CORS)
CLIENT_URL=http://localhost:3000
```

> ⚠ **보안**: 위 값은 전부 자리표시자다. 실제 API 키·비밀번호·시크릿을 이 문서나 공개 리포에 커밋하지 않는다. `.env`는 `.gitignore`에 등록돼 있는지 확인하고 사용한다.

`src/config/env.ts`가 정의한 기본값(미설정 시 적용)은 다음과 같다.

| 변수 | 기본값 |
|------|--------|
| `NODE_ENV` | `development` |
| `PORT` | `4000` |
| `MONGODB_URI` | `mongodb://localhost:27017/youth-sermon` |
| `REDIS_URL` | `redis://localhost:6379` |
| `R2_BUCKET_NAME` | `youth-sermon-assets` |
| `CLIENT_URL` | `http://localhost:3000` |
| JWT 만료 | access `15m` / refresh `7d` |

프로덕션(`NODE_ENV=production`)에서는 `validateEnv()`가 다음 5개를 **필수**로 검증하며, 하나라도 없으면 기동이 실패한다.

```
MONGODB_URI, REDIS_URL, JWT_ACCESS_SECRET, JWT_REFRESH_SECRET, ANTHROPIC_API_KEY
```

### 3.4 데이터베이스 준비

루트 `package.json`이 선언한 DB 스크립트다.

```bash
npm run db:migrate       # → packages/backend: migrate-mongo up
npm run db:seed          # → packages/backend: ts-node database/seeds/run-seeds.ts
npm run db:import-bible  # → packages/backend: ts-node src/bible-db/import-krv.ts
```

> ⚠ **실측 주의(미검증)**: 이 3개 스크립트는 선언은 있으나 대상 파일이 현재 커밋(`f0ec74a`)의 트리에서 확인되지 않는다. 시드 파일은 리포 **루트**의 `database/seeds/`에 `index.ts`, `method-templates.seed.ts`, `preacher-styles.seed.ts`, `theological-standards.seed.ts`, `youth-minister-styles.seed.ts`로 존재하지만, 스크립트가 가리키는 `packages/backend/database/seeds/run-seeds.ts`와 `packages/backend/src/bible-db/import-krv.ts`는 트리에 없다. `migrate-mongo`도 의존성 목록에 없다. 따라서 이 단계는 **현 커밋에서 그대로 동작한다고 단정할 수 없다** — 실행 전 리포 상태를 확인한다.

### 3.5 개발 서버 실행

루트에서 Turborepo로 전체를 띄운다.

```bash
npm run dev      # turbo run dev — backend(nodemon) + frontend(vite) 동시 기동
```

워크스페이스를 개별로 띄우려면 다음과 같이 한다.

```bash
npm run dev --workspace @youth-sermon/backend    # nodemon (기본 포트 4000)
npm run dev --workspace @youth-sermon/frontend   # vite  (포트 3000)
```

포트와 프록시는 `packages/frontend/vite.config.ts`에 고정돼 있다.

```
frontend  : http://localhost:3000
backend   : http://localhost:4000
프록시     : /api        → http://localhost:4000
            /socket.io  → http://localhost:4000 (ws: true)
```

> ⚠ **실측 주의(미검증)**: 루트 스크립트는 `turbo`를 쓰지만 현재 커밋의 트리에 `turbo.json`이 없다. Turborepo는 통상 `turbo.json`으로 태스크 파이프라인을 정의하므로, `npm run dev`가 그대로 동작하지 않으면 각 워크스페이스를 위처럼 개별 실행한다.

### 3.6 빌드·기타 스크립트

루트(`turbo run <task>`로 전 워크스페이스 위임):

```bash
npm run build             # 전체 빌드
npm run test              # 전체 테스트
npm run test:unit
npm run test:integration
npm run test:e2e
npm run lint
npm run lint:fix
npm run format            # prettier --write "packages/**/*.{ts,tsx,js,json,css}"
npm run clean             # turbo run clean + node_modules 삭제
```

백엔드 개별:

```bash
npm run build --workspace @youth-sermon/backend   # tsc
npm run start --workspace @youth-sermon/backend   # node dist/server.js  (빌드 후 프로덕션 기동)
npm run lint  --workspace @youth-sermon/backend   # eslint src/
```

프런트엔드 개별:

```bash
npm run build   --workspace @youth-sermon/frontend   # vite build
npm run preview --workspace @youth-sermon/frontend   # vite preview
```

> ⚠ **실측 주의(미검증)**: 백엔드 `package.json`에는 `test`/`test:unit`/`test:integration`이 `jest`로 선언돼 있으나, 현재 커밋 트리에 `packages/backend/tests/` 디렉터리와 jest 설정 파일이 없다. `test:e2e`를 정의한 워크스페이스도 확인되지 않는다. 테스트 명령은 현 커밋 기준으로 동작이 보장되지 않는다.

### 3.7 주요 의존성 (실측)

| 계층 | 핵심 패키지 |
|------|-----------|
| Backend | `express@^4.21`, `mongoose@^8.9`, `ioredis@^5.4`, `bull@^4.16`, `socket.io@^4.8`, `@anthropic-ai/sdk@^0.39`, `jsonwebtoken@^9`, `bcrypt@^5.1`, `helmet@^8`, `zod@^3.24`, `winston@^3.17`, `dompurify@^3.2`+`jsdom@^25`, `docx@^9`, `pptxgenjs@^3.12`, `puppeteer@^23`, `better-sqlite3@^11`, `dotenv@^16.4` |
| Frontend | `react@^19`, `react-dom@^19`, `react-router-dom@^7`, `vite@^6`, `zustand@^5`, `axios@^1.7`, `socket.io-client@^4.8`, `@tiptap/react@^2.10`(+starter-kit, placeholder, text-align, underline), `reveal.js@^5.1`, `lucide-react@^0.577` |
| Shared | 워크스페이스 `@youth-sermon/shared` — 타입·enum·성경 66권 상수 |
| Tooling | `turbo@^2.4`, `typescript@^5.7`, `prettier@^3.4`, `eslint@^9`, `nodemon@^3.1`, `ts-node@^10.9` |

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(설교기획부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지).
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):
  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "youth-sermon-app" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\youth-sermon-app"
  ```
- 또는 패키지의 `tools/setup.ps1 -Dept fm-sermon -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

## 5. 대표 사용 시나리오

**상황**: 중고등부 주일 설교 원고를 앱으로 만들고, 예배용 슬라이드까지 뽑아야 한다. 로컬 개발 환경에서 앱을 띄워 작업한다.

```powershell
# ① 기술자 패인을 연다 (부서 소켓 번호는 설치 시 발급된 값으로 대체)
$env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
& "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "youth-sermon-app" --cwd "$env:USERPROFILE\Future-Ministry\설교기획부\youth-sermon-app"
```

```bash
# ② 최초 1회 — 의존성 설치
cd "$HOME/Future-Ministry/설교기획부/youth-sermon-app"
node -v          # v20 이상인지 확인
npm install

# ③ 환경 변수 파일 생성 후 값 채우기
cp .env.example .env
#   에디터로 .env 를 열어 MONGODB_URI / REDIS_URL / JWT_* / ANTHROPIC_API_KEY 를 채운다.
#   ⚠ 채운 .env 는 절대 커밋하지 않는다.

# ④ MongoDB·Redis 가 로컬에서 떠 있는지 확인
#   (기본값 사용 시: mongodb://localhost:27017/youth-sermon, redis://localhost:6379)

# ⑤ 개발 서버 기동
npm run dev
#   turbo 가 동작하지 않으면 두 개의 패인/터미널로 나눠 실행한다:
#     npm run dev --workspace @youth-sermon/backend
#     npm run dev --workspace @youth-sermon/frontend
```

```bash
# ⑥ 브라우저로 접속 (프런트 1회만 연다)
start "" "http://localhost:3000"
```

앱 화면에서의 흐름은 다음과 같다.

1. `AuthPage`에서 로그인하거나 계정을 만든다.
2. `SermonInputPage`에서 본문을 입력한다 — 성경 본문(`BibleTextInput`), 전례력 절기(`LiturgicalSeasonSelector`), 설교 방법론(`MethodCategoryTabs`), 설교자 문체(`PreacherSelector`), 청소년 사역자 문체(`YouthMinisterSelector`), 대상 그룹(`TargetGroupSelector`), 설교 길이(`SermonLengthSlider`)를 지정한다. 필요하면 상호참조 패널(`CrossReferencePanel`)로 평행 본문을 확인한다.
3. 생성을 요청하면 백엔드가 Bull 큐에 작업을 넣고, 오케스트레이터가 `text-analyzer → method-selector → style-analyzer → sermon-generator → youth-adapter → visual-generator` 순으로 에이전트를 굴린다. 진행률은 Socket.IO로 `GenerationProgress` 컴포넌트에 실시간 표시된다.
4. `SermonEditPage`의 Tiptap 편집기에서 원고를 다듬는다. 자동 저장이 걸려 있고, 버전 관리로 이전 판본과 비교할 수 있다. 예상 설교 시간은 `SermonTimeEstimate`가 계산한다.
5. 시각자료 탭에서 슬라이드를 생성해 `SlideViewer`(reveal.js)로 미리 본다.
6. 내보내기에서 PPTX(`pptxgenjs`) 또는 DOCX(`docx`)로 받는다.

배포용 빌드가 필요하면 다음과 같이 굽고 기동한다.

```bash
npm run build
npm run start --workspace @youth-sermon/backend    # node dist/server.js
```

> 프로덕션 기동 전에 `MONGODB_URI`, `REDIS_URL`, `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET`, `ANTHROPIC_API_KEY` 5개가 모두 설정돼 있어야 한다 — `validateEnv()`가 누락 시 예외를 던지고 서버가 뜨지 않는다.
