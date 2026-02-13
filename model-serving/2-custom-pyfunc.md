# 自訂 PyFunc 模型 (Custom PyFunc Models)

部署具有預處理、後處理或複雜邏輯的自訂 Python 模型。

## 何時使用自訂 PyFunc

- sklearn pipeline 無法捕捉的自訂預處理
- 一個端點中有多個模型
- 自訂輸出格式
- 推論期間的外部 API 呼叫
- 複雜的業務邏輯

## 基本模式

```python
import mlflow
import pandas as pd

class MyCustomModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        """模型載入時載入工件 (artifacts)。"""
        import pickle
        with open(context.artifacts["preprocessor"], "rb") as f:
            self.preprocessor = pickle.load(f)
        with open(context.artifacts["model"], "rb") as f:
            self.model = pickle.load(f)
    
    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        """執行帶有預處理的預測。"""
        # 預處理
        processed = self.preprocessor.transform(model_input)
        # 預測
        predictions = self.model.predict(processed)
        # 以 DataFrame 返回
        return pd.DataFrame({"prediction": predictions})

# 記錄模型
with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=MyCustomModel(),
        artifacts={
            "preprocessor": "artifacts/preprocessor.pkl",
            "model": "artifacts/model.pkl"
        },
        pip_requirements=["scikit-learn==1.3.0", "pandas"],
        registered_model_name="main.models.custom_model"
    )
```

## 帶有模型簽章 (Model Signature)

```python
from mlflow.models import infer_signature, ModelSignature
from mlflow.types.schema import Schema, ColSpec

# 選項 1：從資料推斷
signature = infer_signature(
    model_input=X_sample,
    model_output=predictions_sample
)

# 選項 2：明確定義
input_schema = Schema([
    ColSpec("double", "age"),
    ColSpec("double", "income"),
    ColSpec("string", "category"),
])
output_schema = Schema([
    ColSpec("double", "probability"),
    ColSpec("string", "class"),
])
signature = ModelSignature(inputs=input_schema, outputs=output_schema)

mlflow.pyfunc.log_model(
    artifact_path="model",
    python_model=MyModel(),
    signature=signature,
    input_example={"age": 25, "income": 50000, "category": "A"},
    registered_model_name="main.models.my_model"
)
```

## 基於檔案的記錄 (來自程式碼的模型)

對於複雜模型，從 Python 檔案而不是類別實例記錄：

```python
# my_model.py
import mlflow
from mlflow.pyfunc import PythonModel

class MyModel(PythonModel):
    def predict(self, context, model_input):
        # 您的預測邏輯
        return model_input * 2

# 匯出模型實例
mlflow.models.set_model(MyModel())
```

```python
# log_model.py
import mlflow

mlflow.set_registry_uri("databricks-uc")

with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        name="my-model",
        python_model="my_model.py",  # 檔案路徑，非實例
        pip_requirements=["mlflow>=3.0"],
        registered_model_name="main.models.my_model"
    )
```

## 帶有外部相依性

```python
mlflow.pyfunc.log_model(
    artifact_path="model",
    python_model=MyModel(),
    pip_requirements=[
        "scikit-learn==1.3.0",
        "pandas==2.0.0",
        "numpy==1.24.0",
        "requests>=2.28.0",  # 用於外部 API 呼叫
    ],
    # 或參考 requirements 檔案
    # pip_requirements="requirements.txt",
    registered_model_name="main.models.my_model"
)
```

## 帶有程式碼相依性

```python
mlflow.pyfunc.log_model(
    artifact_path="model",
    python_model=MyModel(),
    code_paths=["src/utils.py", "src/preprocessing.py"],
    pip_requirements=["scikit-learn"],
    registered_model_name="main.models.my_model"
)
```

## 部署前測試

```python
# 在本地載入並測試
loaded_model = mlflow.pyfunc.load_model(model_info.model_uri)

# 測試預測
test_input = pd.DataFrame({"age": [25], "income": [50000]})
result = loaded_model.predict(test_input)
print(result)

# 部署前驗證
mlflow.models.predict(
    model_uri=model_info.model_uri,
    input_data={"age": 25, "income": 50000},
    env_manager="uv",  # 使用 uv 加速環境建立
)
```

## 部署自訂模型

與經典 ML 相同 - 使用 UI、MLflow SDK 或 Databricks SDK：

```python
from mlflow.deployments import get_deploy_client

client = get_deploy_client("databricks")
endpoint = client.create_endpoint(
    name="custom-model-endpoint",
    config={
        "served_entities": [
            {
                "entity_name": "main.models.custom_model",
                "entity_version": "1",
                "workload_size": "Small",
                "scale_to_zero_enabled": True
            }
        ]
    }
)
```

## 查詢自訂模型

```
query_serving_endpoint(
    name="custom-model-endpoint",
    dataframe_records=[
        {"age": 25, "income": 50000, "category": "A"}
    ]
)
```

或使用輸入格式：

```
query_serving_endpoint(
    name="custom-model-endpoint",
    inputs={"age": 25, "income": 50000, "category": "A"}
)
```
