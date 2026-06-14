# notes-search · notes 全文搜索 CLI

> Owner: fast118 · 2026-06-14 创建
> 范围：递归扫 `notes/` 下 `.md` / `.txt`，支持正则、文件名匹配、上下文行、编码容错
> 配套：TASK-003（notes 全文搜索）+ 狗粮 Session 6 脚手架 add_project.py

![License](https://img.shields.io/badge/license-MIT-blue)
![Language](https://img.shields.io/badge/language-python-green)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey)
![Stars](https://img.shields.io/github/stars/fast118/notes-search?style=social)

## 是什么

`notes-search` 是 `D:\Github开源项目\notes\` 下的命令行全文搜索工具。8 个文件 / 25KB 规模，**纯 Python 标准库** 200 行实现，不建索引、一次扫完。CLI 风格对齐 `rg` 子集，支持：

- 正则 / 字面匹配
- 大小写不敏感
- 文件名 / 后缀过滤
- 上下文行（前后 N 行）
- GBK / BOM 编码兜底

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

# 上下文行 (前 1 + 后 1)
python search.py "GitHub" -B 1 -A 1 ../../notes

# 字面匹配 (关闭正则)
python search.py "AI永不失忆" --literal ../../notes

# 详细帮助
python search.py --help
```

输出格式（grep 风格）：
```
notes/CHANGELOG.md:12:## 2026-06-14
notes/DAILY-STATS.md:42:GitHub trending 实跑 (Clash 必需)
```

## 测试

```bash
cd projects/notes-search
python -m pytest tests/ -v
# 3/3 pass (found / not-found / encoding 容错)
```

## License

MIT © fast118
