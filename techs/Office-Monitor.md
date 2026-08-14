# Office-Monitor — 행정관리부 기술자

> 실측 근거: yijae78/Office-Monitor@0b51636 · README 있음 · 확인 2026-08-14

## 1. 무엇을 하는가

사무실 출입자를 실시간으로 감지하고 인식하는 데스크톱 모니터링 시스템이다.

카메라 영상에서 사람을 추적하고, 등록된 방문자를 자동으로 식별하며, 방문 기록을 관리한다. PyQt6로 만든 Windows 데스크톱 앱이며 웹 서버가 아니다 — 실행하면 창이 뜨고, 최소화하면 시스템 트레이로 내려가 백그라운드에서 계속 감시한다.

핵심 기능은 여덟 가지다. **실시간 얼굴 인식**은 InsightFace(`buffalo_l`) 기반 얼굴 임베딩 매칭으로 수행한다. **사람 추적**은 YOLO11n + ByteTrack으로 전신을 감지·추적하므로 뒷모습이어도 추적이 유지된다. **방문자 관리**는 등록/삭제/복구를 지원하며 인물당 최대 10개의 다각도 임베딩을 자동 수집한다. **방문 기록**은 타임라인 UI, 일별/시간대별 통계, KPI 대시보드로 제공된다. **영상 녹화**는 수동 녹화와 30분 세그먼트 자동 분할을 지원한다. **스냅샷 캡처**는 전체 화면 또는 드래그한 영역만 잡는다. **미등록자 자동 캡처**는 3초간 최고 품질 프레임을 선별해 저장한다. **시스템 트레이**는 최소화 시 트레이로 이동해 백그라운드 동작을 이어간다.

이 시스템의 특징은 **얼굴이 안 보여도 사람을 놓치지 않는다**는 점이다. 감지 파이프라인은 카메라 프레임 → YOLO11n(모든 각도에서 사람 바운딩박스) → ByteTrack(track_id 부여·유지) → InsightFace(얼굴 검출 시 임베딩 매칭 → track_id에 이름 바인딩) 순으로 흐르고, 얼굴이 검출되지 않으면 해당 track_id의 기존 이름을 그대로 유지한다. 한 번 이름이 바인딩된 추적 ID는 그 사람이 화면을 벗어날 때까지 유지되므로, 뒤돌아서 얼굴이 안 보여도 추적이 끊기지 않는다. 화면에서는 이것이 실선/점선으로 구분된다 — 등록자 얼굴 보임은 녹색 실선 + 이름, 등록자 뒷모습은 녹색 점선 + 이름, 미등록자 얼굴 보임은 붉은색 실선, 미등록자 뒷모습(사람은 감지·얼굴 미검출)은 붉은색 점선이다.

기술 스택은 Python 3.10+, PyQt6(데스크톱 UI), InsightFace(얼굴 검출·임베딩 추출), Ultralytics YOLO11n(사람 전신 감지), ByteTrack(다중 객체 추적), OpenCV(카메라 캡처·이미지 처리), SQLite WAL 모드(방문자·방문기록 저장)로 구성된다.

코드 구조는 `main.py`(앱 진입점), `config.yaml`(카메라/감지/녹화/저장 설정), `paths.py`(config.yaml 기반 경로 설정), `database.py`(SQLite DB), `detection_engine.py`(얼굴 인식 + YOLO 추적 스레드), `monitor_engine.py`(카메라 캡처 스레드), `recording_engine.py`(영상 녹화 스레드)가 뼈대이고, `ui/` 아래에 `main_window.py`·`camera_widget.py`(줌·영역 캡처·감지 오버레이)·`visitor_manager.py`·`visitor_timeline.py`·`stats_view.py`·`settings_dialog.py`·`new_face_dialog.py`·`header_bar.py`·`kpi_card.py`·`toast_widget.py`·`glass_card.py`(글래스모피즘 카드)·`design_tokens.py`·`styles.py`·`flow_layout.py` 가 붙는다. `assets/`에 ICO + PNG 16~512px 앱 아이콘이, `tools/generate_icon.py`에 아이콘 생성 스크립트가 있다.

DB 스키마는 6개 테이블이다. `visitors`(등록된 방문자 — 이름, 썸네일, 상태), `face_embeddings`(얼굴 벡터 — 방문자당 최대 10개, 품질 점수 포함), `visit_logs`(방문 기록 — 시간, 등록 여부, 썸네일), `pending_faces`(미등록 얼굴 캡처 — 등록 대기), `snapshots`(스냅샷 파일 기록), `recordings`(녹화 파일 기록).

**소스 코드와 데이터가 완전히 분리되어 있다.** 모든 런타임 데이터는 `config.yaml`의 `storage.data_dir` 경로에 저장되며 기본값은 `C:\OfficeMonitor` 다. 그 아래에 `data/monitor.db`(SQLite), `data/thumbnails/`(방문 썸네일), `data/pending_faces/`(미등록 얼굴 캡처), `snapshots/`, `recordings/`, `app.log`(5MB × 3 로테이션), `crash.log` 가 생긴다. git은 이 경로를 추적하지 않는다.

운영상 알아둘 점 하나 — 이 시스템은 사무실 출입자의 **얼굴 이미지와 생체 임베딩을 로컬 DB에 축적**한다. 데이터 보존 기간은 기본 3일(`storage.retention_days`)이며 그 이후 자동 정리된다. 교회·사무실 환경에 도입할 때는 촬영 고지와 동의 절차를 각 기관 책임으로 갖춰야 한다.

리포 라이선스는 README 명시로 "Private repository. All rights reserved." 다 — 코드는 열려 있으나 자유 재배포 라이선스가 아니다.

## 2. 리포·클론

- 리포: https://github.com/yijae78/Office-Monitor.git
- 대상 경로: `$HOME/Future-Ministry/행정관리부/Office-Monitor`

```bash
mkdir -p "$HOME/Future-Ministry/행정관리부"
git clone https://github.com/yijae78/Office-Monitor.git \
  "$HOME/Future-Ministry/행정관리부/Office-Monitor"
cd "$HOME/Future-Ministry/행정관리부/Office-Monitor"
```

## 3. 설치·실행법

### 3-1. 요구 사항 (`MANUAL.md` 실측)

| 항목 | 조건 |
|------|------|
| OS | Windows 10/11 |
| Python | 3.10 이상 |
| 카메라 | USB 웹캠 (DirectShow 지원) |
| 저장 공간 | 최소 2GB 여유 (모델 다운로드 + 데이터) |

### 3-2. 설치 순서

**1단계: 저장소 클론**

```bash
git clone https://github.com/yijae78/Office-Monitor.git
cd Office-Monitor
```

**2단계: 가상환경 생성 (권장)**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**3단계: 의존성 설치**

```bash
pip install -r requirements.txt
```

> **설치 실패 시:** `insightface`나 `onnxruntime` 패키지에서 에러가 발생하면 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)를 먼저 설치한 후 다시 시도한다. 설치 시 "C++를 사용한 데스크톱 개발" 워크로드를 선택한다.

**4단계: 실행**

```bash
python main.py
```

> 최초 실행 시 InsightFace 모델(`buffalo_l`, 약 300MB)과 YOLO11n 모델이 자동 다운로드된다. 인터넷 연결이 필요하며 1~5분 소요될 수 있다.

### 3-3. 의존성 (`requirements.txt` 실측)

```
PyQt6>=6.6
opencv-python>=4.9
insightface>=0.7
ultralytics>=8.1
numpy>=1.24
pyyaml>=6.0
onnxruntime>=1.17
```

### 3-4. 첫 실행 — 자동으로 생성되는 것들

앱이 처음 실행되면 다음 폴더와 파일이 자동 생성된다.

```
C:\OfficeMonitor\              ← 기본 데이터 저장 경로
├── data\
│   ├── monitor.db             ← SQLite 데이터베이스
│   ├── thumbnails\            ← 방문 썸네일 이미지
│   └── pending_faces\         ← 미등록 얼굴 캡처 이미지
├── snapshots\                 ← 스냅샷 이미지
├── recordings\                ← 녹화 영상
└── app.log                    ← 앱 로그
```

> 데이터 저장 경로는 `config.yaml`의 `storage.data_dir`에서 변경할 수 있다.

**카메라 연결** — 앱이 시작되면 자동으로 카메라를 찾아 연결한다. 기본 카메라(ID 0)가 실패하면 대체 ID(2, 3)를 순서대로 시도한다. 가상 카메라(화면 캡처 소프트웨어 등)는 자동으로 건너뛴다. 연결 상태는 우측 패널의 **카메라 정보** 카드에서 확인할 수 있다.

**데모 데이터로 체험하기** — 기능을 먼저 둘러보고 싶다면 ①상단 **⚙ 설정** 버튼 클릭 ②맨 아래 **데모 모드** 섹션에서 **데모 생성** 클릭 ③방문자관리·통계 탭에서 샘플 데이터 확인 ④체험 후 **데모 삭제**로 정리(실제 데이터는 보존됨).

### 3-5. 설정 (`config.yaml`)

README 요약본:

```yaml
camera:
  id: 0                          # 카메라 장치 ID
  resolution: [1280, 720]        # 해상도
  fallback_ids: [2, 3]           # 메인 카메라 실패 시 대체 ID

detection:
  model: "buffalo_l"             # InsightFace 모델
  interval_ms: 200               # 감지 주기 (ms)
  similarity_threshold: 0.65     # 얼굴 매칭 임계값 (0~1)
  cooldown_seconds: 300          # 같은 사람 재기록 쿨다운 (초)
  auto_augment_embeddings: true  # 다각도 임베딩 자동 수집

recording:
  codec: "XVID"                  # 녹화 코덱
  fps: 15                        # 녹화 FPS
  segment_minutes: 30            # 세그먼트 길이

storage:
  data_dir: "C:\\OfficeMonitor"  # 데이터 저장 경로
  retention_days: 3              # 데이터 보존 기간
```

`MANUAL.md` 부록의 **전체 예시**:

```yaml
camera:
  id: 0
  resolution: [1280, 720]
  backend: "dshow"
  fallback_ids: [2, 3]

detection:
  model: "buffalo_l"
  det_size: [640, 640]
  interval_ms: 200
  score_threshold: 0.35
  similarity_threshold: 0.65
  min_consecutive_frames: 3
  cooldown_seconds: 300
  auto_augment_embeddings: true

recording:
  codec: "XVID"
  fps: 15
  segment_minutes: 30
  auto_start: false

storage:
  data_dir: "C:\\OfficeMonitor"
  retention_days: 3
  cleanup_interval_hours: 1

shortcuts:
  capture: "Ctrl+Shift+C"
  record_toggle: "Ctrl+R"
  record_pause: "Ctrl+P"
```

### 3-6. 설정 다이얼로그 항목 (⚙ 버튼)

**카메라**

| 항목 | 설명 | 기본값 |
|------|------|--------|
| 카메라 ID | 사용할 카메라 장치 번호 | 0 |
| 해상도 (가로) | 카메라 가로 해상도 | 1280 |
| 해상도 (세로) | 카메라 세로 해상도 | 720 |

**얼굴 감지**

| 항목 | 설명 | 기본값 | 범위 |
|------|------|--------|------|
| 감지 간격 | 얼굴 감지 주기 (낮을수록 빠르지만 CPU 부하 증가) | 200ms | 50~2000ms |
| 감지 임계값 | 얼굴 존재 판단 신뢰도 | 0.35 | 0.1~1.0 |
| 유사도 임계값 | 등록 얼굴과 비교 시 매칭 기준 (낮을수록 관대) | 0.65 | 0.1~1.0 |
| 쿨다운 | 같은 사람 재기록 방지 시간 | 300초 | 10~3600초 |
| 자동 임베딩 보강 | 다각도 임베딩 자동 수집 여부 | ON | - |

> **유사도 임계값 조정 팁:** 인식이 잘 안 되면 0.55~0.60으로 낮추고, 다른 사람으로 오인식되면 0.70~0.75로 높인다.

**녹화**

| 항목 | 설명 | 기본값 |
|------|------|--------|
| FPS | 녹화 프레임 속도 | 15 |
| 분할 단위 | 자동 파일 분할 시간 | 30분 |
| 자동 녹화 시작 | 앱 시작 시 자동 녹화 | OFF |

**저장**

| 항목 | 설명 | 기본값 |
|------|------|--------|
| 데이터 보존 | 오래된 데이터 자동 삭제 기간 | 3일 |
| 정리 주기 | 자동 정리 실행 간격 | 1시간 |

**데모 모드** — **데모 생성**(샘플 방문자 + 방문 기록 생성), **데모 삭제**(데모 데이터만 삭제, 실제 데이터 보존).

설정 변경 후 **저장** 버튼을 누르면 `config.yaml`에 기록된다. 일부 설정은 **↻ 새로고침** 후 적용된다.

### 3-7. 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+Shift+C` | 영역 캡처 |
| `Ctrl+R` | 녹화 시작/중지 |
| `Ctrl+P` | 녹화 일시정지/재개 |
| `Ctrl+마우스 휠` | 카메라 줌 |
| `F11` | 전체화면 전환 |
| `ESC` | 영역 선택 취소 / 전체화면 해제 |

### 3-8. 문제 해결 (`MANUAL.md` §11)

**카메라가 연결되지 않음** — 증상: "카메라를 찾을 수 없습니다" 메시지. 해결: ①웹캠이 USB에 제대로 연결되었는지 확인 ②다른 프로그램(Zoom, Teams 등)이 카메라를 사용 중인지 확인 → 해당 프로그램 종료 ③설정에서 **카메라 ID**를 변경(0, 1, 2 등) ④장치 관리자에서 카메라 드라이버 상태 확인.

**얼굴 인식률이 낮음** — ①카메라 해상도를 높이기(1280x720 이상 권장) ②조명 개선(얼굴에 그림자가 지지 않도록) ③**유사도 임계값**을 0.55~0.60으로 낮추기 ④여러 각도에서 얼굴을 보여주어 임베딩 추가 학습 ⑤**이미지에서 등록** 기능으로 정면 사진 직접 등록.

**다른 사람으로 잘못 인식됨** — ①**유사도 임계값**을 0.70~0.75로 높이기 ②해당 방문자를 삭제 후 더 선명한 사진으로 재등록.

**앱이 느리거나 CPU 사용량이 높음** — ①**감지 간격**을 300~500ms로 높이기(기본 200ms) ②카메라 해상도를 낮추기(640x480) ③다른 무거운 프로그램 종료 ④백그라운드 녹화 중지.

**pip install 실패 (insightface / onnxruntime)** — ①Visual C++ Build Tools 설치 ②설치 시 **"C++를 사용한 데스크톱 개발"** 워크로드 선택 ③설치 완료 후 터미널 재시작하고 `pip install -r requirements.txt` 재시도.

**모델 다운로드 실패** — ①인터넷 연결 확인 ②방화벽/프록시 설정 확인 ③앱 종료 후 다시 실행 ④InsightFace 모델이 `~/.insightface/` 폴더에 있는지 확인.

**데이터 경로 변경** — `config.yaml`에서 `storage.data_dir`을 원하는 경로로 변경한다.

```yaml
storage:
  data_dir: "D:\\MyMonitorData"
```

> 기존 데이터를 유지하려면 이전 폴더의 내용을 새 경로로 복사한 후 변경한다.

**로그 확인** — 앱 로그: `<data_dir>\app.log`, 크래시 로그: `<data_dir>\crash.log` (기본 `data_dir` = `C:\OfficeMonitor`).

## 4. 자비스 기술자 pane으로 붙이기

- 부 탭(행정관리부) 우클릭 → "기술자 추가" → 이름에 리포 원명을 그대로 입력한다(축약 금지).
- 또는 PowerShell CLI(부서 소켓은 설치 시 발급된 번호로 바꾼다):

  ```powershell
  $env:CYS_SOCKET = '\\.\pipe\cys-dept-<N>'
  & "$env:LOCALAPPDATA\cys\cys.exe" new-surface --title "Office-Monitor" --cwd "$env:USERPROFILE\Future-Ministry\행정관리부\Office-Monitor"
  ```

- 또는 패키지의 `tools/setup.ps1 -Dept fm-admin -Apply` 로 카탈로그 선언대로 일괄 수렴시킨다.
- ★기술자는 데몬이 아니라 패인(pane) 노드다.

## 5. 대표 사용 시나리오

### 시나리오 — 교회 사무실 출입 모니터링을 하루 만에 세운다

**1단계 — 설치.** 기술자 pane에서:

```powershell
cd "$env:USERPROFILE\Future-Ministry\행정관리부\Office-Monitor"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`insightface` / `onnxruntime` 빌드 에러가 나면 Visual C++ Build Tools("C++를 사용한 데스크톱 개발" 워크로드)를 먼저 설치하고 터미널을 재시작한 뒤 다시 시도한다.

**2단계 — 데이터 경로 정하기.** 사무실 PC의 C 드라이브가 빠듯하면 `config.yaml` 을 먼저 손본다.

```yaml
storage:
  data_dir: "D:\\OfficeMonitorData"
  retention_days: 3
  cleanup_interval_hours: 1
```

**3단계 — 첫 실행.**

```powershell
python main.py
```

최초 실행에서 `buffalo_l`(약 300MB)과 YOLO11n 모델이 자동으로 내려온다. 1~5분 걸린다. 끝나면 `data_dir` 아래에 `data/monitor.db`, `data/thumbnails/`, `data/pending_faces/`, `snapshots/`, `recordings/`, `app.log` 가 자동 생성된다.

**4단계 — 카메라 확인.** 우측 패널 **카메라 정보** 카드에서 연결 상태를 본다. 안 잡히면 Zoom·Teams가 카메라를 붙잡고 있는지 먼저 확인하고, 그래도 안 되면 ⚙ 설정에서 카메라 ID를 0 → 1 → 2 로 바꿔 본다.

**5단계 — 기능 먼저 둘러보기(선택).** ⚙ 설정 → 맨 아래 **데모 모드** → **데모 생성**. 방문자관리·통계 탭에서 UI가 어떻게 도는지 확인한 뒤 **데모 삭제**로 정리한다. 실제 데이터는 건드리지 않는다.

**6단계 — 직원 등록.** 두 갈래가 있다.

- *사진으로*: 방문자관리 탭 → 상단 **+ 이미지에서 등록** → jpg/png/bmp 선택 → 자동 얼굴 검출·임베딩 추출 → 이름 입력 → 완료.
- *현장에서*: 앱을 켜 둔 채로 직원이 카메라 앞을 지나가면 미등록자로 3초간 최고 품질 프레임이 자동 캡처된다. 방문자관리 탭 → **미등록 캡처** → 각 카드의 **등록** 버튼 → 이름 입력. 이후부터 자동 인식된다.

**7단계 — 운영.** 앱을 최소화하면 트레이로 내려가 계속 감시한다. 트레이 아이콘 더블클릭으로 복원, 우클릭 메뉴에서 **열기** / **종료**.

- 등록자가 들어오면 녹색 박스 + 이름, 미등록자면 붉은 박스 + 경고음, 우측 **오늘 방문자** 타임라인에 자동 추가되고 토스트가 뜬다.
- 동일인은 쿨다운(기본 300초) 안에서는 중복 기록되지 않는다.
- 타임라인 항목을 클릭하면 썸네일 팝업이 뜨고, 미등록 방문자는 그 자리에서 **방문자로 등록**하거나 **삭제**할 수 있다.
- 등록자가 다시 잡힐 때마다 다른 각도 얼굴이면 임베딩이 자동 보강된다(최대 10개). 각도가 쌓일수록 인식률이 올라간다.

**8단계 — 인식이 안 맞을 때 튜닝.** ⚙ 설정에서 **유사도 임계값** 한 개만 만진다.

| 증상 | 조치 |
|---|---|
| 등록자인데 인식이 안 됨 | 0.55~0.60 으로 낮춤 |
| 다른 사람으로 오인식 | 0.70~0.75 로 높임 |
| CPU가 너무 튐 | 감지 간격을 300~500ms 로, 해상도를 640x480 으로 |

저장 후 헤더바 **↻ 새로고침**(엔진 재시작 + 코드 핫리로드)으로 적용한다.

**9단계 — 사건 기록 남기기.** 특정 시간대를 남겨야 하면 `Ctrl+R` 로 녹화를 시작한다. `<data_dir>\recordings\rec_YYYYMMDD_HHMMSS.avi` 로 저장되고 30분마다 자동 분할된다. 화면 일부만 필요하면 `Ctrl+Shift+C` 로 영역을 드래그해 캡처하고, 캡처 직후 뜨는 "방문자로 등록하시겠습니까?" 팝업에서 바로 등록까지 이어갈 수 있다(드래그 없이 클릭만 하면 전체 화면 캡처, `ESC` 로 취소).

**10단계 — 주간 리포트.** 통계 탭 → 기간 드롭다운에서 **최근 7일** 선택 → 요약 카드(총 방문/등록/미등록), 일별 방문자 막대 차트, 시간대별 분포, TOP 5 방문자를 확인한다. 특정 날짜만 보려면 좌측 달력에서 날짜를 클릭한다. **📥 CSV 내보내기** 로 ID·방문자ID·이름·시간·신뢰도·등록 여부를 내려받아 행정 보고에 붙인다.

**11단계 — 정리.** 퇴사·오등록이 생기면 방문자관리 → 등록된 방문자에서 **삭제**(임베딩 포함, 삭제된 방문자 탭으로 이동)한다. 실수였으면 **복구**로 되살리고, 확정이면 **영구삭제** 한다. 캡처 이미지는 휴지통 탭에서 선택 삭제 또는 전체 비우기로 처리한다. 오늘 기록을 통째로 초기화하려면 우측 패널 **초기화** 버튼을 쓴다(확인 다이얼로그가 뜬다).

**문제가 생기면** `<data_dir>\app.log` 와 `<data_dir>\crash.log` 를 먼저 본다.
