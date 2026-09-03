"""설치 단계 0~11 (스펙 §3) — 멱등. 각 단계는 (status, detail) 을 돌려주고 로그에 남긴다.

status: 'done'(새로 함) | 'skipped'(이미 됨·대상 없음) | 'failed'
setup.ps1 ①~⑨ 를 이식했다. dry-run 이면 모든 쓰기·실행을 "(예정)" 로그로 대체한다.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import resolve
from .log import Log
from .manifest import Dept, Manifest, Tech, expand_home

DEPT_RE = re.compile(r"^dept-\d+$")
DEPT_CAP_DEFAULT = 8
CYS_PASSTHROUGH = ("CYS_DEPT_CAP", "CYS_PRIMARY_ACCOUNT")  # cys-dept 의 '입력' 변수 — 오너가 켰으면 존중

# cys-dept create 종료코드 → 목사님 언어
EXIT_MSG = {
    2: "부서 이름 규칙 위반 — 영문·숫자·'-'·'_' 만 쓸 수 있습니다 (패키지 오류이니 제작자에게 알려 주세요)",
    3: "자비스 부서 카탈로그 파일이 없습니다 — 1단계(카탈로그 등록)가 먼저 되어야 합니다. 설치를 다시 실행해 주세요",
    4: "카탈로그에서 이 부서를 찾지 못했거나 파일이 손상됐습니다 — 설치를 다시 실행해 주세요",
    5: "자비스 계정 폴더(~/.cys/claude)가 없습니다 — 자비스 앱을 한 번 실행해 로그인한 뒤 다시 설치해 주세요",
    6: "부서 초기 설정(시드)에 실패했습니다 — 자비스 운영 틀(~/.cys/pack)이 온전한지 확인이 필요합니다. 로그를 보내주세요",
    7: "자비스 역할(CYS_ROLE)이 켜진 창에서 실행됐습니다 — 새 창(또는 바탕화면 설치 파일)에서 다시 실행해 주세요",
    8: "부서 수가 상한(8개)에 도달했습니다 — 자비스에서 쓰지 않는 부서를 정리한 뒤 다시 실행해 주세요",
}


def exit_message(code: int) -> str:
    return EXIT_MSG.get(code, f"부서 데몬을 시작하지 못했습니다(exit={code}) — 자비스 앱이 켜져 있는지 확인하고 다시 실행해 주세요")


@dataclass
class Seat:
    id: int
    role: str
    exited: bool
    title: str
    cwd: str = ""


@dataclass
class Ctx:
    pkg_dir: Path
    mf: Manifest
    home: Path
    root: Path | None
    lay: dict
    log: Log
    dry_run: bool = False
    ci: bool = False
    dept: str | None = None
    only: list[str] | None = None
    deps: bool | None = None          # None = delivery:install 기본 on · False = --no-deps
    pause: float = 1.2                # cys 연속 호출 간격(백신 락 회피)
    ping_wait: float = 30.0           # 좌석 단계 데몬 ping 대기(초)
    dept_id_of: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    probe: list = field(default_factory=list)
    pkg_commit: str = ""

    @property
    def cys_home(self) -> Path:
        return self.home / ".cys"

    def targets(self) -> list[Dept]:
        return self.mf.targets(self.dept)

    def selected(self, tech: Tech) -> bool:
        return self.only is None or tech.id in self.only

    def expand(self, template: str | None) -> Path | None:
        return expand_home(template, self.home)

    def record(self, name: str, status: str, detail: str = "") -> tuple[str, str]:
        self.results[name] = (status, detail)
        return status, detail


# ── 공통 유틸 ─────────────────────────────────────────────────────────────────
def now_ts() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def atomic_write_json(path: Path, obj) -> None:
    """임시파일 + 원자 교체 · UTF-8(BOM 없음 — cys-dept 의 json.load 가 BOM 에 죽는다)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(data)
        last: Exception | None = None
        for _ in range(10):  # Windows 는 다른 프로세스가 열어 둔 파일 교체가 잠깐 실패할 수 있다
            try:
                os.replace(tmp, path)
                return
            except PermissionError as e:
                last = e
                time.sleep(0.2)
        raise last  # type: ignore[misc]
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def run_capture(argv: list[str], env: dict, cwd: Path | None = None, timeout: float = 600.0,
                stdin_text: str | None = None) -> tuple[int, str, str]:
    """stdout/stderr 를 임시파일로 받는다 — 백그라운드 자식(nohup cysd 등)이 파이프를 물고 있어도 hang 하지 않는다."""
    with tempfile.TemporaryFile(mode="w+b") as out, tempfile.TemporaryFile(mode="w+b") as err:
        kw: dict = dict(stdout=out, stderr=err, env=env, cwd=str(cwd) if cwd else None,
                        stdin=subprocess.DEVNULL if stdin_text is None else subprocess.PIPE)
        if resolve.IS_WIN:
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            p = subprocess.Popen(argv, **kw)
        except OSError as e:
            return 127, "", f"실행 불가: {e}"
        try:
            p.communicate(input=stdin_text.encode("utf-8") if stdin_text is not None else None, timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            try:
                p.wait(10)
            except Exception:
                pass
            out.seek(0); err.seek(0)
            return 124, out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace") + "\n[시간 초과]"
        out.seek(0); err.seek(0)
        return p.returncode, out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace")


def tail(text: str, n: int = 3) -> str:
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    return " / ".join(lines[-n:])


def load_depts(ctx: Ctx) -> dict:
    p = ctx.cys_home / "depts.json"
    if not p.exists():
        return {}
    try:
        d = read_json(p)
    except Exception as e:
        ctx.log.warn(f"depts.json 을 읽지 못했다: {e}")
        return {}
    depts = d.get("depts") if isinstance(d, dict) else None
    return depts if isinstance(depts, dict) else {}


def dept_by_mission(depts: dict, mission_key: str) -> tuple[str, dict] | None:
    for name, e in depts.items():
        if isinstance(e, dict) and e.get("mission_key") == mission_key:
            return name, e
    return None


def dept_id_for(ctx: Ctx, d: Dept, depts: dict | None = None) -> str | None:
    if d.key in ctx.dept_id_of:
        return ctx.dept_id_of[d.key]
    depts = depts if depts is not None else load_depts(ctx)
    hit = dept_by_mission(depts, d.mission_key)
    if hit:
        ctx.dept_id_of[d.key] = hit[0]
        return hit[0]
    return None


def cys_env(ctx: Ctx, socket: str | None = None) -> dict:
    return resolve.env_for_cys(ctx.root, ctx.home, socket)


def cys_ping(ctx: Ctx, socket: str, wait_s: float = 0.0, interval: float = 1.0) -> bool:
    """`cys ping --socket S` — 자동기동 없음. wait_s 동안 재시도."""
    if not ctx.root or not ctx.lay.get("cys") or not Path(ctx.lay["cys"]).exists():
        return False
    deadline = time.monotonic() + max(0.0, wait_s)
    while True:
        rc, _, _ = run_capture([str(ctx.lay["cys"]), "ping", "--socket", socket], cys_env(ctx), timeout=10)
        if rc == 0:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)


def cys_list(ctx: Ctx, socket: str) -> list[Seat] | None:
    """`cys list` 파싱 — 탭 구분: surface:N · role=X · pid=N · exited=bool · title · cwd. 무응답이면 None."""
    rc, out, err = run_capture([str(ctx.lay["cys"]), "list", "--socket", socket], cys_env(ctx), timeout=20)
    if rc != 0 or re.search(r"cannot connect|not running", out + err, re.I):
        return None
    seats: list[Seat] = []
    for line in out.splitlines():
        f = line.rstrip("\r").split("\t")
        if len(f) < 5:
            continue
        m = re.match(r"^surface:(\d+)$", f[0])
        if not m:
            continue
        exited = f[3].replace("exited=", "") == "true"
        seats.append(Seat(id=int(m.group(1)), role=f[1].replace("role=", ""), exited=exited,
                          title=f[4], cwd=f[5] if len(f) > 5 else ""))
    return seats


def _pkg_commit(ctx: Ctx) -> str:
    git = ctx.lay.get("git")
    if git and Path(git).exists() and (ctx.pkg_dir / ".git").exists():
        rc, out, _ = run_capture([str(git), "-C", str(ctx.pkg_dir), "rev-parse", "--short", "HEAD"],
                                 resolve.env_for_tools(ctx.root, ctx.home), timeout=30)
        if rc == 0 and out.strip():
            return out.strip()
    try:  # git 없이도 읽는다
        head = (ctx.pkg_dir / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            ref = ctx.pkg_dir / ".git" / head[4:].strip()
            if ref.exists():
                return ref.read_text(encoding="utf-8").strip()[:12]
            return head
        return head[:12]
    except Exception:
        return "(git 정보 없음)"


# ── 0. 자기진단 헤더 ─────────────────────────────────────────────────────────
def step0_selfdiag(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    hr = resolve.home_report()
    ctx.pkg_commit = _pkg_commit(ctx)
    diag: dict = {}
    o = resolve.os_summary()
    diag["OS"] = f"{o['os']} · {o['platform']} · {o['arch']}"
    diag["python(설치기)"] = f"{o['python']} · {o['executable']}"
    diag["자비스 루트"] = str(ctx.root) if ctx.root else "(없음)"
    diag["HOME(cys)"] = str(hr["cys_home"]) + (" [FM_HOME 강제]" if hr["forced"] else "")
    if not hr["match"]:
        diag["HOME(python)"] = f"{hr['python_home']}  ← 다르다. cys 쪽 홈을 채택한다"
    diag["패키지"] = f"{ctx.pkg_dir} @ {ctx.pkg_commit} (manifest v{ctx.mf.version})"
    diag["모드"] = ("DRY-RUN(쓰기 0)" if ctx.dry_run else "적용") + (" · CI/비대화" if ctx.ci else "")
    if ctx.dept:
        diag["대상 부서"] = ctx.dept
    if ctx.only:
        diag["대상 기술자(--only)"] = ", ".join(ctx.only)
    if ctx.root:
        ctx.probe = resolve.probe(ctx.root)
        diag["PATH 선두"] = resolve.path_prepend(ctx.root)
        rows = []
        for p in ctx.probe:
            mark = "OK " if p["ok"] else "-- "
            rows.append(f"{mark}{p['name']:<8} {p['version'] or '-':<12} {p['path']}{('  ' + p['error']) if p['error'] else ''}")
        diag["실행체(--version 실측)"] = rows
    log.header(diag)
    if not ctx.root:
        log.fail(resolve.missing_javis_message())
        return ctx.record("selfdiag", "failed", "javis-missing")
    bad = [p for p in ctx.probe if p["required"] and not p["ok"]]
    if bad:
        for p in bad:
            log.fail(f"자비스 런타임 '{p['name']}' 를 실행하지 못했습니다: {p['path']} ({p['error']}) — 자비스를 다시 설치해 주세요")
        return ctx.record("selfdiag", "failed", "runtime-missing")
    return ctx.record("selfdiag", "done", ctx.pkg_commit)


# ── 1. 카탈로그 병합 ─────────────────────────────────────────────────────────
def _rotate_backups(path: Path, keep: int = 3) -> None:
    baks = sorted(path.parent.glob(path.name + ".bak-*"), key=lambda p: p.name)
    for old in baks[:-keep] if len(baks) > keep else []:
        try:
            old.unlink()
        except OSError:
            pass


def step1_catalog(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step(1, "매니페스트 → dept-catalog.json 병합")
    cat = ctx.cys_home / "dept-catalog.json"
    existing: dict = {}
    if cat.exists():
        try:
            existing = read_json(cat)
        except Exception as e:
            log.fail(f"카탈로그를 읽지 못했습니다({e}) — 손상된 파일입니다. 로그를 보내주세요: {cat}")
            return ctx.record("catalog", "failed", str(e))
    new = json.loads(json.dumps(existing)) if existing else {}
    if not isinstance(new.get("accounts"), dict):
        new["accounts"] = {}
    if not isinstance(new.get("departments"), dict):
        new["departments"] = {}
    for k, v in ctx.mf.accounts.items():
        if k not in new["accounts"]:
            new["accounts"][k] = v
            log.act(f"accounts['{k}'] = {v}")
    for d in ctx.targets():
        proj: dict = {"display": d.display, "account": d.account, "mission_key": d.mission_key, "cwd": d.cwd_template}
        pd = ctx.mf.parent_display(d)
        if pd:
            proj["parent"] = pd
        if d.techs:
            proj["techs"] = [{"name": t.name, "repo": t.repo, "cwd": t.cwd_template} for t in d.techs]
        cur = new["departments"].get(d.key)
        entry = dict(cur) if isinstance(cur, dict) else {}
        entry.update(proj)
        if cur == entry:
            log.same(f"departments['{d.key}'] 이미 일치 (기술자 {len(d.techs)})")
        else:
            log.act(f"departments['{d.key}'] {'갱신' if cur else '추가'} (기술자 {len(d.techs)})")
        new["departments"][d.key] = entry
    if new == existing:
        log.same(f"변경 없음: {cat}")
        return ctx.record("catalog", "skipped", "unchanged")
    if cat.exists():
        log.act(f"백업: {cat}.bak-<ts> (3개 회전)")
    log.act(f"저장: {cat}")
    if ctx.dry_run:
        return ctx.record("catalog", "done", "planned")
    try:
        if cat.exists():
            shutil.copyfile(cat, Path(str(cat) + f".bak-{now_ts()}"))
            _rotate_backups(cat, 3)
        atomic_write_json(cat, new)
    except Exception as e:
        log.fail(f"카탈로그 저장 실패: {e}")
        return ctx.record("catalog", "failed", str(e))
    log.ok(f"병합 완료: {cat}")
    return ctx.record("catalog", "done", str(cat))


# ── 2. 미션 이식 ─────────────────────────────────────────────────────────────
def _copy_if_changed(ctx: Ctx, src: Path, dst: Path, label: str) -> str:
    if not src.exists():
        ctx.log.warn(f"{label}: 원본 없음 {src}")
        return "skipped"
    try:
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            ctx.log.same(f"{label}: 이미 같음 {dst}")
            return "skipped"
    except OSError:
        pass
    ctx.log.act(f"{label}: {src.name} → {dst}")
    if ctx.dry_run:
        return "done"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return "done"


def step2_missions(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step(2, "미션 파일 이식 → ~/.cys/dept-missions/")
    mdir = ctx.cys_home / "dept-missions"
    statuses = []
    for d in ctx.targets():
        if not d.mission_file:
            continue
        src = ctx.pkg_dir / Path(d.mission_file.replace("\\", "/"))
        dst = mdir / f"{d.mission_key}.md"
        statuses.append(_copy_if_changed(ctx, src, dst, f"미션[{d.key}]"))
    st = "done" if "done" in statuses else "skipped"
    return ctx.record("missions", st, f"{statuses.count('done')} copied")


# ── 3. 작업 폴더 ─────────────────────────────────────────────────────────────
def step3_workdirs(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step(3, "작업 폴더 생성")
    made = 0
    for d in ctx.targets():
        p = ctx.expand(d.cwd_template)
        if p is None:
            continue
        if p.exists():
            log.same(f"이미 있음: {p}")
            continue
        log.act(f"생성: {p}")
        made += 1
        if not ctx.dry_run:
            try:
                p.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                log.fail(f"작업 폴더를 만들지 못했습니다: {p} ({e})")
                return ctx.record("workdirs", "failed", str(e))
    return ctx.record("workdirs", "done" if made else "skipped", f"{made} created")


# ── 4. 부서 생성 ─────────────────────────────────────────────────────────────
def _ensure_pack(ctx: Ctx) -> bool:
    tool = resolve.cys_dept_path(ctx.home)
    if tool.exists():
        return True
    ctx.log.warn(f"자비스 운영 틀(pack)이 없습니다: {tool}")
    ctx.log.act("cys init-pack (운영 틀 설치)")
    if ctx.dry_run:
        return True
    if os.environ.get("FM_HOME"):
        ctx.log.fail("FM_HOME(샌드박스)에서는 init-pack 을 실행하지 않습니다 — cys init-pack 은 env HOME 을 무시하고 실제 홈에 씁니다")
        return False
    rc, out, err = run_capture([str(ctx.lay["cys"]), "init-pack"], cys_env(ctx), timeout=300)
    if rc != 0 or not tool.exists():
        ctx.log.fail(f"운영 틀 설치 실패(exit={rc}): {tail(out + err)} — 자비스 앱을 한 번 실행한 뒤 다시 설치해 주세요")
        return False
    ctx.log.ok(f"운영 틀 설치 완료: {tool}")
    return True


def _dept_env(ctx: Ctx) -> dict:
    env = resolve.env_for_cys_dept(ctx.root, ctx.home)
    for k in CYS_PASSTHROUGH:
        v = os.environ.get(k)
        if v:
            env[k] = v
    return env


def step4_create_depts(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step(4, "부서 생성 — cys-dept create (멱등 · REUSE 정상)")
    if not _ensure_pack(ctx):
        return ctx.record("depts", "failed", "pack-missing")
    tool = resolve.cys_dept_path(ctx.home)
    # 계정 폴더 선행 생성
    for acct in sorted({d.account for d in ctx.targets()}):
        p = ctx.expand(ctx.mf.accounts[acct])
        if p and not p.exists():
            log.act(f"계정 폴더 생성: {p}")
            if not ctx.dry_run:
                p.mkdir(parents=True, exist_ok=True)
    # 상한 사전 계산
    depts = load_depts(ctx)
    targets = ctx.targets()
    new_depts = [d for d in targets if not dept_by_mission(depts, d.mission_key)]
    try:
        cap = int(os.environ.get("CYS_DEPT_CAP") or DEPT_CAP_DEFAULT)
    except ValueError:
        cap = DEPT_CAP_DEFAULT
    if new_depts:
        live = 0
        for _, e in depts.items():
            if isinstance(e, dict) and e.get("socket") and cys_ping(ctx, str(e["socket"]), wait_s=0):
                live += 1
        log.info(f"부서 상한 점검: 살아있는 부서 {live} + 새로 만들 부서 {len(new_depts)} / 상한 {cap}")
        if live + len(new_depts) > cap:
            log.warn(f"부서 수가 상한({cap})을 넘을 수 있습니다 — 자비스에서 쓰지 않는 부서를 정리해 주세요(초과분은 exit 8 로 거부됩니다)")
    failed = 0
    created = 0
    for d in targets:
        hit = dept_by_mission(depts, d.mission_key)
        if ctx.dry_run:
            log.plan(f"bash cys-dept create {d.key}" + (f"  (이미 등록: {hit[0]} → REUSE)" if hit else "  (신규)"))
            if hit:
                ctx.dept_id_of[d.key] = hit[0]
            continue
        rc, out, err = run_capture([str(ctx.lay["bash"]), resolve.to_bash_arg(tool), "create", d.key],
                                   _dept_env(ctx), timeout=600)
        names = [ln.strip() for ln in out.splitlines() if DEPT_RE.match(ln.strip())]
        name = names[-1] if names else None
        if rc != 0 or not name:
            failed += 1
            log.fail(f"부서 생성 실패 [{d.key}] exit={rc}: {exit_message(rc)}")
            if out.strip() or err.strip():
                log.raw(f"      원문: {tail(out + chr(10) + err, 4)}", to_console=True)
            continue
        ctx.dept_id_of[d.key] = name
        if hit and hit[0] == name:
            log.same(f"{d.key} → {name} (재사용)")
        else:
            created += 1
            log.ok(f"{d.key} → {name}")
        time.sleep(ctx.pause)
    if failed:
        return ctx.record("depts", "failed", f"{failed} failed")
    return ctx.record("depts", "done" if (created or ctx.dry_run) else "skipped", f"{created} new")


# ── 5. parent 백필 ───────────────────────────────────────────────────────────
def step5_parent_backfill(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step("5", "parent 백필 → depts.json (부서 트리의 진실원)")
    need = [d for d in ctx.targets() if d.parent]
    if not need:
        log.same("parent 가 있는 부서 없음")
        return ctx.record("parent", "skipped", "none")
    path = ctx.cys_home / "depts.json"
    if not path.exists():
        for d in need:
            log.plan(f"depts.json: <발급번호>.parent = '{ctx.mf.parent_display(d)}'  [{d.key}]")
        if ctx.dry_run:
            return ctx.record("parent", "done", "planned")
        log.fail(f"depts.json 이 없어 parent 백필 불가: {path}")
        return ctx.record("parent", "failed", "depts.json missing")
    try:
        reg = read_json(path)
    except Exception as e:
        log.fail(f"depts.json 을 읽지 못했습니다: {e}")
        return ctx.record("parent", "failed", str(e))
    depts = reg.get("depts") if isinstance(reg, dict) else None
    if not isinstance(depts, dict):
        log.fail("depts.json 형식이 다릅니다('depts' 맵 없음)")
        return ctx.record("parent", "failed", "bad format")
    changed = False
    failed = 0
    for d in need:
        want = ctx.mf.parent_display(d)
        did = dept_id_for(ctx, d, depts)
        if not did or did not in depts:
            if ctx.dry_run:
                log.plan(f"depts.json: <발급번호>.parent = '{want}'  [{d.key}]")
                continue
            failed += 1
            log.fail(f"depts.json 에 {d.key} 엔트리가 없어 parent 백필 실패")
            continue
        cur = depts[did].get("parent")
        if cur == want:
            log.same(f"{did}.parent 이미 일치 ('{want}')")
            continue
        log.act(f"{did}.parent = '{want}'  [{d.key}]")
        if not ctx.dry_run:
            depts[did]["parent"] = want
            changed = True
    if changed:
        try:
            atomic_write_json(path, reg)
            log.ok(f"백필 완료: {path}")
        except Exception as e:
            log.fail(f"depts.json 저장 실패: {e}")
            return ctx.record("parent", "failed", str(e))
    if failed:
        return ctx.record("parent", "failed", f"{failed} failed")
    return ctx.record("parent", "done" if (changed or ctx.dry_run) else "skipped", "")


# ── 6. 헌장 이식 ─────────────────────────────────────────────────────────────
def step6_charter(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step(6, "헌장(CHARTER.md) 이식 → ~/.cys/pack-dept-<dept-N>/")
    statuses = []
    for d in ctx.targets():
        if not d.charter_file:
            continue
        src = ctx.pkg_dir / Path(d.charter_file.replace("\\", "/"))
        did = dept_id_for(ctx, d)
        if not did:
            if ctx.dry_run:
                log.plan(f"{src.name} → {ctx.cys_home / 'pack-dept-<발급번호>' / 'CHARTER.md'}  [{d.key}]")
                statuses.append("done")
            else:
                log.warn(f"[{d.key}] 부서 번호를 몰라 헌장을 옮기지 못했습니다(부서 생성 실패 참조)")
            continue
        statuses.append(_copy_if_changed(ctx, src, ctx.cys_home / f"pack-dept-{did}" / "CHARTER.md", f"헌장[{d.key}]"))
    if not statuses:
        log.same("헌장 선언 없음")
    return ctx.record("charter", "done" if "done" in statuses else "skipped", "")


# ── 7. 기술자 클론 ───────────────────────────────────────────────────────────
def step7_clone(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step(7, "기술자 리포 클론 (번들 git · --depth 1)")
    if ctx.only:
        log.info(f"--only 활성 — 선택한 {len(ctx.only)}종만 내려받는다. 부서 선언·좌석 수렴은 전체 유지")
    git = str(ctx.lay["git"])
    env = resolve.env_for_tools(ctx.root, ctx.home)
    failed = cloned = 0
    for d, t in ctx.mf.all_techs(ctx.dept):
        if not ctx.selected(t):
            continue
        if t.delivery == "hosted":
            log.same(f"{t.id}: 호스팅 — 설치 대상 아님")
            continue
        if not t.installable:
            log.warn(f"{t.id}: repo/cwd 선언이 없어 건너뜀")
            continue
        dest = ctx.expand(t.cwd_template)
        assert dest is not None
        if (dest / ".git").exists():
            log.same(f"이미 있음: {dest}")
            continue
        if dest.exists():
            broken = Path(str(dest) + f".broken-{now_ts()}")
            log.act(f"git 리포가 아닌 폴더를 치운다: {dest} → {broken.name}")
            if not ctx.dry_run:
                try:
                    shutil.move(str(dest), str(broken))
                except OSError as e:
                    log.fail(f"[{t.id}] 폴더를 옮기지 못했습니다: {e}")
                    failed += 1
                    continue
        log.act(f"clone {t.repo} → {dest}" + ("" if t.required else "  (선택 항목)"))
        if ctx.dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        rc, out, err = run_capture([git, "clone", "--depth", "1", str(t.repo), str(dest)], env, timeout=1800)
        if rc != 0 or not (dest / ".git").exists():
            why = tail(err or out, 2)
            if t.visibility == "private":
                log.warn(f"[{t.id}] 클론 실패 — 비공개(PRIVATE) 리포입니다. 접근 권한이 필요합니다. 나머지 설치는 계속합니다: {why}")
            elif t.optional:
                log.warn(f"[{t.id}] 클론 실패(선택 항목) — 인터넷 연결을 확인해 주세요: {why}")
            else:
                failed += 1
                log.fail(f"[{t.id}] 클론 실패 — 인터넷 연결을 확인해 주세요: {t.repo} ({why})")
            continue
        cloned += 1
        log.ok(f"{dest}")
    if failed:
        return ctx.record("clone", "failed", f"{failed} failed")
    return ctx.record("clone", "done" if cloned or ctx.dry_run else "skipped", f"{cloned} cloned")


# ── 8. 의존성 ────────────────────────────────────────────────────────────────
def resolve_install_argv(ctx: Ctx, cmd: str, runtime: str) -> list[str] | None:
    """선언된 install 문자열을 (번들 실행체 + 인자배열)로 — 셸 해석 없음(매니페스트 한 줄 = 임의 코드 실행 차단)."""
    tok = cmd.split()
    if not tok:
        return None
    head, rest = tok[0], tok[1:]
    py = str(ctx.lay["python3"])
    if head in ("pip", "pip3"):
        return [py, "-m", "pip"] + rest
    if head in ("python", "python3"):
        return [py] + rest
    if head in ("npm", "npx"):
        if resolve.IS_WIN:
            js = resolve.npm_cli_js(ctx.root) if ctx.root else None
            if js:
                node = str(ctx.lay["node"])
                if head == "npx":
                    js = js.with_name("npx-cli.js")
                return [node, str(js)] + rest
            return None
        exe = ctx.lay["npm"] if head == "npm" else ctx.lay["npm"].with_name("npx")
        return [str(exe)] + rest
    if head == "node":
        return [str(ctx.lay["node"])] + rest
    return None


def step8_deps(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step("8", "의존성 설치 (번들 node/python · 기본 on · --no-deps 로 끔)")
    if ctx.deps is False:
        log.info("--no-deps — 의존성 설치를 건너뜁니다")
        return ctx.record("deps", "skipped", "--no-deps")
    env = resolve.env_for_tools(ctx.root, ctx.home)
    failed = done = 0
    for d, t in ctx.mf.all_techs(ctx.dept):
        if not ctx.selected(t) or t.delivery == "hosted" or not t.installable:
            continue
        cmd = t.install_cmd
        if not cmd:
            log.same(f"{t.id}: 의존성 선언 없음")
            continue
        dest = ctx.expand(t.cwd_template)
        assert dest is not None
        if not (dest / ".git").exists():
            log.same(f"{t.id}: 아직 클론 안 됨 — 의존성 대상 아님")
            continue
        if re.match(r"^\s*(npm|pnpm|yarn)\b", cmd) and (dest / "node_modules").exists():
            log.same(f"{t.id}: 이미 설치됨(node_modules)")
            continue
        argv = resolve_install_argv(ctx, cmd, t.runtime)
        if not argv:
            failed += 1
            log.fail(f"[{t.id}] 설치 명령을 실행할 수 없습니다 — '{cmd}' 의 실행 파일을 번들에서 찾지 못했습니다")
            continue
        if not Path(argv[0]).exists():
            failed += 1
            log.fail(f"[{t.id}] 런타임 '{t.runtime}' 이 자비스 번들에 없습니다: {argv[0]}")
            continue
        log.act(f"{t.id}: {cmd}   (cwd={dest})")
        if ctx.dry_run:
            continue
        rc, out, err = run_capture(argv, env, cwd=dest, timeout=1800)
        if rc != 0:
            failed += 1
            log.fail(f"[{t.id}] 의존성 설치 실패 exit={rc}: {tail(err or out, 3)}")
            continue
        done += 1
        log.ok(f"{t.id} 의존성 설치 완료")
    if failed:
        return ctx.record("deps", "failed", f"{failed} failed")
    return ctx.record("deps", "done" if done or ctx.dry_run else "skipped", f"{done} installed")


# ── 9. 좌석 정합 ─────────────────────────────────────────────────────────────
def step9_seats(ctx: Ctx) -> tuple[str, str]:
    log = ctx.log
    log.step(9, "기술자 좌석(surface) 정합 — 데몬 ping 후 선언 vs 실좌석 수렴")
    depts = load_depts(ctx)
    plan: list[dict] = []
    reachable = 0
    for d in ctx.targets():
        if not d.techs:
            continue
        hit = dept_by_mission(depts, d.mission_key)
        if not hit or not hit[1].get("socket"):
            log.warn(f"[{d.key}] depts.json 에 소켓 매핑이 없어 좌석 정합을 건너뜁니다" + (" (dry-run: 부서 미생성)" if ctx.dry_run else ""))
            continue
        did, sock = hit[0], str(hit[1]["socket"])
        wait = ctx.ping_wait if not ctx.dry_run else min(ctx.ping_wait, 3.0)
        if not cys_ping(ctx, sock, wait_s=wait):
            log.warn(f"[{d.key}] 부서 데몬 무응답({int(wait)}초) — 판정 보류(좌석을 지우지 않습니다)")
            continue
        seats = cys_list(ctx, sock)
        if seats is None:
            log.warn(f"[{d.key}] 좌석 목록을 읽지 못해 판정 보류")
            continue
        reachable += 1
        live = [s for s in seats if not s.exited]
        want = [t.name for t in d.techs]
        have = [s for s in live if s.role == "-"]
        log.info(f"=== {d.display} [{did}] {d.key} ===")
        log.info(f"  목표 기술자 {len(want)}: {', '.join(want)}")
        log.info(f"  현재 기술자 {len(have)}: {', '.join(f'{s.title}#{s.id}' for s in have) or '-'}")
        for t in d.techs:
            if not any(s.title == t.name for s in have):
                cwd = ctx.expand(t.cwd_template)
                plan.append({"dept": d.key, "sock": sock, "act": "create", "title": t.name,
                             "cwd": str(cwd) if cwd and cwd.exists() else str(ctx.home), "why": "선언에 있으나 좌석 없음"})
        by_title: dict[str, list[Seat]] = {}
        for s in have:
            by_title.setdefault(s.title, []).append(s)
        for title, group in by_title.items():
            if title not in want:
                for s in group:
                    plan.append({"dept": d.key, "sock": sock, "act": "reap", "title": title, "id": s.id, "why": "선언에 없는 좌석"})
            elif len(group) > 1:
                for dup in sorted(group, key=lambda s: s.id)[:-1]:  # 가장 최근(높은 id) 하나만 남긴다
                    plan.append({"dept": d.key, "sock": sock, "act": "reap", "title": title, "id": dup.id,
                                 "why": f"중복 {len(group)}좌석 중 구본"})
        roles = [s for s in live if s.role != "-"]
        if roles:
            log.info(f"  역할 좌석 {len(roles)}개는 건드리지 않습니다")
    if not plan:
        log.same("수렴 완료 — 편차 없음" if reachable else "판정 가능한 부서 없음")
        return ctx.record("seats", "skipped" if reachable else "skipped", "no-diff" if reachable else "unreachable")
    log.info("-- 좌석 계획 --")
    for p in plan:
        log.act(f"[{p['dept']}] {p['act']} '{p['title']}'{('#' + str(p['id'])) if p.get('id') else ''} — {p['why']}")
    if ctx.dry_run:
        return ctx.record("seats", "done", f"planned {len(plan)}")
    cys = str(ctx.lay["cys"])
    failed = 0
    for p in plan:
        env = cys_env(ctx, p["sock"])
        if p["act"] == "create":
            rc, out, err = run_capture([cys, "new-surface", "--socket", p["sock"], "--title", p["title"], "--cwd", p["cwd"]], env, timeout=60)
            if rc != 0:
                failed += 1
                log.fail(f"[{p['dept']}] 좌석 생성 실패 '{p['title']}' exit={rc}: {tail(err or out, 2)}")
            else:
                log.ok(f"[{p['dept']}] '{p['title']}' → {out.strip()}")
        else:
            rc, out, err = run_capture([cys, "close-surface", "--socket", p["sock"], "--reap", str(p["id"])], env, timeout=60)
            if rc != 0:
                failed += 1
                log.fail(f"[{p['dept']}] 좌석 제거 실패 '{p['title']}'#{p['id']} exit={rc}: {tail(err or out, 2)}")
            else:
                log.ok(f"[{p['dept']}] '{p['title']}'#{p['id']} 제거")
        time.sleep(ctx.pause)
    if failed:
        return ctx.record("seats", "failed", f"{failed} failed")
    return ctx.record("seats", "done", f"{len(plan)} applied")


# ── 10. 수신부 ───────────────────────────────────────────────────────────────
def step10_receiver(ctx: Ctx) -> tuple[str, str]:
    from . import receiver
    ctx.log.step(10, "원클릭 수신부(cys-install://) 등록")
    st, detail = receiver.register(ctx)
    return ctx.record("receiver", st, detail)


# ── 실행기 ───────────────────────────────────────────────────────────────────
STEP_ORDER = (step1_catalog, step2_missions, step3_workdirs, step4_create_depts, step5_parent_backfill,
              step6_charter, step7_clone, step8_deps, step9_seats, step10_receiver)


def run_all(ctx: Ctx) -> int:
    """0~11 전 단계. 종료코드: 0 성공 · 1 실패 있음 · 10 자비스 없음."""
    from . import doctor
    log = ctx.log
    st, detail = step0_selfdiag(ctx)
    if st == "failed":
        log.banner(False, "자비스 런타임")
        log.desktop_copy()
        return 10 if detail == "javis-missing" else 1
    for fn in STEP_ORDER:
        try:
            fn(ctx)
        except Exception as e:  # 한 단계의 예외가 나머지 단계·보고를 삼키지 않게 한다
            log.fail(f"{fn.__name__}: 예기치 못한 오류 — {type(e).__name__}: {e}")
            ctx.record(fn.__name__, "failed", str(e))
    log.step(11, "설치 자가 진단(doctor)")
    result = doctor.run(ctx)
    doctor.report(ctx, result)
    doctor.write_result(ctx, result)
    ok = (not log.failures) and bool(result.get("ok"))
    log.desktop_copy()
    log.banner(ok, "" if ok else "진단 실패 항목 참조")
    log.desktop_copy()
    return 0 if ok else 1


def make_ctx(pkg_dir: Path, *, sub: str = "install", dry_run: bool = False, ci: bool = False,
             dept: str | None = None, only: list[str] | None = None, deps: bool | None = None,
             log: Log | None = None) -> Ctx:
    from . import manifest as mf_mod
    pkg_dir = Path(pkg_dir)
    mf = mf_mod.load(pkg_dir)
    home = resolve.cys_home()
    root = resolve.javis_root()
    lay = resolve.layout(root) if root else {}
    log = log or Log(home, sub, dry_run=dry_run, ci=ci)
    try:
        pause = float(os.environ.get("FM_PAUSE", "1.2"))
    except ValueError:
        pause = 1.2
    try:
        ping_wait = float(os.environ.get("FM_PING_WAIT", "30"))
    except ValueError:
        ping_wait = 30.0
    if dept and not mf.dept(dept):
        raise ValueError(f"대상 부서가 없다: '{dept}' (가능: {', '.join(d.key for d in mf.departments)})")
    if only:
        known = mf.tech_ids()
        bad = [o for o in only if o not in known]
        if bad:
            raise ValueError(f"--only 에 없는 기술자 id: {', '.join(bad)} (가능: {', '.join(known)})")
    return Ctx(pkg_dir=pkg_dir, mf=mf, home=home, root=root, lay=lay, log=log, dry_run=dry_run, ci=ci,
               dept=dept, only=only, deps=deps, pause=pause, ping_wait=ping_wait)
