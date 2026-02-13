# Databricks Asset Bundles 的 SQL 警報資源

## 重要：先進行結構描述驗證

**務必從檢查結構描述開始：**
```bash
databricks bundle schema | grep -A 100 'sql.AlertV2'
```

Alert v2 API 結構描述與其他資源有顯著差異。不要假設欄位名稱。

## 要避免的常見結構描述錯誤

### ❌ 錯誤 - 這些欄位不存在：
```yaml
condition:                    # 應該是 "evaluation"
  op: LESS_THAN
  operand:
    column:                   # 錯誤的巢狀結構
      name: "r"

schedule:
  cron_schedule:              # 應該是 schedule 下的直接欄位
    quartz_cron_expression: "..."

subscriptions:                # 應該在 evaluation.notification 下
  - destination_type: "EMAIL"
```

### ✅ 正確 - Alerts v2 API 結構：
```yaml
evaluation:                   # 不是 "condition"
  comparison_operator: 'LESS_THAN_OR_EQUAL'
  source:                     # 不是巢狀在 "operand.column" 下
    name: 'column_name'
    display: 'column_name'
  threshold:
    value:
      double_value: 100
  notification:               # 訂閱巢狀在這裡
    notify_on_ok: false
    subscriptions:
      - user_email: "${workspace.current_user.userName}"

schedule:                     # 欄位直接在 schedule 下
  pause_status: 'UNPAUSED'    # 必要
  quartz_cron_schedule: '0 38 16 * * ?'  # 必要
  timezone_id: 'America/Los_Angeles'     # 必要
```

## 警報觸發邏輯

**重要：**警報在條件評估為 **TRUE** 時觸發，而非 FALSE。

**錯誤方法：**使用 `GREATER_THAN` 並期望在條件為 false 時觸發警報
**正確方法：**使用直接符合您意圖的運算子

### 範例：當計數不大於 100 時（即 ≤ 100）觸發警報
```yaml
# ❌ 錯誤 - 這會在計數大於 100 時觸發
comparison_operator: 'GREATER_THAN'

# ✅ 正確 - 這會在計數小於或等於 100 時觸發
comparison_operator: 'LESS_THAN_OR_EQUAL'
```

## 電子郵件通知

```yaml
evaluation:
  notification:
    subscriptions:
      - user_email: "${workspace.current_user.userName}"
```

## Quartz Cron

格式：`秒 分 時 日 月 星期` (當日使用 `*` 時，星期使用 `?`)

範例：`'0 0 9 * * ?'` (每日上午 9 點)、`'0 */30 * * * ?'` (每 30 分鐘)

## 必要欄位

```yaml
resources:
  alerts:
    alert_name:
      display_name: "[${bundle.target}] 警報名稱"        # 必要
      query_text: "SELECT count(*) c FROM table"        # 必要
      warehouse_id: ${var.warehouse_id}                 # 必要

      evaluation:                                        # 必要
        comparison_operator: 'LESS_THAN'                # 必要
        source:                                          # 必要
          name: 'c'
          display: 'c'
        threshold:
          value:
            double_value: 100
        notification:
          notify_on_ok: false
          subscriptions:
            - user_email: "${workspace.current_user.userName}"

      schedule:                                          # 必要
        pause_status: 'UNPAUSED'                        # 必要
        quartz_cron_schedule: '0 0 9 * * ?'            # 必要
        timezone_id: 'America/Los_Angeles'             # 必要

      permissions:
        - level: CAN_RUN
          group_name: "users"
```

## 比較運算子

`EQUAL`、`NOT_EQUAL`、`GREATER_THAN`、`GREATER_THAN_OR_EQUAL`、`LESS_THAN`、`LESS_THAN_OR_EQUAL`

## 權限層級

`CAN_READ`、`CAN_RUN`（建議）、`CAN_EDIT`、`CAN_MANAGE`
