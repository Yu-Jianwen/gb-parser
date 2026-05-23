# GB-Parser

标准 PDF 一键转结构化 Markdown，自动修复因 PDF 字体编码损坏导致的英文乱码。适用于 GB/T、ISO、ASTM 等各类标准文件。

## 安装

```bash
# 通过 GitHub Release 安装
pip install git+https://github.com/Yu-Jianwen/gb-parser.git

# 本地开发安装
git clone https://github.com/Yu-Jianwen/gb-parser.git
cd gb-parser
pip install -e ".[dev]"
```

**前置条件**: Python >= 3.11。首次运行 MinerU 会自动下载模型到 `~/.cache/modelscope/`（约 2-4GB）。

## 快速开始

```bash
# 单文件转换
gb-convert GB5823-2008.pdf -o ./output

# 带英文标题提升准确率
gb-convert GB5823-2008.pdf -o ./output --seed "Terminology for building windows and doors"

# 批量转换
gb-convert ./pdfs/ -o ./output

# 仅检测 PDF 类型
gb-detect GB5823-2008.pdf

# 仅修复已有 MinerU 输出
gb-fix ./output/some-standard/auto/some-standard.md
```

所有命令支持 `--json` 输出机器可读的状态报告。

## Python API

```python
from gb_parser import detect_pdf, convert_pdf, fix_garbled

# 检测 PDF 类型
result = detect_pdf("GB5823.pdf")
# {"ok": True, "pdf_type": "text", "pdf_pages": 32, ...}

# 一站式转换
result = convert_pdf("GB5823.pdf", output_dir="./output", seed="English title")
# {"ok": True, "output_md": "./output/GB5823/auto/GB5823.md", "garbled": {...}}

# 单独修复乱码
result = fix_garbled("./output/GB5823/auto/GB5823.md", seed_text="English title")
```

所有函数返回状态报告 dict。Agent 应读取状态报告中的字段判断结果，而不是解析 Markdown 内容。

## 状态报告

| 场景 | `ok` | `garbled` |
|------|------|-----------|
| 完美转换 | `true` | `None` |
| 乱码已修复 | `true` | `{detected: true, fixed: true, residual_runs: 0}` |
| 乱码待补种 | `true` | `{detected: true, fixed: true, score: <200}` |
| 转换失败 | `false` | — |

## 开源依赖

本项目基于以下开源项目构建：

| 依赖 | 许可证 | 用途 |
|------|--------|------|
| [MinerU](https://github.com/opendatalab/MinerU) | Apache-2.0 | PDF 解析与结构化转换引擎 |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause | PDF 类型检测（文本型/扫描型） |
| [modelscope](https://github.com/modelscope/modelscope) | Apache-2.0 | MinerU 模型下载与管理（间接依赖） |
| [Hatchling](https://github.com/pypa/hatch) | MIT | Python 构建系统 |

### MinerU

MinerU 是 PDF 内容提取的核心引擎，负责将 PDF 解析为结构化 Markdown。
- 仓库: https://github.com/opendatalab/MinerU
- 许可证: Apache License 2.0
- 首次运行时，MinerU 会自动从 ModelScope 下载所需的 AI 模型文件（约 2-4GB），
  缓存于 `~/.cache/modelscope/` 目录。

### pypdf

pypdf 用于检测 PDF 类型（文本型电子文档 vs 扫描件），
以选择最合适的 MinerU 转换后端。
- 仓库: https://github.com/py-pdf/pypdf
- 许可证: BSD-3-Clause

---

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 发布。

## 给 Agent 使用的 Skill

本项目附带 `gb-convert` Skill，支持 Claude Code 和 OpenClaw 自动调用。
将 `.claude/skills/gb-convert/SKILL.md` 复制到项目的 `.claude/skills/gb-convert/` 目录即可使用 `/gb-convert` 命令。
