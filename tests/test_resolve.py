import os
import tempfile
import unittest
from pathlib import Path

from fm_testlib import Sandbox, javis_ready  # noqa: F401  (sys.path 설정)
from fm import resolve


class ResolveLayoutTest(unittest.TestCase):
    def test_layout_paths(self):
        root = Path("C:/x/cys") if resolve.IS_WIN else Path("/Applications/cys.app")
        lay = resolve.layout(root)
        self.assertEqual(set(lay), set(resolve.ALL_NAMES))
        if resolve.IS_WIN:
            self.assertEqual(lay["cys"], root / "cys.exe")
            self.assertEqual(lay["python3"], root / "runtime" / "python" / "python3.exe")
            self.assertEqual(lay["git"], root / "runtime" / "git" / "cmd" / "git.exe")
            self.assertEqual(lay["bash"], root / "runtime" / "git" / "usr" / "bin" / "bash.exe")
            self.assertEqual(lay["npm"], root / "runtime" / "node" / "npm.cmd")
        else:
            self.assertEqual(lay["cys"], root / "Contents" / "MacOS" / "cys")
            self.assertEqual(lay["python3"], root / "Contents" / "Resources" / "runtime" / "python" / "bin" / "python3")
            self.assertEqual(lay["bash"], Path("/bin/bash"))

    def test_path_prepend_order(self):
        root = Path("C:/x/cys") if resolve.IS_WIN else Path("/Applications/cys.app")
        pre = resolve.path_prepend(root)
        if resolve.IS_WIN:
            self.assertEqual(pre[0], str(root))
            self.assertTrue(pre[1].endswith("python"))
            self.assertTrue(pre[2].endswith("cmd"))
            self.assertTrue(pre[3].endswith("bin"))
            self.assertTrue(pre[4].endswith("node"))
        else:
            self.assertTrue(pre[0].endswith("MacOS"))
            self.assertIn("/usr/bin", pre)
            self.assertIn("/bin", pre)

    def test_javis_root_override(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["FM_JAVIS_ROOT"] = d
            try:
                self.assertEqual(resolve.javis_root(), Path(d))
                os.environ["FM_JAVIS_ROOT"] = str(Path(d) / "nope")
                self.assertIsNone(resolve.javis_root())
            finally:
                os.environ.pop("FM_JAVIS_ROOT", None)

    def test_to_bash_arg(self):
        if resolve.IS_WIN:
            self.assertEqual(resolve.to_bash_arg(Path(r"C:\Users\신이재\.cys\pack\bin\cys-dept")),
                             "C:/Users/신이재/.cys/pack/bin/cys-dept")
        else:
            self.assertEqual(resolve.to_bash_arg(Path("/a/b")), "/a/b")


class ResolveEnvTest(unittest.TestCase):
    def test_env_for_cys_dept_contract(self):
        saved = {k: os.environ.get(k) for k in ("CYS_ROLE", "CYS_SOCKET", "ORIGINAL_PATH", "MSYS_NO_PATHCONV", "FM_HOME")}
        os.environ["CYS_ROLE"] = "worker"
        os.environ["CYS_SOCKET"] = "x"
        os.environ["ORIGINAL_PATH"] = "y"
        os.environ["MSYS_NO_PATHCONV"] = "1"
        with tempfile.TemporaryDirectory() as d:
            os.environ["FM_HOME"] = d
            try:
                root = Path("C:/x/cys") if resolve.IS_WIN else Path("/Applications/cys.app")
                env = resolve.env_for_cys_dept(root)
                self.assertFalse([k for k in env if k.upper().startswith("CYS_")], "CYS_* 전삭제")
                self.assertNotIn("ORIGINAL_PATH", env)
                self.assertNotIn("MSYS_NO_PATHCONV", env, "★켜면 cys-dept python heredoc 인자 경로가 깨진다(실측)")
                self.assertEqual(env["PYTHONUTF8"], "1")
                self.assertEqual(env["HOME"], d)
                pre = resolve.path_prepend(root)
                self.assertTrue(env["PATH"].startswith(os.pathsep.join(pre)), env["PATH"][:200])
                # 원래 PATH 는 뒤에 보존된다
                self.assertIn(os.environ["PATH"].split(os.pathsep)[0], env["PATH"])
                tools = resolve.env_for_tools(root)
                self.assertEqual(tools["GIT_TERMINAL_PROMPT"], "0")
                cys = resolve.env_for_cys(root, socket="S")
                self.assertEqual(cys["CYS_SOCKET"], "S")
                self.assertEqual(cys["CYS_NO_AUTOSTART"], "1")
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

    def test_home_report_forced(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["FM_HOME"] = d
            try:
                hr = resolve.home_report()
                self.assertEqual(hr["home"], Path(d))
                self.assertTrue(hr["forced"])
                self.assertFalse(hr["match"])
            finally:
                os.environ.pop("FM_HOME", None)


@unittest.skipUnless(javis_ready(), "이 PC 에 자비스 런타임이 없다")
class ResolveProbeRealTest(unittest.TestCase):
    """실물 자비스 런타임을 읽기 전용으로 --version 실행한다(쓰기 0)."""

    def test_probe_real_runtime(self):
        rows = {p["name"]: p for p in resolve.probe()}
        self.assertEqual(set(rows), set(resolve.ALL_NAMES))
        for n in ("cys", "python3", "git", "bash"):
            self.assertTrue(rows[n]["ok"], rows[n])
            self.assertRegex(rows[n]["version"], r"^\d+\.\d+")
        # cysd 는 실행하지 않는다(--version 이 데몬 기동을 시도한다) — 존재만 확인
        self.assertTrue(rows["cysd"]["ok"])
        self.assertIn("cys", rows["cysd"]["version"])
        self.assertTrue(rows["cysd"]["required"])
        self.assertFalse(rows["node"]["required"])


if __name__ == "__main__":
    unittest.main()
