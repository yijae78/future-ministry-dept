#!/bin/bash
# install.sh — 퓨처 미니스트리(칼빈) 부서 패키지 macOS 런처 (설치기 v2 · Stage0 겸용).
#   curl -fsSL https://raw.githubusercontent.com/yijae78/future-ministry-dept/main/tools/install.sh | bash
#   bash tools/install.sh [bootstrap|install|doctor|handle <url>|receiver-register|env] [옵션]
#   (같은 파일을 「퓨처미니스트리-설치.command」 로 복사해 우클릭→열기 로도 쓴다)
# 종료코드는 fm.cli 의 것을 그대로 돌려준다: 0 성공 · 1 실패 · 2 인자/주소 · 10 자비스 없음.
# 환경변수: FM_PKG_DIR(패키지 루트 고정 · clone/pull 생략 · CI/개발자용) · FM_CI=1(완전 비대화)
# 믿는 것은 자비스 번들 런타임(python3·git)뿐 — 시스템 /usr/bin/python3·git 은 CLT 셔틀이라 절대 부르지 않는다.
# bash 3.2 호환(맥 기본 bash): 배열 확장·${var,,}·[[ =~ ]] 캡처 등 bash4 문법 금지.
set -u

DL="https://github.com/idoforgod/cys-terminal/releases/latest"
REPO="${FM_REPO_URL:-https://github.com/yijae78/future-ministry-dept}"

# ── 1. 자비스 번들 런타임 ──────────────────────────────────────────────────────
ROOT="${FM_JAVIS_ROOT:-}"
if [ -z "$ROOT" ]; then
  if [ -x "/Applications/cys.app/Contents/MacOS/cys" ]; then ROOT="/Applications/cys.app"
  elif [ -x "$HOME/Applications/cys.app/Contents/MacOS/cys" ]; then ROOT="$HOME/Applications/cys.app"
  else ROOT="/Applications/cys.app"; fi
fi
PY="$ROOT/Contents/Resources/runtime/python/bin/python3"
GIT="$ROOT/Contents/Resources/runtime/git/bin/git"
if [ ! -x "$PY" ]; then
  echo "자비스가 아직 설치되지 않았습니다 → 내려받기: $DL"
  if [ "${FM_CI:-}" != "1" ] && [ -t 1 ]; then /usr/bin/open "$DL" 2>/dev/null || true; fi
  exit 10
fi
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 GIT_TERMINAL_PROMPT=0

# ── 2. 패키지 위치 (fm/cli.py 가 이 파일 옆에 있으면 패키지 안에서 실행 중) ────
CLI=""
self="${BASH_SOURCE[0]:-}"
if [ -n "$self" ] && [ -f "$self" ]; then
  here="$(cd "$(dirname "$self")" && pwd)"
  if [ -f "$here/fm/cli.py" ]; then CLI="$here/fm/cli.py"; fi
fi
if [ -z "$CLI" ]; then
  if [ -n "${FM_PKG_DIR:-}" ]; then
    CLI="$FM_PKG_DIR/tools/fm/cli.py"
  else
    # 단독 실행(curl | bash · Stage0): 번들 git 으로 패키지를 받는다
    PKG="$HOME/Future-Ministry/_pkg/future-ministry-dept"
    if [ -d "$PKG/.git" ]; then
      echo "[pkg] 최신화: $PKG"
      "$GIT" -C "$PKG" pull --ff-only || echo "[pkg] 최신화는 건너뜁니다(네트워크 없음?) — 받아 둔 판으로 진행합니다"
    else
      if [ -e "$PKG" ]; then
        echo "[pkg] 지난번에 받다 만 폴더를 옆으로 치웁니다"
        mv "$PKG" "$PKG.broken-$(date +%Y%m%d-%H%M%S)"
      fi
      mkdir -p "$(dirname "$PKG")"
      echo "[pkg] 받기: $REPO → $PKG"
      "$GIT" clone "$REPO" "$PKG" || { echo "[멈춤] 패키지를 받아오지 못했습니다 — 인터넷 연결을 확인하고 다시 실행해 주세요."; exit 1; }
    fi
    CLI="$PKG/tools/fm/cli.py"
  fi
fi
if [ ! -f "$CLI" ]; then echo "[멈춤] 설치기 파일을 찾지 못했습니다: $CLI"; exit 1; fi

# ── 3. fm.cli 실행 (서브커맨드 없음 = bootstrap) ───────────────────────────────
if [ $# -eq 0 ]; then
  exec "$PY" -X utf8 "$CLI" bootstrap
fi
exec "$PY" -X utf8 "$CLI" "$@"
