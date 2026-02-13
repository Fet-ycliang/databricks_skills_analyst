# 完整範例

## 目錄
- [帶有多個任務的 ETL 管線](#帶有多個任務的-etl-管線)
- [排程的資料倉儲重新整理](#排程的資料倉儲重新整理)
- [事件驅動管線](#事件驅動管線)
- [ML 訓練管線](#ml-訓練管線)
- [多環境部署](#多環境部署)
- [串流作業](#串流作業)
- [跨作業編排](#跨作業編排)

---

## 帶有多個任務的 ETL 管線

具有任務相依性的經典提取-轉換-載入管線。

### DABs YAML

```yaml
# resources/etl_job.yml
resources:
  jobs:
    daily_etl:
      name: "[${bundle.target}] 每日 ETL 管線"

      # 排程：每日 UTC 上午 6 點
      schedule:
        quartz_cron_expression: "0 0 6 * * ?"
        timezone_id: "UTC"
        pause_status: UNPAUSED

      # 作業參數
      parameters:
        - name: load_date
          default: "{{start_date}}"
        - name: env
          default: "${bundle.target}"

      # 所有任務的共用叢集
      job_clusters:
        - job_cluster_key: etl_cluster
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 4
            spark_conf:
              spark.sql.shuffle.partitions: "200"

      # 電子郵件通知
      email_notifications:
        on_failure:
          - "data-team@example.com"
        on_success:
          - "data-team@example.com"

      tasks:
        # 從來源系統提取
        - task_key: extract_orders
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ../src/notebooks/extract_orders.py
            base_parameters:
              load_date: "{{job.parameters.load_date}}"

        - task_key: extract_customers
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ../src/notebooks/extract_customers.py
            base_parameters:
              load_date: "{{job.parameters.load_date}}"

        - task_key: extract_products
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ../src/notebooks/extract_products.py

        # 轉換：等待所有提取完成
        - task_key: transform_facts
          depends_on:
            - task_key: extract_orders
            - task_key: extract_customers
            - task_key: extract_products
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ../src/notebooks/transform_facts.py
            base_parameters:
              load_date: "{{job.parameters.load_date}}"

        # 載入：在轉換後執行
        - task_key: load_warehouse
          depends_on:
            - task_key: transform_facts
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ../src/notebooks/load_warehouse.py

        # 資料品質檢查
        - task_key: validate_data
          depends_on:
            - task_key: load_warehouse
          run_if: ALL_SUCCESS
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ../src/notebooks/validate_data.py

      permissions:
        - level: CAN_VIEW
          group_name: "data-analysts"
        - level: CAN_MANAGE_RUN
          group_name: "data-engineers"
```

### Python SDK 等效程式碼

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import (
    Task, NotebookTask, Source,
    JobCluster, ClusterSpec,
    CronSchedule, PauseStatus,
    JobEmailNotifications,
    JobParameterDefinition
)

w = WorkspaceClient()

job = w.jobs.create(
    name="每日 ETL 管線",
    schedule=CronSchedule(
        quartz_cron_expression="0 0 6 * * ?",
        timezone_id="UTC",
        pause_status=PauseStatus.UNPAUSED
    ),
    parameters=[
        JobParameterDefinition(name="load_date", default="{{start_date}}"),
        JobParameterDefinition(name="env", default="prod")
    ],
    job_clusters=[
        JobCluster(
            job_cluster_key="etl_cluster",
            new_cluster=ClusterSpec(
                spark_version="15.4.x-scala2.12",
                node_type_id="i3.xlarge",
                num_workers=4
            )
        )
    ],
    email_notifications=JobEmailNotifications(
        on_failure=["data-team@example.com"],
        on_success=["data-team@example.com"]
    ),
    tasks=[
        Task(
            task_key="extract_orders",
            job_cluster_key="etl_cluster",
            notebook_task=NotebookTask(
                notebook_path="/Workspace/etl/extract_orders",
                source=Source.WORKSPACE,
                base_parameters={"load_date": "{{job.parameters.load_date}}"}
            )
        ),
        Task(
            task_key="extract_customers",
            job_cluster_key="etl_cluster",
            notebook_task=NotebookTask(
                notebook_path="/Workspace/etl/extract_customers",
                source=Source.WORKSPACE
            )
        ),
        Task(
            task_key="transform_facts",
            depends_on=[
                {"task_key": "extract_orders"},
                {"task_key": "extract_customers"}
            ],
            job_cluster_key="etl_cluster",
            notebook_task=NotebookTask(
                notebook_path="/Workspace/etl/transform_facts",
                source=Source.WORKSPACE
            )
        ),
        Task(
            task_key="load_warehouse",
            depends_on=[{"task_key": "transform_facts"}],
            job_cluster_key="etl_cluster",
            notebook_task=NotebookTask(
                notebook_path="/Workspace/etl/load_warehouse",
                source=Source.WORKSPACE
            )
        )
    ]
)

print(f"已建立作業：{job.job_id}")
```

---

## 排程的資料倉儲重新整理

基於 SQL 的倉儲重新整理，包含多個查詢。

### DABs YAML

```yaml
resources:
  jobs:
    warehouse_refresh:
      name: "[${bundle.target}] 倉儲重新整理"

      schedule:
        quartz_cron_expression: "0 0 4 * * ?"  # 每日上午 4 點
        timezone_id: "America/New_York"
        pause_status: UNPAUSED

      tasks:
        # 重新整理維度資料表
        - task_key: refresh_dim_customers
          sql_task:
            file:
              path: ../src/sql/refresh_dim_customers.sql
              source: WORKSPACE
            warehouse_id: ${var.warehouse_id}

        - task_key: refresh_dim_products
          sql_task:
            file:
              path: ../src/sql/refresh_dim_products.sql
              source: WORKSPACE
            warehouse_id: ${var.warehouse_id}

        # 重新整理事實資料表（相依於維度）
        - task_key: refresh_fact_sales
          depends_on:
            - task_key: refresh_dim_customers
            - task_key: refresh_dim_products
          sql_task:
            file:
              path: ../src/sql/refresh_fact_sales.sql
              source: WORKSPACE
            warehouse_id: ${var.warehouse_id}

        # 更新聚合
        - task_key: update_aggregations
          depends_on:
            - task_key: refresh_fact_sales
          sql_task:
            file:
              path: ../src/sql/update_aggregations.sql
              source: WORKSPACE
            warehouse_id: ${var.warehouse_id}

        # 重新整理儀表板
        - task_key: refresh_dashboard
          depends_on:
            - task_key: update_aggregations
          sql_task:
            dashboard:
              dashboard_id: "dashboard-uuid-here"
            warehouse_id: ${var.warehouse_id}
```

---

## 事件驅動管線

由檔案到達和資料表更新觸發的管線。

### DABs YAML

```yaml
resources:
  jobs:
    event_driven_pipeline:
      name: "[${bundle.target}] 事件驅動管線"

      # 檔案到達時觸發
      trigger:
        pause_status: UNPAUSED
        file_arrival:
          url: "s3://data-lake/incoming/orders/"
          min_time_between_triggers_seconds: 300  # 5 分鐘冷卻時間
          wait_after_last_change_seconds: 60  # 等待批次完成

      # 健康監控
      health:
        rules:
          - metric: RUN_DURATION_SECONDS
            op: GREATER_THAN
            value: 1800  # 如果 > 30 分鐘則警報

      email_notifications:
        on_failure:
          - "data-alerts@example.com"
        on_duration_warning_threshold_exceeded:
          - "data-alerts@example.com"

      tasks:
        - task_key: process_incoming
          notebook_task:
            notebook_path: ../src/notebooks/process_incoming_files.py
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            autoscale:
              min_workers: 2
              max_workers: 10
```

### 資料表更新觸發器範例

```yaml
resources:
  jobs:
    table_triggered_job:
      name: "[${bundle.target}] 資料表更新處理器"

      trigger:
        pause_status: UNPAUSED
        table_update:
          table_names:
            - "main.bronze.raw_orders"
            - "main.bronze.raw_inventory"
          condition: ANY_UPDATED
          min_time_between_triggers_seconds: 600
          wait_after_last_change_seconds: 120

      tasks:
        - task_key: process_updates
          notebook_task:
            notebook_path: ../src/notebooks/process_table_updates.py
```

---

## ML 訓練管線

包含訓練、評估和部署的機器學習工作流程。

### DABs YAML

```yaml
resources:
  jobs:
    ml_training:
      name: "[${bundle.target}] ML 訓練管線"

      # 每週重新訓練
      schedule:
        quartz_cron_expression: "0 0 2 ? * SUN"  # 星期日上午 2 點
        timezone_id: "UTC"
        pause_status: UNPAUSED

      parameters:
        - name: model_name
          default: "sales_forecaster"
        - name: experiment_name
          default: "/Shared/experiments/sales_forecast"

      # 用於訓練的 GPU 叢集
      job_clusters:
        - job_cluster_key: gpu_cluster
          new_cluster:
            spark_version: "15.4.x-gpu-ml-scala2.12"
            node_type_id: "g5.xlarge"
            num_workers: 2
            aws_attributes:
              first_on_demand: 1

        - job_cluster_key: cpu_cluster
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 4

      # ML 環境
      environments:
        - environment_key: ml_env
          spec:
            dependencies:
              - mlflow>=2.10.0
              - scikit-learn>=1.4.0
              - pandas>=2.0.0
              - xgboost>=2.0.0

      tasks:
        # 資料準備
        - task_key: prepare_training_data
          job_cluster_key: cpu_cluster
          environment_key: ml_env
          notebook_task:
            notebook_path: ../src/ml/prepare_training_data.py
            base_parameters:
              output_table: "main.ml.training_data"

        # 特徵工程
        - task_key: engineer_features
          depends_on:
            - task_key: prepare_training_data
          job_cluster_key: cpu_cluster
          environment_key: ml_env
          notebook_task:
            notebook_path: ../src/ml/engineer_features.py

        # 模型訓練
        - task_key: train_model
          depends_on:
            - task_key: engineer_features
          job_cluster_key: gpu_cluster
          environment_key: ml_env
          notebook_task:
            notebook_path: ../src/ml/train_model.py
            base_parameters:
              model_name: "{{job.parameters.model_name}}"
              experiment_name: "{{job.parameters.experiment_name}}"

        # 模型評估
        - task_key: evaluate_model
          depends_on:
            - task_key: train_model
          job_cluster_key: cpu_cluster
          environment_key: ml_env
          notebook_task:
            notebook_path: ../src/ml/evaluate_model.py

        # 條件式部署（僅在成功時）
        - task_key: deploy_model
          depends_on:
            - task_key: evaluate_model
          run_if: ALL_SUCCESS
          job_cluster_key: cpu_cluster
          environment_key: ml_env
          notebook_task:
            notebook_path: ../src/ml/deploy_model.py
            base_parameters:
              model_name: "{{job.parameters.model_name}}"
```

---

## 多環境部署

具有環境特定設定的作業配置。

### databricks.yml

```yaml
bundle:
  name: data-pipeline

include:
  - resources/*.yml

variables:
  warehouse_id:
    lookup:
      warehouse: "Shared SQL Warehouse"
  notification_email:
    default: "data-team@example.com"

targets:
  dev:
    default: true
    mode: development
    workspace:
      profile: dev-profile
    variables:
      notification_email: "dev-team@example.com"

  staging:
    mode: development
    workspace:
      profile: staging-profile

  prod:
    mode: production
    workspace:
      profile: prod-profile
    run_as:
      service_principal_name: "production-sp"
```

### resources/jobs.yml

```yaml
resources:
  jobs:
    data_pipeline:
      name: "[${bundle.target}] 資料管線"

      # 僅在 prod 中排程
      schedule:
        quartz_cron_expression: "0 0 6 * * ?"
        timezone_id: "UTC"
        pause_status: ${if(bundle.target == "prod", "UNPAUSED", "PAUSED")}

      # 環境特定的叢集大小
      job_clusters:
        - job_cluster_key: main_cluster
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: ${if(bundle.target == "prod", "i3.2xlarge", "i3.xlarge")}
            num_workers: ${if(bundle.target == "prod", 8, 2)}

      email_notifications:
        on_failure:
          - ${var.notification_email}

      tasks:
        - task_key: process_data
          job_cluster_key: main_cluster
          notebook_task:
            notebook_path: ../src/notebooks/process_data.py
            base_parameters:
              env: "${bundle.target}"
              catalog: "${bundle.target}_catalog"

      permissions:
        - level: CAN_VIEW
          group_name: "data-analysts"
        - level: CAN_MANAGE_RUN
          group_name: "data-engineers"
        - level: CAN_MANAGE
          service_principal_name: "deployment-sp"
```

---

## 串流作業

具有監控的持續串流作業。

### DABs YAML

```yaml
resources:
  jobs:
    streaming_processor:
      name: "[${bundle.target}] 串流處理器"

      # 持續執行
      continuous:
        pause_status: UNPAUSED

      # 串流的健康監控
      health:
        rules:
          - metric: STREAMING_BACKLOG_SECONDS
            op: GREATER_THAN
            value: 300  # 如果落後 > 5 分鐘則警報
          - metric: STREAMING_BACKLOG_RECORDS
            op: GREATER_THAN
            value: 1000000  # 如果落後 > 100 萬筆記錄則警報

      email_notifications:
        on_failure:
          - "streaming-alerts@example.com"
        on_streaming_backlog_exceeded:
          - "streaming-alerts@example.com"

      webhook_notifications:
        on_failure:
          - id: "pagerduty-streaming-alerts"
        on_streaming_backlog_exceeded:
          - id: "slack-streaming-channel"

      tasks:
        - task_key: stream_processor
          notebook_task:
            notebook_path: ../src/notebooks/stream_processor.py
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            autoscale:
              min_workers: 2
              max_workers: 16
            spark_conf:
              spark.databricks.streaming.statefulOperator.asyncCheckpoint.enabled: "true"
              spark.sql.streaming.stateStore.providerClass: "com.databricks.sql.streaming.state.RocksDBStateStoreProvider"
```

---

## 跨作業編排

使用 run_job_task 的多個作業相依性。

### DABs YAML

```yaml
resources:
  jobs:
    # 資料擷取作業
    ingestion_job:
      name: "[${bundle.target}] 資料擷取"
      tasks:
        - task_key: ingest
          notebook_task:
            notebook_path: ../src/notebooks/ingest.py

    # 資料轉換作業
    transformation_job:
      name: "[${bundle.target}] 資料轉換"
      tasks:
        - task_key: transform
          notebook_task:
            notebook_path: ../src/notebooks/transform.py

    # 主編排作業
    orchestrator:
      name: "[${bundle.target}] 主編排器"

      schedule:
        quartz_cron_expression: "0 0 1 * * ?"
        timezone_id: "UTC"
        pause_status: UNPAUSED

      tasks:
        # 先執行擷取
        - task_key: run_ingestion
          run_job_task:
            job_id: ${resources.jobs.ingestion_job.id}

        # 在擷取後執行轉換
        - task_key: run_transformation
          depends_on:
            - task_key: run_ingestion
          run_job_task:
            job_id: ${resources.jobs.transformation_job.id}

        # 最終驗證
        - task_key: validate_all
          depends_on:
            - task_key: run_transformation
          notebook_task:
            notebook_path: ../src/notebooks/validate_all.py
```

---

## For Each 任務 - 平行處理

使用 for_each_task 平行處理多個項目。

### DABs YAML

```yaml
resources:
  jobs:
    parallel_processor:
      name: "[${bundle.target}] 平行地區處理器"

      schedule:
        quartz_cron_expression: "0 0 8 * * ?"
        timezone_id: "UTC"
        pause_status: UNPAUSED

      tasks:
        # 生成要處理的項目列表
        - task_key: get_regions
          notebook_task:
            notebook_path: ../src/notebooks/get_active_regions.py

        # 平行處理每個地區
        - task_key: process_regions
          depends_on:
            - task_key: get_regions
          for_each_task:
            inputs: "{{tasks.get_regions.values.regions}}"
            concurrency: 10  # 最多 10 個平行
            task:
              task_key: process_region
              notebook_task:
                notebook_path: ../src/notebooks/process_region.py
                base_parameters:
                  region: "{{input}}"

        # 在所有地區處理後聚合結果
        - task_key: aggregate_results
          depends_on:
            - task_key: process_regions
          run_if: ALL_DONE  # 即使某些地區失敗也執行
          notebook_task:
            notebook_path: ../src/notebooks/aggregate_results.py
```

### Notebook: get_active_regions.py

```python
# 取得要處理的活躍地區列表
regions = spark.sql("""
    SELECT DISTINCT region_code
    FROM main.config.active_regions
    WHERE is_active = true
""").collect()

region_list = [row.region_code for row in regions]

# 傳遞給下游的 for_each_task
dbutils.jobs.taskValues.set(key="regions", value=region_list)
```

### Notebook: process_region.py

```python
# 從參數取得地區
region = dbutils.widgets.get("region")

# 處理此地區的資料
df = spark.sql(f"""
    SELECT * FROM main.bronze.orders
    WHERE region = '{region}'
""")

# 轉換並寫入
df_transformed = transform_orders(df)
df_transformed.write.mode("append").saveAsTable(f"main.silver.orders_{region}")

print(f"已處理地區：{region}")
```
