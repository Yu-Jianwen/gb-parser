---
name: gb-convert
description: 标准 PDF 一键转 Markdown，自动修复英文乱码。当用户需要处理 GB/T、ISO、ASTM 等标准 PDF 时使用。
allowed-tools: Bash, Read
---

## 概述

使用 `gb-convert` CLI 将标准 PDF（GB/T、ISO、ASTM 等）转换为结构化 Markdown，自动修复因 PDF 字体编码损坏导致的英文乱码。底层基于 MinerU PDF 解析引擎 + 自研乱码修复算法。

## 安装

如果 `gb-convert` 命令不可用，先安装：
```bash
pip install git+https://github.com/Yu-Jianwen/gb-parser.git
```

首次运行 MinerU 会自动下载模型到 `~/.cache/modelscope/`（约 2-4GB），需等待下载完成。

## 使用

**所有命令必须加 `--json`** 以获取机器可读的状态报告，不要解析 Markdown 内容来判断成功与否。

### 单文件转换
```bash
gb-convert <input.pdf> -o <output_dir> --json
```

### 批量转换
```bash
gb-convert ./pdfs/ -o ./output --json
```

### 仅修复已有 MinerU 输出
```bash
gb-fix ./output/some-standard/auto/some-standard.md --json
```

### 带英文标题（提升乱码修复准确率）
当 `garbled.score < 200` 时，建议用 `--seed` 重试：
```bash
gb-convert <input.pdf> -o <output_dir> --seed "English title of the standard" --json
```

## 结果判断

解析 JSON 输出的关键字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | bool | `true` 成功，`false` 失败 |
| `output_md` | str | 输出 Markdown 文件路径 |
| `garbled` | obj/null | 乱码检测与修复结果，无乱码时为 `null` |
| `garbled.detected` | bool | 是否检测到英文乱码 |
| `garbled.fixed` | bool | 乱码是否已修复 |
| `garbled.score` | int | 映射质量评分（<200 表示质量较低） |
| `garbled.residual_runs` | int | 修复后剩余乱码数（0 表示完全修复） |

### 处理逻辑

1. `ok: false` → 报告错误，检查 PDF 是否损坏或是否为扫描件
2. `ok: true, garbled: null` → 完美转换，直接使用 `output_md`
3. `ok: true, garbled.fixed: true, garbled.residual_runs: 0` → 乱码已完全修复，直接使用
4. `ok: true, garbled.score < 200` → 建议用 `--seed "英文标题"` 重试以提高质量

## 输出结构

```
output_dir/
└── <pdf_name>/
    └── auto/
        └── <pdf_name>.md    # 最终 Markdown
```
