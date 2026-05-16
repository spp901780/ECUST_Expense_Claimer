# ECUST Expense Claimer

面向校内报销流程的自动化工具集，覆盖发票格式化、分类、认证以及财务处报销单填报，实装处审核单等环节。

<!-- Highlight: Quick summary and warnings -->
<div style="border-radius:6px; padding:10px; background:#fff8e1; border-left:6px solid #ffa000; margin:12px 0;">
   <strong style="color:#bf360c; font-size:1.05em;">重要提醒：</strong>
   <span style="color:#bf360c; font-weight:600;">本工具支持自动填表与保存，但请在每次提交前<strong>人工复核</strong>所有填写项与附件（尤其是发票类型与金额）。</span>
</div>

<div style="border-radius:6px; padding:8px; background:#e3f2fd; border-left:6px solid #1976d2; margin-bottom:16px;">
   <strong style="color:#0d47a1">安全提示：</strong>
   <span>不要在共享或不受信环境中保存明文凭证；程序依赖.auth/文件夹保存的浏览器凭据，该文件夹可以在运行完成后手动删除。</span>
</div>

<!-- Quick highlights -->
<div style="display:flex; gap:12px; margin-bottom:18px;">
   <div style="flex:1; padding:8px; background:#f1f8e9; border-radius:6px; border:1px solid #c5e1a5;">
      <strong>适用场景</strong>
      <div>校内财务系统报销单自动化（发票识别 → 分类 → 填报）。</div>
   </div>
   <div style="flex:1; padding:8px; background:#fff3e0; border-radius:6px; border:1px solid #ffd180;">
      <strong>当前限制</strong>
      <div>只支持数电票；差旅发票目前不支持自动填报；对复杂实装处选项默认使用安全/缺省值。</div>
   </div>
</div>

## 功能概览
- 发票格式化识别与存储
- 发票分类与认证流程自动化
- 财务处登录与报销单申请自动化
- 实装处审核申请

## 快速开始


1) 克隆仓库并进入项目目录：

```bash
git clone <repo_url>
cd ECUST_Expense_Claimer
```

2) 创建并启用虚拟环境：

```bash
python -m venv .venv
```

- Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

- macOS / Linux:

   ```bash
   source .venv/bin/activate
   ```

3) 安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

4) 安装 Playwright 浏览器：

```bash
python -m playwright install
```

5) 运行主程序：

```bash
python main.py
```


## 使用方法

### 注意事项
- 识别：只支持数电发票（即没有发票代号的普通数字发票）
- 分类：将识别出的发票自动分类为 **材料费 / 服务费 / 差旅费**。
- 认证：所有发票均进行查验与认证。
- 财务处填报：对材料费与服务费自动填报报销单（差旅发票暂不支持）。


### 运行流程：

-  在项目文件夹终端中激活虚拟环境

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

    macOS / Linux:

   ```bash
   source .venv/bin/activate
   ```
- 运行项目
   
   ```bash 
   python main.py
   ```
    
- 在终端输入<strong>发票文件或目录路径</strong>
- 等待识别与分类完成（长任务，耐心等待）
- 在弹出的浏览器中完成登录并授权
- 按提示编辑并保存 `reimbursement_info.json`，回到终端回车继续
- 程序会在填写到“转卡详情”后暂停，等待人工完成提交并记录报销单号
- 将报销单号输入程序以继续实装处的自动填报
- 最终在查询页面人工检查并提交

<strong style="color:#bf360c">务必人工复核所有自动填充项与附件</strong>，本项目无法对资金安全负责

未识别或无法处理的发票会在分类完成后被移动到子文件夹，便于人工检查与补处理。

## 项目架构（模块说明）

1. **发票分类 — `invoice_formatter/`**
   - 发票文本提取、字段识别与分类。
   - 默认使用 **BGE** 模型（`BAAI/bge-small-zh-v1.5`），模型文件位于 `invoice_formatter/models/`，可替换为兼容模型。

2. **登录 — `login/`**
   - 使用 Playwright 打开并复用登录态，完成系统登录流程。

3. **自动填充 — `finance_fill/`**
   - 基于识别结果自动执行查验与报销单填写、提交等操作。

4. **自动填充 — `equip_fill/`**
   - 基于识别结果自动执行采购审核填写等操作。

入口脚本：`main.py`（执行顺序：发票识别与分类 → 登录 → 自动填报）。

## 待开发任务

使用OCR识别无法读取的发票

提供便于人工分类发票的方式
