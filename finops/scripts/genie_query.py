"""
Genie API 查詢函式（適配本地 Agent）

用於與 Databricks Genie API 互動的簡單介面
以自然語言查詢資料空間 (Async/Threaded 版本)。
"""

import os
import re
import time
import json
import logging
import asyncio
from datetime import timedelta
from typing import Optional, Dict, Any

# 回退到同步 WorkspaceClient
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import GenieMessage

# 設定詳細日誌（標準模式）
logger = logging.getLogger(__name__)

# 常數（可由環境變數覆寫）
DEFAULT_TIMEOUT_MINUTES = int(os.getenv('GENIE_TIMEOUT_MINUTES', '30'))

def _validate_space_id(space_id: str) -> bool:
    """
    驗證 Genie Space ID 格式。
    
    參數:
        space_id: 要驗證的 Space ID
        
    回傳:
        True 如果格式正確（32 位 hex 字串），否則 False
    """
    if not space_id:
        return False
    # Space ID 格式：32 位 hex 字串（無連字號）
    pattern = r'^[0-9a-f]{32}$'
    return bool(re.match(pattern, space_id.lower()))

def _create_error_response(error_message: str, space_id: str = None, **kwargs) -> str:
    """
    建立統一的錯誤回應 JSON 格式。
    
    參數:
        error_message: 錯誤訊息
        space_id: Space ID（可選）
        **kwargs: 其他要包含的欄位
        
    回傳:
        JSON 格式的錯誤回應字串
    """
    result = {
        "success": False,
        "error": error_message
    }
    if space_id:
        result["space_id"] = space_id
    result.update(kwargs)
    return json.dumps(result, ensure_ascii=False)

def _get_workspace_client() -> WorkspaceClient:
    """
    初始化 WorkspaceClient 並自動認證 (同步)。
    支援 PAT (DATABRICKS_TOKEN) 和 Service Principal (AZURE_CLIENT_ID/SECRET)。
    """
    logger.debug('🔌 初始化 Databricks WorkspaceClient...')
    client = WorkspaceClient()
    logger.debug(f'✅ WorkspaceClient 已初始化，主機: {client.config.host}')
    return client

async def start_conversation(question: str, space_id: str, timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES) -> str:
    """
    啟動與 Databricks Genie 的新對話 (Async/Threaded)。
    
    參數:
        question: 要詢問的自然語言問題
        space_id: Genie Space ID (從 config.md 讀取實際值，格式為 32 位 hex 字串)
        timeout_minutes: 等待回應的最長時間
        
    回傳:
        包含對話結果的 JSON 字串（成功或錯誤）
    """
    # 驗證 space_id
    if not space_id or not _validate_space_id(space_id):
        error_msg = f'無效的 space_id 格式: {space_id}' if space_id else '未提供 space_id 參數'
        logger.error(f'❌ {error_msg}')
        return _create_error_response(error_msg, space_id)
    
    logger.info(f'🎯 啟動 Genie 對話')
    logger.info(f'   Space ID: {space_id[:8]}...{space_id[-4:]}')  # 只顯示部分 ID
    logger.info(f'   問題: {question[:100]}...' if len(question) > 100 else f'   問題: {question}')
    
    # 記錄詳細輸入（debug 級別）
    input_json = {
        "space_id": space_id,
        "question": question,
        "timeout_minutes": timeout_minutes
    }
    logger.debug(f'📥 完整輸入參數：{json.dumps(input_json, ensure_ascii=False, indent=2)}')
    
    start_time = time.time()
    try:
        # 在 thread 中初始化 client，避免 environ I/O 阻塞
        w = await asyncio.to_thread(_get_workspace_client)
        
        logger.info(f'📤 發送請求到 Genie API...')
        
        # 使用 asyncio.to_thread 執行阻塞的 start_conversation_and_wait
        response = await asyncio.to_thread(
            w.genie.start_conversation_and_wait,
            space_id=space_id,
            content=question,
            timeout=timedelta(minutes=timeout_minutes)
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f'✅ Genie 回應完成 (耗時: {elapsed_time:.2f}秒)')
        logger.debug(f'   對話 ID: {response.conversation_id}')
        logger.debug(f'   消息 ID: {response.message_id}')
        logger.debug(f'   消息狀態: {response.status if hasattr(response, "status") else "N/A"}')
        
        return _process_genie_response(response, space_id, question)
        
    except Exception as e:
        logger.error(f'❌ 啟動 Genie 對話失敗: {str(e)}', exc_info=True)
        return _create_error_response(f"啟動 Genie 對話時發生錯誤: {str(e)}", space_id)

async def ask_followup(conversation_id: str, question: str, space_id: str, timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES) -> str:
    """
    在現有的 Genie 對話中提出後續問題 (Async/Threaded)。
    
    參數:
        conversation_id: 現有對話 ID
        question: 後續問題
        space_id: Genie Space ID (從 config.md 讀取實際值，格式為 32 位 hex 字串)
        timeout_minutes: 等待回應的最長時間
        
    回傳:
        包含回應的 JSON 字串（成功或錯誤）
    """
    # 驗證 space_id
    if not space_id or not _validate_space_id(space_id):
        error_msg = f'無效的 space_id 格式: {space_id}' if space_id else '未提供 space_id 參數'
        logger.error(f'❌ {error_msg}')
        return _create_error_response(error_msg, space_id, conversation_id=conversation_id)
    
    logger.info(f'💬 提出後續問題')
    logger.info(f'   對話 ID: {conversation_id}')
    logger.info(f'   問題: {question[:100]}...' if len(question) > 100 else f'   問題: {question}')
    
    # 記錄詳細輸入（debug 級別）
    input_json = {
        "space_id": space_id,
        "conversation_id": conversation_id,
        "question": question,
        "timeout_minutes": timeout_minutes
    }
    logger.debug(f'📥 完整輸入參數：{json.dumps(input_json, ensure_ascii=False, indent=2)}')
    
    start_time = time.time()
    try:
        w = await asyncio.to_thread(_get_workspace_client)
        
        logger.info(f'📝 使用 create_message_and_wait 提出後續問題...')
        
        # 優先使用 SDK 提供的 create_message_and_wait
        try:
            response = await asyncio.to_thread(
                w.genie.create_message_and_wait,
                space_id=space_id,
                conversation_id=conversation_id,
                content=question,
                timeout=timedelta(minutes=timeout_minutes)
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f'✅ Genie 後續回應完成 (耗時: {elapsed_time:.2f}秒)')
            return _process_genie_response(response, space_id, question, conversation_id)
            
        except AttributeError:
            # 備選方案：create_message + 輪詢
            logger.info(f'⚠️ create_message_and_wait 不可用，使用備選方案...')
            
            # 建立消息
            message = await asyncio.to_thread(
                w.genie.create_message,
                space_id=space_id,
                conversation_id=conversation_id,
                content=question
            )
            
            message_id = getattr(message, 'message_id', None) or getattr(message, 'id', None)
            logger.debug(f'✅ 消息已建立，ID: {message_id}')
            
            # 輪詢等待回應
            max_polls = int(timeout_minutes * 20)  # 每 3 秒輪詢一次
            poll_interval = 3.0
            
            for poll_count in range(1, max_polls + 1):
                await asyncio.sleep(poll_interval)
                
                try:
                    conversation = await asyncio.to_thread(
                        w.genie.get_conversation,
                        space_id=space_id,
                        conversation_id=conversation_id
                    )
                    
                    if conversation and conversation.messages:
                        latest = conversation.messages[-1]
                        latest_id = getattr(latest, 'message_id', None) or getattr(latest, 'id', None)
                        
                        # 檢查是否是新的回應
                        if latest_id and latest_id != message_id:
                            status = getattr(latest, 'status', None)
                            if status == 'COMPLETED' or (hasattr(latest, 'content') and latest.content):
                                elapsed_time = time.time() - start_time
                                logger.info(f'✅ 收到回應 (耗時: {elapsed_time:.2f}秒，輪詢: {poll_count}次)')
                                return _process_genie_response(latest, space_id, question, conversation_id)
                        
                        logger.debug(f'輪詢 #{poll_count}: 等待回應...')
                except Exception as e:
                    logger.debug(f'輪詢 #{poll_count} 失敗: {e}')
            
            # 超時
            return _create_error_response(
                f"等待回應超時 ({timeout_minutes} 分鐘)",
                space_id,
                conversation_id=conversation_id
            )
            
    except Exception as e:
        logger.error(f'❌ 提出後續問題失敗: {str(e)}', exc_info=True)
        return _create_error_response(
            f"提出後續問題時發生錯誤: {str(e)}",
            space_id,
            conversation_id=conversation_id
        )

async def delete_conversation(conversation_id: str, space_id: str) -> str:
    """
    刪除 Genie 對話。
    
    參數:
        conversation_id: 要刪除的對話 ID
        space_id: Genie Space ID (從 config.md 讀取實際值)
        
    回傳:
        包含刪除結果的 JSON 字串
    """
    # 驗證 space_id
    if not space_id or not _validate_space_id(space_id):
        error_msg = f'無效的 space_id 格式: {space_id}' if space_id else '未提供 space_id 參數'
        logger.error(f'❌ {error_msg}')
        return _create_error_response(error_msg, space_id, conversation_id=conversation_id)
    
    logger.info(f'🗑️  刪除 Genie 對話')
    logger.info(f'   對話 ID: {conversation_id}')
    
    try:
        w = await asyncio.to_thread(_get_workspace_client)
        
        await asyncio.to_thread(
            w.genie.delete_conversation,
            space_id=space_id,
            conversation_id=conversation_id
        )
        
        logger.info(f'✅ 對話已刪除')
        
        result = {
            "success": True,
            "message": "對話已成功刪除",
            "space_id": space_id,
            "conversation_id": conversation_id
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f'❌ 刪除對話失敗: {str(e)}', exc_info=True)
        return _create_error_response(
            f"刪除對話時發生錯誤: {str(e)}",
            space_id,
            conversation_id=conversation_id
        )

async def send_message_feedback(space_id: str, conversation_id: str, message_id: str, rating: str) -> str:
    """
    發送對 Genie 消息的反饋。
    
    參數:
        space_id: Genie Space ID (從 config.md 讀取實際值)
        conversation_id: 對話 ID
        message_id: 消息 ID
        rating: 評分 ('positive' 或 'negative')
        
    回傳:
        包含反饋結果的 JSON 字串
    """
    # 驗證 space_id
    if not space_id or not _validate_space_id(space_id):
        error_msg = f'無效的 space_id 格式: {space_id}' if space_id else '未提供 space_id 參數'
        logger.error(f'❌ {error_msg}')
        return _create_error_response(error_msg, space_id)
    
    logger.info(f'👍 發送消息反饋')
    logger.info(f'   對話 ID: {conversation_id}')
    logger.info(f'   消息 ID: {message_id}')
    logger.info(f'   評分: {rating}')
    
    try:
        w = await asyncio.to_thread(_get_workspace_client)
        
        await asyncio.to_thread(
            w.genie.execute_message_query,
            space_id=space_id,
            conversation_id=conversation_id,
            message_id=message_id
        )
        
        logger.info(f'✅ 反饋已發送')
        
        result = {
            "success": True,
            "message": "反饋已成功發送",
            "space_id": space_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "rating": rating
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f'❌ 發送反饋失敗: {str(e)}', exc_info=True)
        return _create_error_response(
            f"發送反饋時發生錯誤: {str(e)}",
            space_id,
            conversation_id=conversation_id,
            message_id=message_id
        )

def _process_genie_response(response, space_id: str, question: str, conversation_id: str = None) -> str:
    """
    統一處理 Genie 回應，提取關鍵資訊並格式化為 JSON。
    
    參數:
        response: Genie API 回應對象
        space_id: Space ID
        question: 原始問題
        conversation_id: 對話 ID（可選）
        
    回傳:
        格式化的 JSON 字串
    """
    logger.debug('📋 處理 Genie 回應...')
    
    # 提取基本資訊
    conv_id = conversation_id or (response.conversation_id if hasattr(response, 'conversation_id') else None)
    msg_id = response.message_id if hasattr(response, 'message_id') else (response.id if hasattr(response, 'id') else None)
    
    result = {
        "success": True,
        "space_id": space_id,
        "conversation_id": conv_id,
        "message_id": msg_id,
        "question": question
    }
    
    # 提取 attachments 內容
    if hasattr(response, 'attachments') and response.attachments:
        logger.debug(f'找到 {len(response.attachments)} 個附件')
        
        for idx, attachment in enumerate(response.attachments):
            # 提取查詢答案
            if hasattr(attachment, 'text') and attachment.text:
                if hasattr(attachment.text, 'content') and attachment.text.content:
                    result["answer"] = attachment.text.content
                    logger.info(f'✅ 找到查詢答案 ({len(attachment.text.content)} 字元)')
            
            # 提取 SQL 查詢
            if hasattr(attachment, 'query') and attachment.query:
                query_info = {}
                
                if hasattr(attachment.query, 'description'):
                    query_info["description"] = attachment.query.description
                    logger.debug(f'查詢描述: {attachment.query.description}')
                
                if hasattr(attachment.query, 'query'):
                    query_info["sql"] = attachment.query.query
                    logger.info(f'✅ 找到 SQL 查詢 ({len(attachment.query.query)} 字元)')
                
                if query_info:
                    result["query"] = query_info
            
            # 提取建議的後續問題
            if hasattr(attachment, 'suggested_questions') and attachment.suggested_questions:
                if hasattr(attachment.suggested_questions, 'questions'):
                    result["suggested_questions"] = attachment.suggested_questions.questions
                    logger.info(f'✅ 找到 {len(attachment.suggested_questions.questions)} 個建議問題')
    
    # 如果沒有找到答案，記錄警告
    if "answer" not in result:
        logger.warning(f'⚠️  未找到明確的回答內容')
        result["answer"] = f"對話已啟動，但未獲得明確回答。對話 ID: {conv_id}"
    
    # 記錄完整回應（debug 級別）
    logger.debug(f'📤 完整回應 JSON：{json.dumps(result, ensure_ascii=False, indent=2)}')
    
    return json.dumps(result, ensure_ascii=False)

# 匯出工具供 FastMCP 使用
exported_tools = [start_conversation, ask_followup, delete_conversation, send_message_feedback]
