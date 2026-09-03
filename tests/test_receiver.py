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
            # (c) 설치 진행이 보이게: 임시 .command 를 ~/.cys/fm-install 아래에 쓰고 Terminal 로 연다
            self.assertIn('" handle " & quoted form of theURL', s)
            self.assertIn('do shell script "open -a Terminal " & quoted form of cmdFile', s)
            self.assertIn('& "/handle-" & stamp & ".command"', s)
            self.assertIn("#!/bin/bash", s)
            self.assertIn('read -p \\"엔터를 누르면 창이 닫힙니다\\"', s)
            self.assertIn("chmod +x", s)
            self.assertIn(receiver._as_str(str(sb.pkg / "tools" / "install.sh")), s)  # AppleScript 문자열 이스케이프 반영
            self.assertIn(receiver._as_str(str(sb.home / ".cys" / "fm-install")), s)
            self.assertIn("display notification", s)
            self.assertNotIn('do shell script "/bin/bash " & quoted form of sh', s, "숨은 실행(do shell script 직접) 금지")

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
