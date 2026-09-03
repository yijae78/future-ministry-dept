"""fm 설치기 v2 진입점.

  python3 -X utf8 tools/fm/cli.py <bootstrap|install|doctor|handle <url>|receiver-register|env> [--dry-run]
  python3 -m fm.cli ...   (tools/ 를 cwd 또는 sys.path 에 둔 경우)

종료코드: 0 성공 · 1 실패 있음 · 2 잘못된 인자/주소 · 10 자비스 미설치
환경변수: FM_PKG_DIR(패키지 루트 고정·clone/pull 생략) · FM_CI=1(완전 비대화) · FM_HOME / FM_JAVIS_ROOT(테스트)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if __package__ in (None, ""):  # `python tools/fm/cli.py` 직접 실행 지원
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "fm"  # noqa: A001

from . import __version__, resolve  # noqa: E402
from .log import Log  # noqa: E402

DEFAULT_REPO = "https://github.com/yijae78/future-ministry-dept"
SELF_PKG_DIR = Path(__file__).resolve().parent.parent.parent  # tools/fm/cli.py → 패키지 루트


def _setup_console() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def is_ci() -> bool:
    if os.environ.get("FM_CI") == "1":
        return True
    try:
        return not sys.stdin.isatty()
    except Exception:
        return True


def default_pkg_dir() -> Path:
    return resolve.cys_home() / "Future-Ministry" / "_pkg" / "future-ministry-dept"


def pkg_dir_for(args) -> Path:
    """install/doctor/handle/receiver-register 의 패키지 루트: --pkg-dir → FM_PKG_DIR → 이 파일이 든 패키지."""
    if getattr(args, "pkg_dir", None):
        return Path(args.pkg_dir)
    env = os.environ.get("FM_PKG_DIR")
    if env:
        return Path(env)
    return SELF_PKG_DIR


def open_url(url: str, ci: bool) -> None:
    if ci:
        return
    try:
        if not sys.stdout.isatty():
            return
    except Exception:
        return
    try:
        if resolve.IS_WIN:
            os.startfile(url)  # type: ignore[attr-defined]
        elif resolve.IS_MAC:
            import subprocess
            subprocess.Popen(["/usr/bin/open", url])
    except Exception:
        pass


def maybe_pause(ci: bool) -> None:
    if ci or os.environ.get("FM_NO_PAUSE") == "1":
        return
    try:
        if not sys.stdin.isatty():
            return
        sys.stderr.write("\n엔터를 누르면 창이 닫힙니다 ")
        sys.stderr.flush()
        input()
    except Exception:
        pass


def require_javis(ci: bool) -> Path | None:
    root = resolve.javis_root()
    if root is None:
        print(resolve.missing_javis_message())
        open_url(resolve.DOWNLOAD_URL, ci)
    return root


# ── env ──────────────────────────────────────────────────────────────────────
def cmd_env(args) -> int:
    _setup_console()
    hr = resolve.home_report()
    o = resolve.os_summary()
    print(f"fm 설치기 v{__version__} · {o['os']} · {o['platform']} · {o['arch']}")
    print(f"HOME(cys)    : {hr['cys_home']}" + ("  [FM_HOME 강제]" if hr["forced"] else ""))
    if not hr["match"]:
        print(f"HOME(python) : {hr['python_home']}  ← 다르다 → cys 쪽 홈을 채택")
    root = resolve.javis_root()
    print(f"자비스 루트  : {root or '(없음)'}")
    if root is None:
        print(resolve.missing_javis_message())
        return 10
    print("PATH 선두    : " + os.pathsep.join(resolve.path_prepend(root)))
    print(f"cys-dept     : {resolve.cys_dept_path()}  {'있음' if resolve.cys_dept_path().exists() else '없음(→ cys init-pack)'}")
    bad = 0
    for p in resolve.probe(root):
        mark = "OK " if p["ok"] else ("-- " if not p["required"] else "!! ")
        print(f"  {mark}{p['name']:<8} {p['version'] or '-':<12} {p['path']}{('  ' + p['error']) if p['error'] else ''}")
        if p["required"] and not p["ok"]:
            bad += 1
    return 1 if bad else 0


# ── bootstrap ────────────────────────────────────────────────────────────────
def _ensure_package(log: Log, root: Path, home: Path, dry_run: bool) -> Path | None:
    """FM_PKG_DIR 없으면 기본 위치에 번들 git 으로 clone/pull. 돌려주는 값 = 패키지 루트."""
    from .steps import now_ts, run_capture, tail
    env_pkg = os.environ.get("FM_PKG_DIR")
    if env_pkg:
        p = Path(env_pkg)
        log.info(f"FM_PKG_DIR → {p} (clone/pull 생략)")
        return p if (p / "manifest.json").exists() else _fail(log, f"FM_PKG_DIR 에 manifest.json 이 없습니다: {p}")
    pkg = default_pkg_dir()
    git = resolve.layout(root)["git"]
    env = resolve.env_for_tools(root, home)
    repo = os.environ.get("FM_REPO_URL", DEFAULT_REPO)
    if (pkg / ".git").exists():
        log.act(f"패키지 최신화: git -C {pkg} pull --ff-only")
        if not dry_run:
            rc, out, err = run_capture([str(git), "-C", str(pkg), "pull", "--ff-only"], env, timeout=180)
            if rc != 0:
                log.warn(f"최신화는 건너뜁니다(네트워크 없음?) — 받아 둔 판으로 진행합니다: {tail(err or out, 2)}")
            else:
                log.ok(f"최신화: {tail(out, 1) or 'up to date'}")
        return pkg
    if pkg.exists():
        broken = Path(str(pkg) + f".broken-{now_ts()}")
        log.act(f"지난번에 받다 만 폴더를 옆으로 치웁니다: {pkg} → {broken.name}")
        if not dry_run:
            import shutil
            shutil.move(str(pkg), str(broken))
    log.act(f"패키지 받기: git clone {repo} → {pkg}")
    if dry_run:
        # 드라이런은 받지 않는다 — 이 파일이 든 패키지로 계획을 세운다.
        return SELF_PKG_DIR if (SELF_PKG_DIR / "manifest.json").exists() else None
    pkg.parent.mkdir(parents=True, exist_ok=True)
    rc, out, err = run_capture([str(git), "clone", repo, str(pkg)], env, timeout=600)
    if rc != 0 or not (pkg / "manifest.json").exists():
        return _fail(log, f"패키지를 받아오지 못했습니다(exit={rc}) — 인터넷 연결을 확인하고 다시 실행해 주세요: {tail(err or out, 2)}")
    log.ok(f"패키지 위치: {pkg}")
    return pkg


def _fail(log: Log, msg: str) -> None:
    log.fail(msg)
    return None


def cmd_bootstrap(args) -> int:
    _setup_console()
    ci = is_ci()
    dry = bool(args.dry_run)
    home = resolve.cys_home()
    log = Log(home, "bootstrap", dry_run=dry, ci=ci)
    log.raw("=" * 52)
    log.raw(" 퓨처 미니스트리 설치를 시작합니다")
    log.raw(" 이 창은 스스로 진행합니다 — 끝날 때까지 닫지 말아 주세요.")
    log.raw(" (중간에 꺼져도 괜찮습니다. 다시 실행하면 이어서 진행됩니다.)")
    log.raw("=" * 52)
    root = require_javis(ci)
    if root is None:
        log.fail(resolve.missing_javis_message())
        log.banner(False, "자비스 없음")
        log.close()
        maybe_pause(ci)
        return 10
    pkg = _ensure_package(log, root, home, dry)
    if pkg is None:
        log.banner(False, "패키지")
        log.desktop_copy()
        log.close()
        maybe_pause(ci)
        return 1
    from .steps import make_ctx, run_all
    try:
        ctx = make_ctx(pkg, sub="bootstrap", dry_run=dry, ci=ci, deps=(False if args.no_deps else None), log=log)
    except Exception as e:
        log.fail(f"패키지 manifest 오류: {e}")
        log.banner(False, "manifest")
        log.close()
        maybe_pause(ci)
        return 1
    rc = run_all(ctx)
    log.close()
    maybe_pause(ci)
    return rc


# ── install ──────────────────────────────────────────────────────────────────
def cmd_install(args) -> int:
    _setup_console()
    ci = is_ci()
    from .manifest import parse_only
    from .steps import make_ctx, run_all
    root = require_javis(ci)
    if root is None:
        return 10
    deps = True if args.deps else (False if args.no_deps else None)
    try:
        ctx = make_ctx(pkg_dir_for(args), sub="install", dry_run=bool(args.dry_run), ci=ci, dept=args.dept,
                       only=parse_only(args.only), deps=deps)
    except ValueError as e:
        print(f"[인자 오류] {e}")
        return 2
    except Exception as e:
        print(f"[패키지 오류] {e}")
        return 1
    rc = run_all(ctx)
    ctx.log.close()
    return rc


# ── doctor ───────────────────────────────────────────────────────────────────
def cmd_doctor(args) -> int:
    _setup_console()
    ci = is_ci()
    from . import doctor
    from .manifest import parse_only
    from .steps import make_ctx, step0_selfdiag
    root = require_javis(ci)
    if root is None:
        return 10
    try:
        ctx = make_ctx(pkg_dir_for(args), sub="doctor", dry_run=bool(args.dry_run), ci=ci, dept=args.dept,
                       only=parse_only(args.only))
    except ValueError as e:
        print(f"[인자 오류] {e}")
        return 2
    except Exception as e:
        print(f"[패키지 오류] {e}")
        return 1
    step0_selfdiag(ctx)
    result = doctor.run(ctx)
    doctor.report(ctx, result)
    doctor.write_result(ctx, result)
    ctx.log.close()
    return 0 if result["ok"] else 1


# ── handle ───────────────────────────────────────────────────────────────────
def cmd_handle(args) -> int:
    _setup_console()
    ci = is_ci()
    from .handler import handle
    rc = handle(args.url, pkg_dir_for(args), dry_run=bool(args.dry_run), ci=ci)
    maybe_pause(ci)
    return rc


# ── receiver-register ────────────────────────────────────────────────────────
def cmd_receiver_register(args) -> int:
    _setup_console()
    ci = is_ci()
    from . import receiver
    from .steps import make_ctx
    root = require_javis(ci)
    if root is None:
        return 10
    try:
        ctx = make_ctx(pkg_dir_for(args), sub="receiver-register", dry_run=bool(args.dry_run), ci=ci)
    except Exception as e:
        print(f"[패키지 오류] {e}")
        return 1
    ctx.log.step(10, "원클릭 수신부(cys-install://) 등록")
    st, detail = receiver.register(ctx)
    ctx.log.close()
    return 0 if st != "failed" else 1


# ── main ─────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fm", description="퓨처 미니스트리 부서 패키지 설치기 v2")
    p.add_argument("--dry-run", action="store_true", help="쓰기·실행 없이 계획만 (실제 홈에 아무것도 쓰지 않는다)")
    p.add_argument("--pkg-dir", help="패키지 루트(기본: FM_PKG_DIR → 이 파일이 든 패키지)")
    sub = p.add_subparsers(dest="cmd")
    b = sub.add_parser("bootstrap", help="자기진단 → 패키지 clone/pull → 전체 설치 → 수신부 → doctor → 배너")
    b.add_argument("--no-deps", action="store_true")
    b.set_defaults(fn=cmd_bootstrap)
    i = sub.add_parser("install", help="설치(전체 또는 --dept/--only 로 좁힘)")
    i.add_argument("--dept", help="대상 부서 키")
    i.add_argument("--only", action="append", help="기술자 id (콤마 구분·반복 가능)")
    g = i.add_mutually_exclusive_group()
    g.add_argument("--deps", action="store_true", help="의존성 설치를 명시적으로 켠다(기본 on)")
    g.add_argument("--no-deps", action="store_true", help="의존성 설치를 끈다")
    i.set_defaults(fn=cmd_install)
    d = sub.add_parser("doctor", help="실물 검사 → last-result.json")
    d.add_argument("--dept")
    d.add_argument("--only", action="append")
    d.set_defaults(fn=cmd_doctor)
    h = sub.add_parser("handle", help="cys-install://(dept|tech)/<id> 처리")
    h.add_argument("url", nargs="?")
    h.set_defaults(fn=cmd_handle)
    r = sub.add_parser("receiver-register", help="수신부만 등록")
    r.set_defaults(fn=cmd_receiver_register)
    e = sub.add_parser("env", help="자비스 런타임 해석 결과(실측)")
    e.set_defaults(fn=cmd_env)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # 전역 옵션(--dry-run · --pkg-dir)이 서브커맨드 뒤에 와도 받는다: `install --dry-run --pkg-dir X`
    globals_: list[str] = []
    rest: list[str] = []
    it = iter(argv)
    for a in it:
        if a == "--dry-run":
            globals_.append(a)
        elif a == "--pkg-dir":
            globals_ += [a, next(it, "")]
        elif a.startswith("--pkg-dir="):
            globals_.append(a)
        else:
            rest.append(a)
    if not rest or (rest[0].startswith("-") and rest[0] not in ("-h", "--help")):
        rest = ["bootstrap"] + rest  # 서브커맨드 생략 = bootstrap (런처 더블클릭)
    args = build_parser().parse_args(globals_ + rest)
    if not getattr(args, "fn", None):
        build_parser().print_help()
        return 2
    return int(args.fn(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
