from __future__ import annotations

import argparse
import json
import re
import pymupdf
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def print_keys(d, indent=0):
    for k, v in d.items():
        print("  " * indent + str(k))
        if isinstance(v, dict):
            print_keys(v, indent + 1)

@dataclass
class FieldRule:
    name: str
    patterns: List[str]
    capture_group: int = 1
    multiple: bool = False
    description: str = ""
    compiled_patterns: List[re.Pattern] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.compiled_patterns = []
        for pattern in self.patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"正则表达式无效: {self.name} -> {pattern!r} ({exc})") from exc
            self.compiled_patterns.append(compiled)

    @property
    def regex_correct(self) -> bool:
        return len(self.compiled_patterns) == len(self.patterns)
        


class InvoiceKeyInfoReaderFormatter:
    TEXT_EXTENSIONS = {".txt"}
    PDF_EXTENSIONS = {".pdf"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    DEFAULT_OUTPUT_SUBDIR = "invoice_parsed"
    DEFAULT_OUTPUT_FILE = "all_invoices.json"

    def __init__(
        self,
        field_rules: Optional[Sequence[FieldRule]] = None,
        output_subdir: str = DEFAULT_OUTPUT_SUBDIR,
        output_filename: str = DEFAULT_OUTPUT_FILE,
        recursive: bool = True,
    ) -> None:
        self.field_rules: Dict[str, FieldRule] = {}
        self.output_subdir = output_subdir
        self.output_filename = output_filename
        self.recursive = recursive

        for rule in field_rules or self.default_field_rules():
            self.add_field_rule(rule)

    @staticmethod
    def default_field_rules() -> List[FieldRule]:
        return [
            FieldRule(
                name="invoice_code",
                description="发票代码",
                patterns=[
                    r"发票代码[:：\s]*([0-9]{10,12})",
                    r"Invoice\s*Code[:：\s]*([A-Z0-9\-]{6,})",
                ],
            ),
            FieldRule(
                name="invoice_number",
                description="发票号码",
                patterns=[
                    r"发票号码[:：\s]*([0-9]{6,})",
                    r"Invoice\s*(?:No\.?|Number)[:：\s]*([A-Z0-9\-]{6,})",
                ],
            ),
            FieldRule(
                name="invoice_date",
                description="开票日期",
                patterns=[
                    r"(?:开票日期|日期)[:：\s]*([0-9]{4}[./-年][0-9]{1,2}[./-月][0-9]{1,2}日?)",
                    r"(?:Date)[:：\s]*([0-9]{4}[./-][0-9]{1,2}[./-][0-9]{1,2})",
                ],
            ),
            FieldRule(
                name="amount_with_tax",
                description="价税合计",
                patterns=[
                    r"(?:.?小写.?)[:：\s]*(?:¥|￥)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
                    r"(?:Total(?:\s*Amount)?)[:：\s]*(?:¥|￥|CNY)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
                ],
            ),
            FieldRule(
                name="seller_name",
                description="销售方名称",
                patterns=[
                    r"(?:销售方(?:名称)?|销方名称)[:：\s]*([^\n\r]+)",
                    r"(?:Seller(?:\s*Name)?)[:：\s]*([^\n\r]+)",
                ],
            ),
            FieldRule(
                name="buyer_name",
                description="购买方名称",
                patterns=[
                    r"(?:购买方(?:名称)?|购方名称)[:：\s]*([^\n\r]+)",
                    r"(?:Buyer(?:\s*Name)?)[:：\s]*([^\n\r]+)",
                ],
            ),
        ]

    def add_field_rule(self, rule: FieldRule) -> None:
        self.field_rules[rule.name] = rule

    def process_and_save(self, invoice_path: str | Path) -> Path:
        input_path = Path(invoice_path).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"路径不存在: {input_path}")

        invoice_files, output_base_dir = self._collect_files_and_output_base(input_path)
        invoices_data = [self._process_single_invoice(path) for path in invoice_files]

        output_dir = output_base_dir / self.output_subdir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self.output_filename

        payload = {
            "version": "1.0",
            "source_path": str(input_path),
            "field_registry": {
                name: {
                    "description": rule.description,
                    "patterns": rule.patterns,
                    "capture_group": rule.capture_group,
                    "multiple": rule.multiple,
                }
                for name, rule in self.field_rules.items()
            },
            "extension_area": {
                "custom_field_rules": [],
                "custom_invoice_tags": [],
                "notes": "",
            },
            "invoices": invoices_data,
        }

        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def _collect_files_and_output_base(self, input_path: Path) -> tuple[List[Path], Path]:
        if input_path.is_file():
            return [input_path], input_path.parent

        if self.recursive:
            candidates = list(input_path.rglob("*"))
        else:
            candidates = list(input_path.glob("*"))

        invoice_files = [
            path
            for path in candidates
            if path.is_file() and path.suffix.lower() in (self.TEXT_EXTENSIONS | self.PDF_EXTENSIONS | self.IMAGE_EXTENSIONS)
        ]
        invoice_files.sort()
        return invoice_files, input_path

    def _process_single_invoice(self, file_path: Path) -> dict:
        text, extraction = self._extract_text(file_path)
        fields = self._extract_fields_from_text(text)

        return {
            "invoice_id": file_path.stem,
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": file_path.suffix.lower(),
            "extraction": extraction,
            "fields": fields,
            "custom_fields": {},
        }

    def _extract_text(self, file_path: Path) -> tuple[str, dict]:
        ext = file_path.suffix.lower()
        if ext in self.TEXT_EXTENSIONS:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return content, {"method": "plain_text", "status": "ok"}

        if ext in self.PDF_EXTENSIONS:
            return self._extract_pdf_text(file_path)

        if ext in self.IMAGE_EXTENSIONS:
            return self._extract_image_text(file_path)

        return "", {"method": "unsupported", "status": "failed", "message": f"不支持的文件类型: {ext}"}

    def _extract_pdf_text(self, file_path: Path) -> tuple[str, dict]:
        try:
            import pdfplumber  # type: ignore
        except ImportError:
            return "", {
                "method": "pdfplumber",
                "status": "failed",
                "message": "未安装 pdfplumber，请执行: .\\venv\\Scripts\\pip install pdfplumber",
            }

        with pymupdf.open(str(file_path)) as pdf:
            for page in pdf:
                blocks = page.get_text("dict")["blocks"]
                text_blocks = [block for block in blocks if block.get("type") == 0]
                print(json.dumps(text_blocks, ensure_ascii=False, indent=2))
        #print(f"已提取文本: {file_path}\n{text}...")
        #return text, {"method": "pdf", "status": status}

    def _extract_image_text(self, file_path: Path) -> tuple[str, dict]:
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            return "", {
                "method": "pytesseract",
                "status": "failed",
                "message": "未安装 Pillow，请执行: .\\venv\\Scripts\\pip install Pillow",
            }
        try:
            import pytesseract  # type: ignore
        except ImportError:
            return "", {
                "method": "pytesseract",
                "status": "failed",
                "message": "未安装 pytesseract，请执行: .\\venv\\Scripts\\pip install pytesseract",
            }

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang="chi_sim+eng")
        status = "ok" if text.strip() else "empty"
        return text, {"method": "pytesseract", "status": status}

    def _extract_fields_from_text(self, text: str) -> dict:
        normalized = text.replace("\u3000", " ")
        result = {}
        for name, rule in self.field_rules.items():
            matches = []
            for pattern in rule.compiled_patterns:
                for match in pattern.finditer(normalized):
                    value = self._extract_match_value(match, rule.capture_group)
                    if value:
                        matches.append(value.strip())

            unique_matches = list(dict.fromkeys(matches))
            if rule.multiple:
                result[name] = {
                    "value": unique_matches,
                    "matched": bool(unique_matches),
                }
            else:
                result[name] = {
                    "value": unique_matches[0] if unique_matches else None,
                    "matched": bool(unique_matches),
                }
        return result

    @staticmethod
    def _extract_match_value(match: re.Match, capture_group: int) -> Optional[str]:
        if capture_group > match.re.groups:
            return None
        return match.group(capture_group)


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="发票关键信息读取与格式化存储")
    parser.add_argument(
        "invoice_path",
        help="发票路径（单个文件或文件夹）",
    )
    parser.add_argument(
        "--output-subdir",
        default=InvoiceKeyInfoReaderFormatter.DEFAULT_OUTPUT_SUBDIR,
        help="输出子目录名（默认: invoice_parsed）",
    )
    parser.add_argument(
        "--output-file",
        default=InvoiceKeyInfoReaderFormatter.DEFAULT_OUTPUT_FILE,
        help="输出文件名（默认: all_invoices.json）",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="扫描目录时关闭递归",
    )
    return parser


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()

    reader = InvoiceKeyInfoReaderFormatter(
        output_subdir=args.output_subdir,
        output_filename=args.output_file,
        recursive=not args.no_recursive,
    )
    output_path = reader.process_and_save(args.invoice_path)
    print(f"已生成: {output_path}")


if __name__ == "__main__":
    main()
