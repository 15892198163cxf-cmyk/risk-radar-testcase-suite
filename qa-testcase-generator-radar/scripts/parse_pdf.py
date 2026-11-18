#!/usr/bin/env python3
"""
parse_pdf.py - PDF 需求文档解析 wrapper

用于 qa-testcase-generator-radar 流程中解析 PDF 格式的需求文档。
内部调用 paddleocr-doc-parsing 技能（官方 Job API）。

用法:
    python parse_pdf.py --file-path "需求文档.pdf"
    python parse_pdf.py --file-path "需求文档.pdf" --output "output/result.json"
    python parse_pdf.py --file-url "https://example.com/prd.pdf"
    python parse_pdf.py --file-path "需求文档.pdf" --stdout

输出:
    默认保存到系统临时目录，并在 stderr 打印保存路径。
    --stdout 模式直接打印 JSON 到 stdout。
    解析成功后可用字段:
      result["text"]   — 全文 Markdown 文本（最常用）

环境变量（必填）:
    PADDLEOCR_API_TOKEN  — 使用者提供的 API token
    PADDLEOCR_SKILL_DIR — 可选，paddleocr-doc-parsing 的安装根目录
"""

import argparse
import io
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def get_ocr_lib_path():
    configured = os.environ.get("PADDLEOCR_SKILL_DIR", "").strip()
    if configured:
        return Path(configured).expanduser() / "scripts" / "lib.py"

    skill_root = Path(__file__).resolve().parents[1]
    candidates = [skill_root.parent / "paddleocr-doc-parsing" / "scripts" / "lib.py"]
    if skill_root.parent.name == "risk-radar-testcase-suite":
        candidates.append(skill_root.parent.parent / "paddleocr-doc-parsing" / "scripts" / "lib.py")
    return next((path for path in candidates if path.is_file()), candidates[0])


def get_default_output_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    short_id = uuid.uuid4().hex[:8]
    return (
        Path(tempfile.gettempdir())
        / "paddleocr" / "doc-parsing" / "results"
        / f"result_{timestamp}_{short_id}.json"
    )


def main():
    parser = argparse.ArgumentParser(
        description="QA 需求文档 PDF 解析 (powered by PaddleOCR 官方 API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python parse_pdf.py --file-path "需求文档.pdf"
  python parse_pdf.py --file-url "https://example.com/prd.pdf"
  python parse_pdf.py --file-path "doc.pdf" --output "output/parsed.json"
  python parse_pdf.py --file-path "doc.pdf" --stdout
        """,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file-path", help="本地 PDF 文件路径")
    input_group.add_argument("--file-url", help="远程 PDF/图片 URL")

    parser.add_argument("--pretty", action="store_true", default=True, help="格式化 JSON 输出（默认开启）")
    parser.add_argument("--no-pretty", dest="pretty", action="store_false")
    parser.add_argument("--no-ocr-for-images", dest="ocr_for_images", action="store_false", default=True)

    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--output", "-o", metavar="FILE", help="保存结果到指定 JSON 文件")
    output_group.add_argument("--stdout", action="store_true", help="直接输出 JSON 到 stdout")

    args = parser.parse_args()

    # 验证文件存在
    if args.file_path and not Path(args.file_path).exists():
        print(f"ERROR: 文件不存在: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    # Explicit configuration wins; support both standalone and nested suite installs.
    lib_path = get_ocr_lib_path()
    if not lib_path.exists():
        print(f"ERROR: paddleocr-doc-parsing lib 未找到: {lib_path}；请安装依赖或设置 PADDLEOCR_SKILL_DIR", file=sys.stderr)
        sys.exit(1)

    import importlib.util
    spec = importlib.util.spec_from_file_location("paddleocr_lib", str(lib_path))
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    # 调用解析
    result = lib.parse_document(
        file_path=str(Path(args.file_path).resolve()) if args.file_path else None,
        file_url=args.file_url if not args.file_path else None,
    )

    # 输出
    indent = 2 if args.pretty else None
    json_str = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.stdout:
        print(json_str)
        sys.exit(0 if result["ok"] else 1)

    out_path = Path(args.output).resolve() if args.output else get_default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json_str, encoding="utf-8")
    print(f"Result saved to: {out_path}", file=sys.stderr)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
