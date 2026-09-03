"""manifest.json 로드·검증 — 스키마 고정.

departments[] 각: key/display/mission_key/parent/tier/account/cwd_template/mission_file/charter_file/techs[]
techs[] 각: name/id/repo/cwd_template/visibility/delivery/requires/skills (+optional)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import resolve

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")          # 화이트리스트(수신부와 동일)
DEPT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")  # cys-dept validate_dept_name 과 동일


class ManifestError(ValueError):
    pass


@dataclass
class Tech:
    name: str
    id: str
    repo: str | None
    cwd_template: str | None
    visibility: str = "public"
    delivery: str = "install"
    requires: dict = field(default_factory=dict)
    skills: list = field(default_factory=list)
    optional: bool = False
    display: str = ""
    type: str = ""

    @property
    def installable(self) -> bool:
        return self.delivery != "hosted" and bool(self.repo) and bool(self.cwd_template)

    @property
    def required(self) -> bool:
        """설치 성공 판정에 반드시 있어야 하는 기술자: 공개·설치형·optional 아님."""
        return self.installable and self.visibility == "public" and not self.optional

    @property
    def install_cmd(self) -> str | None:
        v = (self.requires or {}).get("install")
        return str(v).strip() if v else None

    @property
    def runtime(self) -> str:
        v = (self.requires or {}).get("runtime") or "none"
        return str(v)


@dataclass
class Dept:
    key: str
    display: str
    mission_key: str
    parent: str | None
    tier: int
    account: str
    cwd_template: str
    mission_file: str | None
    charter_file: str | None
    techs: list[Tech] = field(default_factory=list)


@dataclass
class Manifest:
    pkg_dir: Path
    path: Path
    package: str
    display: str
    version: str
    accounts: dict[str, str]
    departments: list[Dept]
    raw: dict

    # ── 조회 ──
    def dept(self, key: str) -> Dept | None:
        for d in self.departments:
            if d.key == key:
                return d
        return None

    def root(self) -> Dept:
        roots = [d for d in self.departments if d.tier == 0]
        return roots[0]

    def targets(self, dept: str | None = None) -> list[Dept]:
        ds = [d for d in self.departments if not dept or d.key == dept]
        return sorted(ds, key=lambda d: (d.tier, self.departments.index(d)))

    def all_techs(self, dept: str | None = None) -> list[tuple[Dept, Tech]]:
        return [(d, t) for d in self.targets(dept) for t in d.techs]

    def tech_ids(self) -> list[str]:
        return [t.id for _, t in self.all_techs()]

    def find_tech(self, tech_id: str) -> tuple[Dept, Tech] | None:
        for d, t in self.all_techs():
            if t.id == tech_id:
                return d, t
        return None

    def parent_display(self, dept: Dept) -> str | None:
        """depts.json 에 기록할 parent 값 — 부모의 **표시명**.

        UI(main.ts:3672-3680 parentOf/deptBareName)는 parent 를 부모의 bare display_name 과 비교한다.
        manifest 의 parent 가 부서 키(예: future-ministry)로 적혀 있어도 표시명으로 환산해 준다.
        """
        if not dept.parent:
            return None
        by_key = self.dept(dept.parent)
        if by_key:
            return by_key.display
        return dept.parent


def expand_home(template: str | None, home: Path | None = None) -> Path | None:
    """`$HOME/...`·`~/...` 템플릿을 이 PC 경로로 전개한다. 한글 경로는 Python 이 그대로 다룬다."""
    if not template:
        return None
    home = Path(home) if home else resolve.cys_home()
    t = str(template)
    if t.startswith("$HOME"):
        t = str(home) + t[len("$HOME"):]
    elif t.startswith("${HOME}"):
        t = str(home) + t[len("${HOME}"):]
    elif t == "~" or t.startswith("~/"):
        t = str(home) + t[1:]
    if resolve.IS_WIN:
        t = t.replace("/", "\\")
    return Path(t)


def _req(d: dict, k: str, where: str):
    if k not in d or d[k] in (None, ""):
        raise ManifestError(f"{where}: 필수 필드 '{k}' 가 없다")
    return d[k]


def load(pkg_dir: Path | str) -> Manifest:
    pkg_dir = Path(pkg_dir)
    path = pkg_dir / "manifest.json"
    if not path.exists():
        raise ManifestError(f"manifest.json 을 찾을 수 없다: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        raise ManifestError(f"manifest.json 을 읽지 못했다: {e}") from e
    return parse(raw, pkg_dir, path)


def parse(raw: dict, pkg_dir: Path, path: Path | None = None) -> Manifest:
    if not isinstance(raw, dict):
        raise ManifestError("manifest 최상위는 객체여야 한다")
    accounts = {k: v for k, v in (raw.get("accounts") or {}).items() if not k.startswith("_")}
    if "owner" not in accounts:
        raise ManifestError("accounts.owner 가 없다")
    deps_raw = raw.get("departments")
    if not isinstance(deps_raw, list) or not deps_raw:
        raise ManifestError("departments 배열이 비어 있다")
    depts: list[Dept] = []
    seen_keys: set[str] = set()
    seen_ids: set[str] = set()
    for i, d in enumerate(deps_raw):
        where = f"departments[{i}]"
        key = str(_req(d, "key", where))
        if not DEPT_KEY_RE.match(key) or len(key) > 40:
            raise ManifestError(f"{where}: 부서 키 '{key}' 가 규칙(^[A-Za-z0-9][A-Za-z0-9_-]*$·40자)에 맞지 않는다")
        if key in seen_keys:
            raise ManifestError(f"{where}: 부서 키 '{key}' 중복")
        seen_keys.add(key)
        tier = d.get("tier", 1)
        if not isinstance(tier, int):
            raise ManifestError(f"{where}: tier 는 정수여야 한다")
        account = str(_req(d, "account", where))
        if account not in accounts:
            raise ManifestError(f"{where}: account '{account}' 가 accounts 에 없다")
        techs: list[Tech] = []
        for j, t in enumerate(d.get("techs") or []):
            tw = f"{where}.techs[{j}]"
            name = str(_req(t, "name", tw))
            tid = str(t.get("id") or name).lower()
            if not SLUG_RE.match(tid):
                raise ManifestError(f"{tw}: id '{tid}' 가 슬러그 규칙(^[a-z0-9][a-z0-9-]*$)에 맞지 않는다")
            if tid in seen_ids:
                raise ManifestError(f"{tw}: 기술자 id '{tid}' 중복")
            seen_ids.add(tid)
            delivery = str(t.get("delivery") or "install")
            if delivery not in ("install", "hosted"):
                raise ManifestError(f"{tw}: delivery 는 install|hosted 여야 한다")
            if delivery == "install" and not t.get("repo"):
                raise ManifestError(f"{tw}: 설치형 기술자에 repo 가 없다")
            techs.append(Tech(
                name=name, id=tid, repo=t.get("repo"), cwd_template=t.get("cwd_template"),
                visibility=str(t.get("visibility") or "public"), delivery=delivery,
                requires=dict(t.get("requires") or {}), skills=list(t.get("skills") or []),
                optional=bool(t.get("optional", False)), display=str(t.get("display") or name),
                type=str(t.get("type") or ""),
            ))
        depts.append(Dept(
            key=key, display=str(_req(d, "display", where)), mission_key=str(_req(d, "mission_key", where)),
            parent=(str(d["parent"]) if d.get("parent") else None), tier=tier, account=account,
            cwd_template=str(_req(d, "cwd_template", where)), mission_file=d.get("mission_file"),
            charter_file=d.get("charter_file"), techs=techs,
        ))
    roots = [d for d in depts if d.tier == 0]
    if len(roots) != 1:
        raise ManifestError(f"tier 0(루트) 부서는 정확히 1개여야 한다 (지금 {len(roots)}개)")
    displays = {d.display for d in depts}
    for d in depts:
        if d.parent and d.parent not in seen_keys and d.parent not in displays:
            raise ManifestError(f"departments[{d.key}]: parent '{d.parent}' 가 어느 부서의 키·표시명도 아니다")
    return Manifest(pkg_dir=pkg_dir, path=path or (pkg_dir / "manifest.json"),
                    package=str(raw.get("package") or ""), display=str(raw.get("display") or ""),
                    version=str(raw.get("version") or ""), accounts=accounts, departments=depts, raw=raw)


def parse_only(value: str | list[str] | None) -> list[str] | None:
    """`--only a,b` / `--only a --only b` 를 소문자 집합 리스트로."""
    if not value:
        return None
    items = value if isinstance(value, list) else [value]
    out: list[str] = []
    for it in items:
        for s in str(it).split(","):
            s = s.strip().lower()
            if s and s not in out:
                out.append(s)
    return out or None
