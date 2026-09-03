"""cys-install://(dept|tech)/<id> 수신 처리 (스펙 §5 핸들러).

안전 원칙(구 cys-install-handler.ps1 계승):
  · URL 의 kind/key 만 읽고, 그 밖의 문자열은 어떤 명령에도 넣지 않는다(인젝션 차단).
  · key 는 소문자·숫자·하이픈 슬러그만 통과 — 화이트리스트 불일치는 로그에 남기고 exit 2.
  · 실행 즉시 새 로그 파일을 만든다(`~/.cys/fm-install/logs/<ts>-handle.log` — CI 가 실행 감지에 쓴다).
  · 패키지 최신화(번들 git · pull --ff-only)는 실패해도 설치를 계속한다(오프라인 허용). FM_PKG_DIR 이면 생략.
  · 결과 알림: Windows = 콘솔 배너 + 로그, macOS = display notification.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from . import resolve
from .log import Log
from .steps import make_ctx, run_all, run_capture, tail

URL_RE = re.compile(r"^cys-install://(dept|tech)/([a-z0-9][a-z0-9-]*)/?$")


def parse_url(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    m = URL_RE.match(url.strip())
    return (m.group(1), m.group(2)) if m else None


def pull_package(pkg_dir: Path, log: Log, root: Path | None, home: Path, dry_run: bool) -> None:
    """번들 git 으로 pull --ff-only. 실패는 경고(오프라인 허용)."""
    if os.environ.get("FM_PKG_DIR"):
        log.info("FM_PKG_DIR 지정 — 패키지 최신화(pull)를 생략합니다")
        return
    if not (pkg_dir / ".git").exists():
        log.info("패키지가 git 리포가 아니라 최신화를 생략합니다")
        return
    if not root:
        return
    git = resolve.layout(root)["git"]
    if not Path(git).exists():
        log.warn("번들 git 이 없어 패키지 최신화를 생략합니다")
        return
    log.act(f"패키지 최신화: git -C {pkg_dir} pull --ff-only")
    if dry_run:
        return
    rc, out, err = run_capture([str(git), "-C", str(pkg_dir), "pull", "--ff-only"],
                               resolve.env_for_tools(root, home), timeout=180)
    if rc != 0:
        log.warn(f"최신화는 건너뜁니다(네트워크 없음?) — 받아 둔 판으로 진행합니다: {tail(err or out, 2)}")
    else:
        log.ok(f"최신화 완료: {tail(out, 1) or 'up to date'}")


def notify(ok: bool, message: str, log_path: Path | None = None) -> None:
    if resolve.IS_MAC:
        title = "자비스 설치"
        body = message.replace('"', "'")
        try:
            subprocess.run(["/usr/bin/osascript", "-e", f'display notification "{body}" with title "{title}"'],
                           capture_output=True, timeout=20)
        except Exception:
            pass
        if not ok and log_path:
            try:
                subprocess.run(["/usr/bin/open", str(log_path)], capture_output=True, timeout=20)
            except Exception:
                pass
    # Windows: 콘솔 배너(run_all 의 최종 배너) + 로그가 곧 알림이다.


def handle(url: str | None, pkg_dir: Path, *, dry_run: bool = False, ci: bool = False) -> int:
    home = resolve.cys_home()
    log = Log(home, "handle", dry_run=dry_run, ci=ci)
    log.raw("=" * 52)
    log.raw(" 원클릭 설치 — 자비스가 받아서 진행합니다")
    log.raw(f"  받은 주소: {url!r}")
    log.raw(" 이 창은 스스로 진행합니다 — 끝날 때까지 닫지 말아 주세요.")
    log.raw("=" * 52)
    parsed = parse_url(url)
    if not parsed:
        log.fail(f"알 수 없는 설치 주소입니다: {url!r} — 안내 화면의 설치 버튼으로 다시 시도해 주세요")
        log.banner(False, "주소 형식")
        log.close()
        return 2
    kind, key = parsed
    root = resolve.javis_root()
    if root is None:
        log.fail(resolve.missing_javis_message())
        log.banner(False, "자비스 없음")
        log.close()
        return 10
    pull_package(pkg_dir, log, root, home, dry_run)
    try:
        from . import manifest as mf_mod
        mf = mf_mod.load(pkg_dir)
    except Exception as e:
        log.fail(f"패키지 manifest 를 읽지 못했습니다: {e} — 설치 파일을 다시 실행해 패키지를 새로 받아 주세요")
        log.banner(False, "manifest")
        log.close()
        return 1
    dept = only = None
    if kind == "dept":
        d = mf.dept(key)
        if not d:
            log.fail(f"이 패키지에 없는 부서입니다: {key} (가능: {', '.join(x.key for x in mf.departments)})")
            log.banner(False, "대상 없음")
            log.close()
            return 2
        dept = None if d.tier == 0 else key   # 루트 부서 = 전체 설치
    else:
        if not mf.find_tech(key):
            log.fail(f"이 패키지에 없는 기술자입니다: {key} (가능: {', '.join(mf.tech_ids())})")
            log.banner(False, "대상 없음")
            log.close()
            return 2
        only = [key]
    log.info(f"대상: {kind} / {key}" + (f"  (--dept {dept})" if dept else "") + (f"  (--only {key})" if only else ""))
    try:
        ctx = make_ctx(pkg_dir, sub="handle", dry_run=dry_run, ci=ci, dept=dept, only=only, log=log)
    except ValueError as e:
        log.fail(str(e))
        log.banner(False, "대상 없음")
        log.close()
        return 2
    rc = run_all(ctx)
    notify(rc == 0, "설치가 끝났습니다. 자비스에서 부서 탭을 확인해 주세요." if rc == 0
           else "설치가 끝나지 않았습니다 — 로그를 확인해 주세요.", log.path)
    log.close()
    return rc
