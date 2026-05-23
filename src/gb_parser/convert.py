"""MinerU 封装 — 调用 mineru CLI 将 PDF 转换为 Markdown。"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

from .detect import detect_pdf


def _find_mineru() -> str:
    """查找 mineru CLI 可执行文件路径。"""
    # 先尝试与当前 Python 同目录的 mineru（venv 场景）
    venv_mineru = Path(sys.executable).parent / "mineru"
    if venv_mineru.exists():
        return str(venv_mineru)
    # 回退到 PATH 查找
    found = shutil.which("mineru")
    if found:
        return found
    raise FileNotFoundError("MinerU 未安装。请运行: pip install mineru")


def convert_pdf(
    pdf_path: str | Path,
    output_dir: str | Path = "./output",
    seed: str = "",
    *,
    backend: str | None = None,
) -> dict:
    """一站式转换：检测 PDF 类型 → MinerU 转换。

    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        seed: 英文标题种子（传递给 fix_garbled）
        backend: 强制指定 MinerU 后端，None 则自动检测

    Returns:
        状态报告 dict
    """
    path = Path(pdf_path)
    out = Path(output_dir)

    # 1. 检测 PDF 类型
    detect_result = detect_pdf(path)
    if not detect_result["ok"]:
        return detect_result

    selected_backend = backend or detect_result["backend"]

    basename = path.stem
    input_size_mb = round(path.stat().st_size / (1024 * 1024), 1)

    # 2. MinerU 转换
    start = time.time()
    try:
        mineru_bin = _find_mineru()
    except FileNotFoundError as e:
        return {
            "ok": False, "error": str(e),
            "input": str(path), "input_size_mb": input_size_mb,
            "pdf_type": detect_result["pdf_type"],
            "pdf_pages": detect_result["pdf_pages"],
            "pdf_chars_per_page": detect_result["pdf_chars_per_page"],
            "backend": selected_backend,
            "output_md": None, "conversion_seconds": 0.0, "garbled": None,
        }

    try:
        proc = subprocess.run(
            [
                mineru_bin,
                "-p", str(path),
                "-o", str(out),
                "-b", selected_backend,
                "-m", "auto",
                "-l", "ch",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": f"MinerU 转换失败 (exit {proc.returncode}): {proc.stderr[:500]}",
                "input": str(path), "input_size_mb": input_size_mb,
                "pdf_type": detect_result["pdf_type"],
                "pdf_pages": detect_result["pdf_pages"],
                "pdf_chars_per_page": detect_result["pdf_chars_per_page"],
                "backend": selected_backend,
                "output_md": None,
                "conversion_seconds": round(time.time() - start, 1),
                "garbled": None,
            }
    except subprocess.TimeoutExpired:
        return {
            "ok": False, "error": "MinerU 转换超时（超过10分钟）",
            "input": str(path), "input_size_mb": input_size_mb,
            "pdf_type": detect_result["pdf_type"],
            "pdf_pages": detect_result["pdf_pages"],
            "pdf_chars_per_page": detect_result["pdf_chars_per_page"],
            "backend": selected_backend,
            "output_md": None,
            "conversion_seconds": round(time.time() - start, 1),
            "garbled": None,
        }

    elapsed = round(time.time() - start, 1)

    # 3. 定位输出文件
    md_file = out / basename / "auto" / f"{basename}.md"
    if not md_file.exists():
        # 尝试不带 auto 子目录的路径
        candidates = list(out.rglob(f"{basename}.md"))
        if candidates:
            md_file = candidates[0]
        else:
            return {
                "ok": False,
                "error": f"MinerU 完成但找不到输出文件，预期路径: {md_file}",
                "input": str(path),
                "input_size_mb": input_size_mb,
                "pdf_type": detect_result["pdf_type"],
                "pdf_pages": detect_result["pdf_pages"],
                "pdf_chars_per_page": detect_result["pdf_chars_per_page"],
                "backend": selected_backend,
                "output_md": None,
                "conversion_seconds": elapsed,
                "garbled": None,
            }

    # 4. 修复乱码
    from .fix_garbled import fix_file

    fix_result = fix_file(md_file, seed_text=seed)

    return {
        "ok": True,
        "input": str(path),
        "input_size_mb": input_size_mb,
        "pdf_type": detect_result["pdf_type"],
        "pdf_pages": detect_result["pdf_pages"],
        "pdf_chars_per_page": detect_result["pdf_chars_per_page"],
        "backend": selected_backend,
        "output_md": str(md_file),
        "conversion_seconds": elapsed,
        "garbled": fix_result,
    }
