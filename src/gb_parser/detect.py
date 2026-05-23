"""PDF 类型检测 — 抽样统计字符数判断文本型/扫描型。"""

import re
from pathlib import Path

import pypdf


def detect_pdf(pdf_path: str | Path, sample_pages: int = 3) -> dict:
    """检测 PDF 类型，返回状态报告 dict。

    Args:
        pdf_path: PDF 文件路径
        sample_pages: 抽样页数，默认 3

    Returns:
        {"ok": True, "pdf_type": "text"|"scan", "pdf_pages": N,
         "pdf_chars_per_page": N, "backend": "pipeline"|"hybrid-auto-engine"}
    """
    path = Path(pdf_path)
    if not path.exists():
        return {"ok": False, "error": f"文件不存在: {pdf_path}"}
    if path.suffix.lower() != ".pdf":
        return {"ok": False, "error": f"不支持的文件类型: {path.suffix}"}

    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as e:
        return {"ok": False, "error": f"PDF 读取失败: {e}"}

    total_pages = len(reader.pages)
    pages_to_sample = min(sample_pages, total_pages)

    total_chars = 0
    for i in range(pages_to_sample):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            text = ""
        total_chars += len(re.findall(r'[一-鿿　-〿＀-￯a-zA-Z]', text))

    chars_per_page = int(total_chars / max(1, pages_to_sample))

    if chars_per_page > 200:
        pdf_type = "text"
        backend = "pipeline"
    else:
        pdf_type = "scan"
        backend = "hybrid-auto-engine"

    return {
        "ok": True,
        "pdf_type": pdf_type,
        "pdf_pages": total_pages,
        "pdf_chars_per_page": chars_per_page,
        "backend": backend,
    }
