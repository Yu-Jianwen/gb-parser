"""GB-Parser: 国标 PDF 结构化转换和英文乱码修复。

核心 API:
    detect_pdf(pdf_path) -> dict      检测 PDF 类型
    convert_pdf(pdf_path, ...) -> dict 一站式转换（检测 → MinerU → 修复乱码）
    fix_garbled(md_path, ...) -> dict  单独修复已有 MinerU 输出中的乱码

所有函数返回状态报告 dict。
"""

from .detect import detect_pdf
from .convert import convert_pdf
from .fix_garbled import fix_file as fix_garbled

__all__ = ["detect_pdf", "convert_pdf", "fix_garbled"]
