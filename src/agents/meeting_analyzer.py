"""
会議分析モジュール

Webhookサーバーとマルチエージェントシステムを統合します。
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from .supervisor import SupervisorAgent
from ..bot.recall_client import RecallAPIClient
from ..utils.config import settings

logger = logging.getLogger(__name__)


class MeetingAnalyzer:
    """会議分析クラス"""
    
    def __init__(
        self,
        bot_id: str,
        min_transcript_count: int = 5,
        analysis_interval: int = 10
    ):
        """
        初期化
        
        Args:
            bot_id: ボットID
            min_transcript_count: 分析を開始する最小文字起こし数
            analysis_interval: 分析を実行する間隔（文字起こし数）
        """
        self.bot_id = bot_id
        self.min_transcript_count = min_transcript_count
        self.analysis_interval = analysis_interval
        
        # Supervisor Agentを初期化
        self.supervisor = SupervisorAgent(
            min_interval_seconds=30,  # 最小30秒間隔
            max_responses_per_agent=5,  # エージェントごと最大5回
            priority_threshold=0.6  # 優先度0.6以上のみ発言
        )
        
        # Recall.ai APIクライアント
        self.recall_client = RecallAPIClient(
            api_key=settings.recall_api_key,
            base_url=settings.recall_api_base_url
        )
        
        # 文字起こしバッファ
        self.transcript_buffer: List[Dict[str, Any]] = []
        self.last_analysis_count = 0
        
        logger.info(f"MeetingAnalyzer initialized for bot {bot_id}")
    
    async def process_transcript(
        self,
        text: str,
        participant: Dict[str, Any],
        is_partial: bool = False
    ):
        """
        文字起こしを処理
        
        Args:
            text: 文字起こしテキスト
            participant: 話者情報
            is_partial: 部分的な文字起こしかどうか
        """
        # 部分的な文字起こしは無視（確定したもののみ処理）
        if is_partial:
            return
        
        # バッファに追加
        transcript_item = {
            "text": text,
            "speaker": participant.get("name", "Unknown"),
            "participant_id": participant.get("id", ""),
            "timestamp": datetime.now().isoformat(),
            "is_host": participant.get("is_host", False)
        }
        
        self.transcript_buffer.append(transcript_item)
        logger.debug(f"Transcript added to buffer: {len(self.transcript_buffer)} items")
        
        # 分析を実行すべきかチェック
        if self._should_analyze():
            await self._analyze_and_respond()
    
    def _should_analyze(self) -> bool:
        """
        分析を実行すべきかどうかを判定
        
        Returns:
            bool: 分析すべきかどうか
        """
        # 最小文字起こし数に達していない場合
        if len(self.transcript_buffer) < self.min_transcript_count:
            return False
        
        # 前回の分析からの増加数をチェック
        new_count = len(self.transcript_buffer) - self.last_analysis_count
        if new_count < self.analysis_interval:
            return False
        
        return True
    
    async def _analyze_and_respond(self):
        """分析を実行し、必要に応じてチャットに投稿"""
        try:
            logger.info("Starting meeting analysis...")
            
            # Supervisorに分析させる
            selected_response = await self.supervisor.analyze_and_select(
                transcript=self.transcript_buffer,
                context={"bot_id": self.bot_id}
            )
            
            # 発言が選択された場合
            if selected_response:
                logger.info(f"Posting message from {selected_response.agent_name}")
                
                # チャットメッセージを整形
                message = self._format_message(selected_response)
                
                # チャットに投稿
                try:
                    self.recall_client.send_chat_message(
                        bot_id=self.bot_id,
                        message=message,
                        to="everyone"
                    )
                    logger.info("Message posted successfully")
                except Exception as e:
                    logger.error(f"Failed to post message: {e}")
            else:
                logger.info("No message to post")
            
            # 最終分析位置を更新
            self.last_analysis_count = len(self.transcript_buffer)
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}", exc_info=True)
    
    def _format_message(self, response) -> str:
        """
        チャットメッセージを整形
        
        Args:
            response: AgentResponse
            
        Returns:
            str: 整形されたメッセージ
        """
        # エージェント名のアイコン
        icons = {
            "PM Agent": "📊",
            "Marketer Agent": "📈",
            "Legal Agent": "⚖️",
            "Sales Agent": "💼",
            "Consultant Agent": "💡"
        }
        
        icon = icons.get(response.agent_name, "🤖")
        
        # メッセージを整形
        message = f"{icon} **{response.agent_name}**\n\n{response.content}"
        
        # Google Meetの500文字制限を考慮
        if len(message) > 480:
            message = message[:477] + "..."
        
        return message
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "transcript_count": len(self.transcript_buffer),
            "last_analysis_count": self.last_analysis_count,
            "supervisor_stats": self.supervisor.get_statistics()
        }
    
    def reset(self):
        """状態をリセット"""
        self.transcript_buffer = []
        self.last_analysis_count = 0
        self.supervisor.reset_history()
        logger.info("MeetingAnalyzer reset")
