"""
Recall.ai API クライアント

このモジュールは、Recall.ai APIとの通信を担当します。
ボットの作成、状態取得、チャットメッセージ送信などの機能を提供します。
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RecallAPIClient:
    """Recall.ai APIクライアント"""
    
    def __init__(self, api_key: str, base_url: str = "https://us-east-1.recall.ai/api/v1"):
        """
        Args:
            api_key: Recall.ai APIキー
            base_url: APIベースURL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.client = httpx.Client(headers=self.headers, timeout=30.0)
        logger.info(f"RecallAPIClient initialized with base_url: {base_url}")
    
    def create_bot(
        self,
        meeting_url: str,
        bot_name: str = "AI Meeting Assistant",
        webhook_url: Optional[str] = None,
        enable_transcript: bool = True,
        transcript_provider: str = "recallai_streaming",
        language: str = "ja",
        join_at: Optional[datetime] = None,
        chat_on_join_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ボットを作成して会議に参加させる
        
        Args:
            meeting_url: 会議URL（Teams/Meet/Zoom）
            bot_name: ボット名
            webhook_url: Webhookエンドポイント（リアルタイムイベント受信用）
            enable_transcript: 文字起こしを有効化
            transcript_provider: STTプロバイダ（recallai_streaming, deepgram_streaming等）
            language: 言語コード（ja, en等）
            join_at: ボット参加時刻（Noneの場合は即座に参加）
            chat_on_join_message: ボット参加時にチャットに投稿するメッセージ
            
        Returns:
            ボット情報（id, status等）
        """
        logger.info(f"Creating bot for meeting: {meeting_url}")
        
        # リクエストボディの構築
        payload: Dict[str, Any] = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
        }
        
        # 参加時刻の設定
        if join_at:
            payload["join_at"] = join_at.isoformat()
        
        # 録音設定
        recording_config: Dict[str, Any] = {}
        
        # 文字起こし設定
        if enable_transcript:
            transcript_config: Dict[str, Any] = {
                "provider": {}
            }
            
            if transcript_provider == "recallai_streaming":
                transcript_config["provider"]["recallai_streaming"] = {
                    "language_code": language
                }
            elif transcript_provider == "deepgram_streaming":
                transcript_config["provider"]["deepgram_streaming"] = {
                    "language": language,
                    "model": "nova-2"
                }
            
            # 話者分離を有効化
            transcript_config["diarization"] = {
                "use_separate_streams_when_available": True
            }
            
            recording_config["transcript"] = transcript_config
        
        # Webhook設定
        if webhook_url:
            recording_config["realtime_endpoints"] = [
                {
                    "type": "webhook",
                    "url": webhook_url,
                    "events": [
                        "transcript.data",
                        "transcript.partial_data",
                        "participant_events.join",
                        "participant_events.leave",
                        "participant_events.chat_message"
                    ]
                }
            ]
        
        if recording_config:
            payload["recording_config"] = recording_config
        
        # チャット設定
        if chat_on_join_message:
            payload["chat"] = {
                "on_bot_join": {
                    "send_to": "everyone",
                    "message": chat_on_join_message
                }
            }
        
        # APIリクエスト
        try:
            response = self.client.post(f"{self.base_url}/bot/", json=payload)
            response.raise_for_status()
            bot_data = response.json()
            logger.info(f"Bot created successfully: {bot_data.get('id')}")
            return bot_data
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create bot: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating bot: {e}")
            raise
    
    def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """
        ボット情報を取得
        
        Args:
            bot_id: ボットID
            
        Returns:
            ボット情報
        """
        logger.debug(f"Fetching bot info: {bot_id}")
        try:
            response = self.client.get(f"{self.base_url}/bot/{bot_id}/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get bot: {e.response.status_code} - {e.response.text}")
            raise
    
    def send_chat_message(
        self,
        bot_id: str,
        message: str,
        to: str = "everyone",
        pin: bool = False
    ) -> Dict[str, Any]:
        """
        チャットメッセージを送信
        
        Args:
            bot_id: ボットID
            message: メッセージ内容
            to: 送信先（"everyone", "host", participant_id）
            pin: メッセージをピン留めするか
            
        Returns:
            送信結果
        """
        logger.info(f"Sending chat message from bot {bot_id}: {message[:50]}...")
        
        payload = {
            "message": message,
            "to": to,
            "pin": pin
        }
        
        try:
            response = self.client.post(
                f"{self.base_url}/bot/{bot_id}/send_chat_message/",
                json=payload
            )
            response.raise_for_status()
            logger.info("Chat message sent successfully")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send chat message: {e.response.status_code} - {e.response.text}")
            raise
    
    def leave_call(self, bot_id: str) -> Dict[str, Any]:
        """
        ボットを会議から退出させる
        
        Args:
            bot_id: ボットID
            
        Returns:
            退出結果
        """
        logger.info(f"Leaving call for bot: {bot_id}")
        try:
            response = self.client.post(f"{self.base_url}/bot/{bot_id}/leave_call/")
            response.raise_for_status()
            logger.info("Bot left the call successfully")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to leave call: {e.response.status_code} - {e.response.text}")
            raise
    
    def close(self):
        """HTTPクライアントをクローズ"""
        self.client.close()
        logger.debug("RecallAPIClient closed")
