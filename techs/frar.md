# frar — 행정관리부 기술자

> 실측 근거: yijae78/frar@3a1c343 · README 있음 · 확인 2026-08-14

## 1. 무엇을 하는가

교회 주일 예배 영상에서 얼굴을 인식해 출석 확인을 **돕는** 로컬 전용 도구다.

구성은 여섯 덩어리다. 교적(교인 명부) 사진 갤러리, 영상 인식, 이름 후보 제안, 사람이 확정하는 검수 화면, 수동 출석 입력, Notion 출석부 내보내기(선택). README는 이 코드를 "한국교회 어디든 가져다 자기 교회 상황에 맞게 고쳐 쓰실 수 있도록 공개"한다고 밝히고 있으며 라이선스는 MIT다.

설계 원칙 세 가지가 이 도구의 성격을 결정한다. 첫째, **생체정보는 로컬 전용**이다. 얼굴 사진과 임베딩(생체 특징값)은 사용하는 컴퓨터 밖으로 나가지 않는다. 클라우드로 전송되는 것은 — Notion 내보내기를 켠 경우에 한해 — 이름·출석 여부 같은 명부 수준 정보뿐이다. 둘째, **거짓 확정 0**이다. 시스템은 절대 출석을 자동 확정하지 않는다. 인식 결과는 「후보 제안」까지만이고 최종 확정은 언제나 사람(교역자)의 클릭이며, 확정·취소는 전부 감사 기록으로 남는다. 셋째, **기록 보존**이다. 등록·출석·확정 이력은 삭제가 아니라 상태 변경으로 관리한다.

기능별로 보면 이렇다. **교적 갤러리**는 교인 명부와 사진을 보는 Streamlit 웹 화면으로, 인식 기능을 전혀 쓰지 않아도 이것만으로 사진 출석부 역할을 한다. **명부 임포트**는 교적 프로그램 디모데의 HTML 내보내기 파일을 읽는 어댑터이며, 다른 교적 프로그램은 어댑터만 추가하면 붙는다. **영상 인식**은 예배 영상에서 얼굴 검출(YuNet)과 특징 추출(SFace)을 수행하며 둘 다 OpenCV Zoo 공개 모델이다. **이름 후보 제안**은 인식된 인물마다 명부에서 유사 후보 상위 3명을 제안하되 자동 확정은 하지 않는다. **비교 검수 화면**은 영상 캡처와 교적 사진·후보를 나란히 놓고 1클릭으로 귀속시킨다. **수동 출석**은 인식과 무관하게 손으로 출석을 입력·취소한다. **Notion 내보내기(선택)**는 확정된 출석부만 Notion 데이터베이스로 멱등 push하며 생체정보는 전송 대상에서 원천 배제된다.

코드 구조는 `config.py`(임계값·검출·정책 상수와 경로의 단일 출처), `app/db/`(SQLite 스키마·모델·리포지토리), `app/engine/`(얼굴 엔진·클러스터링·매칭·모델 조달), `app/security/`(감사 로그·인증·암호화), `app/services/`(등록·처리·검수·리포트·출석 매트릭스·이름 제안·Notion 내보내기·검증), `app/ui/`(홈·로그인·등록·처리·검수·인물·출석 화면)로 나뉜다. `run.py`가 진입점이다. 별도로 `phase0/`에 카메라 환경 실측용 벤치마크 키트가 들어 있다.

로컬 전용 원칙은 코드 레벨에서 강제된다. `run.py` 주석에 따르면 Streamlit은 기본이 `0.0.0.0`(LAN 노출)이라 반드시 `127.0.0.1`로 묶으며, `run.py`에는 `0.0.0.0`이 아예 등장하지 않고(grep 검증), 텔레메트리는 `.streamlit/config.toml`과 명령행 양쪽에서 끈다. 앱 코드 어디서도 네트워크 호출을 하지 않고 모델 조달만 `app.engine` 경계에서 이루어진다. 암호화 키는 D-12 결정에 따라 DB 파일과 **분리 저장**된다 — `church.db` 안에 키가 없어야 클라우드 동기화 시에도 at-rest 보호 가치가 유지되기 때문이다.

README가 굵게 강조하는 현실적 경고가 하나 있다. **영상 화질이 실용성을 가른다.** 운영 실측 공유에 따르면 원거리·저해상 예배 영상(화면 속 얼굴이 48px 수준)에서는 얼굴 검출률이 24%에 그쳤다. 이것은 코드로 해결되는 문제가 아니라 입력의 문제다. 카메라가 회중과 가깝고 얼굴이 크게 잡힐수록, 해상도가 높을수록 실용성이 올라간다. 각 교회의 카메라 위치·화질·조명에 맞추어 적응해서 써야 하며, 화질 조건이 안 되는 교회라도 교적 갤러리 + 수동 출석 + 검수 화면은 그대로 유용하다. 그래서 `phase0/` 벤치마크 키트로 **먼저 우리 교회 카메라 환경이 충분한지 실측**하고 개발·도입 여부를 판단하는 절차가 따로 마련되어 있다.

회귀 테스트는 160여 건이며 `tests/` 아래에 인증·클러스터링·완전삭제·계약·디모데 HTML·E2E·수동출석·다중템플릿·이름제안·Notion 내보내기·보안 프라이버시·블라인드 감사 등 26개 테스트 파일로 존재한다.

## 2. 리포·클론

- 리포: https://github.com/yijae78/frar.git
- 대상 경로: `$HOME/Future-Ministry/행정관리부/frar`

```bash
mkdir -p "$HOME/Future-Ministry/행정관리부"
git clone https://github.com/yijae78/frar.git \
  "$HOME/Future-Ministry/행정관리부/frar"
cd "$HOME/Future-Ministry/행정관리부/frar"
```

## 3. 설치·실행법

### 3-1. 시작하기 (README 원문 절차)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python phase0/download_models.py   # OpenCV Zoo 모델 내려받기
python run.py                      # 브라우저에서 안내 화면이 열립니다
```

Windows PowerShell에서는 가상환경 활성화만 다르다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python phase0/download_models.py
python run.py
```

테스트: `python -m pytest` (회귀 160여 건).

### 3-2. 의존성 (`requirements.txt` 실측 — 전부 자유 라이선스)

```
opencv-python>=4.10      # Apache 2.0 — YuNet 검출 + SFace 인식 내장
numpy>=1.24              # BSD
pandas>=2.0              # BSD — 디모데 엑셀 명단 처리
openpyxl>=3.1            # MIT — 출석부 Excel 출력
streamlit>=1.30          # Apache 2.0 — UI
cryptography>=42.0       # Apache/BSD — 임베딩 암호화
```

### 3-3. 실행 방식 두 가지 (둘 다 localhost로 뜬다)

`run.py` 모듈 독스트링 실측 내용이다.

- **가장 쉬움**: `python run.py`
  이 스크립트가 streamlit 런타임 밖이면 subprocess로 자기 자신을 `streamlit run run.py --server.address=127.0.0.1 ...` 로 **재실행**한다(N-6 강제).
- **직접**: `streamlit run run.py`
  이미 `.streamlit/config.toml` 이 `address=127.0.0.1`·`gatherUsageStats=false` 를 강제하므로 동일하게 localhost·텔레메트리 off 로 뜬다(이중 방어).

부트스트랩은 앱 본체에서 1회만 돈다(`@st.cache_resource`). ① `init_db(DB_PATH)` ② connect 단일 연결 ③ `KeyManager.generate`(최초 키)·Crypto·Audit ④ 기동 스윕(`purge_expired_unknowns` + `purge_service_videos` — 멱등, 실패는 홈 배너로 표시) ⑤ `OpenCVEngine` 로드(모델 부재 시 `ensure_models` 시도 → 실패 시 안내 메시지).

### 3-4. 경로·데이터 레이아웃 (`config.py` 실측)

모든 경로는 `config.py`가 위치한 프로젝트 루트 기준 상대 경로다. 절대경로를 하드코딩하지 않으므로 Mac·Windows·이동 설치 어디서나 동작한다.

| 상수 | 경로 | 용도 |
|---|---|---|
| `PROJECT_ROOT` | 리포 루트 | 기준점 |
| `DATA_DIR` | `data/` | 런타임 데이터 (`.gitignore` 대상, 로컬 전용) |
| `DB_PATH` | `data/church.db` | SQLite 단일 DB (암호화된 임베딩·사진 BLOB 포함) |
| `MODELS_DIR` | `data/models` | YuNet·SFace ONNX 모델 |
| `VIDEOS_DIR` | `data/videos` | 처리 대상 원본 영상 (D-14 정책 — 처리·검수 후 자동 파기) |
| `KEY_DIR` | `data/keys` | 암호화 키 저장소 — D-12: 키를 DB 파일과 **분리** 저장 |

> ⚠ `KEY_DIR` 은 운영 시 클라우드 동기화 트리 **밖**에 두거나 백업키 패스프레이즈로 보호한다. 키가 DB와 같이 흘러가면 at-rest 암호화 가치가 사라진다.

### 3-5. 데이터 준비 — 전부 로컬에서

- **교인 명부**: 디모데 사용자는 HTML 내보내기 파일을 그대로 임포트할 수 있다. 다른 프로그램 사용자는 `app/services` 의 어댑터 구조를 참고해 자기 형식 어댑터를 추가한다.
- **사진**: 인물별 사진 폴더를 등록 화면에서 지정한다. 사진이 좋을수록 제안 정확도가 올라간다.
- 명부·사진·데이터베이스(`data/`)는 `.gitignore` 로 저장소에서 원천 배제되어 있다 — **성도 개인정보는 각 교회가 로컬에서 책임지고 관리하는 구조**다.

### 3-6. Phase 0 벤치마크 키트 — 도입 전 카메라 환경 실측

`phase0/README.md` 원문 절차다. 이번 주일 예배 영상을 받으면 이 키트로 우리 교회 카메라 환경이 충분한지 먼저 실측하고, 결과에 따라 엔진·임계값·카메라 개선 여부를 결정한다.

**Python 확인** — Mac: `python3 --version` 이 3.10 이상이면 OK. Windows: https://python.org 에서 설치하되 **"Add Python to PATH" 반드시 체크**.

**가상환경 + 라이브러리 (Mac / 터미널)**

```bash
cd attendance_phase0
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**가상환경 + 라이브러리 (Windows / 명령 프롬프트)**

```bat
cd attendance_phase0
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> 설치되는 것은 `opencv-python`, `numpy` 단 두 개. 컴파일러·GPU 불필요.
> (리포에서는 이 키트가 `phase0/` 디렉터리에 들어 있으므로 `cd attendance_phase0` 대신 `cd phase0` 로 읽는다.)

**모델 다운로드 (약 37MB)**

```bash
python download_models.py
```

실패 시 안내되는 주소를 브라우저로 열어 직접 받아 `models/` 폴더에 넣으면 된다.

**벤치마크 실행 (필수, 약 10~30분)** — 예배 영상 파일을 이 폴더에 복사한 뒤:

```bash
python benchmark.py --video 주일1부.mp4
```

끝나면 `benchmark_out/` 폴더에 **report.txt**(핵심 리포트), **annotated_frames/**(검출 결과가 박스로 표시된 프레임 — 육안 확인), **per_frame.csv**(상세 데이터)가 생긴다.

**리포트에서 볼 것 한 가지 ★** — "인식 가능 비율(48px+)" 이 숫자가 모든 것을 결정한다.

| 값 | 판정 |
|---|---|
| **60% 이상** | 현재 카메라로 진행. 바로 Phase 1 개발 착수 |
| **30~60%** | 진행 가능하나 뒷좌석 검수 비중 높아짐. 카메라 줌/위치 조정 검토 |
| **30% 미만** | 개발 전에 카메라 환경 개선 필요 |

### 3-7. 원격 접속 (선택)

`scripts/tunnel_start.sh` 는 Cloudflare Tunnel + Access(이메일 OTP)로 대시보드를 외부에서 안전하게 여는 예시다. **Access(인증) 활성화를 확인하기 전에는 터널이 열리지 않게** 잠금 파일 방식으로 짜여 있다. 도메인·터널 이름은 각 교회 것으로 바꾸어 쓴다. 관련 스크립트는 `scripts/tunnel_start.sh`·`scripts/tunnel_stop.sh`·`scripts/tunnel_health.sh` 세 개다.

### 3-8. Notion 내보내기 (선택)

`scripts/notion_push_attendance.py` 는 확정된 출석부만 Notion 데이터베이스로 멱등 push한다. 토큰은 `.env.local` 의 `NOTION_ATTENDANCE_TOKEN` 항목만 메모리로 읽으며, 스크립트 설계상 **로그·에러·콘솔에 평문 노출 0**이다. `.env.local` 에 해당 키가 없으면 스크립트가 오류를 내고 중단한다.

```bash
# .env.local (리포에 커밋 금지 — .gitignore 대상)
NOTION_ATTENDANCE_TOKEN=<여기에 본인 Notion 통합 토큰>
```

> ⚠ 위 값은 **자리표시자**다. 실제 토큰을 이 문서·리포·채팅·로그 어디에도 남기지 않는다. Notion으로 나가는 것은 이름·출석 여부 수준의 명부 정보뿐이며 얼굴 사진·임베딩은 전송 대상에서 원천 배제되어 있다.

### 3-9. 라이선스

- 이 저장소의 코드: **MIT** — 자유롭게 가져다 고쳐 쓸 수 있다.
- 내려받는 모델: YuNet(얼굴 검출) = **MIT**, SFace(특징 추출) = **Apache 2.0** (OpenCV Zoo).
- 성도 개인정보·사진·생체정보의 수집과 관리는 각 교회의 동의 절차와 책임 아래 이루어져야 한다.

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(행정관리부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지).
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):

  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "frar" --cwd "$env:USERPROFILE\Future-Ministry\행정관리부\frar"
  ```

- 또는 패키지의 `tools/setup.ps1 -Dept fm-admin -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

## 5. 대표 사용 시나리오

### 시나리오 — 주일 1부 예배 영상으로 출석부를 만든다 (도입 실측 → 운영까지)

**0단계 — 도입 전 카메라 환경 실측.** 이번 주일 영상을 받았다면 먼저 벤치마크부터 돌린다. 여기서 숫자가 안 나오면 인식 기능에 시간을 쓰지 않는 것이 맞다.

```bash
cd "$HOME/Future-Ministry/행정관리부/frar/phase0"
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python download_models.py
python benchmark.py --video 주일1부.mp4
```

`benchmark_out/report.txt` 를 열어 **"인식 가능 비율(48px+)"** 한 줄만 본다. 60% 이상이면 그대로 진행, 30~60%면 진행하되 뒷좌석 검수 비중을 각오, 30% 미만이면 카메라부터 손본다. `benchmark_out/annotated_frames/` 를 육안으로 훑어 검출 박스가 어느 좌석까지 잡히는지 확인한다.

**1단계 — 본 앱 설치.**

```bash
cd "$HOME/Future-Ministry/행정관리부/frar"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python phase0/download_models.py
python run.py
```

브라우저가 `http://127.0.0.1:8501` 안내 화면으로 열린다(LAN에 노출되지 않는다). 최초 기동 시 DB 초기화, 암호화 키 생성(`data/keys/`), 기동 스윕(만료 미상 인물·서비스 영상 자동 파기)이 자동으로 돈다.

**2단계 — 명부·사진 등록.** 등록 화면에서 디모데 HTML 내보내기 파일을 임포트하고, 인물별 사진 폴더를 지정한다. 명부·사진·DB는 전부 `data/` 아래 로컬에만 남는다.

**3단계 — 영상 처리.** 예배 영상을 `data/videos/` 에 넣고 처리 화면에서 실행한다. YuNet이 얼굴을 검출하고 SFace가 특징을 뽑아 명부와 대조한 뒤, 인물마다 **유사 후보 상위 3명**을 제안한다. 이 단계에서 출석이 확정되는 일은 없다.

**4단계 — 사람이 확정한다(핵심).** 검수 화면에서 영상 캡처와 교적 사진·후보가 나란히 뜬다. 교역자가 눈으로 보고 1클릭으로 귀속시킨다. 확정·취소는 전부 감사 로그로 남는다. 후보 중에 맞는 사람이 없으면 넘기고, 인식이 아예 안 된 사람은 수동 출석으로 직접 넣는다.

**5단계 — 출석부 산출.** 출석 매트릭스를 만들고 Excel로 내보낸다.

```bash
python scripts/build_attendance_matrix.py
```

**6단계 — Notion 동기화 (선택).** `.env.local` 에 `NOTION_ATTENDANCE_TOKEN` 을 넣어 둔 뒤:

```bash
python scripts/notion_push_attendance.py
```

확정된 출석부만 멱등 push된다(같은 주차를 여러 번 돌려도 중복 생성되지 않는다). 얼굴 사진·임베딩은 전송되지 않는다.

**7단계 — 원격 확인이 필요하면.** Cloudflare Access 인증을 붙인 터널을 연다. Access가 켜져 있지 않으면 스크립트가 잠금 파일 때문에 터널을 열지 않는다.

```bash
bash scripts/tunnel_start.sh
bash scripts/tunnel_health.sh
bash scripts/tunnel_stop.sh     # 끝나면 반드시 닫는다
```

**회귀 확인.** 코드를 손댔다면 커밋 전에 테스트를 돌린다.

```bash
python -m pytest
```

**화질이 안 나오는 교회라면.** 인식 파이프라인을 아예 건너뛰고 교적 갤러리 + 수동 출석 + 검수 화면만 써도 사진 출석부로서 충분히 굴러간다. README가 그렇게 쓰라고 명시한 용법이다.
