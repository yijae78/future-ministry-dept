"""steps 각 단계의 동작·멱등성 — HOME 샌드박스 + 가짜 cys-dept 스텁(bash · dept-9 출력)."""
import json
import os
import unittest
from pathlib import Path

from fm_testlib import Sandbox, javis_ready
from fm import resolve, steps
from fm.log import Log


def make_ctx(sb: Sandbox, **kw):
    kw.setdefault("sub", "install")
    return steps.make_ctx(sb.pkg, **kw)


class DryRunTest(unittest.TestCase):
    """dry-run: 실제 홈(샌드박스라도)에 아무것도 쓰지 않고 전 단계 '(예정)' 로그를 낸다."""

    def test_dry_run_writes_nothing(self):
        with Sandbox() as sb:
            ctx = make_ctx(sb, dry_run=True)
            rc = steps.run_all(ctx)
            self.assertEqual(rc, 1, "설치 전이라 doctor 는 실패해야 한다(거짓 성공 금지)")
            text = Path(ctx.log.path).read_text(encoding="utf-8")
            for expected in ("(예정) accounts['owner']", "(예정) departments['future-ministry'] 추가",
                             "(예정) 미션[fm-admin]", "(예정) 생성:", "(예정) bash cys-dept create future-ministry",
                             "(예정) bash cys-dept create fm-admin", "parent = 'Future Ministry(칼빈)'",
                             "CHARTER.md", "(예정) clone", "[OK]" if False else "[FAIL]"):
                self.assertIn(expected, text, expected)
            self.assertFalse((sb.cys / "dept-catalog.json").exists())
            self.assertFalse((sb.cys / "depts.json").exists())
            self.assertFalse((sb.cys / "dept-missions").exists())
            self.assertFalse((sb.home / "Future-Ministry").exists())
            self.assertFalse((sb.cys / "fm-install").exists(), "dry-run 은 ~/.cys/fm-install 에 로그·결과를 쓰지 않는다")
            self.assertFalse((sb.home / "Desktop" / "퓨처미니스트리-설치로그.txt").exists())
            # 마지막 stdout 줄 계약: [OK]/[FAIL] 한 줄
            last = [ln for ln in text.splitlines() if ln.strip()][-1]
            self.assertTrue(last.startswith("[FAIL]") or last.startswith("[OK]"), last)
            self.assertEqual(ctx.results["catalog"][0], "done")
            self.assertEqual(ctx.results["receiver"], ("done", "planned"))


@unittest.skipUnless(javis_ready(), "이 PC 에 자비스 런타임(bash·python3)이 없다")
class RealRunTest(unittest.TestCase):
    """실제 쓰기(샌드박스 한정) — 스텁 cys-dept 로 부서 생성, 로컬 리포 클론, 2회 실행 멱등."""

    def test_full_install_then_idempotent_rerun(self):
        with Sandbox() as sb:
            os.environ["CYS_ROLE"] = "worker"      # ★잔존 CYS_ROLE 은 삭제돼야 한다(스텁은 있으면 exit 7)
            os.environ["CYS_SOCKET"] = r"\\.\pipe\bogus"
            try:
                ctx = make_ctx(sb, deps=None)
                rc = steps.run_all(ctx)
            finally:
                os.environ.pop("CYS_ROLE", None)
                os.environ.pop("CYS_SOCKET", None)
            r = ctx.results
            self.assertEqual(r["catalog"][0], "done")
            self.assertEqual(r["missions"][0], "done")
            self.assertEqual(r["workdirs"][0], "done")
            self.assertEqual(r["depts"][0], "done", ctx.log.failures)
            self.assertEqual(r["parent"][0], "done")
            self.assertEqual(r["charter"][0], "done")
            self.assertEqual(r["clone"][0], "done", ctx.log.failures)
            self.assertEqual(r["deps"][0], "done", ctx.log.failures)
            self.assertEqual(r["seats"][0], "skipped")   # 가짜 소켓 → 데몬 무응답 → 판정 보류
            self.assertEqual(r["receiver"][0], "done")
            # 산출물 실물
            cat = sb.read_json(".cys/dept-catalog.json")
            self.assertEqual(cat["accounts"]["owner"], "$HOME/.cys/claude")
            self.assertEqual(set(cat["departments"]), {"future-ministry", "fm-admin", "fm-worship", "fm-sermon"})
            self.assertEqual(cat["departments"]["fm-admin"]["parent"], "Future Ministry(칼빈)")
            self.assertEqual(cat["departments"]["fm-worship"]["parent"], "Future Ministry(칼빈)", "키로 적힌 parent → 표시명")
            self.assertEqual([t["name"] for t in cat["departments"]["fm-admin"]["techs"]], ["frar", "Church-Admin"])
            self.assertNotIn("id", cat["departments"]["fm-admin"]["techs"][0], "카탈로그 투영은 name·repo·cwd 뿐")
            for k in ("future-ministry", "fm-admin", "fm-worship", "fm-sermon"):
                self.assertTrue((sb.cys / "dept-missions" / f"{k}.md").exists())
            self.assertTrue((sb.home / "Future-Ministry" / "행정관리부").is_dir())
            reg = sb.read_json(".cys/depts.json")["depts"]
            self.assertEqual(len(reg), 4)
            self.assertEqual(ctx.dept_id_of["future-ministry"], "dept-9")
            by_mk = {e["mission_key"]: e for e in reg.values()}
            self.assertNotIn("parent", by_mk["future-ministry"])
            for k in ("fm-admin", "fm-worship", "fm-sermon"):
                self.assertEqual(by_mk[k]["parent"], "Future Ministry(칼빈)")
            self.assertTrue((sb.cys / "pack-dept-dept-9" / "CHARTER.md").exists())
            self.assertTrue((sb.home / "Future-Ministry" / "행정관리부" / "frar" / ".git").exists())
            self.assertTrue((sb.home / "Future-Ministry" / "행정관리부" / "Church-Admin" / ".git").exists())
            self.assertTrue((sb.home / "Future-Ministry" / "설교기획부" / "pray-news" / ".git").exists())
            self.assertFalse((sb.home / "Future-Ministry" / "예배교육부" / "godsaengbook-grace").exists(), "hosted 는 클론 안 함")
            self.assertTrue((sb.cys / "fm-install" / "receiver-sandbox.json").exists())
            self.assertTrue((sb.cys / "fm-install" / "last-result.json").exists())
            self.assertEqual(len(sb.logs()), 1)
            self.assertTrue((sb.home / "Desktop" / "퓨처미니스트리-설치로그.txt").exists())
            # 스텁이 본 실행 환경: python3/cys 는 자비스 번들, CYS_ROLE 없음, MSYS_NO_PATHCONV 미설정
            text = Path(ctx.log.path).read_text(encoding="utf-8")
            self.assertNotIn("exit=7", text)
            # doctor: ping 만 실패(가짜 소켓) — 나머지 필수 항목은 전부 성공, 최종 rc=1(거짓 성공 금지)
            res = sb.read_json(".cys/fm-install/last-result.json")
            bad = sorted(c["id"] for c in res["checks"] if c["required"] and not c["ok"])
            self.assertEqual(bad, ["ping:fm-admin", "ping:fm-sermon", "ping:fm-worship", "ping:future-ministry"], bad)
            self.assertFalse(res["ok"])
            self.assertEqual(rc, 1)
            self.assertTrue(text.rstrip().splitlines()[-1].startswith("[FAIL]"))

            # ── 2회째 실행: 모든 쓰기 단계가 '이미 됨' 이어야 한다 ──
            ctx2 = make_ctx(sb, deps=None)
            rc2 = steps.run_all(ctx2)
            r2 = ctx2.results
            for name in ("catalog", "missions", "workdirs", "depts", "parent", "charter", "clone"):
                self.assertEqual(r2[name][0], "skipped", (name, r2[name], ctx2.log.failures))
            self.assertEqual(r2["receiver"][0], "skipped")
            self.assertEqual(rc2, rc)
            self.assertEqual(sb.read_json(".cys/depts.json")["depts"], reg, "재실행이 등록부를 바꾸지 않는다")
            self.assertEqual(sb.read_json(".cys/dept-catalog.json"), cat)
            self.assertEqual(len(sb.logs()), 2, "실행마다 새 로그 파일")
            self.assertEqual(len(list(sb.cys.glob("dept-catalog.json.bak-*"))), 0, "변경 없으면 백업도 없다")

    def test_catalog_preserves_user_values_and_rotates_backups(self):
        with Sandbox() as sb:
            cat = sb.cys / "dept-catalog.json"
            cat.write_text(json.dumps({"accounts": {"owner": "$HOME/.cys/claude", "extra": "$HOME/.cys/claude-x"},
                                       "departments": {"other-dept": {"display": "다른 부서", "account": "owner",
                                                                      "mission_key": "other", "cwd": "$HOME/O"},
                                                       "fm-admin": {"display": "옛이름", "account": "owner",
                                                                    "mission_key": "fm-admin", "cwd": "$HOME/x",
                                                                    "user_note": "keep me"}}},
                                      ensure_ascii=False), encoding="utf-8")
            for i in range(4):
                ctx = make_ctx(sb, dept="fm-admin", deps=False)
                steps.step1_catalog(ctx)
                # 매번 다르게 만들어 백업 회전을 유도
                d = json.loads(cat.read_text(encoding="utf-8"))
                d["departments"]["fm-admin"]["display"] = f"변경{i}"
                cat.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            d = json.loads(cat.read_text(encoding="utf-8"))
            self.assertIn("other-dept", d["departments"], "사용자 부서 보존")
            self.assertEqual(d["accounts"]["extra"], "$HOME/.cys/claude-x", "사용자 계정 보존")
            self.assertEqual(d["departments"]["fm-admin"]["user_note"], "keep me", "엔트리 안의 사용자 필드 보존")
            self.assertLessEqual(len(list(sb.cys.glob("dept-catalog.json.bak-*"))), 3, "백업 3개 회전")

    def test_exit_code_mapping_and_role_guard(self):
        with Sandbox() as sb:
            ctx = make_ctx(sb, dept="fm-admin", deps=False)
            steps.step1_catalog(ctx)
            os.environ["FM_STUB_EXIT"] = "8"
            try:
                st, _ = steps.step4_create_depts(ctx)
            finally:
                os.environ.pop("FM_STUB_EXIT", None)
            self.assertEqual(st, "failed")
            self.assertTrue(any("상한" in f for f in ctx.log.failures), ctx.log.failures)
            # exit 5: 계정 폴더 없음 메시지
            ctx = make_ctx(sb, dept="fm-admin", deps=False)
            os.environ["FM_STUB_EXIT"] = "5"
            try:
                steps.step4_create_depts(ctx)
            finally:
                os.environ.pop("FM_STUB_EXIT", None)
            self.assertTrue(any("계정 폴더" in f for f in ctx.log.failures), ctx.log.failures)
            for code in (2, 3, 4, 6, 7, 8, 1, 99):
                self.assertTrue(steps.exit_message(code))

    def test_parent_backfill_uses_display_and_is_idempotent(self):
        with Sandbox() as sb:
            ctx = make_ctx(sb, deps=False)
            steps.step1_catalog(ctx)
            steps.step4_create_depts(ctx)
            st, _ = steps.step5_parent_backfill(ctx)
            self.assertEqual(st, "done")
            reg = sb.read_json(".cys/depts.json")["depts"]
            subs = [e for e in reg.values() if e["mission_key"] != "future-ministry"]
            self.assertEqual({e["parent"] for e in subs}, {"Future Ministry(칼빈)"})
            ctx2 = make_ctx(sb, deps=False)
            steps.step4_create_depts(ctx2)   # REUSE
            self.assertEqual(ctx2.results["depts"][0], "skipped")
            st2, _ = steps.step5_parent_backfill(ctx2)
            self.assertEqual(st2, "skipped")

    def test_broken_clone_folder_is_moved_and_recloned(self):
        with Sandbox() as sb:
            dest = sb.home / "Future-Ministry" / "행정관리부" / "frar"
            dest.mkdir(parents=True)
            (dest / "junk.txt").write_text("x", encoding="utf-8")
            ctx = make_ctx(sb, dept="fm-admin", only=["frar"], deps=False)
            st, _ = steps.step7_clone(ctx)
            self.assertEqual(st, "done", ctx.log.failures)
            self.assertTrue((dest / ".git").exists())
            broken = list(dest.parent.glob("frar.broken-*"))
            self.assertEqual(len(broken), 1)
            self.assertTrue((broken[0] / "junk.txt").exists())

    def test_only_filters_clone_but_not_declaration(self):
        with Sandbox() as sb:
            ctx = make_ctx(sb, only=["frar"], deps=False)
            steps.step1_catalog(ctx)
            steps.step7_clone(ctx)
            cat = sb.read_json(".cys/dept-catalog.json")
            self.assertEqual(len(cat["departments"]), 4, "--only 는 선언(카탈로그)을 좁히지 않는다")
            self.assertTrue((sb.home / "Future-Ministry" / "행정관리부" / "frar" / ".git").exists())
            self.assertFalse((sb.home / "Future-Ministry" / "행정관리부" / "Church-Admin").exists())

    def test_deps_no_deps_and_unknown_command(self):
        with Sandbox() as sb:
            ctx = make_ctx(sb, dept="fm-admin", deps=False)
            steps.step7_clone(ctx)
            st, d = steps.step8_deps(ctx)
            self.assertEqual((st, d), ("skipped", "--no-deps"))
            ctx = make_ctx(sb, dept="fm-admin", deps=True)
            st, _ = steps.step8_deps(ctx)
            self.assertEqual(st, "done", ctx.log.failures)
            argv = steps.resolve_install_argv(ctx, "pip install -r requirements.txt", "python")
            self.assertEqual(argv[1:3], ["-m", "pip"])
            self.assertEqual(Path(argv[0]), Path(ctx.lay["python3"]))
            self.assertIsNone(steps.resolve_install_argv(ctx, "make all", "none"))
            argv = steps.resolve_install_argv(ctx, "npm install", "node")
            self.assertIsNotNone(argv)
            self.assertIn("install", argv)


class ParseHelpersTest(unittest.TestCase):
    def test_dept_name_regex(self):
        self.assertTrue(steps.DEPT_RE.match("dept-12"))
        self.assertFalse(steps.DEPT_RE.match("dept-12 "))
        self.assertFalse(steps.DEPT_RE.match("[cys-dept] dept-1"))

    def test_atomic_write_json_no_bom(self):
        with Sandbox(with_stub=False) as sb:
            p = sb.cys / "x.json"
            steps.atomic_write_json(p, {"한글": 1})
            b = p.read_bytes()
            self.assertFalse(b.startswith(b"\xef\xbb\xbf"))
            self.assertIn("한글".encode("utf-8"), b)
            self.assertEqual(json.loads(b.decode("utf-8")), {"한글": 1})
            self.assertEqual(list(sb.cys.glob("x.json.tmp-*")), [])


if __name__ == "__main__":
    unittest.main()
