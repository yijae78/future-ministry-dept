# godsaengbook-grace — 예배교육부 기술자

> 실측 근거: https://github.com/yijae78/godsaengbook-grace.git@fd05f78 · README 있음(단, create-next-app 기본 템플릿 원문 그대로 — 이 앱에 관한 설명이 아님) · 확인 2026-08-14

> ★**README 실질 부재 고지** — 리포에 `README.md`는 존재하나 내용이 `create-next-app` 부트스트랩 기본 문구(Next.js 소개·`npm run dev`·Vercel 배포 링크)뿐이며 **이 앱 고유의 설치·설정 안내가 한 줄도 없다.** `CLAUDE.md`는 `@AGENTS.md` 한 줄이고, `AGENTS.md`는 Next.js 에이전트 규칙 4줄이다. 따라서 아래 1·3항은 **리포의 실제 소스코드·`package.json`·`supabase/migrations/*.sql`·`docs/GSE_*.md` 5본 실측을 근거로** 작성했다.

---

## 1. 무엇을 하는가

**수련회·선교·캠프·예배·셀모임에서 참여자들이 QR 하나로 접속해 사진과 글을 직접 남기면, 그것이 시간순 플립북과 PDF 책 한 권으로 완성되는 Next.js + Supabase 웹앱이다. AI를 일절 쓰지 않아 운영비가 0이다.**

`docs/GSE_PRD.md`가 밝히는 비전은 "수련회, 선교여행, 캠프, 예배, 셀 모임 등 **교회 공동체의 소중한 경험**을 각자의 신앙 서사로 기록하고, 평생 소장 가능한 디지털 플립북 & PDF로 남깁니다"이다. 부제는 "v1.0 · 2026.03 · 교회 전용 완전 무료 버전".

### 1-1. 설계의 핵심 — AI를 뺐다

이 앱의 정체성은 **AI를 의도적으로 제거한 것**이다. PRD가 기존 갓생북과의 차이를 표로 대비해 둔다.

| 기존 갓생북 (AI) | 갓생북 은혜 (직접 작성) |
|---|---|
| AI 에세이 자동 생성 | 본인이 직접 작성 (묵상 가이드 + 예시 템플릿 제공) |
| AI 성경 구절 추천 | 성경 구절 직접 입력 (선택 사항) |
| AI 인용 문구 추천 | 인용 문구 직접 입력 (선택 사항) |
| AI 이미지 생성 | 직접 사진 업로드 권장 / 없으면 기본 템플릿 이미지 선택 |

그 결과 **AI API 비용이 0**이 되고, Vercel Free Tier + Supabase Free Tier만으로 지속 가능한 구조가 된다. PRD의 수익 모델 항목은 단 한 줄 — "**없음 — 완전 무료**". 그리고 신앙적으로도 더 중요한 결과가 따라온다: 기록이 본인의 문장이라는 것. 요약을 AI가 대신 써 준 책은 남의 책이지만, 서툴러도 본인이 쓴 책은 본인의 신앙 서사다.

### 1-2. 두 종류의 사용자

- **계정 사용자(리더)** — 교회 리더·교사·간사·목사 등 이벤트를 만들고 관리하는 사람. **회원가입 필수.** PC 또는 모바일.
- **참여자** — 수련회 학생·선교팀 단원·셀 구성원. **회원가입 불필요 — QR 스캔 후 이름 입력만으로 접속.** 모바일 중심.
- **개인 기록자** — 계정 사용자 본인이 개인 묵상/여정을 기록(회원가입 필수).

"리더 1명만 가입하면 나머지는 링크만으로 참여"가 이 앱의 진입장벽 설계다. 실제 라우팅에서도 이 구조가 그대로 드러난다 — `middleware.ts`가 보호하는 경로는 `/dashboard`와 `/events` 두 개뿐이고, 참여자 경로(`/join`)는 매처에서 아예 제외되어 있다(`matcher: ['/((?!_next/static|_next/image|favicon.ico|join).*)']`).

### 1-3. 이벤트 유형과 데이터 모델

이벤트 카테고리는 6종이다. 마이그레이션 `002_rename_category_mission.sql`이 '선교여행'을 '선교'로 바꿔, 현재 CHECK 제약은 `('수련회', '선교', '캠프', '예배', '모임', '개인')`이다. 이벤트 타입은 `group`(단체) / `personal`(개인) 두 가지다.

DB 스키마(`supabase/migrations/001_grace_schema.sql`)는 **모든 테이블이 `grace_` 접두어**를 쓰며 auth는 `auth.users`를 공유한다.

| 테이블 | 역할 |
|---|---|
| `grace_users` | 은혜 전용 사용자 프로필(이름·소속 교회·마케팅 수신 동의). `auth.users(id)` 참조 |
| `grace_events` | 이벤트(이름·타입·카테고리·기간·예상 인원·QR URL·상태 active/completed) |
| `grace_sections` | 목차 — 리더가 수동 등록(순서·제목·날짜·시각) |
| `grace_participants` | 단체 이벤트 참여자(이름·부가정보·`session_token` UNIQUE·기록 수). **회원가입 불필요** |
| `grace_entries` | 기록 — 본문 텍스트·성경 구절·인용 문구·사진 URL·템플릿 이미지·임시저장 여부 |
| `grace_group_contents` | 리더 업로드 공통 콘텐츠(`photo` / `notice` / `summary`, 페이지 순서) |

`grace_entries`에는 `updated_at` 자동 갱신 트리거(`grace_update_updated_at`)가 걸려 있고, **6개 테이블 전부에 RLS(Row Level Security)가 활성화**되어 있다. 정책 골자는 "이벤트 생성자는 자기 이벤트 전권 / status='active'인 이벤트는 참여자가 읽고 쓸 수 있음 / 기록은 본인 것만 전권, 생성자는 읽기"다.

### 1-4. 실제 화면 구성 (`app/` 라우트 실측)

- **인증**(`app/(auth)/`) — `login`, `signup`, `reset-password`, `update-password` 4종. Supabase Auth 이메일/비밀번호 방식이며 비밀번호 재설정은 PKCE 플로우(`/auth/confirm` → `/update-password`)를 탄다.
- **리더 대시보드**(`app/(dashboard)/`) — `dashboard`(이벤트 목록), `events/new`(이벤트 생성), `events/[id]`(이벤트 상세), `events/[id]/schedule`(목차·일정), `events/[id]/summary`(마무리 총평).
- **참여자**(`app/(participant)/`) — `join/[eventId]`(QR 진입·이름 입력), `record/[eventId]`(기록 작성), `essay/[eventId]`(글 작성), `grid/[eventId]`(기록 격자 보기), `flipbook/[eventId]`(플립북 감상), `pdf/[eventId]`(PDF 빌드).
- **공유**(`app/share/[participantId]`) — 개인 플립북 공유 페이지(`ShareFlipbook.tsx`).
- **랜딩**(`app/page.tsx` + `components/LandingFlipbook.tsx` + `components/ui/HeroSection.tsx`) — 서비스 소개와 샘플 플립북 미리보기. 샘플 이미지는 `public/sample-bible-school.png`, `sample-cell.png`, `sample-mission.png`, `sample-retreat.png` 4종이 실제로 들어 있다.
- **OG 이미지** — `app/api/og/route.tsx`, `app/opengraph-image.tsx`로 공유 링크 미리보기를 동적 생성한다.

### 1-5. 플립북 렌더링

`components/flipbook/`가 책의 페이지 종류를 구성한다 — `PageCover`(표지), `PageTableOfContents`(목차), `PageTocCompanion`(목차 동반면), `PagePhotoLeft`(왼면 사진), `PageEssayRight`(오른면 글), `PageSummary`(마무리), 그리고 이를 넘기는 `FlipbookViewer`. 즉 **왼면=사진 / 오른면=글**의 펼침면 구조가 책의 기본 단위다. 라이브러리는 `react-pageflip ^2.0.3`(책장 넘김 애니메이션)이다.

테마는 `lib/themes.ts`에 **7종**이 정의되어 있다 — `luxe-cream`(Luxe Cream), `sacred`(Sacred), `adventure`(Adventure), `editorial`(Editorial), `archive`(Archive), `mission`(Mission), `minimal`(Minimal). 리더가 `components/ui/ThemePicker.tsx`에서 고르고 `hooks/useTheme.ts`가 적용한다.

### 1-6. 사진과 PDF

사진 업로드는 `POST /api/upload-photo`가 처리한다(`multipart/form-data`로 `file`·`path` 전달). 서버가 Supabase Storage의 **`photos` 버킷**에 `upsert: true`로 올리고 public URL을 돌려준다. 업로드 전 크롭은 `components/ui/PhotoCropModal.tsx`(`react-easy-crop`)가 담당한다. PRD는 사진 업로드를 적극 권장하되("사진 한 장이 기억을 살려줘요!"), 없을 경우 기본 템플릿 이미지 선택을 필수로 둔다.

PDF는 **서버가 아니라 브라우저에서 만든다.** PRD 원문: "계정 사용자 PC 브라우저에서 클라이언트 사이드 빌드(`html2pdf.js`) — 서버 비용 없음." 다운로드 옵션은 개별 참여자 PDF / 그룹 통합 PDF 두 가지다. 이것이 "완전 무료"를 지탱하는 두 번째 장치다(첫 번째는 AI 제거).

### 1-7. 자동 정리 크론 — 무료 티어를 지키는 장치

`vercel.json`에 크론이 선언되어 있다.

```json
"crons": [{ "path": "/api/cron/cleanup", "schedule": "0 2 * * *" }]
```

매일 새벽 2시에 `app/api/cron/cleanup/route.ts`가 돈다. 하는 일은 **종료 30일 경과 이벤트의 전면 삭제**다 — 기준일은 `dates_end` → 없으면 `dates_start` → 둘 다 없으면 `created_at` 순으로 폴백한다. 삭제 순서는 ①해당 이벤트의 모든 사진 URL 수집(`toc_photo_url` + `grace_entries.photo_url`) ②Storage `photos` 버킷에서 파일 제거 ③`grace_entries` → `grace_participants` → `grace_sections` → `grace_events` 순으로 DB 레코드 삭제다. 이 라우트는 `Authorization: Bearer <CRON_SECRET>` 헤더를 검사해 일치하지 않으면 401을 반환한다.

★**운영상 반드시 인지할 점** — 이 앱은 **기록을 영구 보관하지 않는다.** 30일이 지나면 사진도 글도 자동으로 사라진다. 따라서 PDF 책 다운로드와 로컬 아카이브(teacher-helper-package의 W1 「은혜 회수」 워크플로우가 이 역할을 맡는 설계다)를 **행사 종료 후 30일 안에** 반드시 끝내야 한다.

### 1-8. 유스케이스 9종 (`docs/GSE_usecase.md`)

| ID | 유스케이스 | 액터 |
|---|---|---|
| UC-01 | 회원가입 & 이메일 수집 | 계정 사용자 |
| UC-02 | 단체 이벤트 생성 | 계정 사용자 |
| UC-03 | 개인 기록 이벤트 생성 | 계정 사용자 |
| UC-04 | QR 코드로 참여자 접속 | 참여자 |
| UC-05 | 활동 기록 입력 (직접 작성) | 참여자, 계정 사용자 |
| UC-06 | 플립북 감상 | 참여자, 계정 사용자 |
| UC-07 | 그룹 공통 콘텐츠 업로드 | 계정 사용자 |
| UC-08 | 이벤트 모니터링 | 계정 사용자 |
| UC-09 | PDF 다운로드 (무료) | 계정 사용자 |

기록 입력에는 **묵상 가이드 템플릿**이 붙는다. PRD가 든 실제 예시 — 수련회: "오늘 말씀 중 내 마음에 꽂힌 한 문장은? 왜 그 말씀이 나에게 왔을까?" / 선교여행: "오늘 만난 사람이나 장면 중 하나님의 마음이 느껴진 순간은?" / 셀 모임: "오늘 나눔에서 새롭게 깨달은 것, 또는 누군가의 이야기가 내게 전해준 것은?" 본문은 최대 500자다. 예시 완성글은 placeholder가 아니라 별도 예시 UI로 제공한다.

---

## 2. 리포·클론

- 리포: `https://github.com/yijae78/godsaengbook-grace.git`
- 커밋(실측): `fd05f78`
- 표준 설치 경로: `$HOME/Future-Ministry/예배교육부/godsaengbook-grace`

```bash
mkdir -p "$HOME/Future-Ministry/예배교육부"
git clone https://github.com/yijae78/godsaengbook-grace.git \
  "$HOME/Future-Ministry/예배교육부/godsaengbook-grace"
cd "$HOME/Future-Ministry/예배교육부/godsaengbook-grace"
```

PowerShell에서는 다음과 같다.

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Future-Ministry\예배교육부" | Out-Null
git clone https://github.com/yijae78/godsaengbook-grace.git `
  "$env:USERPROFILE\Future-Ministry\예배교육부\godsaengbook-grace"
Set-Location "$env:USERPROFILE\Future-Ministry\예배교육부\godsaengbook-grace"
```

> 참고 — teacher-helper-package의 README는 이 앱을 다른 계정 URL(`2020jihyunlee-ship-it/godsaengbook-grace`)로 링크하고 있다. **예배교육부 표준 배포 원본은 위 `yijae78/godsaengbook-grace`**이며, 본 문서의 모든 실측은 이 리포 `fd05f78` 기준이다.

---

## 3. 설치·실행법

> ★다시 고지 — README에는 `create-next-app` 기본 문구뿐이라 이 앱 고유의 설치 절차가 없다. 아래는 **`package.json` · `lib/supabase/*` · `middleware.ts` · `app/api/*` · `vercel.json` · `supabase/migrations/*.sql` · `docs/GSE_implementation_plan.md` 실측**을 근거로 재구성한 실제 절차다.

### 3-1. 사전 준비

- **Node.js** — `next 16.2.1` / `react 19.2.4` 기준. Node 20 LTS 이상을 쓴다.
- **Supabase 프로젝트** — `docs/GSE_implementation_plan.md`가 "Supabase 프로젝트 생성 (별도)"로 명시한다. 기존 갓생북과 **별도 프로젝트**로 만드는 것이 기본 설계다.
- **Vercel 프로젝트**(배포 시) — 구현 계획서: "별도 Vercel 프로젝트, 별도 도메인".

### 3-2. 의존성 설치

```bash
cd "$HOME/Future-Ministry/예배교육부/godsaengbook-grace"
npm install
```

`package.json` 실측 의존성:

- dependencies: `@supabase/ssr ^0.9.0`, `@supabase/supabase-js ^2.100.1`, `framer-motion ^12.38.0`, `html2pdf.js ^0.14.0`, `next 16.2.1`, `qrcode ^1.5.4`, `react 19.2.4`, `react-dom 19.2.4`, `react-easy-crop ^5.5.7`, `react-pageflip ^2.0.3`
- devDependencies: `@tailwindcss/postcss ^4`, `@types/html2pdf.js ^0.10.0`, `@types/node ^20`, `@types/qrcode ^1.5.6`, `@types/react ^19`, `@types/react-dom ^19`, `eslint ^9`, `eslint-config-next 16.2.1`, `tailwindcss ^4`, `typescript ^5`

### 3-3. 환경변수 (필수)

`docs/GSE_implementation_plan.md` §5 「배포 환경 변수 (Vercel)」 원문:

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

코드 전수 grep 결과 실제로 참조되는 환경변수는 **4개**다(구현 계획서의 3개 + 크론 시크릿).

| 변수 | 참조 위치 | 용도 |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `lib/supabase/client.ts`, `lib/supabase/server.ts`, `middleware.ts`, `app/api/upload-photo/route.ts`, `app/api/cron/cleanup/route.ts` | Supabase 프로젝트 URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `lib/supabase/client.ts`, `lib/supabase/server.ts`, `middleware.ts` | 공개 anon 키(브라우저 노출 전제, RLS로 보호) |
| `SUPABASE_SERVICE_ROLE_KEY` | `app/api/upload-photo/route.ts`, `app/api/cron/cleanup/route.ts` | 서버 전용 전권 키(RLS 우회) |
| `CRON_SECRET` | `app/api/cron/cleanup/route.ts` | Vercel Cron 호출 인증(`Bearer` 비교) |

로컬 개발용 파일을 만든다. `.gitignore`가 `.env*`와 `.env*.local`을 모두 제외하므로 커밋되지 않는다.

```bash
cat > .env.local <<'ENV'
NEXT_PUBLIC_SUPABASE_URL=<supabase-project-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<supabase-service-role-key>
CRON_SECRET=<random-long-string>
ENV
```

> ⚠ **보안 경고 (반드시 지킬 것)**: 위 `<...>` 는 전부 **자리표시자다. 실제 키 값을 이 문서·저장소·커밋·로그·대화창·스크린샷 어디에도 적지 마라.**
> - `SUPABASE_SERVICE_ROLE_KEY`는 **RLS를 완전히 우회하는 전권 키**다. 절대 `NEXT_PUBLIC_` 접두어를 붙이지 말고, 클라이언트 컴포넌트에서 참조하지 말며, 서버 라우트 밖으로 내보내지 않는다. 이 리포에서 이 키를 쓰는 곳은 `app/api/upload-photo/route.ts`와 `app/api/cron/cleanup/route.ts` 두 서버 라우트뿐이다.
> - `CRON_SECRET`은 충분히 긴 난수 문자열로 만든다. 이 값이 새면 누구나 정리 크론을 호출해 **데이터를 삭제**할 수 있다.
> - `NEXT_PUBLIC_SUPABASE_ANON_KEY`는 설계상 브라우저에 노출되는 값이지만, 그 안전성은 **RLS 정책이 제대로 걸려 있다는 전제**에 100% 의존한다. 마이그레이션의 RLS 활성화·정책 생성을 건너뛰면 이 키만으로 전체 데이터가 열린다.
> - 키가 유출되었거나 의심되면 Supabase 대시보드에서 **즉시 회전(rotate)**하고 Vercel 환경변수도 함께 갱신한다.

### 3-4. DB 마이그레이션 적용

`supabase/migrations/`에 SQL 3본이 있다.

| 파일 | 줄 수 | 내용 |
|---|---|---|
| `001_initial_schema.sql` | 194 | 초기 스키마(접두어 없는 `users`/`events` 계열) |
| `001_grace_schema.sql` | 195 | **갓생북 은혜 스키마 — `grace_` 접두어. auth는 `auth.users` 공유. 이것이 현행이다** |
| `002_rename_category_mission.sql` | 8 | 카테고리 '선교여행' → '선교' 변경 + CHECK 제약 재설정 |

두 개의 `001_*`이 공존하므로 **어느 쪽을 쓸지 먼저 정한다.** 기존 갓생북 Supabase를 공유하는 현행 설계라면 `001_grace_schema.sql`을 적용한다(파일 헤더 원문: "갓생북 은혜 스키마 (갓생북 Supabase 공유) / 모든 테이블은 grace_ 접두어 사용 / Auth는 기존 갓생북 auth.users 공유"). 코드가 실제로 조회하는 테이블명도 `grace_events`·`grace_entries`·`grace_participants`·`grace_sections`이므로 **`001_grace_schema.sql`이 코드와 정합한다.**

Supabase 대시보드 SQL Editor에 다음 순서로 붙여넣어 실행한다.

```
1) supabase/migrations/001_grace_schema.sql
2) supabase/migrations/002_rename_category_mission.sql
```

Supabase CLI가 설치되어 있다면:

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

**★`001_grace_schema.sql`의 주석 처리된 트리거를 반드시 확인한다.** 파일 하단에 `handle_grace_new_user()` 함수는 생성되지만 이를 `auth.users`에 거는 트리거는 **주석으로 막혀 있다.**

```sql
-- 주의: 갓생북의 on_auth_user_created 트리거와 충돌 방지
-- 갓생북 은혜 가입자는 app_metadata로 구분 가능
-- 아래 트리거는 필요 시 활성화 (갓생북과 auth 완전 공유 시 주석 처리)
-- CREATE TRIGGER on_grace_user_created
--   AFTER INSERT ON auth.users
--   FOR EACH ROW EXECUTE FUNCTION handle_grace_new_user();
```

- **독립 Supabase 프로젝트로 운영**한다면 → 이 트리거의 주석을 풀어 활성화해야 가입 시 `grace_users` row가 자동 생성된다.
- **기존 갓생북과 auth를 완전 공유**한다면 → 주석 처리 상태를 유지한다(기존 `on_auth_user_created`와 충돌 방지).

적용 후 RLS가 켜졌는지 확인한다. 6개 테이블 전부 `ENABLE ROW LEVEL SECURITY`가 걸리고 정책이 붙어야 한다.

```sql
select tablename, rowsecurity from pg_tables where tablename like 'grace_%';
select tablename, policyname from pg_policies where tablename like 'grace_%';
```

### 3-5. Storage 버킷 생성 (코드 실측 — 필수)

`app/api/upload-photo/route.ts`와 `app/api/cron/cleanup/route.ts`가 모두 **`photos`** 라는 이름의 버킷을 사용하며, cleanup 라우트는 public URL 접두어를 `<SUPABASE_URL>/storage/v1/object/public/photos/` 로 계산한다. 즉 **버킷 이름은 정확히 `photos`, 접근은 public**이어야 한다.

Supabase 대시보드 → Storage → New bucket:
- Name: `photos`
- Public bucket: **켬**(public URL을 그대로 플립북·PDF에 싣기 때문)

> `docs/GSE_dataflow_schema.md`에는 `participant-photos/` 라는 폴더 표기가 나오지만, **코드가 실제로 쓰는 버킷명은 `photos`**다. 코드를 사실로 삼는다.

### 3-6. 개발 서버 실행 (README 원문 그대로)

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

README 원문: "Open [http://localhost:3000](http://localhost:3000) with your browser to see the result."

### 3-7. package.json 전체 스크립트 (실측)

```bash
npm run dev     # next dev    — 개발 서버
npm run build   # next build  — 프로덕션 빌드
npm run start   # next start  — 빌드 결과 구동
npm run lint    # eslint      — 린트
```

### 3-8. 배포 (Vercel)

`vercel.json` 실측:

```json
{
  "alias": ["godsaengbook-grace.vercel.app", "gatsaengbook-grace.vercel.app"],
  "crons": [
    {
      "path": "/api/cron/cleanup",
      "schedule": "0 2 * * *"
    }
  ]
}
```

배포 절차:

1. Vercel에 리포를 연결한다(`docs/GSE_implementation_plan.md`: "별도 Vercel 프로젝트, 별도 도메인").
2. Vercel 프로젝트 Settings → Environment Variables에 **4개 변수**를 등록한다 — `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `CRON_SECRET`. **값은 Vercel 대시보드에만 입력하고 저장소에 넣지 않는다.**
3. `CRON_SECRET`은 반드시 등록한다 — 없으면 크론 라우트의 비교(`authHeader !== 'Bearer ' + undefined`)가 항상 실패해 정리가 돌지 않는다(`route.ts` 주석 원문: "환경변수 CRON_SECRET을 Vercel 대시보드에 등록해야 합니다").
4. Supabase Auth 설정에서 Site URL / Redirect URL에 배포 도메인을 등록한다(비밀번호 재설정 PKCE 플로우가 `/auth/confirm` 으로 돌아온다).
5. 배포 후 `docs/GSE_implementation_plan.md` Phase 7 체크: "Supabase Storage 버킷 + RLS 최종 확인" → "Vercel 프로덕션 배포".

크론 라우트는 `runtime = 'nodejs'`, `maxDuration = 60`으로 선언되어 있다.

### 3-9. 구현 계획서의 Phase 체크리스트 (`docs/GSE_implementation_plan.md` 발췌)

- **Phase 1 — 기반 설정(1~2일)**: Supabase 프로젝트 생성(별도) → RLS 정책 설정 → Vercel 프로젝트 연결 + 환경변수 설정 → 별도 Vercel 배포 URL 확보
- **Phase 2**: Supabase Auth 연동(이메일/비밀번호)
- **Phase 7 — 마무리 & 배포(1일)**: PWA 설정(`manifest.json`, Service Worker) → Supabase Storage 버킷 + RLS 최종 확인 → Vercel 프로덕션 배포

★실측 고지 — Phase 7의 **PWA 설정은 현행 커밋에 미반영**이다. `public/`에 `manifest.json`도 Service Worker도 없고 `next.config.ts`는 빈 설정(`const nextConfig: NextConfig = {}`)이다. PRD가 "PWA 지원(오프라인 캐시)"을 적고 있으나 이는 **아직 계획 단계**다. 참여자에게는 일반 웹 링크로 안내한다.

### 3-10. 문서 (`docs/`)

| 파일 | 내용 |
|---|---|
| `GSE_PRD.md` | 제품 요구사항 정의서 — 비전·사용자·이벤트 유형·핵심 기능 7종·수익 모델·기술 스택 |
| `GSE_usecase.md` | 유스케이스 9종(UC-01~09) 기본 흐름·예외 흐름·관련 테이블 |
| `GSE_dataflow_schema.md` | 데이터 흐름 + 스키마 + Storage 버킷 구조 |
| `GSE_implementation_plan.md` | 구현 Phase 계획 + 폴더 구조 + 배포 환경변수 |
| `GSE_userflow.md` | 사용자 플로우 |

---

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(예배교육부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지). → `godsaengbook-grace`
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):
  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "godsaengbook-grace" --cwd "$env:USERPROFILE\Future-Ministry\예배교육부\godsaengbook-grace"
  ```
- 또는 패키지의 `tools/setup.ps1 -Dept fm-worship -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

---

## 5. 대표 사용 시나리오

### 시나리오 — "1박2일 중등부 수련회를 갓생북으로 기록하고, 폐회 전에 책 한 권을 완성한다"

**상황**: 중등부 수련회 1박2일, 참여자 34명, 리더는 김OO 전도사 1명만 가입. 참여자는 회원가입 없이 QR로만 참여한다. 종료 후 학부모에게 PDF 책을 보낸다.

#### ① 최초 1회 — 기술자 pane 셋업

```bash
mkdir -p "$HOME/Future-Ministry/예배교육부"
git clone https://github.com/yijae78/godsaengbook-grace.git \
  "$HOME/Future-Ministry/예배교육부/godsaengbook-grace"
cd "$HOME/Future-Ministry/예배교육부/godsaengbook-grace"
node -v          # Node 20 LTS 이상
npm install
```

#### ② Supabase 준비 (D-14)

1. Supabase에서 새 프로젝트를 만든다.
2. SQL Editor에 `supabase/migrations/001_grace_schema.sql` → `002_rename_category_mission.sql` 순으로 실행한다.
3. 독립 프로젝트로 운영하므로 `001_grace_schema.sql` 하단의 `on_grace_user_created` 트리거 주석을 풀어 실행한다(가입 시 `grace_users` 자동 생성).
4. Storage에서 **`photos`** 버킷을 public으로 만든다.
5. RLS가 6개 테이블에 걸렸는지 확인한다.

```sql
select tablename, rowsecurity from pg_tables where tablename like 'grace_%';
```

#### ③ 로컬 환경변수 구성 (키는 절대 커밋하지 않는다)

```bash
cat > .env.local <<'ENV'
NEXT_PUBLIC_SUPABASE_URL=<supabase-project-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<supabase-service-role-key>
CRON_SECRET=<random-long-string>
ENV
git check-ignore -v .env.local   # .gitignore가 잡는지 확인 (반드시 출력이 나와야 한다)
```

#### ④ 로컬 검증

```bash
npm run dev
```

`http://localhost:3000` 에서 랜딩 → 회원가입 → 대시보드 진입까지 통과하는지 본다. `middleware.ts`가 미로그인 상태의 `/dashboard`·`/events` 접근을 `/login`으로 돌리고, 로그인 상태의 `/login`·`/signup` 접근을 `/dashboard`로 돌리는 것도 함께 확인한다.

빌드 검증:

```bash
npm run lint
npm run build
```

#### ⑤ 배포 (D-10)

Vercel에 리포를 연결하고 환경변수 4개를 대시보드에 등록한다(**값은 대시보드에만**). Supabase Auth의 Site URL / Redirect URL에 배포 도메인을 등록한다. `vercel.json`의 크론이 자동 등록되어 매일 02:00에 `/api/cron/cleanup`이 돈다.

크론 인증이 제대로 걸렸는지는 **시크릿 없이 호출해 401이 나오는지**로 확인한다(정상 동작 확인용이며, 올바른 시크릿을 붙인 호출은 실제로 데이터를 지우므로 프로덕션에서 임의로 실행하지 않는다).

```bash
curl -i https://<배포도메인>/api/cron/cleanup
# HTTP/2 401  {"error":"Unauthorized"} 가 나오면 인증 게이트 정상
```

#### ⑥ D-7 — 이벤트 생성

리더가 배포 사이트에 로그인 → 대시보드 → 「새 이벤트 만들기」(`/events/new`).
- 이벤트 타입: `단체(group)`
- 카테고리: `수련회`
- 이름: `2026 중등부 여름수련회`
- 기간: 시작일·종료일
- 예상 참여 인원: `34`

저장하면 `grace_events`에 row가 생기고 **QR 코드 URL이 자동 생성**된다(`components/QRCodeDisplay.tsx`가 `qrcode` 패키지로 렌더). 이 QR이 `/join/[eventId]` 로 연결된다.

이어서 `/events/[id]/schedule`에서 **목차(`grace_sections`)를 미리 등록**한다 — 예: `1. 첫날 도착·등록`, `2. 저녁집회`, `3. 조별나눔`, `4. 둘째날 아침예배`, `5. 폐회예배`. 참여자의 기록이 이 섹션에 붙어 책의 목차가 된다.

테마도 여기서 고른다(`ThemePicker` — `luxe-cream`·`sacred`·`adventure`·`editorial`·`archive`·`mission`·`minimal` 7종 중 선택. 수련회면 `adventure`나 `sacred`가 무난하다).

#### ⑦ D-3 — QR 배포

QR 이미지를 저장해 안내문·조장 카드·수련회 팜플렛에 인쇄한다. 학부모 안내문에도 링크를 넣는다. **참여자는 가입하지 않는다** — QR을 찍고 이름만 입력하면 `grace_participants`에 `session_token`이 발급되고 이후 그 기기에서 이어서 쓸 수 있다.

#### ⑧ 행사 중 — 기록 수집

각 세션이 끝날 때 5분씩 시간을 준다. 참여자는 `/record/[eventId]`에서:
- 사진을 찍거나 고른다 → 크롭 모달(`PhotoCropModal`)로 잘라 `POST /api/upload-photo`가 `photos` 버킷에 올린다. 사진이 없으면 기본 템플릿 이미지를 고른다(필수).
- 묵상 가이드 질문을 보며 본문을 **최대 500자**로 직접 쓴다.
- (선택) 마음에 와 닿은 성경 구절·인용 문구를 직접 입력한다.

리더는 `/events/[id]`에서 참여자 목록과 기록 현황을 실시간으로 본다(UC-08). 아직 안 쓴 조를 콕 집어 독려할 수 있다.

리더 공통 콘텐츠도 올린다(UC-07) — 단체 사진(`photo`), 말씀 공지(`notice`), 마무리 총평(`summary`). `/events/[id]/summary`에서 총평을 쓰면 모든 참여자 플립북 끝에 자동으로 붙는다(`PageSummary`).

#### ⑨ 폐회식 — 완성돼 가는 책을 함께 본다

`/flipbook/[eventId]`를 빔프로젝터에 띄운다. `react-pageflip`이 왼면 사진(`PagePhotoLeft`) / 오른면 글(`PageEssayRight`) 펼침면을 넘기며 표지 → 목차 → 장면들 → 마무리 순으로 보여 준다. `/grid/[eventId]`로 격자 보기 전환도 된다. 개인별 공유 링크는 `/share/[participantId]`다.

#### ⑩ 종료 직후 — PDF 책을 뽑는다 (★30일 시한)

리더가 **PC 브라우저**에서 `/pdf/[eventId]`를 연다. `html2pdf.js`가 클라이언트에서 PDF를 빌드하므로 서버 비용이 0이다. 개별 참여자 PDF와 그룹 통합 PDF 두 가지를 뽑는다. 완성 파일은 학부모 공지로 공유한다 — "우리 아이의 수련회가 책 한 권으로".

**★반드시 이 시점에 로컬 아카이브까지 끝낸다.** 크론이 매일 02:00에 돌면서 **종료 30일 경과 이벤트의 사진과 DB 레코드를 전부 삭제**한다. 클라우드에는 아무것도 남지 않는다.

```bash
mkdir -p "$HOME/Future-Ministry/예배교육부/grace-archive/2026-중등부여름수련회"
# 다운로드한 PDF와 사진 원본을 이 폴더로 이관해 보관
```

이 로컬 이관을 자동화하는 것이 teacher-helper-package의 **W1「은혜 회수」 워크플로우**이며(현재 명세 단계), 이관된 폴더를 그대로 **`book_to_video.py`** 에 넣으면 다음 주일 상영용 회고 영상이 나온다.

```bash
python "$HOME/Future-Ministry/예배교육부/teacher-helper-package/workflows/book_to_video.py" \
  "$HOME/Future-Ministry/예배교육부/grace-archive/2026-중등부여름수련회" \
  --title "2026 중등부 여름수련회" --sec 4 \
  --out "$HOME/Future-Ministry/예배교육부/grace-archive/2026-중등부여름수련회/recap.mp4"
```

#### ⑪ 마무리 — 이벤트 상태를 `completed`로 바꾼다

`grace_events.status`를 `completed`로 전환하면 RLS 정책상 참여자의 신규 기록 입력이 닫힌다(정책 조건이 `status = 'active'`이기 때문). 책은 확정되고, 30일 뒤 크론이 클라우드 흔적을 정리한다 — 무료 티어가 다음 행사를 위해 다시 비워진다.
