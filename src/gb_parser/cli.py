"""CLI 入口: gb-convert / gb-fix / gb-detect。"""

import argparse
import json
import sys
from pathlib import Path

from .detect import detect_pdf
from .convert import convert_pdf
from .fix_garbled import fix_file, fix_directory


def _print_result(result: dict, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        garbled = result.get("garbled")
        if garbled and garbled.get("detected"):
            status = "已修复" if garbled.get("fixed") else f"残留 {garbled.get('residual_runs', '?')} 段"
            print(f"ok: {result.get('output_md', 'N/A')}")
            print(f"乱码: {status} | 映射 {garbled.get('chars_mapped', 0)} 字符 | 评分 {garbled.get('score', 0)}")
        else:
            print(f"ok: {result.get('output_md', 'N/A')}")
    else:
        print(f"error: {result.get('error', '未知错误')}", file=sys.stderr)
        sys.exit(1)


def main_convert():
    p = argparse.ArgumentParser(
        description="标准 PDF 一键转 Markdown（检测 → MinerU → 修复乱码）")
    p.add_argument("input", help="PDF 文件路径或目录")
    p.add_argument("-o", "--output", default="./output", help="输出目录 (默认 ./output)")
    p.add_argument("--seed", default="", help="正确的英文标题（提升映射准确率）")
    p.add_argument("--json", action="store_true", help="输出 JSON 状态报告")
    args = p.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        results = []
        for pdf_file in sorted(list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF"))):
            result = convert_pdf(pdf_file, output_dir=args.output, seed=args.seed)
            results.append(result)
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                status = "ok" if result["ok"] else "FAIL"
                garbled_info = ""
                if result.get("garbled") and result["garbled"].get("detected"):
                    garbled_info = f" | 乱码: {'已修复' if result['garbled']['fixed'] else '残留'}"
                print(f"  [{status}] {pdf_file.name} → {result.get('output_md', 'N/A')}{garbled_info}")
        if not args.json:
            ok_count = sum(1 for r in results if r["ok"])
            print(f"\n总计: {len(results)} 个 PDF, {ok_count} 成功")
    else:
        result = convert_pdf(input_path, output_dir=args.output, seed=args.seed)
        _print_result(result, args.json)


def main_fix():
    p = argparse.ArgumentParser(
        description="修复 MinerU 输出中的英文乱码")
    p.add_argument("path", help="Markdown 文件或目录")
    p.add_argument("--seed", default="", help="正确的英文标题（推导映射用）")
    p.add_argument("--json", action="store_true", help="输出 JSON 状态报告")
    args = p.parse_args()

    path = Path(args.path)
    if path.is_dir():
        results = fix_directory(path, seed_text=args.seed)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            fixed = sum(1 for r in results if r.get("fixed"))
            detected = sum(1 for r in results if r.get("detected"))
            print(f"处理 {len(results)} 文件: {detected} 检测到乱码, {fixed} 已修复")
    else:
        result = fix_file(path, seed_text=args.seed)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result.get("detected"):
            status = "已修复" if result.get("fixed") else "部分修复"
            print(f"乱码: {status} | {result.get('chars_mapped', 0)} 字符映射 | 评分 {result.get('score', 0)}")
        else:
            print("未检测到乱码，跳过")


def main_detect():
    p = argparse.ArgumentParser(
        description="检测 PDF 类型（文本型/扫描型）")
    p.add_argument("input", help="PDF 文件路径")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    args = p.parse_args()

    result = detect_pdf(args.input)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        print(f"类型: {result['pdf_type']}")
        print(f"页数: {result['pdf_pages']}")
        print(f"抽样页均字符: {result['pdf_chars_per_page']}")
        print(f"推荐后端: {result['backend']}")
    else:
        print(f"error: {result.get('error')}", file=sys.stderr)
        sys.exit(1)
