"""
RAG対応メインアプリケーション（MySQL統合版）

過去の会議履歴を参照した高度な会議分析を実行し、
データをMySQLに同期します。
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from workflow.meeting_analyzer_v3 import MeetingAnalyzerV3
from database.mysql_client import MySQLClient
from integrations.slack_notifier import slack_notifier
from utils.config import settings
from utils.logger import setup_logging

# ロギング設定
setup_logging()
logger = logging.getLogger(__name__)

# FastAPIアプリ
app = FastAPI(
    title="AI Meeting Agent System with RAG and MySQL",
    description="会議に参加して各専門家の視点で発言するAIエージェントシステム（RAG + MySQL対応）",
    version="4.0.0"
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
        "message": "AI Meeting Agent System with RAG and MySQL",
        "version": "4.0.0",
        "features": [
            "Real-time transcription",
            "Multi-agent analysis",
            "RAG (Retrieval-Augmented Generation)",
            "MySQL data sync",
            "Meeting summary generation"
        ],
        "mysql_connected": mysql_client.is_connected()
    }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "mysql_connected": mysql_client.is_connected()
    }


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
            meeting_title = f"Meeting {bot_id[:8]}"
            
            meeting_analyzers[bot_id] = MeetingAnalyzerV3(
                bot_id=bot_id,
                meeting_url=meeting_url,
                meeting_title=meeting_title,
                enable_rag=True
            )
            logger.info(f"Created new MeetingAnalyzerV3 for bot {bot_id}")
            
            # MySQLに会議レコードを作成
            mysql_meeting_id = mysql_client.create_or_update_meeting(
                bot_id=bot_id,
                meeting_url=meeting_url,
                meeting_title=meeting_title,
                start_time=datetime.now(),
                rag_enabled=True
            )
            if mysql_meeting_id:
                logger.info(f"Created meeting {mysql_meeting_id} in MySQL for bot {bot_id}")
        
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
                
                # MySQLに文字起こしを保存（部分的でない場合のみ）
                if not is_partial:
                    mysql_meeting = mysql_client.get_meeting_by_bot_id(bot_id)
                    if mysql_meeting:
                        speaker = participant.get("name", "Unknown")
                        mysql_client.add_transcript(
                            meeting_id=mysql_meeting["id"],
                            speaker=speaker,
                            text=text,
                            timestamp=datetime.now(),
                            is_partial=False
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
                
                # MySQLに議事録を保存
                mysql_meeting = mysql_client.get_meeting_by_bot_id(bot_id)
                if mysql_meeting and summary:
                    mysql_client.create_or_update_meeting(
                        bot_id=bot_id,
                        meeting_url=mysql_meeting["meetingUrl"],
                        meeting_title=mysql_meeting["meetingTitle"],
                        end_time=datetime.now(),
                        summary=summary.get("summary", ""),
                        rag_enabled=True
                    )
                    
                    # 決定事項とアクションアイテムを保存
                    mysql_client.update_meeting_summary(
                        meeting_id=mysql_meeting["id"],
                        summary=summary.get("summary", ""),
                        decisions=summary.get("decisions", []),
                        action_items=summary.get("action_items", [])
                    )
                    logger.info(f"Saved summary to MySQL for meeting {mysql_meeting['id']}")
                    
                    # Slackに通知
                    if slack_notifier.is_enabled():
                        slack_sent = slack_notifier.send_meeting_summary(
                            meeting_title=mysql_meeting["meetingTitle"],
                            meeting_url=mysql_meeting["meetingUrl"],
                            summary=summary.get("summary", ""),
                            decisions=summary.get("decisions", []),
                            action_items=summary.get("action_items", []),
                            bot_id=bot_id
                        )
                        if slack_sent:
                            logger.info(f"Sent meeting summary to Slack for bot {bot_id}")
                        else:
                            logger.warning(f"Failed to send meeting summary to Slack for bot {bot_id}")
        
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


@app.get("/statistics")
async def get_statistics():
    """統計情報を取得"""
    try:
        stats = {
            "total_meetings": len(meeting_analyzers),
            "active_meetings": sum(1 for a in meeting_analyzers.values() if a.is_active),
            "mysql_connected": mysql_client.is_connected()
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {"error": str(e)}


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("Shutting down...")
    mysql_client.close()


if __name__ == "__main__":
    import uvicorn
    
    port = int(settings.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    
    uvicorn.run(
        "main_with_rag_mysql:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
