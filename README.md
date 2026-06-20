# notes-search · notes 全文搜索 CLI

> Owner: fast118 · 2026-06-14 创建 · 2026-06-20 升 v0.2
> 范围：递归扫 `notes/` 下 `.md` / `.txt`，支持正则、文件名匹配、上下文行、编码容错、JSON 输出
> 配套：TASK-003（notes 全文搜索）+ 狗粮 Session 6 脚手架 add_project.py

![License](https://img.shields.io/badge/license-MIT-blue)
![Language](https://img.shields.io/badge/language-python-green)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey)
![Stars](https://img.shields.io/github/stars/fast118/notes-search?style=social)

## 是什么

`notes-search` 是 `D:\Github开源项目\notes\` 下的命令行全文搜索工具。10 个文件 / 30KB 规模，**纯 Python 标准库** ~260 行实现，不建索引、一次扫完。CLI 风格对齐 `rg` 子集，支持：

- 正则 / 字面匹配
- 大小写不敏感
- **文件名匹配 (`-F`)** — v0.2 新增，只对文件名正则，不扫内容
- 文件名 / 后缀过滤
- 上下文行（前后 N 行）
- GBK / BOM 编码兑底
- **JSON 输出 (`--json`)** — v0.2 新增，含 pattern/path/file_count/match_count/results

## 安装

```bash
# 1. 克隆
git clone https://github.com/fast118/notes-search.git
cd notes-search

# 2. 仅用 Python 3.10+ 标准库，零第三方依赖
# 3. (可选) 跑测试
pip install pytest
```

## 使用

```bash
# 默认扫 ../notes
python search.py "Clash"

# 指定路径
python search.py "trending" ../../notes

# 大小写不敏感
python search.py "github" -i ../../notes

# 只列文件名
python search.py "TODO" -l ../../notes

# v0.2: 只匹配文件名 (不扫内容)
python search.py "todo" -F ../../notes

# 上下文行 (前 1 + 后 1)
python search.py "GitHub" -B 1 -A 1 ../../notes

# 字面匹配 (关闭正则)
python search.py "AI永不失忆" --literal ../../notes

# v0.2: JSON 输出 (供下游脚本使用)
python search.py "Python" --json ../../notes
# {
#   "pattern": "Python",
#   "path": "...",
#   "file_count": 3,
#   "match_count": 7,
#   "results": [
#     {"path": "notes/a.md", "matches": [{"line": 2, "content": "Python is great"}]},
#     ...
#   ]
# }

# 详细帮助
python search.py --help
```

输出格式（grep 风格，默认）：
```
notes/CHANGELOG.md:12:## 2026-06-14
notes/DAILY-STATS.md:42:GitHub trending 实跑 (Clash 必需)
```

## v0.2 更新日志

- ✨ 新增 `-F` / `--filename`：只对文件名正则匹配，不扫文件内容
- ✨ 新增 `--json`：结构化输出，含 pattern/path/file_count/match_count/results
- ✅ 3 个新 test：test_filename_only / test_json_output / test_json_no_match
- ✅ 10 tests 全过 (原 7 + 新 3)

## 测试

```bash
cd projects/notes-search
python -m pytest tests/ -v
# 10/10 pass
```

## License

MIT © fast118


## 💬 联系

扫码加微信群（AI 工具使用 / 提 issue / 需求讨论）：

![微信群](assets/wechat-qr.png)

或提 [GitHub Issue](https://github.com/fast118/notes-search/issues)
