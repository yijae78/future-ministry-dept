import json
import unittest

from fm_testlib import Sandbox
from fm import receiver, resolve, steps


class ReceiverTest(unittest.TestCase):
    def test_win_command_shape(self):
        with Sandbox() as sb:
            ctx = steps.make_ctx(sb.pkg, sub="receiver-register", dry_run=True)
            cmd = receiver.win_command(ctx)
            self.assertTrue(cmd.endswith('handle "%1"'))
            self.assertIn("-X utf8", cmd)
            self.assertIn(str(sb.pkg / "tools" / "fm" / "cli.py"), cmd)
            self.assertTrue(cmd.startswith('"'), "python 절대경로는 따옴표로 감싼다(PATH 무의존)")

    def test_mac_script_quotes_url_and_uses_install_sh(self):
        with Sandbox() as sb:
            ctx = steps.make_ctx(sb.pkg, sub="receiver-register", dry_run=True)
            s = receiver.mac_script(ctx)
            self.assertIn("on open location theURL", s)
            self.assertIn('do shell script "/bin/bash " & quoted form of sh & " handle " & quoted form of theURL', s)
            self.assertIn(receiver._as_str(str(sb.pkg / "tools" / "install.sh")), s)  # AppleScript 문자열 이스케이프 반영
            self.assertIn("display notification", s)
            self.assertIn("fm-install", s)

    def test_dry_run_register_touches_nothing(self):
        with Sandbox() as sb:
            ctx = steps.make_ctx(sb.pkg, sub="receiver-register", dry_run=True)
            self.assertEqual(receiver.register(ctx), ("done", "planned"))
            self.assertFalse((sb.cys / "fm-install").exists())
            self.assertFalse(receiver.status(ctx)["ok"])

    def test_sandbox_register_status_roundtrip(self):
        with Sandbox() as sb:
            ctx = steps.make_ctx(sb.pkg, sub="receiver-register")
            st, detail = receiver.register(ctx)
            self.assertEqual(st, "done")
            self.assertTrue(receiver.status(ctx)["ok"], receiver.status(ctx))
            self.assertEqual(receiver.register(ctx), ("skipped", "unchanged"))
            rec = json.loads((sb.cys / "fm-install" / "receiver-sandbox.json").read_text(encoding="utf-8"))
            if resolve.IS_WIN:
                self.assertEqual(rec["command"], receiver.win_command(ctx))


if __name__ == "__main__":
    unittest.main()
