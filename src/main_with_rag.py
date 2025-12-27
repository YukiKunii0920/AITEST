"""
RAG対応メインアプリケーション

過去の会議履歴を参照した高度な会議分析を実行します。
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from workflow.meeting_analyzer_v3 import MeetingAnalyzerV3
from database.mysql_client import MySQLClient
from utils.config import settings
from utils.logger import setup_logging

# ロギング設定
setup_logging()
logger = logging.getLogger(__name__)

# FastAPIアプリ
app = FastAPI(
    title="AI Meeting Agent System with RAG",
    description="会議に参加して各専門家の視点で発言するAIエージェントシステム（RAG対応）",
    version="3.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル変数
meeting_analyzers: Dict[str, MeetingAnalyzerV3] = {}
mysql_client = MySQLClient()


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "AI Meeting Agent System with RAG",
        "version": "3.0.0",
        "features": [
            "Recall.ai Bot Integration",
            "Multi-Agent Analysis",
            "LangGraph Workflow",
            "Meeting Summary Generation",
            "Database Integration",
            "RAG (Retrieval-Augmented Generation)"
        ]
    }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "healthy"}


@app.post("/webhook/bot.{event_type}")
async def webhook_handler(event_type: str, payload: dict):
    """
    Recall.ai Webhookハンドラー
    
    イベントタイプ:
    - transcript: リアルタイム文字起こし
    - status_change: ボット状態変更
    - participant_joined: 参加者参加
    - participant_left: 参加者退出
    - chat_message: チャットメッセージ
    """
    logger.info(f"Received webhook: bot.{event_type}")
    logger.debug(f"Payload: {payload}")
    
    try:
        # ボットIDを取得
        bot_id = payload.get("data", {}).get("bot_id")
        if not bot_id:
            logger.warning("No bot_id in payload")
            return {"status": "error", "message": "No bot_id"}
        
        # MeetingAnalyzerを取得または作成
        if bot_id not in meeting_analyzers:
            meeting_url = payload.get("data", {}).get("meeting_url", "")
            meeting_analyzers[bot_id] = MeetingAnalyzerV3(
                bot_id=bot_id,
                meeting_url=meeting_url,
                meeting_title=f"Meeting {bot_id[:8]}",
                enable_rag=True  # RAGを有効化
            )
            logger.info(f"Created new MeetingAnalyzerV3 for bot {bot_id}")
        
        analyzer = meeting_analyzers[bot_id]
        
        # イベントタイプに応じて処理
        if event_type == "transcript":
            # リアルタイム文字起こし
            transcript_data = payload.get("data", {}).get("transcript", {})
            text = transcript_data.get("text", "")
            participant = transcript_data.get("participant", {})
            is_partial = transcript_data.get("is_partial", False)
            
            if text:
                await analyzer.process_transcript(
                    text=text,
                    participant=participant,
                    is_partial=is_partial
                )
        
        elif event_type == "status_change":
            # ボット状態変更
            status = payload.get("data", {}).get("status", {})
            code = status.get("code")
            logger.info(f"Bot {bot_id} status changed: {code}")
            
            # 会議終了時に議事録を生成
            if code in ["done", "fatal"]:
                logger.info(f"Meeting ended for bot {bot_id}, generating summary...")
                summary = await analyzer.generate_final_summary()
                logger.info(f"Summary generated: {summary}")
        
        elif event_type == "participant_joined":
            # 参加者参加
            participant = payload.get("data", {}).get("participant", {})
            logger.info(f"Participant joined: {participant.get('name', 'Unknown')}")
        
        elif event_type == "participant_left":
            # 参加者退出
            participant = payload.get("data", {}).get("participant", {})
            logger.info(f"Participant left: {participant.get('name', 'Unknown')}")
        
        elif event_type == "chat_message":
            # チャットメッセージ
            message = payload.get("data", {}).get("message", {})
            logger.info(f"Chat message: {message.get('text', '')}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/bot/register")
async def register_bot(bot_id: str, meeting_url: str, meeting_title: str = None):
    """
    ボットを登録
    
    Args:
        bot_id: ボットID
        meeting_url: 会議URL
        meeting_title: 会議タイトル
    """
    try:
        if bot_id in meeting_analyzers:
            return {"status": "error", "message": "Bot already registered"}
        
        analyzer = MeetingAnalyzerV3(
            bot_id=bot_id,
            meeting_url=meeting_url,
            meeting_title=meeting_title,
            enable_rag=True
        )
        meeting_analyzers[bot_id] = analyzer
        
        # current_bot_id.txtに保存
        bot_id_file = Path("config/current_bot_id.txt")
        bot_id_file.write_text(bot_id)
        
        logger.info(f"Bot registered: {bot_id}")
        return {"status": "success", "bot_id": bot_id}
        
    except Exception as e:
        logger.error(f"Error registering bot: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/statistics")
async def get_statistics():
    """統計情報を取得"""
    try:
        stats = {
            "total_bots": len(meeting_analyzers),
            "bots": {}
        }
        
        for bot_id, analyzer in meeting_analyzers.items():
            stats["bots"][bot_id] = analyzer.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/generate_summary/{bot_id}")
async def generate_summary(bot_id: str):
    """
    議事録を生成
    
    Args:
        bot_id: ボットID
    """
    try:
        if bot_id not in meeting_analyzers:
            return {"status": "error", "message": "Bot not found"}
        
        analyzer = meeting_analyzers[bot_id]
        summary = await analyzer.generate_final_summary()
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/rag/search")
async def search_similar_meetings(query: str, n_results: int = 5):
    """
    類似会議を検索
    
    Args:
        query: 検索クエリ
        n_results: 取得件数
    """
    try:
        from rag import MeetingVectorStore
        
        vector_store = MeetingVectorStore()
        results = vector_store.search_similar_meetings(
            query=query,
            n_results=n_results
        )
        
        return {
            "query": query,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching similar meetings: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    # ポート番号
    port = settings.webhook_port
    
    logger.info(f"Starting AI Meeting Agent System with RAG on port {port}...")
    logger.info(f"Webhook URL: {settings.webhook_public_url}")
    
    # サーバーを起動
    uvicorn.run(
        "main_with_rag:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
