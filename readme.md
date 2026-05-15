# ECUST Expense Claimer

面向校内报销流程的自动化工具集，覆盖发票格式化、分类、认证以及财务处报销单填报等环节。

## 功能概览
- 发票格式化识别与存储
- 发票分类与认证流程自动化
- 财务处登录与报销单申请自动化

## 快速开始

### 1. 下载源代码
使用 Git 克隆或直接下载压缩包解压。

```bash
git clone <repo_url>
cd ECUST_Expense_Claimer
```

### 2. 创建并启用虚拟环境 (venv)

```bash
python -m venv .venv
```

-   Windows PowerShell:

    ```powershell
    .\.venv\Scripts\Activate.ps1
    ```

-  macOS/Linux:

    ```bash
    source .venv/bin/activate
    ```

### 3. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 4. 安装 Playwright 浏览器

```bash
python -m playwright install
```

### 5. 运行

```bash
python main.py
```

## 使用方法

！！！目前实装部的功能未完成，在“手动完成报销单填写并提交后继续...”即无功能！！！

启动后按终端提示依次操作即可：
- 输入发票文件或目录路径；
- 等待发票识别与分类完成；
- 在弹出的浏览器中完成登录；
- 按提示编辑并保存 `reimbursement_info.json`；
- 回到终端回车后继续自动填报流程。

## 项目架构

项目整体分为三部分：

1. **发票分类（`invoice_formatter/`）**  
   负责发票文本提取、字段识别与分类。分类默认使用 **BGE** 模型（`BAAI/bge-small-zh-v1.5`），仓库内已包含模型文件（`invoice_formatter/models/`），也可替换为其他兼容嵌入模型。
2. **登录页面（`login/`）**  
   使用 Playwright 打开并复用登录态，完成华东理工财务系统登录流程。
3. **自动填充（`finance_fill/`）**  
   基于已识别与分类的发票数据，自动执行发票查验、报销单信息填写与提交流程。

入口文件为 `main.py`，按“发票识别与分类 -> 登录 -> 自动填报”的顺序串联执行。

## 开发进度
完成发票格式化识别并存储 （已完成）  
测试财务处登录 (已完成)  
测试财务处基本功能 (已完成)  
完成发票认证自动化流程（已完成）  
添加发票分类功能以排除不需要实装处认证的发票（已完成）  
完成财务处报销单申请部分自动化（已完成）  
完成发票分类（已完成）

测试实装处基本功能  
完成分发流程
