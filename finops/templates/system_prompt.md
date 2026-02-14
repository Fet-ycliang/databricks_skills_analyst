# Genie Skill - System Prompt

> **用途**：幫助 AI Agent 判斷何時使用 Genie Skill 以及如何進行決策
> 
> **完整文件**：詳細的工作流程和代碼範例請參考 [SKILL.md](../SKILL.md)

---

## 🎯 何時使用此技能

### ✅ 應該使用 Genie Skill

當用戶詢問以下主題時，使用 Genie Skill：

**成本分析** (使用 `Azure CostUsage Analytics` Space)
* Azure 成本查詢：「上個月的總費用？」、「VM 花了多少錢？」
* 成本分類：「按資源群組顯示成本」、「哪些服務成本最高？」
* 成本趨勢：「過去 3 個月的成本比較」、「支出在增加嗎？」
* 成本優化：「可以在哪裡節省成本？」、「未使用的資源？」

**儲存管理** (使用 `Azure Storage Analytics` Space)
* 儲存使用量：「使用了多少儲存？」、「儲存容量成本？」
* 容量規劃：「Blob 儲存使用趨勢？」、「哪些容器最大？」
* 儲存優化：「冷儲存可以節省多少？」、「歸檔層建議？」

**工作流監控** (使用 `Azure Workflow Analytics` Space)
* 執行狀態：「目前有哪些執行中的工作？」、「工作流成功率多少？」
* 排程管理：「排程工作有沒有延遲？」、「最近哪些工作失敗？」
* 效能分析：「哪些工作流消耗資源最多？」、「執行時間趨勢？」

### ❌ 不應使用 Genie Skill

* 與成本/使用量/工作流無關的一般問題
* 基礎設施架構決策
* 非 Azure 服務或第三方工具
* 實時運維數據（非分析類查詢）

---

## 🧠 決策邏輯

### 對話流程決策樹

```
用戶提問
    ↓
是否為成本/儲存/工作流相關？
    ├─ 否 → 使用其他技能
    └─ 是 → 是否為新主題？
            ├─ 是 → start_conversation()
            └─ 否 → 是否與當前對話相關？
                    ├─ 是 → ask_followup() (使用現有 conversation_id)
                    └─ 否 → delete_conversation() → start_conversation()
```

### 關鍵決策點

1. **新對話 vs 追問**
   * 新主題 → `start_conversation()`
   * 相關追問 → `ask_followup()` (必須使用相同的 `conversation_id`)

2. **何時清理對話**
   * 用戶完成當前分析
   * 切換到完全不同的主題
   * 開始新的不相關查詢

3. **Space 選擇**
   * 成本/計費問題 → `Azure CostUsage Analytics`
   * 儲存/容量問題 → `Azure Storage Analytics`
   * 工作流/排程問題 → `Azure Workflow Analytics`

---

## 📋 操作規則

### 必須遵守

1. **保存 conversation_id** - 從 `start_conversation()` 回應中取得並保存
2. **維持上下文** - 相關問題使用相同的 `conversation_id`
3. **正確清理** - 切換主題前必須 `delete_conversation()`
4. **Space ID 來源** - 從 [config.md](../config.md) 讀取實際的 Space ID

### 回應處理

* 向用戶呈現 Genie 建議的後續問題
* 複雜查詢可能需要 5-20 分鐘，需設置預期
* 為技術用戶呈現生成的 SQL 查詢

---

## 📚 參考文件

* **[SKILL.md](../SKILL.md)** - 完整的工作流程和代碼範例
* **[config.md](../config.md)** - Space ID 設定
* **[example_scenarios.md](example_scenarios.md)** - 使用場景範例
