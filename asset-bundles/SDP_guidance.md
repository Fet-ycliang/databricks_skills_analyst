# DABs 的 SDP 管線配置

## 關鍵決策（如果不清楚請詢問）
1. 串流還是批次導向？
2. 持續還是觸發式執行？
3. 無伺服器（預設）還是傳統運算？

## 管線資源模式

```yaml
resources:
  pipelines:
    pipeline_name:
      name: "[${bundle.target}] 管線名稱"

      # 目標目錄和結構描述
      catalog: ${var.catalog}
      target: ${var.schema}

      # 管線程式庫
      libraries:
        - glob:
            include: ../src/pipelines/<pipeline_folder>/transformations/**
      
      root_path: ../src/pipelines/<pipeline_folder>

      serverless: true

      # 管線配置
      configuration:
        source_catalog: ${var.source_catalog}
        source_schema: ${var.source_schema}

      continuous: false
      development: true
      photon: true

      channel: current

      permissions:
        - level: CAN_VIEW
          group_name: "users"
```

**權限層級**：`CAN_VIEW`、`CAN_RUN`、`CAN_MANAGE`

## 最佳實踐

1. **使用 `root_path` 和 `libraries.glob`** 以獲得更新的組織結構
2. **預設使用無伺服器**，除非使用者另有指定
3. **使用變數**進行目錄/結構描述參數化
4. **為 dev/staging 目標設定 `development: true`**
