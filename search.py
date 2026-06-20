"""search.py — notes/ 全文搜索 CLI (TASK-003 / v0.2)

Usage:
    python search.py PATTERN [PATH] [选项]

设计取舍：
- 8 文件 25KB 规模，索引是过度工程。纯 stdlib 200 行。
- 编码兜底：utf-8 失败 → errors='replace' 跳过坏字节。
- 二进制检测：读头 8KB，空字节 > 5% 视为二进制跳过。
- 大文件保护：> 5MB 跳过，避免 OOM。
- 输出格式对齐 grep (path:line:content) + 上下文用 path-line-content (rg/grep 风格)。
- v0.2: 加 -F 文件名匹配 + --json 输出
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Windows GBK stdout 打不动 U+FFFD (编码兜底产物)，强制 UTF-8 + replace
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PATH = SCRIPT_DIR.parent.parent / "文档计划" / "notes"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
BINARY_SAMPLE_SIZE = 8192
BINARY_NULL_RATIO = 0.05
DEFAULT_EXTS = {".md", ".txt"}


def is_binary(data: bytes) -> bool:
    """True if data looks like a binary file"""
    if not data:
        return False
    sample = data[:BINARY_SAMPLE_SIZE]
    return (sum(1 for b in sample if b == 0) / len(sample)) > BINARY_NULL_RATIO


def read_lines(path: Path):
    """Read file lines with encoding fallback. Returns None on hard failure."""
    try:
        with open(path, "rb") as f:
            sample = f.read(BINARY_SAMPLE_SIZE)
        if is_binary(sample):
            print(f"[skip] binary: {path}", file=sys.stderr)
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.readlines()
        except UnicodeDecodeError:
            print(f"[warn] non-utf8: {path}, fallback to replace mode", file=sys.stderr)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.readlines()
    except (OSError, IOError) as e:
        print(f"[warn] read fail: {path}: {e}", file=sys.stderr)
        return None


def find_matches(path: Path, pattern: re.Pattern):
    """Yield (lineno, line) tuples for each match in path. None if file unreadable."""
    lines = read_lines(path)
    if lines is None:
        return
    for i, line in enumerate(lines):
        if pattern.search(line):
            yield (i + 1, line.rstrip("\n"))


def emit_with_context(path: Path, lineno: int, line: str, before: int, after: int, lines_cache):
    """Print match line with --before/--after context lines.

    Format: path:line:content  (match)
            path-line-content   (context)
    """
    if before == 0 and after == 0:
        print(f"{path}:{lineno}:{line}")
        return
    start = max(0, lineno - 1 - before)
    end = min(len(lines_cache), lineno - 1 + after + 1)
    for i in range(start, end):
        content = lines_cache[i].rstrip("\n")
        if i == lineno - 1:
            print(f"{path}:{i+1}:{content}")
        else:
            print(f"{path}-{i+1}-{content}")


def main():
    parser = argparse.ArgumentParser(
        description="notes/ 全文搜索 CLI (TASK-003)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="输出: <path>:<line>:<content> (match) / <path>-<line>-<content> (context)",
    )
    parser.add_argument("pattern", help="搜索关键词 (正则)")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH), help=f"搜索路径 (默认 {DEFAULT_PATH})")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="大小写不敏感")
    parser.add_argument("-l", "--files-with-matches", action="store_true", help="只列文件名")
    parser.add_argument("-F", "--filename", action="store_true", help="只匹配文件名 (不扫内容)")
    parser.add_argument("-e", "--ext", default=",".join(sorted(DEFAULT_EXTS)), help=f"后缀过滤，逗号分隔 (默认 {','.join(sorted(DEFAULT_EXTS))})")
    parser.add_argument("-B", "--before", type=int, default=0, help="前文 N 行 (默认 0)")
    parser.add_argument("-A", "--after", type=int, default=0, help="后文 N 行 (默认 0)")
    parser.add_argument("--literal", action="store_true", help="字面匹配，关闭正则")
    parser.add_argument("--json", action="store_true", help="输出 JSON (含 pattern/path/matches)")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"[error] 路径不存在: {root}", file=sys.stderr)
        sys.exit(1)

    flags = re.IGNORECASE if args.ignore_case else 0
    pattern = re.compile(re.escape(args.pattern) if args.literal else args.pattern, flags)

    exts = set()
    for e in args.ext.split(","):
        e = e.strip()
        if not e:
            continue
        exts.add(e if e.startswith(".") else "." + e)

    # JSON 收集器 (—F 模式只填 path; 内容模式填 path+line+content)
    json_results = []

    file_count = 0
    match_count = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in exts:
                continue
            # —F 模式: 只对文件名匹配
            if args.filename:
                if not pattern.search(fn):
                    continue
                file_count += 1
                if args.json:
                    json_results.append({"path": str(p), "matches": [{"name": fn}]})
                else:
                    print(p)
                continue
            try:
                if p.stat().st_size > MAX_FILE_SIZE:
                    print(f"[skip] too large: {p}", file=sys.stderr)
                    continue
            except OSError:
                continue

            # For context mode, we need full lines in memory (file already loaded)
            # For non-context mode, stream matches.
            if args.before > 0 or args.after > 0:
                lines = read_lines(p)
                if lines is None:
                    continue
                # Filter lines matching pattern
                file_matches = [i for i, ln in enumerate(lines) if pattern.search(ln)]
                if not file_matches:
                    continue
                file_count += 1
                if args.files_with_matches:
                    if args.json:
                        json_results.append({"path": str(p), "matches": [{"count": len(file_matches)}]})
                    else:
                        print(p)
                    match_count += len(file_matches)
                    continue
                for i in file_matches:
                    if args.json:
                        json_results.append({
                            "path": str(p),
                            "matches": [{"line": i + 1, "content": lines[i].rstrip("\n")}],
                        })
                    else:
                        emit_with_context(p, i + 1, lines[i].rstrip("\n"), args.before, args.after, lines)
                    match_count += 1
            else:
                matches = list(find_matches(p, pattern))
                if not matches:
                    continue
                file_count += 1
                if args.files_with_matches:
                    if args.json:
                        json_results.append({"path": str(p), "matches": [{"count": len(matches)}]})
                    else:
                        print(p)
                    match_count += len(matches)
                    continue
                for lineno, line in matches:
                    if args.json:
                        json_results.append({
                            "path": str(p),
                            "matches": [{"line": lineno, "content": line}],
                        })
                    else:
                        print(f"{p}:{lineno}:{line}")
                    match_count += 1

    # JSON 模式输出总包
    if args.json:
        print(json.dumps({
            "pattern": args.pattern,
            "path": str(root),
            "file_count": file_count,
            "match_count": match_count,
            "results": json_results,
        }, ensure_ascii=False, indent=2))
        if file_count == 0:
            sys.exit(2)
        sys.exit(0)

    # grep convention: exit 0 on match, 1 on error, 2 on no match
    if file_count == 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
