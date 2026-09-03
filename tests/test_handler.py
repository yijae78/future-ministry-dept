import unittest
from pathlib import Path

from fm_testlib import Sandbox
from fm import handler


class WhitelistTest(unittest.TestCase):
    def test_accepts(self):
        self.assertEqual(handler.parse_url("cys-install://dept/future-ministry"), ("dept", "future-ministry"))
        self.assertEqual(handler.parse_url("cys-install://tech/frar/"), ("tech", "frar"))
        self.assertEqual(handler.parse_url("cys-install://tech/church-admin"), ("tech", "church-admin"))
        self.assertEqual(handler.parse_url(" cys-install://tech/frar \n"), ("tech", "frar"))

    def test_rejects(self):
        for bad in (None, "", "cys-install://dept/", "cys-install://Dept/frar", "cys-install://tech/FRAR",
                    "cys-install://tech/-x", "cys-install://tech/a b", "cys-install://tech/a;rm", "http://x/",
                    "cys-install://tech/a/b", "cys-install://tech/a?x=1", "cys-install://user/frar",
                    "cys-install://tech/한글", "cys-install://tech/frar&&calc"):
            self.assertIsNone(handler.parse_url(bad), bad)


class HandleFlowTest(unittest.TestCase):
    def test_bad_url_logs_and_exit_2(self):
        with Sandbox() as sb:
            rc = handler.handle("cys-install://tech/../etc", sb.pkg, dry_run=False, ci=True)
            self.assertEqual(rc, 2)
            logs = sb.logs()
            self.assertEqual(len(logs), 1, "실행 즉시 새 로그 파일")
            self.assertIn("-handle", logs[0].name)
            text = logs[0].read_text(encoding="utf-8")
            self.assertIn("알 수 없는 설치 주소", text)
            self.assertIn("[FAIL]", text)

    def test_unknown_tech_exit_2(self):
        with Sandbox() as sb:
            rc = handler.handle("cys-install://tech/nope", sb.pkg, dry_run=True, ci=True)
            self.assertEqual(rc, 2)
            rc = handler.handle("cys-install://dept/nope", sb.pkg, dry_run=True, ci=True)
            self.assertEqual(rc, 2)

    def test_tech_url_maps_to_only_and_dept_root_maps_to_all(self):
        import tempfile

        def latest_log() -> str:
            d = Path(tempfile.gettempdir()) / "fm-install" / "logs"   # dry-run 로그는 실제 홈이 아닌 임시 폴더
            p = max(d.glob("*-handle*.log"), key=lambda x: x.stat().st_mtime_ns)
            return p.read_text(encoding="utf-8")

        with Sandbox() as sb:
            rc = handler.handle("cys-install://tech/frar", sb.pkg, dry_run=True, ci=True)
            self.assertIn(rc, (0, 1))
            text = latest_log()
            self.assertIn("대상: tech / frar  (--only frar)", text)
            self.assertIn("(예정) clone", text)
            handler.handle("cys-install://dept/future-ministry", sb.pkg, dry_run=True, ci=True)
            text = latest_log()
            self.assertIn("대상: dept / future-ministry", text)
            self.assertNotIn("--dept", text.split("대상: dept / future-ministry")[1].splitlines()[0])
            handler.handle("cys-install://dept/fm-admin", sb.pkg, dry_run=True, ci=True)
            text = latest_log()
            self.assertIn("(--dept fm-admin)", text)


if __name__ == "__main__":
    unittest.main()
