"""cys-install:// 수신부 등록 (스펙 §3-10 · §5).

Windows: HKCU\\Software\\Classes\\cys-install (관리자 불필요) →
         "<python3 절대경로>" -X utf8 "<pkg>\\tools\\fm\\cli.py" handle "%1"   (PATH 무의존)
macOS  : ~/Applications/자비스 설치 수신부.app (osacompile 로컬 생성 → 격리 없음 → 경고 없음)
         Info.plist CFBundleURLTypes(cys-install) + lsregister -f.
         AppleScript: on open location → do shell script "/bin/bash" "<pkg>/tools/install.sh" handle <url quoted form>
OS 전용 코드는 함수 안에서만 import 한다(다른 OS 에서 import 오류 없음).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from . import resolve
from .steps import Ctx, run_capture, tail

SCHEME = "cys-install"
WIN_KEY = r"Software\Classes\cys-install"
# v2 명령줄 형태: "<python3>" -X utf8 "<...cli.py>" handle "%1"
WIN_CMD_RE = re.compile(r'^"([^"]+)" -X utf8 "([^"]+[\\/]cli\.py)" handle "%1"$')
MAC_APP_NAME = "자비스 설치 수신부.app"
MAC_BUNDLE_ID = "fm.cys-install.receiver"
LSREGISTER = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
PLISTBUDDY = "/usr/libexec/PlistBuddy"

APPLESCRIPT = '''-- 자비스 설치 수신부 (fm 설치기 v2 가 생성) — cys-install:// 를 받아 Terminal 에서 install.sh handle 을 연다.
-- 설치 진행이 보이도록: 임시 .command 파일을 ~/.cys/fm-install/ 아래에 쓰고 `open -a Terminal` 로 연다
-- (Automation 권한 프롬프트 없음 · 로컬 생성 파일이라 격리 없음). 끝나면 fm.cli 가 display notification 을 띄운다.
on open location theURL
\tset sh to "{sh}"
\tset workDir to "{workdir}"
\ttry
\t\tset stamp to do shell script "date +%Y%m%d-%H%M%S-$$"
\t\tset cmdFile to workDir & "/handle-" & stamp & ".command"
\t\tset body to "#!/bin/bash" & linefeed & "\\"/bin/bash\\" " & quoted form of sh & " handle " & quoted form of theURL & linefeed & "read -p \\"엔터를 누르면 창이 닫힙니다\\"" & linefeed
\t\tdo shell script "mkdir -p " & quoted form of workDir & " && printf '%s' " & quoted form of body & " > " & quoted form of cmdFile & " && chmod +x " & quoted form of cmdFile
\t\tdo shell script "open -a Terminal " & quoted form of cmdFile
\ton error errMsg number errNum
\t\tdisplay notification "설치 창을 열지 못했습니다 — 로그 폴더를 엽니다." with title "자비스 설치"
\t\ttry
\t\t\tdo shell script "/usr/bin/open " & quoted form of "{logs}"
\t\tend try
\tend try
end open location

on run
\tdisplay notification "이 앱은 설치 안내 화면의 설치 버튼이 부릅니다." with title "자비스 설치"
end run
'''


# ── 공통 ─────────────────────────────────────────────────────────────────────
def cli_path(ctx: Ctx) -> Path:
    return ctx.pkg_dir / "tools" / "fm" / "cli.py"


def sh_path(ctx: Ctx) -> Path:
    return ctx.pkg_dir / "tools" / "install.sh"


def register(ctx: Ctx) -> tuple[str, str]:
    if os.environ.get("FM_HOME"):
        return _sandbox_register(ctx)
    if resolve.IS_WIN:
        return _win_register(ctx)
    if resolve.IS_MAC:
        return _mac_register(ctx)
    ctx.log.warn("이 OS 에는 수신부 등록을 지원하지 않습니다(Windows·macOS 만)")
    return "skipped", "unsupported-os"


def status(ctx: Ctx) -> dict:
    if os.environ.get("FM_HOME"):
        return _sandbox_status(ctx)
    if resolve.IS_WIN:
        return _win_status(ctx)
    if resolve.IS_MAC:
        return _mac_status(ctx)
    return {"ok": False, "detail": "지원하지 않는 OS"}


# ── 샌드박스(FM_HOME) — 레지스트리·LaunchServices 는 사용자 전역이라 테스트에서 절대 건드리지 않는다 ──
def _sandbox_file(ctx: Ctx) -> Path:
    return ctx.home / ".cys" / "fm-install" / "receiver-sandbox.json"


def _sandbox_register(ctx: Ctx) -> tuple[str, str]:
    want = win_command(ctx) if resolve.IS_WIN else f'/bin/bash "{sh_path(ctx)}" handle <url>'
    f = _sandbox_file(ctx)
    cur = None
    if f.exists():
        try:
            cur = json.loads(f.read_text(encoding="utf-8")).get("command")
        except Exception:
            cur = None
    if cur == want:
        ctx.log.same(f"(샌드박스) 이미 등록됨: {want}")
        return "skipped", "unchanged"
    ctx.log.act(f"(샌드박스 · FM_HOME) 수신부 등록 기록 → {f}: {want}")
    if ctx.dry_run:
        return "done", "planned"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"command": want}, ensure_ascii=False), encoding="utf-8")
    return "done", want


def _sandbox_status(ctx: Ctx) -> dict:
    f = _sandbox_file(ctx)
    if not f.exists():
        return {"ok": False, "detail": "(샌드박스) 등록되어 있지 않습니다"}
    try:
        cur = json.loads(f.read_text(encoding="utf-8")).get("command", "")
    except Exception:
        return {"ok": False, "detail": "(샌드박스) 기록을 읽지 못했습니다"}
    q = re.findall(r'"([^"]+)"', cur)
    if resolve.IS_WIN and (len(q) < 2 or not Path(q[0]).exists() or not Path(q[1]).exists()):
        return {"ok": False, "detail": f"(샌드박스) 명령줄이 가리키는 파일이 없습니다: {cur}"}
    return {"ok": True, "detail": f"(샌드박스) 등록됨: {cur}"}


# ── Windows ──────────────────────────────────────────────────────────────────
def win_command(ctx: Ctx) -> str:
    py = ctx.lay.get("python3")
    return f'"{py}" -X utf8 "{cli_path(ctx)}" handle "%1"'


def _win_read() -> str | None:
    try:
        import winreg  # type: ignore
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_KEY + r"\shell\open\command") as k:
            v, _ = winreg.QueryValueEx(k, "")
            return str(v)
    except OSError:
        return None


def _win_register(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    want = win_command(ctx)
    cur = _win_read()
    if cur == want:
        log.same(f"이미 등록됨: {want}")
        return "skipped", "unchanged"
    log.act(f"HKCU\\{WIN_KEY} → {want}" + (f"  (기존: {cur})" if cur else ""))
    if ctx.dry_run:
        return "done", "planned"
    try:
        import winreg  # type: ignore
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_KEY) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "URL:cys-install Protocol")
            winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_KEY + r"\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, want)
    except OSError as e:
        log.fail(f"수신부 등록 실패(레지스트리 쓰기): {e}")
        return "failed", str(e)
    if _win_read() != want:
        log.fail("수신부 등록을 확인하지 못했습니다(다시 읽은 값이 다릅니다)")
        return "failed", "verify"
    log.ok("등록 완료 — 안내 화면의 설치 버튼이 원클릭으로 작동합니다")
    return "done", want


def _win_status(ctx: Ctx) -> dict:
    cur = _win_read()
    if not cur:
        return {"ok": False, "detail": "등록되어 있지 않습니다"}
    m = WIN_CMD_RE.match(cur)
    if not m:  # v1(powershell → cys-install-handler.ps1) 등 다른 형태 — 설치를 다시 실행하면 v2 로 재등록된다
        return {"ok": False, "detail": f"구형 등록(v1)입니다 — 재등록 필요: {cur}"}
    py, cli = Path(m.group(1)), Path(m.group(2))
    if not py.exists():
        return {"ok": False, "detail": f"등록된 python 이 없습니다: {py}"}
    if not cli.exists():
        return {"ok": False, "detail": f"등록된 설치기 파일이 없습니다: {cli}"}
    same = _same(cli, cli_path(ctx))
    return {"ok": True, "detail": f"등록됨: {cur}" + ("" if same else "  (다른 패키지 위치를 가리킵니다)")}


def _same(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except Exception:
        return str(a).lower() == str(b).lower()


# ── macOS ────────────────────────────────────────────────────────────────────
def mac_app_path(ctx: Ctx) -> Path:
    return ctx.home / "Applications" / MAC_APP_NAME


def _as_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def mac_script(ctx: Ctx) -> str:
    work = ctx.home / ".cys" / "fm-install"
    return APPLESCRIPT.format(sh=_as_str(str(sh_path(ctx))), workdir=_as_str(str(work)),
                              logs=_as_str(str(work / "logs")))


def _mac_marker(app: Path) -> Path:
    return app / "Contents" / "Resources" / "fm-receiver.json"


def _mac_register(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    app = mac_app_path(ctx)
    script = mac_script(ctx)
    digest = hashlib.sha256(script.encode("utf-8")).hexdigest()[:16]
    marker = _mac_marker(app)
    fresh = False
    if app.exists() and marker.exists():
        try:
            fresh = json.loads(marker.read_text(encoding="utf-8")).get("sha") == digest
        except Exception:
            fresh = False
    if fresh:
        log.same(f"수신부 앱 이미 최신: {app}")
        if not ctx.dry_run:
            run_capture([LSREGISTER, "-f", str(app)], resolve.env_for_tools(ctx.root, ctx.home), timeout=60)
        return "skipped", "unchanged"
    log.act(f"osacompile → {app} (CFBundleURLTypes {SCHEME}) + lsregister -f")
    if ctx.dry_run:
        return "done", "planned"
    env = resolve.env_for_tools(ctx.root, ctx.home)
    try:
        app.parent.mkdir(parents=True, exist_ok=True)
        if app.exists():
            import shutil
            shutil.rmtree(app, ignore_errors=True)
        with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False, encoding="utf-8") as fh:
            fh.write(script)
            src = fh.name
        rc, out, err = run_capture(["/usr/bin/osacompile", "-o", str(app), src], env, timeout=120)
        if rc != 0 or not (app / "Contents" / "Info.plist").exists():
            log.fail(f"수신부 앱 생성 실패(osacompile exit={rc}): {tail(err or out)}")
            return "failed", "osacompile"
        pl = str(app / "Contents" / "Info.plist")
        cmds = [
            f"Set :CFBundleIdentifier {MAC_BUNDLE_ID}", f"Add :CFBundleIdentifier string {MAC_BUNDLE_ID}",
            "Delete :CFBundleURLTypes", "Add :CFBundleURLTypes array", "Add :CFBundleURLTypes:0 dict",
            f"Add :CFBundleURLTypes:0:CFBundleURLName string fm.{SCHEME}",
            "Add :CFBundleURLTypes:0:CFBundleURLSchemes array",
            f"Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string {SCHEME}",
        ]
        for c in cmds:
            run_capture([PLISTBUDDY, "-c", c, pl], env, timeout=30)  # Set/Add·Delete 는 한쪽이 실패해도 정상
        chk = subprocess.run([PLISTBUDDY, "-c", "Print :CFBundleURLTypes:0:CFBundleURLSchemes:0", pl],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if chk.stdout.strip() != SCHEME:
            log.fail(f"Info.plist 에 URL 스킴을 쓰지 못했습니다: {tail(chk.stderr or chk.stdout)}")
            return "failed", "plist"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"sha": digest, "pkg_dir": str(ctx.pkg_dir), "sh": str(sh_path(ctx))},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
        rc, out, err = run_capture([LSREGISTER, "-f", str(app)], env, timeout=60)
        if rc != 0:
            log.warn(f"lsregister 가 비정상 종료(exit={rc}) — 앱을 한 번 열면 등록됩니다: {tail(err or out)}")
    except Exception as e:
        log.fail(f"수신부 앱 생성 중 오류: {type(e).__name__}: {e}")
        return "failed", str(e)
    log.ok(f"수신부 앱 등록 완료: {app}")
    return "done", str(app)


def _mac_status(ctx: Ctx) -> dict:
    app = mac_app_path(ctx)
    if not app.exists():
        return {"ok": False, "detail": f"수신부 앱이 없습니다: {app}"}
    try:
        r = subprocess.run([LSREGISTER, "-dump"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        dump = r.stdout
    except Exception as e:
        return {"ok": False, "detail": f"lsregister -dump 실패: {e}"}
    if SCHEME not in dump:
        return {"ok": False, "detail": "LaunchServices 에 cys-install 스킴이 없습니다(lsregister -f 필요)"}
    return {"ok": True, "detail": f"등록됨: {app}"}
