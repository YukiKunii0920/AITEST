"""
Webhook受信サーバー

Recall.aiからのリアルタイムイベント（文字起こし、参加者イベント等）を受信し、
適切なハンドラーに振り分けます。
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime
import json

from src.utils.database import db_manager

logger = logging.getLogger(__name__)

app = FastAPI(title="Meeting AI Agent Webhook Server")


class WebhookHandler:
    """ウェブフックイベントハンドラー"""
    
    def __init__(self):
        self.transcript_handlers: List[Callable] = []
        self.participant_handlers: List[Callable] = []
        self.chat_handlers: List[Callable] = []
        self.transcripts: List[Dict[str, Any]] = []
        self.participants: Dict[str, Dict[str, Any]] = {}
        self.bot_id: Optional[str] = None
        self.meeting_id: Optional[int] = None
        logger.info("WebhookHandler initialized")
    
    def register_transcript_handler(self, handler: Callable):
        """文字起こしイベントハンドラーを登録"""
        self.transcript_handlers.append(handler)
        logger.info(f"Registered transcript handler: {handler.__name__}")
    
    def register_participant_handler(self, handler: Callable):
        """参加者イベントハンドラーを登録"""
        self.participant_handlers.append(handler)
        logger.info(f"Registered participant handler: {handler.__name__}")
    
    def register_chat_handler(self, handler: Callable):
        """チャットイベントハンドラーを登録"""
        self.chat_handlers.append(handler)
        logger.info(f"Registered chat handler: {handler.__name__}")
    
    async def handle_transcript_event(self, event: Dict[str, Any]):
        """
        文字起こしイベントを処理
        
        Args:
            event: transcript.data または transcript.partial_data イベント
        """
        event_type = event.get("event")
        data = event.get("data", {}).get("data", {})
        
        words = data.get("words", [])
        participant = data.get("participant", {})
        
        # テキストを結合
        text = " ".join([w.get("text", "") for w in words])
        
        # ログ出力
        participant_name = participant.get("name", "Unknown")
        is_partial = event_type == "transcript.partial_data"
        log_prefix = "[PARTIAL]" if is_partial else "[FINAL]"
        
        logger.info(f"{log_prefix} {participant_name}: {text}")
        
        # 確定した文字起こしのみ保存
        if not is_partial:
            transcript_entry = {
                "timestamp": datetime.now().isoformat(),
                "participant": participant,
                "text": text,
                "words": words
            }
            self.transcripts.append(transcript_entry)
            
            # MySQLに保存
            if self.meeting_id:
                db_manager.save_transcript(
                    meeting_id=self.meeting_id,
                    speaker_name=participant_name,
                    text=text
                )
        
        # 登録されたハンドラーを実行
        for handler in self.transcript_handlers:
            try:
                await handler(text, participant, is_partial)
            except Exception as e:
                logger.error(f"Error in transcript handler {handler.__name__}: {e}")
    
    async def handle_participant_event(self, event: Dict[str, Any]):
        """
        参加者イベントを処理
        
        Args:
            event: participant_events.join または participant_events.leave イベント
        """
        event_type = event.get("event")
        data = event.get("data", {}).get("data", {})
        participant = data.get("participant", {})
        
        participant_id = str(participant.get("id"))
        participant_name = participant.get("name", "Unknown")
        
        if event_type == "participant_events.join":
            self.participants[participant_id] = participant
            logger.info(f"Participant joined: {participant_name} (ID: {participant_id})")
        elif event_type == "participant_events.leave":
            if participant_id in self.participants:
                del self.participants[participant_id]
            logger.info(f"Participant left: {participant_name} (ID: {participant_id})")
        
        # 登録されたハンドラーを実行
        for handler in self.participant_handlers:
            try:
                await handler(event_type, participant)
            except Exception as e:
                logger.error(f"Error in participant handler {handler.__name__}: {e}")
    
    async def handle_chat_event(self, event: Dict[str, Any]):
        """
        チャットイベントを処理
        
        Args:
            event: participant_events.chat_message イベント
        """
        data = event.get("data", {}).get("data", {})
        participant = data.get("participant", {})
        message = data.get("message", "")
        
        participant_name = participant.get("name", "Unknown")
        logger.info(f"Chat message from {participant_name}: {message}")
        
        # 登録されたハンドラーを実行
        for handler in self.chat_handlers:
            try:
                await handler(message, participant)
            except Exception as e:
                logger.error(f"Error in chat handler {handler.__name__}: {e}")
    
    async def process_webhook(self, payload: Dict[str, Any]):
        """
        Webhookペイロードを処理
        
        Args:
            payload: Recall.aiから送信されたWebhookペイロード
        """
        event_type = payload.get("event")
        
        if not event_type:
            logger.warning("Received webhook without event type")
            return
        
        # bot_idを取得してmeeting_idを設定
        data = payload.get("data", {})
        bot_id = data.get("bot_id")
        
        if bot_id and bot_id != self.bot_id:
            self.bot_id = bot_id
            # 会議をデータベースから取得または作成
            meeting = db_manager.get_meeting_by_bot_id(bot_id)
            if meeting:
                self.meeting_id = meeting['id']
                logger.info(f"Meeting found: id={self.meeting_id}, bot_id={bot_id}")
            else:
                # 会議が存在しない場合は作成
                meeting_url = data.get("meeting_url", "")
                self.meeting_id = db_manager.save_meeting(bot_id, meeting_url)
                logger.info(f"Meeting created: id={self.meeting_id}, bot_id={bot_id}")
        
        logger.debug(f"Processing webhook event: {event_type}")
        
        # イベントタイプに応じて処理を振り分け
        if event_type in ["transcript.data", "transcript.partial_data"]:
            await self.handle_transcript_event(payload)
        elif event_type in ["participant_events.join", "participant_events.leave"]:
            await self.handle_participant_event(payload)
        elif event_type == "participant_events.chat_message":
            await self.handle_chat_event(payload)
        else:
            logger.debug(f"Unhandled event type: {event_type}")
    
    def get_transcript_history(self) -> List[Dict[str, Any]]:
        """文字起こし履歴を取得"""
        return self.transcripts
    
    def get_participants(self) -> Dict[str, Dict[str, Any]]:
        """現在の参加者リストを取得"""
        return self.participants


# グローバルハンドラーインスタンス
webhook_handler = WebhookHandler()


@app.get("/")
async def root():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "ok",
        "service": "Meeting AI Agent Webhook Server",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/webhook/recall")
async def receive_recall_webhook(request: Request):
    """
    Recall.aiからのWebhookを受信
    
    このエンドポイントは、Recall.aiのCreate Bot APIで指定したWebhook URLとして使用されます。
    """
    try:
        payload = await request.json()
        logger.debug(f"Received webhook payload: {json.dumps(payload, indent=2)}")
        
        # Webhookを処理
        await webhook_handler.process_webhook(payload)
        
        return {"status": "ok"}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/status")
async def get_status():
    """現在の状態を取得"""
    return {
        "participants": webhook_handler.get_participants(),
        "transcript_count": len(webhook_handler.get_transcript_history()),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/transcript")
async def get_transcript():
    """文字起こし履歴を取得"""
    return {
        "transcripts": webhook_handler.get_transcript_history(),
        "count": len(webhook_handler.get_transcript_history())
    }


@app.post("/webhook/transcript")
async def receive_transcript_webhook(request: Request):
    """
    Recall.aiからのリアルタイム文字起こしWebhookを受信
    
    このエンドポイントは、real_time_transcription.destination_urlとして使用されます。
    """
    try:
        payload = await request.json()
        logger.debug(f"Received transcript webhook: {json.dumps(payload, indent=2)}")
        
        # Webhookを処理
        await webhook_handler.process_webhook(payload)
        
        return {"status": "ok"}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing transcript webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def get_webhook_handler() -> WebhookHandler:
    """グローバルWebhookハンドラーを取得"""
    return webhook_handler
