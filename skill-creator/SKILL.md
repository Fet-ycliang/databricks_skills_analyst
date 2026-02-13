---
name: skill-creator
description: 用於建立有效技能的指南，適用於使用 Azure SDK 和 Microsoft Foundry 服務的 AI 編碼代理。在建立新技能或更新現有技能時使用。
---

# 技能建立器

建立技能以擴展 AI 代理能力的指南，重點關注 Azure SDK 和 Microsoft Foundry。

## 關於技能

技能是模組化的知識套件，可將通用代理轉變為專業專家：

1. **程序性知識** — 特定領域的多步驟工作流程
2. **SDK 專業知識** — Azure 服務的 API 模式、身份驗證、錯誤處理
3. **領域上下文** — 結構描述、業務邏輯、公司特定模式
4. **捆綁資源** — 用於複雜任務的腳本、參考資料、範本

---

## 核心原則

### 1. 簡潔是關鍵

上下文視窗是共享資源。挑戰每個部分：「這是否值得其 token 成本？」

**預設假設：代理已經有能力。** 只添加他們不知道的內容。

### 2. 優先使用最新文件

**Azure SDK 經常變更。** 技能應指示代理驗證文件：

```markdown
## 實施前

搜尋 `microsoft-docs` MCP 以獲取當前 API 模式：

- 查詢：「[SDK 名稱] [操作] python」
- 驗證：參數與您安裝的 SDK 版本匹配
```

### 3. 自由度

根據任務脆弱性匹配具體程度：

| 自由度 | 使用時機 | 範例 |
| ---------- | -------------------------------- | ---------------- |
| **高** | 多種有效方法 | 文字指南 |
| **中** | 首選模式但有變化 | 偽代碼 |
| **低** | 必須精確 | 特定腳本 |

### 4. 漸進式揭露

技能分三個層級載入：

1. **元資料**（約 100 字）— 始終在上下文中
2. **SKILL.md 主體**（< 5k 字）— 當技能觸發時
3. **參考資料**（無限制）— 根據需要

**保持 SKILL.md 在 500 行以內。** 接近此限制時拆分為參考檔案。

---

## 技能結構

```
skill-name/
├── SKILL.md（必需）
│   ├── YAML frontmatter（name、description）
│   └── Markdown 指令
└── 捆綁資源（可選）
    ├── scripts/      — 可執行代碼
    ├── references/   — 根據需要載入的文件
    └── assets/       — 輸出資源（範本、圖片）
```

### SKILL.md

- **Frontmatter**：`name` 和 `description`。description 是觸發機制。
- **主體**：僅在觸發後載入的指令。

### 捆綁資源

| 類型 | 目的 | 何時包含 |
| ------------- | ------------------------ | ---------------------------------- |
| `scripts/` | 確定性操作 | 重複編寫相同代碼 |
| `references/` | 詳細模式 | API 文件、結構描述、詳細指南 |
| `assets/` | 輸出資源 | 範本、圖片、樣板代碼 |

**不要包含**：README.md、CHANGELOG.md、安裝指南。

---

## 建立 Azure SDK 技能

建立 Azure SDK 技能時，請始終遵循這些模式。

### 技能章節順序

遵循此結構（基於現有 Azure SDK 技能）：

1. **標題** — `# SDK 名稱`
2. **安裝** — `pip install`、`npm install` 等
3. **環境變數** — 必需的配置
4. **身份驗證** — 始終使用 `DefaultAzureCredential`
5. **核心工作流程** — 最小可行範例
6. **功能表格** — 客戶端、方法、工具
7. **最佳實踐** — 編號列表
8. **參考連結** — 連結到 `/references/*.md` 的表格

### 身份驗證模式（所有語言）

始終使用 `DefaultAzureCredential`：

```python
# Python
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
client = ServiceClient(endpoint, credential)
```

```csharp
// C#
var credential = new DefaultAzureCredential();
var client = new ServiceClient(new Uri(endpoint), credential);
```

```java
// Java
TokenCredential credential = new DefaultAzureCredentialBuilder().build();
ServiceClient client = new ServiceClientBuilder()
    .endpoint(endpoint)
    .credential(credential)
    .buildClient();
```

```typescript
// TypeScript
import { DefaultAzureCredential } from "@azure/identity";
const credential = new DefaultAzureCredential();
const client = new ServiceClient(endpoint, credential);
```

**絕不硬編碼憑證。使用環境變數。**

### 標準動詞模式

Azure SDK 在所有語言中使用一致的動詞：

| 動詞 | 行為 |
| -------- | ---------------------------- |
| `create` | 建立新的；如果存在則失敗 |
| `upsert` | 建立或更新 |
| `get` | 檢索；如果缺少則錯誤 |
| `list` | 返回集合 |
| `delete` | 即使缺少也成功 |
| `begin` | 啟動長時間運行的操作 |

### 特定語言模式

詳細模式請參閱 `references/azure-sdk-patterns.md`，包括：

- **Python**：`ItemPaged`、`LROPoller`、上下文管理器、Sphinx 文件字串
- **.NET**：`Response<T>`、`Pageable<T>`、`Operation<T>`、模擬支援
- **Java**：建構器模式、`PagedIterable`/`PagedFlux`、Reactor 類型
- **TypeScript**：`PagedAsyncIterableIterator`、`AbortSignal`、瀏覽器考量

### 範例：Azure SDK 技能結構

```markdown
---
name: skill-creator
description: |
  Python 的 Azure AI 範例 SDK。用於 [特定服務功能]。
  觸發器：「example service」、「create example」、「list examples」。
---

# Azure AI 範例 SDK

## 安裝

\`\`\`bash
pip install azure-ai-example
\`\`\`

## 環境變數

\`\`\`bash
AZURE_EXAMPLE_ENDPOINT=https://<resource>.example.azure.com
\`\`\`

## 身份驗證

\`\`\`python
from azure.identity import DefaultAzureCredential
from azure.ai.example import ExampleClient

credential = DefaultAzureCredential()
client = ExampleClient(
    endpoint=os.environ["AZURE_EXAMPLE_ENDPOINT"],
    credential=credential
)
\`\`\`

## 核心工作流程

\`\`\`python
# 建立
item = client.create_item(name="example", data={...})

# 列出（自動處理分頁）
for item in client.list_items():
    print(item.name)

# 長時間運行的操作
poller = client.begin_process(item_id)
result = poller.result()

# 清理
client.delete_item(item_id)
\`\`\`

## 參考檔案

| 檔案 | 內容 |
| -------------------------------------------------- | ------------------------ |
| [references/tools.md](references/tools.md) | 工具整合 |
| [references/streaming.md](references/streaming.md) | 事件串流模式 |
```

---

## 技能建立流程

1. **理解** — 收集具體使用範例
2. **規劃** — 識別可重用資源
3. **初始化** — 執行 `init_skill.py`
4. **實施** — 建立資源，編寫 SKILL.md
5. **打包** — 執行 `package_skill.py`
6. **迭代** — 根據實際使用進行優化

### 步驟 1：理解技能

收集具體範例：

- 「此技能應涵蓋哪些 SDK 操作？」
- 「哪些觸發器應啟動此技能？」
- 「開發人員常遇到哪些錯誤？」

### 步驟 2：規劃可重用內容

| 範例任務 | 可重用資源 |
| -------------------------- | ------------------------------ |
| 每次相同的身份驗證代碼 | SKILL.md 中的代碼範例 |
| 複雜的串流模式 | `references/streaming.md` |
| 工具配置 | `references/tools.md` |
| 錯誤處理模式 | `references/error-handling.md` |

### 步驟 3：初始化

```bash
scripts/init_skill.py <skill-name> --path <output-directory>
```

### 步驟 4：實施

**對於 Azure SDK 技能：**

1. 搜尋 `microsoft-docs` MCP 以獲取當前 API 模式
2. 對照已安裝的 SDK 版本進行驗證
3. 遵循上述章節順序
4. 在範例中包含清理代碼
5. 添加功能比較表格

**先編寫捆綁資源**，然後再編寫 SKILL.md。

**Frontmatter：**

```yaml
---
name: skill-creator
description: |
  技能的功能以及何時使用。
  包含觸發短語：「在 [場景] 時使用」。
---
```

### 步驟 5：打包

```bash
scripts/package_skill.py <path/to/skill-folder>
```

### 步驟 6：迭代

在實際使用後，識別代理遇到困難的地方並相應更新。

---

## 漸進式揭露模式

### 模式 1：高層指南與參考資料

```markdown
# SDK 名稱

## 快速入門

[最小範例]

## 進階功能

- **串流**：參見 [references/streaming.md](references/streaming.md)
- **工具**：參見 [references/tools.md](references/tools.md)
```

### 模式 2：語言變體

```
azure-service-skill/
├── SKILL.md（概述 + 語言選擇）
└── references/
    ├── python.md
    ├── dotnet.md
    ├── java.md
    └── typescript.md
```

### 模式 3：功能組織

```
azure-ai-agents/
├── SKILL.md（核心工作流程）
└── references/
    ├── tools.md
    ├── streaming.md
    ├── async-patterns.md
    └── error-handling.md
```

---

## 設計模式參考

| 參考資料 | 內容 |
| ---------------------------------- | ------------------------------------ |
| `references/workflows.md` | 順序和條件工作流程 |
| `references/output-patterns.md` | 範本和範例 |
| `references/azure-sdk-patterns.md` | 特定語言的 Azure SDK 模式 |

---

## 反模式

| 不要做 | 原因 |
| --------------------------- | ------------------------------ |
| 將「何時使用」放在主體中 | 主體在觸發後才載入 |
| 硬編碼憑證 | 安全風險 |
| 跳過身份驗證章節 | 代理會即興發揮且效果不佳 |
| 使用過時的 SDK 模式 | API 會變更；先搜尋文件 |
| 包含 README.md | 代理不需要元文件 |
| 深度嵌套參考資料 | 保持一層深度 |

---

## 檢查清單

打包技能前：

- [ ] Description 包含功能和使用時機（觸發短語）
- [ ] SKILL.md 在 500 行以內
- [ ] 身份驗證使用 `DefaultAzureCredential`
- [ ] 範例中包含清理/刪除
- [ ] 參考資料按功能組織
- [ ] 無重複內容
- [ ] 指示搜尋 `microsoft-docs` MCP 以獲取當前 API
- [ ] 所有腳本已測試
