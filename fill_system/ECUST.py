import re
from pathlib import Path
from fill_system import FillSystem
import time

class ECUST_FillSystem(FillSystem):

    def start_finance_fill(self) -> int:
        if self.reimbursement_info is None:
            print("reimbursement_info not available. Cannot start operation.")
            return -1

        page = self.page
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
                page.wait_for_timeout(5000)
                frame = page.frame_locator("iframe[src*='WF_YB6']")
        except TimeoutError:
            print("Failed to load the main page within the expected time.")

    
        if self.invoice_info is None:
            print("No invoice information available to fill the form.")
            raise Exception("No invoice information available.")
        
        self._verify_invoices(page, frame)
        while True:
            number = self._apply_for_reimbursement(page, frame)
            if number > 0:
                break
            else:
                print("重新执行自动填充报销单...")
        input("Input to stop")   
        return number


    def _verify_invoices(self, page, frame):
        # This is a placeholder implementation. You should replace it with actual logic to fill the form.

        frame.locator("li[onclick*='10313']").click()
        
        for invoice in self.invoice_info.get("invoices", []):
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
        for invoice in self.invoice_info.get("invoices", []):
            if self.get_invoice_type(invoice) == "数电票" \
            and invoice["classification"]["value"] in ["material", "software"]:
                #找到对应的发票行并勾选
                try:
                    row = frame.locator("tr").filter(
                    has=frame.locator(f"td:nth-child(3):text-is('{invoice['fields']['invoice_number']['value']}')")
                    )
                    row.locator("input[type='checkbox']").check(timeout=1000)
                except :
                    print("请务必注意，有发票没有认证成功，无法找到对应的行，请检查发票信息是否正确")
                    print(f"Failed to find the row for invoice {invoice['invoice_id']} with number {invoice['fields']['invoice_number']['value']}")
                    raise

                select_invoices_number += 1
                classification = invoice["classification"]["value"]
                amount_by_class[classification] = amount_by_class.get(classification, 0.0) + float(invoice["fields"]["amount_with_tax"]["value"])

        frame.locator("button", has_text="确定").click()

        # 填写必要信息
        assert self.reimbursement_info is not None # 这里应该永远不会触发，因为在 start_operation 的开头就检查过了
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
        page.wait_for_load_state("networkidle")
        page.locator("div[onclick*='WF_YB6']").first.click()
        while True:
            print("若未完成报销单提交，输入\"n\"重新执行自动填充报销单")
            raw_input = input("请输入刚才提交的报销单的报销单号: ")
            if raw_input.lower() == "n":
                return -1
            try:
                number = int(raw_input)
                return number
            except ValueError:
                print("输入无效，重新输入报销单号或输入\"n\"重新执行自动填充报销单", end='\n\n')

                
    def start_equip_fill(self, serial_number: int) -> int:
        if self.reimbursement_info is None:
            print("reimbursement_info not available. Cannot start operation.")
            return -1

        page = self.page
        #enter the main page
        page.goto("https://wzsh.ecust.edu.cn/sso/index.do") 
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(200)
        frame = next(
            f for f in page.frames
            if "turnMain.do" in f.url
        )
        with page.expect_response(lambda r: "My97DatePicker.htm" in r.url) as response_info:
            frame.locator(
                "a",
                has_text="发票审核"
            ).filter(
                has_text="(无请款)"
            ).click(timeout=2000)


        dia_frame = None
        def process_dialog():
            frame.wait_for_selector("iframe[name='dialog']", timeout=2000)
            nonlocal dia_frame
            dia_frame = frame.frame_locator("iframe[name='dialog']")
            dia_frame.locator('input[value="确定"].ui_state_highlight').click()

            dia_frame.locator("td:has-text('财务系统预约号：') + td input").fill(str(serial_number))
            dia_frame.locator("td:has-text('安全类别：') + td select").select_option("无")

        def fill_invoice(invoice, count):
            assert dia_frame is not None, "对话框未正确弹出，无法继续执行。2"
            upload_td = dia_frame.locator("td:has-text('发票上传') + td")
            upload = upload_td.locator("input[type='file'][name='file1']").first
            upload.set_input_files(str(Path(invoice["file_path"]).expanduser().resolve(strict=True)))

            table = dia_frame.locator("table[id='table_qk']")
            def qk_cell(header_keyword: str, line: int):
                header_td = table.locator("td,th", has_text=header_keyword).first
                header_tr = header_td.locator("xpath=ancestor::tr[1]")

                # 在本 tr 内部遍历每个单元格，找到“那个包含关键字的单元格”所在列
                cells = header_tr.locator("td,th")
                key = "".join(header_keyword.split())

                idx = None
                for i in range(cells.count()):
                    txt = "".join(cells.nth(i).inner_text().split())  # 去空白
                    if key in txt:
                        idx = i
                        break
                if idx is None:
                    raise RuntimeError(f"找不到表头列：{header_keyword}，header_tr文本={header_tr.inner_text()}")

                return header_tr.locator(f"xpath=following-sibling::tr[{line}]").locator("td").nth(idx)

            qk_cell("发票号码", count).locator("input").fill(str(invoice["fields"]["invoice_number"]["value"]))
            qk_cell("材料品名", count).locator("select").select_option("材料")
            qk_cell("金额", count).locator("input").fill(str(invoice["fields"]["amount_with_tax"]["value"]))
            qk_cell("是否平台外化学品", count).locator("select").select_option("否")

        process_dialog()
        assert dia_frame is not None, "对话框未正确弹出，无法继续执行。1"

        invoice_count = 1
        for invoice in self.invoice_info.get("invoices", []):
            if invoice_count <= 10:
                if invoice["classification"]["value"] in ["material"]:
                    if invoice_count != 1:
                        dia_frame.locator("a", has_text="追加").click()
                    fill_invoice(invoice, invoice_count)
                    invoice_count += 1
            else:
                with page.expect_response(lambda r: "listUnCommit.do" in r.url) as response_info:
                    dia_frame.locator("input[value='保存']").click()
                invoice_count = 1
                frame.locator("input[value='发票审核(无请款)']").click()
                process_dialog()
        with page.expect_response(lambda r: "listUnCommit.do" in r.url) as response_info:
                    dia_frame.locator("input[value='保存']").click()

        input("input to exit")
        return False
    
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




