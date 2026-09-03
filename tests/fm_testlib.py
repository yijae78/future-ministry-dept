"""fm 테스트 공통 — HOME 샌드박스(tempfile) + 가짜 cys-dept 스텁 + 가짜 패키지.

실행: <번들 python3> -X utf8 -m unittest discover -s tests -v
원칙: 실제 ~/.cys · 레지스트리 · 바탕화면에 절대 쓰지 않는다(FM_HOME 샌드박스). 자비스 런타임은 읽기만 한다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from fm import resolve  # noqa: E402

REPO_ROOT = TOOLS.parent

# 가짜 cys-dept — 계약: stdout 마지막 줄 = dept-N · 진단은 stderr · exit 3/4/7 · python3 는 PATH bare 이름
STUB = r'''#!/usr/bin/env bash
# fake cys-dept (fm tests)
set -u
if [ -n "${CYS_ROLE:-}" ]; then echo "[stub] CYS_ROLE=$CYS_ROLE → exit 7" >&2; exit 7; fi
[ "${1:-}" = "create" ] || { echo "[stub] usage" >&2; exit 2; }
key="${2:-}"
cat="${CYS_DEPT_CATALOG:-$HOME/.cys/dept-catalog.json}"
reg="${CYS_DEPTS_JSON:-$HOME/.cys/depts.json}"
[ -f "$cat" ] || { echo "[stub] no catalog $cat" >&2; exit 3; }
echo "[stub] python3=$(command -v python3 || echo none) cys=$(command -v cys || echo none) HOME=$HOME PATHCONV=${MSYS_NO_PATHCONV:-unset}" >&2
if [ -n "${FM_STUB_EXIT:-}" ]; then echo "[stub] forced exit $FM_STUB_EXIT" >&2; exit "$FM_STUB_EXIT"; fi
echo "[stub] progress line on stdout (must be ignored by the parser)"
python3 - "$cat" "$reg" "$key" <<'PY'
import json, os, sys
cat, reg, key = sys.argv[1:4]
c = json.load(open(cat, encoding="utf-8"))
dep = c["departments"].get(key)
if not dep:
    sys.exit(4)
acct = c["accounts"][dep["account"]]
acctdir = os.path.expandvars(acct)
if not os.path.isdir(acctdir):
    sys.stderr.write("[stub] account dir missing: %s\n" % acctdir); sys.exit(5)
r = {"depts": {}}
if os.path.exists(reg):
    r = json.load(open(reg, encoding="utf-8"))
mk = dep["mission_key"]
for n, e in r["depts"].items():
    if e.get("mission_key") == mk:
        sys.stderr.write("[stub] %s 이미 생존(%s) — 재사용\n" % (key, n)); print(n); sys.exit(0)
n = "dept-%d" % (9 + len(r["depts"]))
home = os.path.expandvars("$HOME")
r["depts"][n] = {"socket": "\\\\.\\pipe\\fm-test-" + n if os.name == "nt" else home + "/.local/state/fm-test-" + n + "/cys.sock",
                 "pack_dir": home + "/.cys/pack-dept-" + n, "role": "dept-master", "mission_key": mk,
                 "cwd": os.path.expandvars(dep["cwd"]), "display_name": dep["display"], "account": dep["account"],
                 "account_dir": acctdir + "-" + key}
os.makedirs(home + "/.cys/pack-dept-" + n, exist_ok=True)
json.dump(r, open(reg, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
sys.stderr.write("[stub] %s allocate 완료\n" % n)
print(n)
PY
'''


def bundled_git() -> Path | None:
    root = resolve.javis_root()
    if root:
        g = resolve.layout(root)["git"]
        if Path(g).exists():
            return Path(g)
    w = shutil.which("git")
    return Path(w) if w else None


def javis_ready() -> bool:
    """이 PC 에 자비스 런타임(bash·python3)이 있어 cys-dept 스텁을 실제로 돌릴 수 있는가 (읽기 전용 사용)."""
    root = resolve.javis_root()
    if not root:
        return False
    lay = resolve.layout(root)
    return Path(lay["bash"]).exists() and Path(lay["python3"]).exists()


def make_local_repo(git: Path, base: Path, name: str, files: dict[str, str] | None = None) -> str:
    """클론 대상이 될 로컬 bare 리포. 반환 = clone 에 넘길 경로(문자열)."""
    src = base / f"{name}-src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    (src / "requirements.txt").write_text("", encoding="utf-8")
    for rel, text in (files or {}).items():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    kw = dict(capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    subprocess.run([str(git), "-C", str(src), "init", "-q"], **kw)
    subprocess.run([str(git), "-C", str(src), "-c", "user.name=t", "-c", "user.email=t@t", "add", "."], **kw)
    subprocess.run([str(git), "-C", str(src), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"], **kw)
    bare = base / f"{name}.git"
    r = subprocess.run([str(git), "clone", "-q", "--bare", str(src), str(bare)], **kw)
    assert r.returncode == 0, r.stderr
    return str(bare).replace("\\", "/")


def make_fake_package(base: Path, git: Path | None) -> Path:
    """실제 manifest 와 같은 위상(4부서)·축소 기술자(로컬 리포)의 가짜 패키지."""
    pkg = base / "pkg"
    (pkg / "missions").mkdir(parents=True)
    (pkg / "tools" / "fm").mkdir(parents=True)
    (pkg / "tools" / "fm" / "cli.py").write_text("# dummy cli for receiver command test\n", encoding="utf-8")
    (pkg / "tools" / "install.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (pkg / "CHARTER.md").write_text("# CHARTER\n", encoding="utf-8")
    for k in ("future-ministry", "fm-admin", "fm-worship", "fm-sermon"):
        (pkg / "missions" / f"{k}.md").write_text(f"# mission {k}\n", encoding="utf-8")
    repos = base / "repos"
    repos.mkdir(exist_ok=True)
    ca_files = {
        "app/main.py": "import sys\nimport fm_probe_dep\nprint('RUN-OK', fm_probe_dep.V, sys.argv)\n",
        "pyproject.toml": '[project]\nname="church-admin"\nversion="0.1"\ndependencies=["six>=1.0"]\n',
    }
    r_frar = make_local_repo(git, repos, "frar") if git else "https://invalid.invalid/frar.git"
    r_ca = make_local_repo(git, repos, "church-admin", ca_files) if git else "https://invalid.invalid/ca.git"
    r_pn = make_local_repo(git, repos, "pray-news") if git else "https://invalid.invalid/pn.git"
    mf = {
        "package": "future-ministry-test", "display": "Future Ministry(칼빈)", "version": "9.9.9",
        "accounts": {"_comment": "x", "owner": "$HOME/.cys/claude"},
        "departments": [
            {"key": "future-ministry", "display": "Future Ministry(칼빈)", "mission_key": "future-ministry", "parent": None,
             "tier": 0, "account": "owner", "cwd_template": "$HOME/Future-Ministry",
             "mission_file": "missions/future-ministry.md", "charter_file": "CHARTER.md", "techs": []},
            {"key": "fm-admin", "display": "행정관리부", "mission_key": "fm-admin", "parent": "Future Ministry(칼빈)",
             "tier": 1, "account": "owner", "cwd_template": "$HOME/Future-Ministry/행정관리부",
             "mission_file": "missions/fm-admin.md", "techs": [
                 {"name": "frar", "id": "frar", "repo": r_frar, "cwd_template": "$HOME/Future-Ministry/행정관리부/frar",
                  "visibility": "public", "delivery": "install",
                  "requires": {"runtime": "python", "install": "pip install -r requirements.txt", "run": "streamlit run run.py"}},
                 {"name": "Church-Admin", "id": "church-admin", "repo": r_ca,
                  "cwd_template": "$HOME/Future-Ministry/행정관리부/Church-Admin", "visibility": "public",
                  "delivery": "install",
                  "requires": {"runtime": "python", "cwd": "app", "install": "pip install -r requirements.txt", "run": "python main.py --flag"}}]},
            {"key": "fm-worship", "display": "예배교육부", "mission_key": "fm-worship", "parent": "future-ministry",
             "tier": 1, "account": "owner", "cwd_template": "$HOME/Future-Ministry/예배교육부",
             "mission_file": "missions/fm-worship.md", "techs": [
                 {"name": "godsaengbook-grace", "id": "godsaengbook-grace", "repo": "https://example.invalid/g.git",
                  "cwd_template": "$HOME/Future-Ministry/예배교육부/godsaengbook-grace", "visibility": "public",
                  "delivery": "hosted", "requires": {"runtime": "node", "install": None}}]},
            {"key": "fm-sermon", "display": "설교기획부", "mission_key": "fm-sermon", "parent": "Future Ministry(칼빈)",
             "tier": 1, "account": "owner", "cwd_template": "$HOME/Future-Ministry/설교기획부",
             "mission_file": "missions/fm-sermon.md", "techs": [
                 {"name": "pray-news", "id": "pray-news", "repo": r_pn,
                  "cwd_template": "$HOME/Future-Ministry/설교기획부/pray-news", "visibility": "public",
                  "delivery": "install", "optional": True,
                  "requires": {"runtime": "node", "install": None, "run": "npm run dev"}}]},
        ],
    }
    (pkg / "manifest.json").write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
    return pkg


class Sandbox:
    """FM_HOME 샌드박스. with 블록 안에서 환경변수를 바꾸고 나갈 때 복원한다."""

    def __init__(self, with_stub: bool = True, javis_root: Path | None = None):
        self.dir = Path(tempfile.mkdtemp(prefix="fm-home-"))
        self.home = self.dir / "home"
        self.home.mkdir()
        (self.home / ".cys" / "claude").mkdir(parents=True)
        (self.home / "Desktop").mkdir()
        self.stub = self.home / ".cys" / "pack" / "bin" / "cys-dept"
        if with_stub:
            self.stub.parent.mkdir(parents=True)
            self.stub.write_text(STUB, encoding="utf-8", newline="\n")
            try:
                os.chmod(self.stub, 0o755)
            except Exception:
                pass
        self.git = bundled_git()
        self.pkg = make_fake_package(self.dir, self.git)
        self._saved: dict[str, str | None] = {}
        self.javis_root = javis_root

    def _set(self, k: str, v: str | None) -> None:
        self._saved.setdefault(k, os.environ.get(k))
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    def __enter__(self):
        self._set("FM_HOME", str(self.home))
        self._set("FM_CI", "1")
        self._set("FM_NO_PAUSE", "1")
        self._set("FM_PAUSE", "0")
        self._set("FM_PING_WAIT", "0")
        self._set("FM_PKG_DIR", None)
        self._set("FM_STUB_EXIT", None)
        if self.javis_root:
            self._set("FM_JAVIS_ROOT", str(self.javis_root))
        return self

    def __exit__(self, *a):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.dir, ignore_errors=True)

    # 조회 도우미
    @property
    def cys(self) -> Path:
        return self.home / ".cys"

    def read_json(self, rel: str):
        return json.loads((self.home / rel).read_text(encoding="utf-8-sig"))

    def logs(self) -> list[Path]:
        d = self.cys / "fm-install" / "logs"
        return sorted(d.glob("*.log")) if d.exists() else []
