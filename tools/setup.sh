#!/usr/bin/env bash
# Future Ministry 부서 설치기 — 맥용 런처.
# bash 재구현이 아니라 setup.ps1 에 그대로 위임한다 (로직을 1벌로 유지한다 · BRIEF T4-B-3 B안).
# 인자는 Windows 와 똑같이 쓴다:  ./tools/setup.sh -Dept future-ministry -Only frar -Apply
set -euo pipefail

if ! command -v pwsh >/dev/null 2>&1; then
  echo "PowerShell 7(pwsh)이 필요하다 — 이 설치기는 pwsh 로 돌아간다." >&2
  echo "  설치:  brew install --cask powershell" >&2
  exit 1
fi

# ★$0 가 아니라 ${BASH_SOURCE[0]} 를 쓰는 이유: `bash tools/setup.sh` 로 부르면 $0 가 상대경로라
#  cd 이후 깨진다. BASH_SOURCE 는 맥 기본 bash 3.2 에도 있다.
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ps1="$here/setup.ps1"
[ -f "$ps1" ] || { echo "setup.ps1 을 찾을 수 없다: $ps1" >&2; exit 1; }

# ★"$@" 가 아니라 ${1+"$@"} 인 이유: 맥 기본 bash 3.2 는 set -u 상태에서 인자가 0개일 때
#  "$@" 를 unbound variable 로 판정한다. 이 형태는 인자가 없으면 아무것도 전개하지 않는다.
exec pwsh -NoProfile -File "$ps1" ${1+"$@"}
