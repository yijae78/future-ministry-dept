import json
import unittest

from fm_testlib import Sandbox, javis_ready
from fm import doctor, steps


class DoctorShapeTest(unittest.TestCase):
    def test_result_shape_before_install(self):
        with Sandbox() as sb:
            ctx = steps.make_ctx(sb.pkg, sub="doctor", dry_run=True)
            steps.step0_selfdiag(ctx)
            res = doctor.run(ctx)
            for k in ("ok", "checks", "log", "os", "ts"):
                self.assertIn(k, res)
            self.assertFalse(res["ok"])
            ids = [c["id"] for c in res["checks"]]
            for expected in ("runtime:cys", "runtime:python3", "catalog:future-ministry", "mission:fm-admin",
                             "workdir:fm-sermon", "dept:fm-worship", "pack:fm-worship", "ping:fm-worship",
                             "tech:frar", "receiver"):
                self.assertIn(expected, ids)
            self.assertNotIn("tech:godsaengbook-grace", ids, "hosted 는 검사 대상 아님")
            for c in res["checks"]:
                self.assertEqual(set(c), {"id", "required", "ok", "detail", "fix"})
            pn = next(c for c in res["checks"] if c["id"] == "tech:pray-news")
            self.assertFalse(pn["required"], "optional 기술자는 필수 아님")
            # dry-run: last-result.json 을 쓰지 않는다
            self.assertIsNone(doctor.write_result(ctx, res))
            self.assertFalse(doctor.result_path(sb.home).exists())

    def test_only_restricts_tech_checks(self):
        with Sandbox() as sb:
            ctx = steps.make_ctx(sb.pkg, sub="doctor", dry_run=True, only=["frar"])
            res = doctor.run(ctx)
            techs = [c["id"] for c in res["checks"] if c["id"].startswith("tech:")]
            self.assertEqual(techs, ["tech:frar"])


@unittest.skipUnless(javis_ready(), "이 PC 에 자비스 런타임이 없다")
class DoctorAfterInstallTest(unittest.TestCase):
    def test_write_result_and_required_failures(self):
        with Sandbox() as sb:
            ctx = steps.make_ctx(sb.pkg, sub="install", deps=False)
            steps.run_all(ctx)
            p = doctor.result_path(sb.home)
            self.assertTrue(p.exists())
            res = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(res["os"], ctx.probe and res["os"])
            bad = {c["id"] for c in res["checks"] if c["required"] and not c["ok"]}
            self.assertTrue(all(b.startswith("ping:") for b in bad), bad)
            ok_ids = {c["id"] for c in res["checks"] if c["ok"]}
            for expected in ("catalog:fm-admin", "mission:fm-admin", "workdir:fm-admin", "dept:fm-admin",
                             "pack:fm-admin", "tech:frar", "receiver", "runtime:cys", "runtime:bash"):
                self.assertIn(expected, ok_ids)
            # (a) 의존성은 참고 항목(required=false): --no-deps 로 돌렸으니 .fm-site 없음 → ok False 지만 필수 아님
            deps = {c["id"]: c for c in res["checks"] if c["id"].startswith("deps:")}
            self.assertIn("deps:frar", deps)
            self.assertFalse(deps["deps:frar"]["required"])
            self.assertIn(".fm-site 없음", deps["deps:frar"]["detail"])
            self.assertIn("실행.c", deps["deps:frar"]["detail"])
            self.assertNotIn("deps:pray-news", deps, "install 선언 없는 기술자는 의존성 항목 없음")
            # 매 실행 덮어쓰기
            ctx2 = steps.make_ctx(sb.pkg, sub="doctor", deps=False)
            steps.step0_selfdiag(ctx2)
            res2 = doctor.run(ctx2)
            doctor.write_result(ctx2, res2)
            self.assertNotEqual(json.loads(p.read_text(encoding="utf-8"))["log"], res["log"])


if __name__ == "__main__":
    unittest.main()
