from __future__ import annotations
from os import read
from threading import stack_size
import time

from playwright.sync_api import TimeoutError
from dataclasses import dataclass, field, fields
from pathlib import Path
import json
import re

class FillFinaceSystem:
    AUTH_DIR = Path(__file__).parent.parent / "auth"
    def __init__(self, invoiceinfo_path: Path, platform: str = "ECUST", context_path: Path = AUTH_DIR):
        self.platform = platform
        self.context_path = context_path
        self.invoiceinfo_path = invoiceinfo_path
        self.invoiceinfo = None

        try:
            self.invoiceinfo = json.loads(self.invoiceinfo_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Failed to open invoice file {self.invoiceinfo_path}: {e}")
            raise


    def open_main_page(self) -> bool:
        # This is a placeholder implementation. You should replace it with actual logic to open the login page.
        from playwright.sync_api import sync_playwright
        playwright_instance = sync_playwright().start()
        self.context_path.mkdir(parents=True, exist_ok=True)
        browser = playwright_instance.chromium.launch_persistent_context(user_data_dir=self.context_path, headless=False)
        page = browser.pages[0]
        if self.platform == "ECUST":
            #enter the main page
            page.goto("https://cwc.ecust.edu.cn/WFManager/home2.jsp")  # Replace with actual login URL
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
                    frame.locator("li[onclick*='10313']").click()
            except TimeoutError:
                print("Failed to load the main page within the expected time.")
                
            self._auto_fill(page, frame)
            input("Input to stop")
            browser.close()
            playwright_instance.stop()
            return True
        
        else:
            print(f"Platform {self.platform} is not supported.")
            browser.close()
            playwright_instance.stop()
            return False

    def _auto_fill(self, page, frame):
        # This is a placeholder implementation. You should replace it with actual logic to fill the form.
        if self.invoiceinfo is None:
            print("No invoice information available to fill the form.")
            raise Exception("No invoice information available.")
        
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

                time.sleep(0.4)
                frame.get_by_role("button", name="查验").click()
                try:
                    with page.expect_response(
                        lambda r: r.request.method == "POST"
                        and r.status == 200
                    ):
                        pass
                except TimeoutError:
                    print(invoice, "查验失败")
                



                    
                
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
    fill_system = FillFinaceSystem(invoiceinfo_path=Path("D:/OneDrive/发票/测试用/眼镜项目发票4821.7/invoice_parsed/all_invoices.json"))
    success = fill_system.open_main_page()
    if success:
        print("Main page opened successfully!")
    else:
        print("Failed to open main page.")