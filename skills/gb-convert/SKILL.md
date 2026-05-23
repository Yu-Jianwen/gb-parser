---
name: gb-convert
description: 国标 PDF 一键转 Markdown，自动修复英文乱码。当用户需要处理 GB/T 标准 PDF 时使用。
allowed-tools: Bash, Read
---

## 使用方法

### 单文件转换
```bash
gb-convert <input.pdf> -o <output_dir>
```

### 批量转换
```bash
gb-convert ./pdfs/ -o ./output
```

### 仅修复已有 MinerU 输出
```bash
gb-fix ./output/some-standard/auto/some-standard.md
```

### 带英文标题提升准确率
```bash
gb-convert <input.pdf> --seed "Terminology for building windows and doors"
```

## 状态报告

所有命令支持 `--json` 输出完整状态报告。关键字段：
- `ok`: 整体成功/失败
- `garbled.detected`: 是否检测到乱码
- `garbled.fixed`: 是否已修复
- `garbled.score`: 映射质量评分（<200 建议提供 `--seed` 重试）
- `output_md`: 输出 Markdown 路径

## 前置条件

```bash
pip install git+https://github.com/Yu-Jianwen/gb-parser.git
```

MinerU 模型首次运行自动下载（约 2-4GB）。
