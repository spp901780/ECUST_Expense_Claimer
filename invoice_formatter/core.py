from __future__ import annotations

import argparse
import json
import re
import shutil
import pymupdf
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Any


@dataclass
class FieldRule:
    """字段匹配规则
    
    region_area: 指定此规则应在PDF哪个区域搜索（left/right/both）
                如果为None则默认搜索全文本
    """
    name: str
    patterns: List[str]
    capture_group: int = 1
    multiple: bool = False
    description: str = ""
    region_areas: Optional[list[str]] = None
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


class FileHandler(ABC):
    """文件处理器基类"""

    @abstractmethod
    def extract_text(self, file_path: Path) -> dict:
        """提取文本和元数据"""
        pass

    @abstractmethod
    def should_handle(self, file_path: Path) -> bool:
        """判断是否能处理此文件"""
        pass


class PDFHandler(FileHandler):
    """PDF 文件处理器 - 特殊处理，支持区域分割"""

    def should_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def extract_text(self, file_path: Path) -> dict:
        """提取PDF文本，按左右区域分割"""
        extracted_lefthalf: str = ""
        extracted_righthalf: str = ""
        
        with pymupdf.open(str(file_path)) as pdf:
            for page in pdf:
                page_rect = page.rect
                middle_x = (page_rect.x0 + page_rect.x1) / 2
                left_rect = pymupdf.Rect(page_rect.x0, page_rect.y0, middle_x, page_rect.y1)
                right_rect = pymupdf.Rect(middle_x, page_rect.y0, page_rect.x1, page_rect.y1)

                words = page.get_text("words", clip=left_rect, sort=True)
                region_lines = self._lines_from_words(words)
                extracted_lefthalf = "".join(region_lines)

                words = page.get_text("words", clip=right_rect, sort=True)
                region_lines = self._lines_from_words(words)
                extracted_righthalf = "".join(region_lines)

        # 返回合并文本和详细的区域信息
        combined_text = extracted_lefthalf + "\n" + extracted_righthalf
        return {
            "method": "pymupdf_words",
            "status": "ok" if extracted_lefthalf or extracted_righthalf else "empty",
            "regions": {
                "left": extracted_lefthalf,
                "right": extracted_righthalf
            }
        }

    @staticmethod
    def _lines_from_words(words: list[tuple]) -> List[str]:
        """将PDF word数据组织成行"""
        lines: List[str] = []
        current_key = None
        current_words: List[str] = []

        for word in words:
            text = str(word[4]).strip()
            if not text:
                continue

            key = (word[5], word[6])
            if current_key is None:
                current_key = key

            if key != current_key:
                lines.append("".join(current_words).strip())
                current_key = key
                current_words = []

            current_words.append(text)

        if current_words:
            lines.append("".join(current_words).strip())

        return [line for line in lines if line]


class ImageHandler(FileHandler):
    """图片文件处理器"""
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

    def should_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.IMAGE_EXTENSIONS

    def extract_text(self, file_path: Path) -> dict:
        """使用OCR提取图片文本"""
        try:
            from PIL import Image
        except ImportError:
            return {
                "method": "pytesseract",
                "status": "failed",
                "message": "未安装 Pillow，请执行: pip install Pillow",
            }
        try:
            import pytesseract
        except ImportError:
            return {
                "method": "pytesseract",
                "status": "failed",
                "message": "未安装 pytesseract，请执行: pip install pytesseract",
            }

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang="chi_sim+eng")
        status = "ok" if text.strip() else "empty"
        return {"method": "pytesseract", 
                "status": status, 
                "regions": {
                    "all": text
                }}


class InvoiceFormatter:
    """发票关键信息读取和格式化存储器"""
    
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
        self.file_handlers: List[FileHandler] = [PDFHandler(), ImageHandler()]

        for rule in field_rules or self.default_field_rules():
            self.add_field_rule(rule)

    @staticmethod
    def default_field_rules() -> List[FieldRule]:
        """默认字段规则"""
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
                region_areas=["right"],
                patterns=[
                    r"发票号码[:：\s]*([0-9]{6,})",
                    r"Invoice\s*(?:No\.?|Number)[:：\s]*([A-Z0-9\-]{6,})",
                ],
            ),
            FieldRule(
                name="invoice_date",
                description="开票日期",
                region_areas=["right"],
                patterns=[
                    r"(?:开票日期)[:：\s]*([0-9]{4}[./-年][0-9]{1,2}[./-月][0-9]{1,2}日?)",
                    r"(?:Date)[:：\s]*([0-9]{4}[./-][0-9]{1,2}[./-][0-9]{1,2})",
                ],
            ),
            FieldRule(
                name="amount_with_tax",
                description="价税合计",
                region_areas=["right"],
                patterns=[
                    r"(?:[\(（]小写[\)）])[:：\s]*(?:¥|￥)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
                    r"(?:Total(?:\s*Amount)?)[:：\s]*(?:¥|￥|CNY)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
                ],
            ),
            FieldRule(
                name="seller_name",
                description="销售方名称",
                region_areas=["right"],
                patterns=[
                    r"(?:销.*(?:名称))[:：\s]([^\n\r]+?(大学|公司|（个体工商户）|商行|店|经营部|营业部|厂))",
                    r"(?:Seller(?:\s*Name)?)[:：\s]*([^\n\r]+)",
                ],
            ),
            FieldRule(
                name="buyer_name",
                description="购买方名称",
                region_areas=["left"],
                patterns=[
                    r"(?:购.*(?:名称))[:：\s]([^\n\r]+?(大学|公司|（个体工商户）|商行|店|经营部|营业部|厂))",
                    r"(?:Buyer(?:\s*Name)?)[:：\s]*([^\n\r]+)",
                ],
            ),
            FieldRule(
                name="invoice_type",
                description="发票类型",
                region_areas=["right"],
                patterns=[
                    r"((普通|专用)发票)",
                ],
            ),
        ]

    def add_field_rule(self, rule: FieldRule) -> None:
        """添加字段规则"""
        self.field_rules[rule.name] = rule

    def process_and_save(self, invoice_path: str | Path) -> Path:
        """处理发票文件并保存结果"""
        input_path = Path(invoice_path).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"路径不存在: {input_path}")

        invoice_files, output_base_dir = self._collect_files_and_output_base(input_path)
        output_dir = output_base_dir / self.output_subdir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self.output_filename
        
        invoices_data = []
        for path in invoice_files:
            invoice = self._process_single_invoice(path)  # 预处理以验证文件可读性
            extract_data = invoice.get("fields", {})
            is_valid = True
            if not extract_data.get("invoice_code", {}).get("matched"):
                for k in extract_data.keys() - {"invoice_code"}:
                    if not extract_data[k].get("matched"):
                        is_valid = False
                        
            if is_valid:
                invoices_data.append(invoice)
            else:
                shutil.copy2(path, output_dir / path.name)

        payload = {
            "version": "1.0",
            "source_path": str(input_path),
            # "field_registry": {
            #     name: {
            #         "description": rule.description,
            #         "patterns": rule.patterns,
            #         "capture_group": rule.capture_group,
            #         "multiple": rule.multiple,
            #         "region_areas": rule.region_areas,
            #     }
            #     for name, rule in self.field_rules.items()
            # },
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
        """收集需要处理的文件"""
        if input_path.is_file():
            return [input_path], input_path.parent

        if self.recursive:
            candidates = list(input_path.rglob("*"))
        else:
            candidates = list(input_path.glob("*"))

        supported_extensions = self.PDF_EXTENSIONS | self.IMAGE_EXTENSIONS
        invoice_files = [
            path
            for path in candidates
            if path.is_file() and path.suffix.lower() in supported_extensions
        ]
        invoice_files.sort()
        return invoice_files, input_path

    def _process_single_invoice(self, file_path: Path) -> dict:
        """处理单个发票文件"""
        extraction = self._extract_text(file_path)
        fields = self._extract_fields_from_text(extraction)

        return {
            "invoice_id": file_path.stem,
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": file_path.suffix.lower(),
            "extraction": extraction,
            "fields": fields,
            "custom_fields": {},
        }

    def _extract_text(self, file_path: Path) -> dict:
        """使用合适的处理器提取文本"""
        for handler in self.file_handlers:
            if handler.should_handle(file_path):
                return handler.extract_text(file_path)
        
        return {
            "method": "unsupported",
            "status": "failed",
            "message": f"不支持的文件类型: {file_path.suffix}"
        }

    def _extract_fields_from_text(self, extraction: dict,) -> dict:
        """从文本中提取字段
        
        对于PDF文件，如果规则指定了region_area，则在对应区域内搜索
        对于其他文件，在全文本中搜索
        """
        result = {}

        for name, rule in self.field_rules.items():
            matches = []
            
            # 确定搜索文本
            search_text = ""
            region_text = extraction["regions"]
            if not rule.region_areas is None:
                if "left" in rule.region_areas:
                    search_text += '\n' + region_text.get("left")
                elif "right" in rule.region_areas:
                    search_text += '\n' + region_text.get("right")
                elif "all" in rule.region_areas:
                    search_text = "\n".join(region_text.values())
            else:
                search_text = "".join(region_text.values())
            
            # 在指定区域搜索
            for pattern in rule.compiled_patterns:
                for match in pattern.finditer(search_text):
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

            if not unique_matches:
                print(rule,extraction)
        return result

    @staticmethod
    def _extract_match_value(match: re.Match, capture_group: int) -> Optional[str]:
        """提取匹配组的值"""
        if capture_group > match.re.groups:
            return None
        return match.group(capture_group)


def _build_cli_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(description="发票关键信息读取与格式化存储")
    parser.add_argument(
        "invoice_path",
        help="发票路径（单个文件或文件夹）",
    )
    parser.add_argument(
        "--output-subdir",
        default=InvoiceFormatter.DEFAULT_OUTPUT_SUBDIR,
        help="输出子目录名（默认: invoice_parsed）",
    )
    parser.add_argument(
        "--output-file",
        default=InvoiceFormatter.DEFAULT_OUTPUT_FILE,
        help="输出文件名（默认: all_invoices.json）",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="扫描目录时关闭递归",
    )
    return parser


def main() -> None:
    """主函数"""
    parser = _build_cli_parser()
    args = parser.parse_args()

    formatter = InvoiceFormatter(
        output_subdir=args.output_subdir,
        output_filename=args.output_file,
        recursive=not args.no_recursive,
    )
    output_path = formatter.process_and_save(args.invoice_path)
    print(f"已生成: {output_path}")


