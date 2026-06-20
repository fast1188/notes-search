"""test_search.py — smoke tests for search.py (stdlib unittest, 零依赖)

跑法:
    python -m unittest tests.test_search -v
    # 或
    python tests/test_search.py
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
SEARCH_PY = SCRIPT_DIR / "search.py"
PY = sys.executable


def run_search(*args, cwd=None):
    """Run search.py with given args, return (returncode, stdout, stderr)"""
    r = subprocess.run(
        [PY, str(SEARCH_PY), *args],
        capture_output=True, text=True,
        cwd=cwd or SCRIPT_DIR,
        encoding="utf-8", errors="replace",
    )
    return r.returncode, r.stdout, r.stderr


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestSearch(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="notes-search-test-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_found(self):
        """基础命中：大小写敏感"""
        write_file(self.tmp / "a.md", "Hello world\nPython is great\nBye")
        write_file(self.tmp / "b.txt", "World of warcraft\nNo python here\nLast line")
        write_file(self.tmp / "c.md", "no match here\nor here")

        rc, out, _ = run_search("Python", str(self.tmp))
        self.assertEqual(rc, 0)
        self.assertIn("a.md:2:Python is great", out)
        # "python" 小写不命中
        self.assertNotIn("b.txt", out)
        self.assertNotIn("c.md", out)

    def test_not_found(self):
        """无命中：exit 2 (grep 约定)"""
        write_file(self.tmp / "a.md", "Hello\nWorld\n")
        write_file(self.tmp / "b.txt", "Foo\nBar\n")

        rc, out, _ = run_search("NONEXISTENT_KEYWORD", str(self.tmp))
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")

    def test_case_insensitive(self):
        """-i 大小写不敏感"""
        write_file(self.tmp / "a.md", "GITHUB\nGitHub\ngithub\n")
        rc, out, _ = run_search("github", "-i", str(self.tmp))
        self.assertEqual(rc, 0)
        self.assertIn("a.md:1:GITHUB", out)
        self.assertIn("a.md:2:GitHub", out)
        self.assertIn("a.md:3:github", out)

    def test_files_with_matches(self):
        """-l 只列文件名"""
        write_file(self.tmp / "a.md", "match this line")
        write_file(self.tmp / "b.txt", "nothing here")
        write_file(self.tmp / "c.md", "match this one too")
        rc, out, _ = run_search("match", "-l", str(self.tmp))
        self.assertEqual(rc, 0)
        files = [ln.replace("\\", "/") for ln in out.strip().splitlines()]
        self.assertTrue(any("a.md" in f for f in files))
        self.assertTrue(any("c.md" in f for f in files))
        self.assertFalse(any("b.txt" in f for f in files))

    def test_literal(self):
        """--literal 字面匹配关闭正则"""
        write_file(self.tmp / "a.md", "a.b.c\nabbbc\n")
        # 正则模式 "a.b" 同时命中 a.b.c 和 abbbc
        rc1, out1, _ = run_search("a.b", str(self.tmp))
        self.assertIn("a.md:1:a.b.c", out1)
        self.assertIn("a.md:2:abbbc", out1)
        # 字面模式 "a.b" 只命中 a.b.c
        rc2, out2, _ = run_search("a.b", "--literal", str(self.tmp))
        self.assertIn("a.md:1:a.b.c", out2)
        self.assertNotIn("abbbc", out2)

    def test_context(self):
        """-B -A 上下文"""
        write_file(self.tmp / "a.md", "line1\nline2\nMATCH\nline4\nline5\n")
        rc, out, _ = run_search("MATCH", "-B", "1", "-A", "1", str(self.tmp))
        self.assertEqual(rc, 0)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 3, f"expected 3 lines, got {lines}")
        # 上下文用 `-` 分隔，匹配用 `:` 分隔
        self.assertIn("a.md-2-line2", lines[0])
        self.assertIn("a.md:3:MATCH", lines[1])
        self.assertIn("a.md-4-line4", lines[2])

    def test_ext_filter(self):
        """-e 后缀过滤"""
        write_file(self.tmp / "a.md", "needle here")
        write_file(self.tmp / "b.txt", "needle here too")
        write_file(self.tmp / "c.py", "needle in py (should skip)")
        rc, out, _ = run_search("needle", "-e", "md", str(self.tmp))
        self.assertEqual(rc, 0)
        self.assertIn("a.md", out)
        self.assertNotIn("b.txt", out)
        self.assertNotIn("c.py", out)

    def test_filename_only(self):
        """-F 只匹配文件名, 不扫内容"""
        write_file(self.tmp / "todo.md", "no keyword in content here")
        write_file(self.tmp / "notes.md", "todo also mentioned in body, should not be hit by -F")
        write_file(self.tmp / "readme.md", "completely unrelated")
        rc, out, _ = run_search("todo", "-F", str(self.tmp))
        self.assertEqual(rc, 0)
        files = [ln.replace("\\", "/") for ln in out.strip().splitlines()]
        # 只匹配文件名含 "todo" 的 todo.md, 不应出 notes.md (内容里含 todo)
        self.assertTrue(any("todo.md" in f for f in files))
        self.assertFalse(any("notes.md" in f for f in files))
        self.assertFalse(any("readme.md" in f for f in files))

    def test_json_output(self):
        """--json 输出 JSON 结构, 含 pattern/path/file_count/match_count/results"""
        import json as _json
        write_file(self.tmp / "a.md", "Hello world\nPython is great")
        write_file(self.tmp / "b.md", "no match here")
        rc, out, _ = run_search("Python", "--json", str(self.tmp))
        self.assertEqual(rc, 0)
        data = _json.loads(out)
        self.assertEqual(data["pattern"], "Python")
        self.assertEqual(data["file_count"], 1)
        self.assertEqual(data["match_count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertTrue(data["results"][0]["path"].endswith("a.md"))
        self.assertEqual(data["results"][0]["matches"][0]["line"], 2)
        self.assertEqual(data["results"][0]["matches"][0]["content"], "Python is great")

    def test_json_no_match(self):
        """--json 无命中时 file_count=0 + exit 2"""
        import json as _json
        write_file(self.tmp / "a.md", "Hello")
        rc, out, _ = run_search("NONEXIST", "--json", str(self.tmp))
        self.assertEqual(rc, 2)
        data = _json.loads(out)
        self.assertEqual(data["file_count"], 0)
        self.assertEqual(data["match_count"], 0)
        self.assertEqual(data["results"], [])


if __name__ == "__main__":
    # 允许直接 python tests/test_search.py
    unittest.main(verbosity=2)
