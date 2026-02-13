# Claude Code 的 Databricks 技能

教導 Claude Code 如何有效地使用 Databricks 的技能 - 提供與 Databricks MCP 工具配合使用的模式、最佳實踐和程式碼範例。

## 安裝

在您的專案根目錄中執行：

```bash
# 安裝所有技能（Databricks + MLflow）
curl -sSL https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/install_skills.sh | bash

# 安裝特定技能
curl -sSL https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/install_skills.sh | bash -s -- asset-bundles agent-evaluation

# 將 MLflow 技能固定到特定版本
curl -sSL https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/install_skills.sh | bash -s -- --mlflow-version v1.0.0

# 列出可用的技能
curl -sSL https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/install_skills.sh | bash -s -- --list
```

這會建立 `.claude/skills/` 並下載所有技能。Claude Code 會自動載入它們。
- **Databricks 技能**從此儲存庫下載
- **MLflow 技能**從 [github.com/mlflow/skills](https://github.com/mlflow/skills) 動態獲取

**手動安裝：**
```bash
mkdir -p .claude/skills
cp -r ai-dev-kit/databricks-skills/agent-bricks .claude/skills/
```

## 可用技能

### 🤖 AI 與代理
- **agent-bricks** - 知識助理、Genie Spaces、多代理監督器
- **databricks-genie** - Genie Spaces：透過 Conversation API 建立、精選和查詢
- **model-serving** - 將 MLflow 模型和 AI 代理部署到端點
- **unstructured-pdf-generation** - 為 RAG 生成合成 PDF
- **vector-search** - 用於 RAG 和語義搜尋的向量相似度搜尋

### 📊 MLflow（來自 [mlflow/skills](https://github.com/mlflow/skills)）
- **agent-evaluation** - 端到端代理評估工作流程
- **analyze-mlflow-chat-session** - 除錯多輪對話
- **analyze-mlflow-trace** - 除錯追蹤、跨度和評估
- **instrumenting-with-mlflow-tracing** - 將 MLflow 追蹤新增到 Python/TypeScript
- **mlflow-onboarding** - 新使用者的 MLflow 設定指南
- **querying-mlflow-metrics** - 聚合指標和時間序列分析
- **retrieving-mlflow-traces** - 追蹤搜尋和篩選
- **searching-mlflow-docs** - 搜尋 MLflow 文件

### 📊 分析與儀表板
- **aibi-dashboards** - AI/BI 儀表板（帶有 SQL 驗證工作流程）
- **databricks-unity-catalog** - 用於血緣、稽核、計費的系統資料表

### 🔧 資料工程
- **spark-declarative-pipelines** - SQL/Python 中的 SDP（前身為 DLT）
- **databricks-jobs** - 多任務工作流程、觸發器、排程
- **synthetic-data-generation** - 使用 Faker 生成逼真的測試資料

### 🚀 開發與部署
- **asset-bundles** - 用於多環境部署的 DABs
- **databricks-app-apx** - 全端應用程式（FastAPI + React）
- **databricks-app-python** - Python 網頁應用程式（Dash、Streamlit、Flask）
- **databricks-python-sdk** - Python SDK、Connect、CLI、REST API
- **databricks-config** - 設定檔驗證設定
- **lakebase-provisioned** - 用於 OLTP 工作負載的託管 PostgreSQL

### 📚 參考
- **databricks-docs** - 透過 llms.txt 的文件索引

## 運作方式

```
┌────────────────────────────────────────────────┐
│  .claude/skills/     +    .claude/mcp.json     │
│  (知識)                    (動作)              │
│                                                │
│  技能教導如何做    +    MCP 執行它             │
│  ↓                        ↓                    │
│  Claude Code 學習模式並執行                    │
└────────────────────────────────────────────────┘
```

**範例：**使用者說「建立銷售儀表板」
1. Claude 載入 `aibi-dashboards` 技能 → 學習驗證工作流程
2. 呼叫 `get_table_details()` → 取得結構描述
3. 呼叫 `execute_sql()` → 測試查詢
4. 呼叫 `create_or_update_dashboard()` → 部署
5. 返回可運作的儀表板 URL

## 自訂技能

在 `.claude/skills/my-skill/SKILL.md` 中建立您自己的技能：

```markdown
---
name: my-skill
description: "這教導什麼"
---

# 我的技能

## 何時使用
...

## 模式
...
```

## 疑難排解

**技能未載入？**檢查 `.claude/skills/` 是否存在，且每個技能都有 `SKILL.md`

**安裝失敗？**執行 `bash install_skills.sh` 或檢查寫入權限

## 相關

- [databricks-tools-core](../databricks-tools-core/) - Python 函式庫
- [databricks-mcp-server](../databricks-mcp-server/) - MCP 伺服器
- [Databricks 文件](https://docs.databricks.com/) - 官方文件
- [MLflow 技能](https://github.com/mlflow/skills) - 上游 MLflow 技能儲存庫
