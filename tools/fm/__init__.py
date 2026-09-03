"""fm — 퓨처 미니스트리(칼빈) 부서 패키지 설치기 v2 (Python 정본 · 1벌).

구조·계약: docs/install-v2-spec.md
  cli.py       서브커맨드 진입점 (bootstrap | install | doctor | handle | receiver-register | env)
  resolve.py   자비스 런타임 해석기(OS별 절대경로) + 실행 환경(PATH·env)
  manifest.py  manifest.json 로드·검증
  log.py       UTF-8 로그(파일·콘솔) · 바탕화면 사본 · 자기진단 헤더 · 최종 배너
  steps.py     설치 단계 0~11 (멱등)
  doctor.py    실물 검사 + last-result.json
  receiver.py  cys-install:// 수신부 등록 (Windows HKCU / macOS osacompile 앱)
  handler.py   cys-install://(dept|tech)/<id> 처리

표준 라이브러리만 사용한다(외부 패키지 금지 · Python 3.12 · 번들 python3 로 실행).
"""

__version__ = "2.0.0"
