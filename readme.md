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

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 4. 安装 Playwright 及浏览器

```bash
python -m pip install playwright
python -m playwright install
```

### 5. 运行

```bash
python main.py
```

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