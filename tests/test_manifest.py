import json
import os
import tempfile
import unittest
from pathlib import Path

from fm_testlib import REPO_ROOT  # noqa: F401  (sys.path 설정)
from fm import manifest as mf_mod
from fm import resolve


class RealManifestTest(unittest.TestCase):
    def test_load_real_manifest(self):
        mf = mf_mod.load(REPO_ROOT)
        self.assertEqual(len(mf.departments), 4)
        self.assertEqual(mf.root().key, "future-ministry")
        self.assertEqual(mf.root().tier, 0)
        ids = mf.tech_ids()
        self.assertEqual(len(ids), 11)
        self.assertEqual(len(set(ids)), 11)
        self.assertIn("frar", ids)
        self.assertIn("dissertation-simulator", ids)
        d, t = mf.find_tech("godsaengbook-grace")
        self.assertEqual(t.delivery, "hosted")
        self.assertFalse(t.required)
        d, t = mf.find_tech("frar")
        self.assertTrue(t.required)
        self.assertEqual(t.install_cmd, "pip install -r requirements.txt")
        self.assertEqual(t.runtime, "python")
        # targets: 루트 → 하위 순
        keys = [d.key for d in mf.targets()]
        self.assertEqual(keys[0], "future-ministry")
        self.assertEqual([d.key for d in mf.targets("fm-admin")], ["fm-admin"])

    def test_parent_display_uses_display_name(self):
        mf = mf_mod.load(REPO_ROOT)
        self.assertIsNone(mf.parent_display(mf.root()))
        self.assertEqual(mf.parent_display(mf.dept("fm-admin")), "Future Ministry(칼빈)")
        # 부서 키로 적혀 있어도 표시명으로 환산한다(UI 는 bare display_name 으로 매칭)
        d = mf.dept("fm-sermon")
        d.parent = "future-ministry"
        self.assertEqual(mf.parent_display(d), "Future Ministry(칼빈)")


class ExpandHomeTest(unittest.TestCase):
    def test_expand(self):
        home = Path(r"C:\Users\신이재") if resolve.IS_WIN else Path("/Users/pastor")
        p = mf_mod.expand_home("$HOME/Future-Ministry/행정관리부", home)
        if resolve.IS_WIN:
            self.assertEqual(str(p), r"C:\Users\신이재\Future-Ministry\행정관리부")
        else:
            self.assertEqual(str(p), "/Users/pastor/Future-Ministry/행정관리부")
        self.assertIsNone(mf_mod.expand_home(None, home))
        self.assertEqual(mf_mod.expand_home("~/x", home), home / "x")


class ValidationTest(unittest.TestCase):
    def _base(self):
        return {"accounts": {"owner": "$HOME/.cys/claude"},
                "departments": [{"key": "root", "display": "R", "mission_key": "root", "tier": 0, "account": "owner",
                                 "cwd_template": "$HOME/R", "techs": []}]}

    def test_missing_owner(self):
        raw = self._base()
        raw["accounts"] = {}
        with self.assertRaises(mf_mod.ManifestError):
            mf_mod.parse(raw, Path("."))

    def test_duplicate_key(self):
        raw = self._base()
        raw["departments"].append(dict(raw["departments"][0], tier=1))
        with self.assertRaises(mf_mod.ManifestError):
            mf_mod.parse(raw, Path("."))

    def test_bad_slug(self):
        raw = self._base()
        raw["departments"][0]["techs"] = [{"name": "X", "id": "Bad_ID", "repo": "r", "cwd_template": "$HOME/x"}]
        with self.assertRaises(mf_mod.ManifestError):
            mf_mod.parse(raw, Path("."))

    def test_two_roots(self):
        raw = self._base()
        raw["departments"].append({"key": "r2", "display": "R2", "mission_key": "r2", "tier": 0, "account": "owner",
                                   "cwd_template": "$HOME/R2"})
        with self.assertRaises(mf_mod.ManifestError):
            mf_mod.parse(raw, Path("."))

    def test_unknown_parent(self):
        raw = self._base()
        raw["departments"].append({"key": "c", "display": "C", "mission_key": "c", "tier": 1, "account": "owner",
                                   "cwd_template": "$HOME/C", "parent": "nobody"})
        with self.assertRaises(mf_mod.ManifestError):
            mf_mod.parse(raw, Path("."))

    def test_parse_only(self):
        self.assertIsNone(mf_mod.parse_only(None))
        self.assertEqual(mf_mod.parse_only("a,B , c"), ["a", "b", "c"])
        self.assertEqual(mf_mod.parse_only(["a", "b,c"]), ["a", "b", "c"])

    def test_load_with_bom(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "manifest.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(self._base()).encode("utf-8"))
            mf = mf_mod.parse(json.loads((Path(d) / "manifest.json").read_text(encoding="utf-8-sig")), Path(d))
            self.assertEqual(mf.root().key, "root")
            mf2 = mf_mod.load(d)
            self.assertEqual(mf2.root().key, "root")


if __name__ == "__main__":
    unittest.main()
