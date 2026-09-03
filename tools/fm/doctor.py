"""실물 검사(스펙 §4) — 필수 항목 하나라도 실패 = exit 1.

검사: 런타임 5종 · 카탈로그 키 · 미션 파일 · 작업 폴더 · depts.json 부서 키 · pack-dept-* 디렉터리 ·
부서 데몬 소켓 ping · 필수 기술자 .git · 수신부 등록.
결과 JSON: {ok, checks:[{id,required,ok,detail,fix}], log, os, ts} → ~/.cys/fm-install/last-result.json
(dry-run 은 stdout 만).
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import resolve
from .steps import Ctx, atomic_write_json, cys_ping, dept_by_mission, load_depts, read_json

RESULT_NAME = "last-result.json"


def result_path(home: Path) -> Path:
    return Path(home) / ".cys" / "fm-install" / RESULT_NAME


def _chk(checks: list, cid: str, required: bool, ok: bool, detail: str, fix: str = "") -> None:
    checks.append({"id": cid, "required": bool(required), "ok": bool(ok), "detail": detail, "fix": fix})


def run(ctx: Ctx) -> dict:
    checks: list[dict] = []
    from . import receiver
    # 1. 런타임
    probe = ctx.probe or (resolve.probe(ctx.root) if ctx.root else resolve.probe(None))
    for p in probe:
        _chk(checks, f"runtime:{p['name']}", p["required"], p["ok"],
             f"{p['version'] or '-'} {p['path']}" + (f" ({p['error']})" if p["error"] else ""),
             "자비스 앱을 다시 설치해 주세요" if p["required"] else "의존성 설치에만 필요합니다")
    # 2. 카탈로그
    cat_path = ctx.cys_home / "dept-catalog.json"
    cat: dict = {}
    if cat_path.exists():
        try:
            cat = read_json(cat_path)
        except Exception:
            cat = {}
    depts_map = cat.get("departments") if isinstance(cat.get("departments"), dict) else {}
    for d in ctx.targets():
        _chk(checks, f"catalog:{d.key}", True, d.key in depts_map,
             "등록됨" if d.key in depts_map else f"카탈로그에 없음 ({cat_path})", "설치를 다시 실행해 주세요")
    # 3. 미션
    for d in ctx.targets():
        if not d.mission_file:
            continue
        p = ctx.cys_home / "dept-missions" / f"{d.mission_key}.md"
        _chk(checks, f"mission:{d.key}", True, p.exists(), str(p), "설치를 다시 실행해 주세요")
    # 4. 작업 폴더
    for d in ctx.targets():
        p = ctx.expand(d.cwd_template)
        _chk(checks, f"workdir:{d.key}", True, bool(p and p.is_dir()), str(p), "설치를 다시 실행해 주세요")
    # 5~7. depts.json · pack-dept · ping
    reg = load_depts(ctx)
    for d in ctx.targets():
        hit = dept_by_mission(reg, d.mission_key)
        _chk(checks, f"dept:{d.key}", True, bool(hit),
             f"{hit[0]} ({hit[1].get('display_name', '')})" if hit else "depts.json 에 등록 없음",
             "자비스 앱을 켠 뒤 설치를 다시 실행해 주세요")
        if not hit:
            _chk(checks, f"pack:{d.key}", True, False, "부서 미등록", "설치를 다시 실행해 주세요")
            _chk(checks, f"ping:{d.key}", True, False, "부서 미등록", "설치를 다시 실행해 주세요")
            continue
        did, e = hit
        pack = ctx.cys_home / f"pack-dept-{did}"
        _chk(checks, f"pack:{d.key}", True, pack.is_dir(), str(pack), "설치를 다시 실행해 주세요")
        sock = str(e.get("socket") or "")
        alive = bool(sock) and cys_ping(ctx, sock, wait_s=min(5.0, ctx.ping_wait))
        _chk(checks, f"ping:{d.key}", True, alive, f"{sock} {'응답' if alive else '무응답'}",
             "자비스 앱을 켜 두고(부서 데몬이 살아 있어야 합니다) 설치를 다시 실행해 주세요")
    # 8. 필수 기술자 .git
    for d, t in ctx.mf.all_techs(ctx.dept):
        if t.delivery == "hosted" or not t.installable:
            continue
        if ctx.only is not None and t.id not in ctx.only:
            continue
        dest = ctx.expand(t.cwd_template)
        ok = bool(dest and (dest / ".git").is_dir())
        _chk(checks, f"tech:{t.id}", t.required, ok, str(dest),
             "인터넷 연결을 확인하고 설치를 다시 실행해 주세요" if t.required else "선택 항목입니다")
    # 9. 수신부
    st = receiver.status(ctx)
    _chk(checks, "receiver", True, st["ok"], st["detail"], "설치를 다시 실행하면 다시 등록됩니다")

    ok = all(c["ok"] for c in checks if c["required"])
    return {"ok": ok, "checks": checks, "log": str(ctx.log.path), "os": resolve.OS_KEY,
            "ts": _dt.datetime.now().isoformat(timespec="seconds"), "dry_run": ctx.dry_run,
            "package": ctx.mf.package, "manifest_version": ctx.mf.version, "pkg_dir": str(ctx.pkg_dir),
            "pkg_commit": ctx.pkg_commit}


def report(ctx: Ctx, result: dict) -> None:
    log = ctx.log
    log.raw("---- 설치 자가 진단 ----")
    for c in result["checks"]:
        mark = "[성공]" if c["ok"] else ("[실패]" if c["required"] else "[참고]")
        log.raw(f"{mark} {c['id']} — {c['detail']}")
        if not c["ok"] and c.get("fix"):
            log.raw(f"       → {c['fix']}")
    bad = [c for c in result["checks"] if c["required"] and not c["ok"]]
    if result["ok"]:
        log.raw("진단 결과: 필수 항목이 모두 정상입니다.")
    else:
        log.raw(f"진단 결과: {len(bad)}개 필수 항목이 아직 안 되어 있습니다. 위의 → 안내대로 해 주세요.")
        if ctx.dry_run:
            log.raw("(dry-run 이라 실제로 바꾸지 않았습니다 — 위 실패는 '아직 설치 전'이라는 뜻일 수 있습니다)")


def write_result(ctx: Ctx, result: dict) -> Path | None:
    if ctx.dry_run:
        ctx.log.raw("(dry-run) last-result.json 은 쓰지 않습니다 — 아래는 그 내용입니다")
        ctx.log.raw(json.dumps(result, ensure_ascii=False, indent=2))
        return None
    p = result_path(ctx.home)
    try:
        atomic_write_json(p, result)
        ctx.log.info(f"진단 결과 저장: {p}")
        return p
    except Exception as e:
        ctx.log.warn(f"진단 결과를 저장하지 못했습니다: {e}")
        return None
