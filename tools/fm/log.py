"""UTF-8 로그(파일·콘솔 동시) · 바탕화면 사본 · 자기진단 헤더 · 최종 배너.

- 로그 파일: `~/.cys/fm-install/logs/<YYYYmmdd-HHMMSS>-<서브커맨드>.log` — 실행마다 새 파일(핸들러 실행 감지용).
- dry-run 은 실제 홈(`~/.cys`)에 아무것도 쓰지 않는다 → 임시 폴더(`<tmp>/fm-install/logs/`)에 남긴다.
- 바탕화면 사본: `퓨처미니스트리-설치로그.txt` — 실패해도 치명적이지 않다(맥 TCC 거부 시 `~/Downloads` 폴백).
"""
from __future__ import annotations

import datetime as _dt
import os
import shutil
import sys
import tempfile
from pathlib import Path

from . import resolve

DESKTOP_LOG_NAME = "퓨처미니스트리-설치로그.txt"


def _setup_console() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def desktop_dir(home: Path) -> Path:
    """바탕화면 실경로. Windows 는 OneDrive 리다이렉트를 반영(SHGetKnownFolderPath)."""
    if os.environ.get("FM_HOME"):
        return Path(home) / "Desktop"
    if resolve.IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                            ("Data4", wintypes.BYTE * 8)]

            # FOLDERID_Desktop {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
            g = GUID(0xB4BFCC3A, 0xDB2C, 0x424C, (wintypes.BYTE * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
            p = ctypes.c_wchar_p()
            res = ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p))
            if res == 0 and p.value:
                path = Path(p.value)
                ctypes.windll.ole32.CoTaskMemFree(p)
                return path
        except Exception:
            pass
    return Path(home) / "Desktop"


class Log:
    def __init__(self, home: Path, sub: str, dry_run: bool = False, ci: bool = False, console: bool = True):
        _setup_console()
        self.home = Path(home)
        self.sub = sub
        self.dry_run = dry_run
        self.ci = ci
        self.console = console
        self.warnings: list[str] = []
        self.failures: list[str] = []
        base = (self.home / ".cys" / "fm-install" / "logs") if not dry_run else (
            Path(tempfile.gettempdir()) / "fm-install" / "logs")
        base.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = base / f"{ts}-{sub}.log"
        n = 2
        while path.exists():  # 같은 초에 두 번 실행돼도 항상 새 파일
            path = base / f"{ts}-{sub}-{n}.log"
            n += 1
        self.path = path
        self._fh = open(path, "a", encoding="utf-8", newline="\n")
        self.raw(f"# fm-install log · {sub} · {_dt.datetime.now().isoformat(timespec='seconds')}"
                 + (" · DRY-RUN(쓰기 0)" if dry_run else ""))

    # ── 기본 출력 ──
    def raw(self, line: str, to_console: bool = True) -> None:
        try:
            self._fh.write(line + "\n")
            self._fh.flush()
        except Exception:
            pass
        if to_console and self.console:
            try:
                print(line, flush=True)
            except Exception:
                pass

    def info(self, m: str) -> None:
        self.raw(f"  {m}")

    def ok(self, m: str) -> None:
        self.raw(f"  + {m}")

    def same(self, m: str) -> None:
        self.raw(f"  = {m}")

    def plan(self, m: str) -> None:
        self.raw(f"  (예정) {m}")

    def act(self, m: str) -> None:
        """dry-run 이면 '예정', 아니면 실행 로그."""
        (self.plan if self.dry_run else self.ok)(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)
        self.raw(f"  ! {m}")

    def fail(self, m: str) -> None:
        self.failures.append(m)
        self.raw(f"  x {m}")

    def step(self, n, title: str) -> None:
        self.raw("")
        self.raw(f"[{n}] {title}")

    # ── 자기진단 헤더 ──
    def header(self, diag: dict) -> None:
        self.raw("=" * 60)
        self.raw(" 퓨처 미니스트리 설치기 v2 — 자기진단")
        self.raw("=" * 60)
        for k, v in diag.items():
            if isinstance(v, (list, tuple)):
                self.raw(f"  {k}:")
                for it in v:
                    self.raw(f"    - {it}")
            else:
                self.raw(f"  {k}: {v}")

    # ── 최종 배너 ──
    def banner(self, ok: bool, detail: str = "") -> str:
        self.raw("")
        if self.warnings:
            self.raw(f"-- 경고 {len(self.warnings)}건 --")
            for w in self.warnings:
                self.raw(f"  ! {w}")
        if self.failures:
            self.raw(f"-- 실패 {len(self.failures)}건 --")
            for f in self.failures:
                self.raw(f"  x {f}")
        self.raw("")
        if ok:
            line = f"[OK] 설치가 끝났습니다 — 로그: {self.path}"
        else:
            line = (f"[FAIL] 설치가 끝나지 않았습니다(실패 {len(self.failures)}건{(' · ' + detail) if detail else ''})"
                    f" — 로그: {self.path} · 이 파일을 보내주세요")
        self.raw(line)
        return line

    # ── 바탕화면 사본 ──
    def desktop_copy(self) -> Path | None:
        """실패해도 예외를 내지 않는다. dry-run 은 사본을 만들지 않는다."""
        if self.dry_run:
            return None
        try:
            self._fh.flush()
        except Exception:
            pass
        cands = [desktop_dir(self.home), self.home / "Downloads"]
        for d in cands:
            try:
                d.mkdir(parents=True, exist_ok=True)
                dst = d / DESKTOP_LOG_NAME
                shutil.copyfile(self.path, dst)
                return dst
            except Exception:
                continue
        return None

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass

    def __del__(self):  # 닫지 않고 버려져도 핸들을 정리한다
        self.close()
