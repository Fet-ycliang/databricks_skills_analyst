# 範例模式 2

## 何時使用

當您需要完成 Y 時使用此模式。

## 程式碼範例

```python
def another_example():
    """
    展示不同模式的另一個範例。
    """
    # 配置設定
    config = {
        "option1": "value1",
        "option2": "value2"
    }

    # 執行
    result = execute_task(config)

    # 處理結果
    if result.success:
        print("成功！")
    else:
        print(f"錯誤：{result.error}")
```

## 最佳實踐

- 保持簡單
- 使用清晰的變數名稱
- 適當地處理錯誤

## 提示

- 提示 1：一個有用的提示
- 提示 2：另一個有用的建議
- 提示 3：還有一件要記住的事
