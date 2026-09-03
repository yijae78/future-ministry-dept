"""자비스 런타임 해석기 — 유일한 진실 (스펙 §2).

원칙: 유저 환경(PATH·시스템 Git·brew·pwsh·코드페이지)을 믿지 않는다. 아는 것은 자비스 설치 위치 하나다.
모든 실행체는 절대경로로 해석하고, 관문(`fm env`)은 그 절대경로 각각을 실제로 실행(--version)한다.

테스트용 환경변수
  FM_HOME        — 홈 디렉터리 강제(샌드박스). cys 가 쓰는 홈 대신 이 값을 홈으로 본다.
  FM_JAVIS_ROOT  — 자비스 앱 루트 강제(스텁 루트).
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
OS_KEY = "win" if IS_WIN else ("mac" if IS_MAC else "other")

DOWNLOAD_URL = "https://github.com/idoforgod/cys-terminal/releases/latest"
MAC_BUNDLE_ID_HINTS = ("cys",)  # mdfind 폴백 — 번들 id 에 'cys' 가 포함된 앱 중 Contents/MacOS/cys 보유본만 채택

# 필수 5종(설치 관문) + 선택 2종(의존성 설치에만 필요)
CORE_NAMES = ("cys", "cysd", "python3", "git", "bash")
EXTRA_NAMES = ("node", "npm")
ALL_NAMES = CORE_NAMES + EXTRA_NAMES

_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


# ── 홈 ────────────────────────────────────────────────────────────────────────
def cys_home() -> Path:
    """cys 가 쓰는 홈(`~/.cys` 의 실제 위치).

    Windows 의 cys(Rust `home` crate)는 FOLDERID_Profile(=USERPROFILE)을, macOS 는 $HOME 을 쓴다.
    FM_HOME 이 있으면 테스트 샌드박스로 본다.
    """
    fm = os.environ.get("FM_HOME")
    if fm:
        return Path(fm)
    if IS_WIN:
        up = os.environ.get("USERPROFILE")
        return Path(up) if up else Path.home()
    h = os.environ.get("HOME")
    return Path(h) if h else Path.home()


def python_home() -> Path:
    return Path.home()


def _same_path(a: Path, b: Path) -> bool:
    try:
        return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))
    except Exception:
        return False


def home_report() -> dict:
    """HOME 정합 보고 — 다르면 cys 쪽을 채택한다(스펙 §2 'HOME 정합')."""
    ch, ph = cys_home(), python_home()
    return {"home": ch, "cys_home": ch, "python_home": ph, "match": _same_path(ch, ph),
            "forced": bool(os.environ.get("FM_HOME"))}


# ── 자비스 앱 루트 ─────────────────────────────────────────────────────────────
def _win_registry_install_location() -> Path | None:
    if not IS_WIN:
        return None
    try:
        import winreg  # type: ignore
    except Exception:
        return None
    hives = ((winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"))
    for hive, base in hives:
        try:
            with winreg.OpenKey(hive, base) as k:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    if "cys" not in sub.lower():
                        continue
                    try:
                        with winreg.OpenKey(k, sub) as sk:
                            loc, _ = winreg.QueryValueEx(sk, "InstallLocation")
                            if loc and (Path(loc) / "cys.exe").exists():
                                return Path(loc)
                    except OSError:
                        continue
        except OSError:
            continue
    return None


def _mac_mdfind_roots() -> list[Path]:
    out: list[Path] = []
    if not IS_MAC:
        return out
    try:
        for hint in MAC_BUNDLE_ID_HINTS:
            r = subprocess.run(["mdfind", f"kMDItemCFBundleIdentifier == '*{hint}*'c"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
            for line in r.stdout.splitlines():
                p = Path(line.strip())
                if p.name == "cys.app" and (p / "Contents" / "MacOS" / "cys").exists():
                    out.append(p)
    except Exception:
        pass
    return out


def javis_root() -> Path | None:
    """자비스 앱 루트. 없으면 None (호출부가 exit 10 처리)."""
    forced = os.environ.get("FM_JAVIS_ROOT")
    if forced:
        p = Path(forced)
        return p if p.exists() else None
    cands: list[Path] = []
    if IS_WIN:
        la = os.environ.get("LOCALAPPDATA")
        if la:
            cands.append(Path(la) / "cys")
        reg = _win_registry_install_location()
        if reg:
            cands.append(reg)
        w = shutil.which("cys")
        if w:
            cands.append(Path(w).resolve().parent)
        for c in cands:
            if (c / "cys.exe").exists():
                return c
        return None
    if IS_MAC:
        cands = [Path("/Applications/cys.app"), cys_home() / "Applications" / "cys.app"]
        cands += _mac_mdfind_roots()
        for c in cands:
            if (c / "Contents" / "MacOS" / "cys").exists():
                return c
        return None
    # 기타 OS(개발·테스트용): FM_JAVIS_ROOT 만 인정
    return None


# ── 절대경로 표 ───────────────────────────────────────────────────────────────
def layout(root: Path) -> dict[str, Path]:
    """앱 루트 기준 실행체 절대경로 표(스펙 §2)."""
    root = Path(root)
    if IS_WIN:
        rt = root / "runtime"
        return {
            "cys": root / "cys.exe",
            "cysd": root / "cysd.exe",
            "python3": rt / "python" / "python3.exe",
            "git": rt / "git" / "cmd" / "git.exe",
            "bash": rt / "git" / "usr" / "bin" / "bash.exe",
            "node": rt / "node" / "node.exe",
            "npm": rt / "node" / "npm.cmd",
        }
    rt = root / "Contents" / "Resources" / "runtime"
    return {
        "cys": root / "Contents" / "MacOS" / "cys",
        "cysd": root / "Contents" / "MacOS" / "cysd",
        "python3": rt / "python" / "bin" / "python3",
        "git": rt / "git" / "bin" / "git",
        "bash": Path("/bin/bash"),  # 맥 런타임에 bash 는 동봉되지 않는다 — 시스템 3.2 (cys-dept 호환 확인)
        "node": rt / "node" / "bin" / "node",
        "npm": rt / "node" / "bin" / "npm",
    }


def npm_cli_js(root: Path) -> Path | None:
    """npm 을 cmd.exe 없이 node 로 직접 부르기 위한 npm-cli.js (있으면)."""
    root = Path(root)
    cands = [root / "runtime" / "node" / "node_modules" / "npm" / "bin" / "npm-cli.js",
             root / "Contents" / "Resources" / "runtime" / "node" / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js"]
    for c in cands:
        if c.exists():
            return c
    return None


def cys_dept_path(home: Path | None = None) -> Path:
    home = Path(home) if home else cys_home()
    return home / ".cys" / "pack" / "bin" / "cys-dept"


def path_prepend(root: Path) -> list[str]:
    root = Path(root)
    if IS_WIN:
        rt = root / "runtime"
        return [str(root), str(rt / "python"), str(rt / "git" / "cmd"), str(rt / "git" / "usr" / "bin"), str(rt / "node")]
    rt = root / "Contents" / "Resources" / "runtime"
    return [str(root / "Contents" / "MacOS"), str(rt / "python" / "bin"), str(rt / "git" / "bin"),
            str(rt / "node" / "bin"), "/usr/bin", "/bin"]


# ── 실행 환경 ─────────────────────────────────────────────────────────────────
def env_for_cys_dept(root: Path | None = None, home: Path | None = None) -> dict[str, str]:
    """cys-dept(bash) 호출용 env.

    - PATH 선두 주입: cys-dept 는 python3·cys·cysd 를 PATH 의 bare 이름으로만 찾는다(35곳).
    - CYS_* 전삭제: CYS_ROLE 잔존 = exit 7, CYS_SOCKET 잔존 = 엉뚱한 데몬.
    - ORIGINAL_PATH 삭제: Git Bash 프로필이 PATH 를 되감는 근거를 없앤다.
    - PYTHONUTF8=1: 번들 python 의 기본 인코딩(cp1252)으로 한글 JSON 이 깨지는 것을 막는다.
    - HOME 명시: bash 와 네이티브 자식이 같은 홈을 보게 한다(MSYS 가 형식 변환을 맡는다).
    - ★MSYS_NO_PATHCONV 는 **설정하지 않는다**(실측 2026-09-03): 켜면 cys-dept 내부 python heredoc 의
      인자 `$HOME/.cys/dept-catalog.json` 이 `/c/...` 그대로 네이티브 python 에 전달되어 열리지 않고
      exit 4(카탈로그 손상)로 오판된다. 부서 키(슬러그)에는 '/' 가 없어 변환 부작용이 없다.
    """
    root = Path(root) if root else javis_root()
    home = Path(home) if home else cys_home()
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("CYS_") and k.upper() not in ("ORIGINAL_PATH", "MSYS_NO_PATHCONV")}
    old = env.get("PATH", "")
    pre = path_prepend(root) if root else []
    parts = pre + [p for p in old.split(os.pathsep) if p and p not in pre]
    env["PATH"] = os.pathsep.join(parts)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # 맥 번들 봉인 보호(cys-dept SEAL-1 과 동일 원칙)
    env["HOME"] = str(home)
    if IS_WIN:
        env.setdefault("USERPROFILE", str(home))
    elif not env.get("LANG") and not env.get("LC_ALL"):
        env["LC_ALL"] = "C.UTF-8"  # 맥 GUI(수신부 앱)에서 온 셸은 로케일이 비어 한글 인자가 깨질 수 있다
    return env


def env_for_tools(root: Path | None = None, home: Path | None = None) -> dict[str, str]:
    """번들 git/node/npm/pip 호출용 env — cys-dept 용과 같되 대화형 프롬프트를 막는다."""
    env = env_for_cys_dept(root, home)
    env["GIT_TERMINAL_PROMPT"] = "0"      # 비공개 리포에서 자격증명 프롬프트로 멈추지 않는다
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INPUT"] = "1"
    env["npm_config_fund"] = "false"
    env["npm_config_audit"] = "false"
    env["npm_config_update_notifier"] = "false"
    env["CI"] = env.get("CI", "1")        # npm/설치 스크립트가 대화형으로 빠지지 않게
    return env


def env_for_cys(root: Path | None = None, home: Path | None = None, socket: str | None = None) -> dict[str, str]:
    """설치기가 직접 cys 를 부를 때의 env — 좀비 데몬 자동기동 금지."""
    env = env_for_cys_dept(root, home)
    env["CYS_NO_AUTOSTART"] = "1"
    if socket:
        env["CYS_SOCKET"] = socket
    return env


def to_bash_arg(p: Path | str) -> str:
    """bash 에 넘길 경로 표기 — Windows 는 `C:/x/y`(MSYS 가 그대로 이해한다)."""
    s = str(p)
    return s.replace("\\", "/") if IS_WIN else s


# ── 실행체 검증 ───────────────────────────────────────────────────────────────
def version_of(exe: Path, timeout: float = 20.0, env: dict | None = None) -> tuple[bool, str, str]:
    """(ok, version, error) — 실제로 `--version` 을 실행한다."""
    exe = Path(exe)
    if not exe.exists():
        return False, "", "파일 없음"
    try:
        kw: dict = dict(capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                        env=env, stdin=subprocess.DEVNULL)
        if IS_WIN:
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        r = subprocess.run([str(exe), "--version"], **kw)
    except subprocess.TimeoutExpired:
        return False, "", "응답 없음(시간 초과)"
    except OSError as e:
        return False, "", f"실행 불가: {e}"
    text = (r.stdout or "") + "\n" + (r.stderr or "")
    for line in text.splitlines():
        m = _VERSION_RE.search(line)
        if m:
            return r.returncode == 0, m.group(1), "" if r.returncode == 0 else f"exit={r.returncode}"
    return r.returncode == 0, text.strip().splitlines()[0] if text.strip() else "", (
        "" if r.returncode == 0 else f"exit={r.returncode}")


def probe(root: Path | None = None, names: tuple[str, ...] = ALL_NAMES) -> list[dict]:
    """실행체 각각을 `--version` 으로 실행해 [{name,path,ok,version,error,required}] 를 돌려준다."""
    root = Path(root) if root else javis_root()
    out: list[dict] = []
    if root is None:
        for n in names:
            out.append({"name": n, "path": "", "ok": False, "version": "", "error": "자비스 루트 없음",
                        "required": n in CORE_NAMES})
        return out
    lay = layout(root)
    env = env_for_tools(root)
    for n in names:
        p = lay[n]
        if n == "cysd":
            # ★cysd 는 `--version` 을 찍은 뒤 **데몬 기동을 시도**한다(실측 2026-09-03: 파이프 점유 시 exit 1,
            #   깨끗한 PC 라면 유령 데몬이 뜬다). 실행하지 않고 실물 존재만 확인하며 버전은 cys 와 동일 배포본으로 본다.
            ok = p.exists()
            out.append({"name": n, "path": str(p), "ok": ok, "version": "(cys 와 동일)" if ok else "",
                        "error": "" if ok else "파일 없음", "required": True})
            continue
        if n == "npm" and IS_WIN:
            # npm.cmd 는 cmd.exe 경유가 필요하다 — node 로 npm-cli.js 를 직접 실행해 확인한다.
            js = npm_cli_js(root)
            if js and lay["node"].exists():
                ok, ver, err = version_of(lay["node"], env=env)
                if ok:
                    try:
                        r = subprocess.run([str(lay["node"]), str(js), "--version"], capture_output=True, text=True,
                                           encoding="utf-8", errors="replace", timeout=30, env=env,
                                           stdin=subprocess.DEVNULL,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                        m = _VERSION_RE.search(r.stdout or "")
                        ok, ver, err = (r.returncode == 0 and bool(m)), (m.group(1) if m else ""), (
                            "" if r.returncode == 0 else f"exit={r.returncode}")
                    except Exception as e:  # pragma: no cover
                        ok, ver, err = False, "", str(e)
                out.append({"name": n, "path": str(js or p), "ok": ok, "version": ver, "error": err, "required": False})
                continue
        ok, ver, err = version_of(p, env=env)
        out.append({"name": n, "path": str(p), "ok": ok, "version": ver, "error": err, "required": n in CORE_NAMES})
    return out


def missing_javis_message() -> str:
    return f"자비스가 아직 설치되지 않았습니다 → 내려받기: {DOWNLOAD_URL}"


def os_summary() -> dict:
    return {"os": OS_KEY, "platform": platform.platform(), "arch": platform.machine(),
            "python": sys.version.split()[0], "executable": sys.executable}
