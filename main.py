import finance_fill
import invoice_formatter
import login
from pathlib import Path

def main():
    invoice_path = Path(input("请输入发票信息文件路径："))
    formatter = invoice_formatter.InvoiceFormatter(invoice_path)
    result = formatter.recognize()
    formatter.classify(result)
    
if __name__ == "__main__":
    main()

