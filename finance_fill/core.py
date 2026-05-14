from __future__ import annotations

from playwright.sync_api import TimeoutError
from dataclasses import dataclass, field
from pathlib import Path

class FillFinaceSystem:
    AUTH_DIR = Path(__file__).parent.parent / "auth"
    def __init__(self, invoiceinfo_path: Path, platform: str = "ECUST", context_path: Path = AUTH_DIR):
        self.platform = platform
        self.context_path = context_path
        self.invoiceinfo_path = invoiceinfo_path


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
                    frame.wait_for_timeout(500)
                    frame = page.frame_locator("iframe[src*='WF_YB6']")
                    frame.locator("li[onclick*='10313']").click()
            except TimeoutError:
                print("Failed to load the main page within the expected time.")
                
            input("Input to stop")
            browser.close()
            playwright_instance.stop()
            return True
        
        else:
            print(f"Platform {self.platform} is not supported.")
            browser.close()
            playwright_instance.stop()
            return False

    def auto_fill(self):
        # This is a placeholder implementation. You should replace it with actual logic to fill the form.
        print("Auto-filling the form...")

    def read_invoice(self):
        # This is a placeholder implementation. You should replace it with actual logic to read the invoice.
        print("Reading the invoice...")

def main():
    fill_system = FillFinaceSystem(invoiceinfo_path=Path("----PATH----"))
    success = fill_system.open_main_page()
    if success:
        print("Main page opened successfully!")
    else:
        print("Failed to open main page.")