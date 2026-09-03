import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fm_testlib import REPO_ROOT, Sandbox, javis_ready
from fm import cli, resolve


class CliArgTest(unittest.TestCase):
    def test_default_subcommand_is_bootstrap(self):
        p = cli.build_parser()
        a = p.parse_args(["--dry-run", "bootstrap"])
        self.assertEqual(a.cmd, "bootstrap")
        self.assertTrue(a.dry_run)

    def test_env_exit_code(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(["env"])
        out = buf.getvalue()
        self.assertIn("HOME(cys)", out)
        if javis_ready():
            self.assertEqual(rc, 0, out)
            self.assertIn("python3", out)
        else:
            self.assertEqual(rc, 10)

    def test_install_bad_only_exit_2(self):
        with Sandbox() as sb:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.main(["install", "--dry-run", "--pkg-dir", str(sb.pkg), "--only", "nope"])
            if javis_ready():
                self.assertEqual(rc, 2)
                self.assertIn("--only 에 없는 기술자", buf.getvalue())
            else:
                self.assertEqual(rc, 10)

    def test_install_bad_dept_exit_2(self):
        with Sandbox() as sb:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.main(["--dry-run", "install", "--dept", "nope", f"--pkg-dir={sb.pkg}"])
            self.assertEqual(rc, 2 if javis_ready() else 10)

    def test_missing_javis_exit_10(self):
        with Sandbox(javis_root=Path("C:/definitely/not/here") if resolve.IS_WIN else Path("/definitely/not/here")) as sb:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.main(["env"])
            self.assertEqual(rc, 10)
            self.assertIn("자비스가 아직 설치되지 않았습니다", buf.getvalue())
            with redirect_stdout(buf):
                rc = cli.main(["bootstrap", "--dry-run"])
            self.assertEqual(rc, 10)


@unittest.skipUnless(javis_ready(), "이 PC 에 자비스 런타임이 없다")
class CliSubprocessTest(unittest.TestCase):
    """번들 python3 로 cli.py 를 직접 실행(sys.path 처리 확인) — dry-run · 샌드박스."""

    def _run(self, sb, *args):
        py = resolve.layout(resolve.javis_root())["python3"]
        env = dict(os.environ)
        return subprocess.run([str(py), "-X", "utf8", str(REPO_ROOT / "tools" / "fm" / "cli.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                              stdin=subprocess.DEVNULL, timeout=300)

    def test_direct_script_dry_run_bootstrap(self):
        with Sandbox() as sb:
            os.environ["FM_PKG_DIR"] = str(sb.pkg)
            try:
                r = self._run(sb, "bootstrap", "--dry-run")
            finally:
                os.environ.pop("FM_PKG_DIR", None)
            self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
            out_lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
            self.assertTrue(out_lines[-1].startswith("[FAIL]") or out_lines[-1].startswith("[OK]"), out_lines[-3:])
            self.assertIn("FM_PKG_DIR", r.stdout)
            self.assertIn("(예정) bash cys-dept create future-ministry", r.stdout)
            self.assertIn("퓨처 미니스트리 설치기 v2 — 자기진단", r.stdout)
            self.assertNotIn("Traceback", r.stderr)

    def test_direct_script_handle_bad_url(self):
        with Sandbox() as sb:
            r = self._run(sb, "--pkg-dir", str(sb.pkg), "handle", "cys-install://tech/BAD")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("알 수 없는 설치 주소", r.stdout)


if __name__ == "__main__":
    unittest.main()
