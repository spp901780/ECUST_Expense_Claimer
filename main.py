import fill_system
import invoice_formatter
import login
from pathlib import Path

def main():
    while True:
        input_raw = input("请输入发票信息文件路径：")
        if input_raw.strip() == "":
            print("未输入路径")
            continue
        try:
            input_path = Path(input_raw).expanduser().resolve()
            if not input_path.exists():
                print(f"路径不存在: {input_path}")
                continue
            else:
                break
        except Exception as e:
            print(f"路径无效: {e}")
            continue
    formatter = invoice_formatter.InvoiceFormatter(input_raw)
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
    
    finance_filler = fill_system.FillSystem(
        invoiceinfo_path=output_path,
        platform="ECUST"
    )

    number = finance_filler.start_finance_fill()
    finance_filler.start_equip_fill(number)

if __name__ == "__main__":
    main()

