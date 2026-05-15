import finance_fill
import invoice_formatter
import login
from pathlib import Path

def main():
    invoice_path = Path(input("请输入发票信息文件路径："))
    formatter = invoice_formatter.InvoiceFormatter(invoice_path)
    print("正在识别发票信息...")
    output_path = formatter.recognize()
    if not output_path is None:
        print(f"已生成: {output_path}")
        print("正在分类发票，可能耗时较长...")
    else:
        print("发票识别失败，请检查输入文件路径和格式。")
        return
    if formatter.classify():
        print("分类完成。")
    else:
        print("分类失败。请检查处理后的文件是否正确生成。")
        return
    print("正在登录")
    login_request = login.LoginRequest()
    if login_request.start_login():
        print("登录成功，正在填报财务系统...")
    else:
        print("登录失败，请检查登录流程。")
        return
    finance_filler = finance_fill.FillFinaceSystem(
        invoiceinfo_path=output_path,
    )
    finance_filler.start_operation()

if __name__ == "__main__":
    main()

