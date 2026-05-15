from __future__ import annotations
from os import read
from threading import stack_size
import time

from playwright.sync_api import TimeoutError
from dataclasses import dataclass, field, fields
from pathlib import Path
import json
import re
import os

class FillFinaceSystem:
    AUTH_DIR = Path(__file__).parent.parent / "auth"
    def __init__(self, invoiceinfo_path: Path, platform: str = "ECUST", context_path: Path = AUTH_DIR):
        self.platform = platform
        self.context_path = context_path
        self.invoiceinfo_path = invoiceinfo_path
        self.reimbursement_info = None

        
        try:
            self.invoiceinfo = json.loads(self.invoiceinfo_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Failed to open invoice file {self.invoiceinfo_path}: {e}")
            raise
        
        self.load_reimbursement_info()

    def load_reimbursement_info(self):
        info_path = Path(__file__).parent.parent / "reimbursement_info.json"
        try:
            if not info_path.exists():
                self._initial_reimbursement_info(info_path)

            while True:
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
                    
                    self.reimbursement_info = loaded_info
                    break
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
        


    def start_operation(self) -> bool:
        if self.reimbursement_info is None:
            print("reimbursement_info not available. Cannot start operation.")
            return False

        from playwright.sync_api import sync_playwright
        playwright_instance = sync_playwright().start()
        self.context_path.mkdir(parents=True, exist_ok=True)
        browser = playwright_instance.chromium.launch_persistent_context(user_data_dir=self.context_path, headless=False)
        page = browser.pages[0]
        if self.platform == "ECUST":
            #enter the main page
            page.goto("https://cwc.ecust.edu.cn/WFManager/home2.jsp") 
            page.wait_for_load_state("networkidle")
            page.locator("div[onclick*='WF_YB6']").first.click()
            #wait for the page to load
            page.wait_for_load_state("networkidle")
                

            frame = page
            try:
                with page.expect_response(
                    lambda r: "commonQuery_doQuery.action" in r.url and r.status == 200
                ):
                    page.wait_for_load_state("networkidle")
                    frame.wait_for_timeout(5000)
                    frame = page.frame_locator("iframe[src*='WF_YB6']")
            except TimeoutError:
                print("Failed to load the main page within the expected time.")

        
            if self.invoiceinfo is None:
                print("No invoice information available to fill the form.")
                raise Exception("No invoice information available.")
            self._verify_invoices(page, frame)
            self._apply_for_reimbursement(page, frame)
            input("Input to stop")

            browser.close()
            playwright_instance.stop()
            return True
        
        else:
            print(f"Platform {self.platform} is not supported.")
            
            return False


    def _verify_invoices(self, page, frame):
        # This is a placeholder implementation. You should replace it with actual logic to fill the form.

        frame.locator("li[onclick*='10313']").click()
        
        for invoice in self.invoiceinfo.get("invoices", []):
            if self.get_invoice_type(invoice) == "数电票":
                print(invoice["invoice_id"])
                row = frame.locator("tr", has_text="发票类型").first
                select = row.locator("select:visible")
                select.select_option("数电票")

                # 限定同一个 tbody
                tbody = select.locator("xpath=ancestor::tbody[1]")
                # 在同一 tbody 内找“发票号码”并输入
                row = tbody.locator("tr", has_text="发票号码").first
                input_box = row.locator("input:visible")
                input_box.fill(invoice["fields"]["invoice_number"]["value"])

                row = tbody.locator("tr", has_text=re.compile(r"开票日期")).first
                input_box = row.locator("input:visible")
                input_box.fill(invoice["fields"]["invoice_date"]["value"].replace("年",'').replace("月",'').replace("日",''))
                
                row = tbody.locator("tr", has_text=re.compile(r"发票金额")).first
                input_box = row.locator("input:visible")
                input_box.fill(invoice["fields"]["amount_with_tax"]["value"])

                time.sleep(0.3)
                frame.get_by_role("button", name="查验").click()
                try:
                    with page.expect_response(
                        lambda r: r.request.method == "POST"
                        and r.status == 200
                    ):
                        pass
                except TimeoutError:
                    print(invoice, "查验失败")
                
    def _apply_for_reimbursement(self, page, frame) -> int:
        frame.locator("li[onclick*='5215']").click()
        frame.get_by_role("button", name="申请报销单").click()

        frame.locator("button[id*='invoice_remark_btn']").click()
        page.wait_for_timeout(500)

        # 选择要要报销的发票并统计不同分类的金额总和
        amount_by_class = {}
        select_invoices_number = 0
        for invoice in self.invoiceinfo.get("invoices", []):
            if self.get_invoice_type(invoice) == "数电票":
                #找到对应的发票行并勾选
                try:
                    row = frame.locator("tr").filter(
                    has=frame.locator(f"td:nth-child(3):text-is('{invoice['fields']['invoice_number']['value']}')")
                    )
                    row.locator("input[type='checkbox']").check(timeout=1000)
                except TimeoutError:
                    print("请务必注意，有发票没有认证成功，无法找到对应的行，请检查发票信息是否正确")
                    print(f"Failed to find the row for invoice {invoice['invoice_id']} with number {invoice['fields']['invoice_number']['value']}")
                    raise

                select_invoices_number += 1
                classification = invoice["classification"]["value"]
                amount_by_class[classification] = amount_by_class.get(classification, 0.0) + float(invoice["fields"]["amount_with_tax"]["value"])

        frame.locator("button", has_text="确定").click()

        # 填写必要信息
        frame.locator("td:has-text('附件张数') + td input").fill(str(select_invoices_number))
        frame.locator("td:has-text('单项目报销') + td input").fill(str(self.reimbursement_info["project_number"]["value"]))
        frame.locator("td:has-text('实际报销人') + td input").fill(str(self.reimbursement_info["name"]["value"]))
        frame.locator("td:has-text('电话') + td input").fill(str(self.reimbursement_info["phone_number"]["value"]))
        frame.locator("td:has-text('手机') + td input").fill(str(self.reimbursement_info["phone_number"]["value"]))
        frame.locator("td:has-text('摘要') + td input").fill(str(self.reimbursement_info["abstract"]["value"]))
        frame.locator("td:has-text('选择支付方式') + td select").select_option("转卡")
        frame.locator("button", has_text="下一步").click()
        try:
            page.expect_response(
                lambda r: "common_getBindingDataBackend.action" in r.url and r.status == 200
            )
        except TimeoutError:
            print("Failed to preceed while waiting for the next page to load.")

        # 填写材料费用信息
        frame.locator("td:has-text('材料费') + td input").fill(str(amount_by_class.get("material", 0.0)))
        frame.locator("td:has-text('软件购置费') + td input").fill(str(amount_by_class.get("software", 0.0)))
        frame.locator("button", has_text="下一步").click()
        try:
            page.expect_response(
                lambda r: "common_getBindingDataBackend.action" in r.url and r.status == 200
            )
        except TimeoutError:
            print("Failed to preceed while waiting for the next page to load.")

        input("手动完成报销单填写并提交后继续...")
        page.goto("https://cwc.ecust.edu.cn/WFManager/home2.jsp") 
        while True:
            raw_input = input("请输入获取的报销单序列号以用于实装处填报")
            try:
                number = int(raw_input)
                return number
            except ValueError:
                print("Invalid input. Please enter a valid number.")

                
    @staticmethod
    def get_invoice_type(invoice) -> str:
        fields = invoice.get("fields", {})
        result = ""
        if fields["invoice_code"]["matched"] == False \
            and fields["invoice_number"]["matched"] == True: #数电票
            result = "数电票"
        elif fields["invoice_code"]["matched"] == True:
            result = "普通数字发票"
        
        return result




def main():
    fill_system = FillFinaceSystem(invoiceinfo_path=Path("D:/OneDrive/发票/测试用/眼镜项目发票4821.7/formatter_processed_invoices/all_invoices.json"))
    success = fill_system.start_operation()
    if success:
        print("Main page opened successfully!")
    else:
        print("Failed to open main page.")