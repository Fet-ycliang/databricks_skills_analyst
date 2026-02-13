# 部署 (Deployment)

將模型部署到服務端點。對於代理，使用非同步基於作業的方法（部署需約 15 分鐘）。

> **如果 MCP 工具不可用**，請直接在筆記本中使用 `databricks.agents.deploy()`，或透過 CLI 建立作業：`databricks jobs create --json @job.json`

## 部署選項

| 模型類型 | 方法 | 時間 |
|------------|--------|------|
| **經典 ML** | SDK/UI | 2-5 分鐘 |
| **GenAI 代理** | `databricks.agents.deploy()` | ~15 分鐘 |

## GenAI 代理部署 (基於作業)

由於代理部署需要約 15 分鐘，使用作業以避免 MCP 逾時。

### 步驟 1：建立部署腳本

```python
# deploy_agent.py
import sys
from databricks import agents

# 從作業或命令列獲取參數
model_name = sys.argv[1] if len(sys.argv) > 1 else "main.agents.my_agent"
version = sys.argv[2] if len(sys.argv) > 2 else "1"

print(f"Deploying {model_name} version {version}...")

# 部署 - 這需要約 15 分鐘
deployment = agents.deploy(
    model_name,
    version,
    tags={"source": "mcp", "environment": "dev"}
)

print(f"Deployment complete!")
print(f"Endpoint: {deployment.endpoint_name}")
```

### 步驟 2：建立部署作業 (一次性)

使用 `create_job` MCP 工具：

```
create_job(
    name="deploy-agent-job",
    tasks=[
        {
            "task_key": "deploy",
            "spark_python_task": {
                "python_file": "/Workspace/Users/you@company.com/my_agent/deploy_agent.py",
                "parameters": ["{{job.parameters.model_name}}", "{{job.parameters.version}}"]
            }
        }
    ],
    parameters=[
        {"name": "model_name", "default": "main.agents.my_agent"},
        {"name": "version", "default": "1"}
    ]
)
```

儲存返回的 `job_id`。

### 步驟 3：執行部署 (非同步)

使用 `run_job_now` - 立即返回：

```
run_job_now(
    job_id="<job_id>",
    job_parameters={"model_name": "main.agents.my_agent", "version": "1"}
)
```

儲存返回的 `run_id`。

### 步驟 4：檢查狀態

檢查作業執行狀態：

```
get_run(run_id="<run_id>")
```

或直接檢查端點：

```
get_serving_endpoint_status(name="<endpoint_name>")
```

## 經典 ML 部署

對於傳統 ML 模型，部署較快 - 直接使用 SDK。

### 透過 MLflow Deployments SDK

```python
from mlflow.deployments import get_deploy_client

mlflow.set_registry_uri("databricks-uc")
client = get_deploy_client("databricks")

endpoint = client.create_endpoint(
    name="my-sklearn-model",
    config={
        "served_entities": [
            {
                "entity_name": "main.models.my_model",
                "entity_version": "1",
                "workload_size": "Small",
                "scale_to_zero_enabled": True
            }
        ]
    }
)
```

### 透過 Databricks SDK

```python
from databricks.sdk import WorkspaceClient
from datetime import timedelta

w = WorkspaceClient()

endpoint = w.serving_endpoints.create_and_wait(
    name="my-sklearn-model",
    config={
        "served_entities": [
            {
                "entity_name": "main.models.my_model",
                "entity_version": "1",
                "workload_size": "Small",
                "scale_to_zero_enabled": True
            }
        ]
    },
    timeout=timedelta(minutes=10)
)
```

## 端點命名

對於使用 `databricks.agents.deploy()` 部署的代理：

- 端點名稱源自模型名稱
- `main.agents.my_agent` → `agents_my_agent` 或類似名稱
- 部署後使用 `list_serving_endpoints()` 檢查

## 部署作業模板

用於可重用代理部署的完整作業定義：

```yaml
# resources/deploy_agent_job.yml (for Asset Bundles)
resources:
  jobs:
    deploy_agent:
      name: "[${bundle.target}] Deploy Agent"
      parameters:
        - name: model_name
          default: ""
        - name: version
          default: "1"
      tasks:
        - task_key: deploy
          spark_python_task:
            python_file: ../src/deploy_agent.py
            parameters:
              - "{{job.parameters.model_name}}"
              - "{{job.parameters.version}}"
          new_cluster:
            spark_version: "16.1.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 0
            spark_conf:
              spark.master: "local[*]"
```

## 更新現有端點

使用新模型版本更新端點：

```python
from mlflow.deployments import get_deploy_client

client = get_deploy_client("databricks")

client.update_endpoint(
    endpoint="my-agent-endpoint",
    config={
        "served_entities": [
            {
                "entity_name": "main.agents.my_agent",
                "entity_version": "2",  # 新版本
                "workload_size": "Small",
                "scale_to_zero_enabled": True
            }
        ],
        "traffic_config": {
            "routes": [
                {"served_model_name": "my_agent-2", "traffic_percentage": 100}
            ]
        }
    }
)
```

## 工作流程總結

| 步驟 | MCP 工具 | 等待? |
|------|----------|--------|
| 上傳部署腳本 | `upload_folder` | 是 |
| 建立作業 (一次性) | `create_job` | 是 |
| 執行部署 | `run_job_now` | **否** - 立即返回 |
| 檢查作業狀態 | `get_run` | 是 |
| 檢查端點狀態 | `get_serving_endpoint_status` | 是 |

## 部署後

一旦端點為 READY：

1. **使用 MCP 測試**：`query_serving_endpoint(name="...", messages=[...])`
2. **與團隊分享**：Databricks UI 中的端點 URL
3. **整合到應用程式**：使用 REST API 或 SDK
