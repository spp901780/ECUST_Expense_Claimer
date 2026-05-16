from __future__ import annotations
from abc import abstractmethod, ABC
from os import read

from pathlib import Path
import json
import importlib
import os

class FillSystem(ABC):
    AUTH_DIR = Path(__file__).parent.parent / "auth"

    def __new__(cls, invoiceinfo_path: Path, platform: str = "ECUST", context_path: Path = AUTH_DIR):
        if cls is FillSystem:
            try:
                module = importlib.import_module(f"fill_system.{platform}")
                return super().__new__(getattr(module, f"{platform}_FillSystem"))
            except ImportError:
                raise ValueError(f"Unsupported platform: {platform}")
        else:
            return super().__new__(cls)
        
    def __init__(self, invoiceinfo_path: Path, platform: str = "ECUST", context_path: Path = AUTH_DIR):
        self.platform = platform
        self.context_path = context_path
        self.invoice_info = self.load_invoice_info(invoiceinfo_path)
        self.reimbursement_info = self.load_reimbursement_info()

        from playwright.sync_api import sync_playwright
        self.playwright_instance = sync_playwright().start()
        self.context_path.mkdir(parents=True, exist_ok=True)
        self.browser = self.playwright_instance.chromium.launch_persistent_context(user_data_dir=self.context_path, headless=False)
        self.page = self.browser.pages[0]

    @abstractmethod
    def start_finance_fill(self) -> int:
        pass

    @abstractmethod
    def start_equip_fill(self, serial_number: int) -> int:
        pass

    def load_invoice_info(self, path: Path):
        try:
            invoice_info = json.loads(path.read_text(encoding="utf-8"))
            return invoice_info
        except Exception as e:
            print(f"Failed to load invoice information from {path}: {e}")
            raise

    def load_reimbursement_info(self):
        info_path = Path(__file__).parent.parent / "reimbursement_info.json"
        try:
            if not info_path.exists():
                self._initial_reimbursement_info(info_path)

            retey_count = 0
            while retey_count < 5:
                try:
                    os.startfile(str(info_path))
                except Exception as e:
                    print(f"Failed to open reimbursement info file: {e}")
                    raise

                input(f"请编辑并保存文件：{info_path}，关闭后按回车继续...")

                try:
                    loaded_info = json.loads(info_path.read_text(encoding="utf-8"))
                    
                    # 验证结构是否正确
                    if not self._validate_reimbursement_info(loaded_info):
                        print("Reimbursement info file structure is invalid. Please ensure it has the correct format.")
                        self._initial_reimbursement_info(info_path)
                        continue
                    
                    # 检查是否所有项目的 value 都已填写
                    if not self._check_values_filled(loaded_info):
                        print("Some fields in the reimbursement info file are not filled. Please fill in all values.")
                        continue
                    
                    return loaded_info
                except json.JSONDecodeError as e:
                    print(f"Failed to parse reimbursement info file: {e}")
                    self._initial_reimbursement_info(info_path)
                    continue
        except Exception as e:
            print(f"Failed to open reimbursement info file: {e}")
            raise

    @staticmethod
    def _validate_reimbursement_info(info: dict) -> bool:
        required_keys = {"project_number", "name", "abstract", "phone_number"}
        
        # 检查是否包含所有必需的键
        if not isinstance(info, dict) or not required_keys.issubset(info.keys()):
            return False
        
        # 检查每个字段是否包含 "discription" 和 "value" 键
        for key in required_keys:
            field = info[key]
            if not isinstance(field, dict) or "discription" not in field or "value" not in field:
                return False
        
        return True

    @staticmethod
    def _check_values_filled(info: dict) -> bool:
        for key, field in info.items():
            if isinstance(field, dict) and "value" in field:
                if not field["value"] or (isinstance(field["value"], str) and not field["value"].strip()):
                    return False
        return True

    def _initial_reimbursement_info(self, info_path):
        info_path.write_text(
            json.dumps({
                "discription": "请在所有value 字段填写对应信息，填写完成后保存并关闭文件",
                "project_number": {
                    "discription": "项目代码",
                    "value": ""
                },
                "name": {
                    "discription": "实际报销人",
                    "value": ""
                },
                "abstract": {
                    "discription": "摘要",
                    "value": ""
                },
                "phone_number": {
                    "discription": "电话/手机",
                    "value": ""
                }
            }, 
                ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.reimbursement_info = None
        
def __deinit__(self):
    self.browser.close()
    self.playwright_instance.stop()

def main():
    fill_system = FillSystem(invoiceinfo_path=Path("D:/OneDrive/发票/测试用/眼镜项目发票4821.7/formatter_processed_invoices/all_invoices.json"))
    success = fill_system.start_finance_fill()
    if success:
        print("Main page opened successfully!")
    else:
        print("Failed to open main page.")