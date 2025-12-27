"""
LangGraphワークフロー統合版MeetingAnalyzer

LangGraphを使用した高度な会議分析を実行します。
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from .state import MeetingState, create_initial_state
from .graph import get_workflow
from ..bot.recall_client import RecallAPIClient
from ..database import MeetingDatabase
from ..utils.config import settings

logger = logging.getLogger(__name__)


class MeetingAnalyzerV2:
    """LangGraphワークフロー統合版会議分析クラス"""
    
    def __init__(
        self,
        bot_id: str,
        meeting_url: str,
        meeting_title: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            bot_id: ボットID
            meeting_url: 会議URL
            meeting_title: 会議タイトル
        """
        self.bot_id = bot_id
        self.meeting_url = meeting_url
        self.meeting_title = meeting_title
        
        # 初期状態を作成
        self.state = create_initial_state(
            bot_id=bot_id,
            meeting_url=meeting_url,
            meeting_title=meeting_title
        )
        
        # ワークフローを取得
        self.workflow = get_workflow()
        
        # Recall.ai APIクライアント
        self.recall_client = RecallAPIClient(
            api_key=settings.recall_api_key,
            base_url=settings.recall_api_base_url
        )
        
        # データベース
        self.db = MeetingDatabase()
        
        # 会議をデータベースに作成
        self.meeting_id = self.db.create_meeting(
            bot_id=bot_id,
            meeting_url=meeting_url,
            meeting_title=meeting_title,
            start_time=self.state["start_time"]
        )
        
        logger.info(f"MeetingAnalyzerV2 initialized for bot {bot_id}, meeting_id={self.meeting_id}")
    
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
        # 部分的な文字起こしは無視
        if is_partial:
            return
        
        # 文字起こしを状態に追加
        transcript_item = {
            "text": text,
            "speaker": participant.get("name", "Unknown"),
            "participant_id": participant.get("id", ""),
            "timestamp": datetime.now().isoformat(),
            "is_host": participant.get("is_host", False)
        }
        
        # 状態を更新（追記型）
        self.state["transcripts"].append(transcript_item)
        
        # データベースに保存
        try:
            self.db.add_transcript(
                meeting_id=self.meeting_id,
                speaker=transcript_item["speaker"],
                text=transcript_item["text"],
                timestamp=transcript_item["timestamp"],
                is_partial=is_partial
            )
        except Exception as e:
            logger.error(f"Failed to save transcript to database: {e}")
        
        # 参加者情報を更新
        participant_id = participant.get("id", "")
        if participant_id:
            self.state["participants"][participant_id] = participant
        
        logger.debug(f"Transcript added: {len(self.state['transcripts'])} total")
        
        # ワークフローを実行
        await self._run_workflow()
    
    async def _run_workflow(self):
        """ワークフローを実行"""
        try:
            logger.debug("Running workflow...")
            
            # ワークフローを実行
            result = self.workflow.invoke(self.state)
            
            # 状態を更新
            self.state = result
            
            # データベースを更新
            try:
                self.db.update_meeting(
                    bot_id=self.bot_id,
                    transcript_count=len(self.state["transcripts"]),
                    participant_count=len(self.state["participants"]),
                    analysis_count=self.state["analysis_count"],
                    message_count=self.state["message_count"],
                    error_count=len(self.state["errors"])
                )
                
                # 選択された発言をデータベースに保存
                if self.state.get("selected_response"):
                    response = self.state["selected_response"]
                    self.db.add_agent_message(
                        meeting_id=self.meeting_id,
                        agent_name=response["agent_name"],
                        content=response["content"],
                        confidence=response["confidence"],
                        urgency=response["urgency"],
                        relevance=response["relevance"],
                        priority_score=response["priority_score"]
                    )
            except Exception as e:
                logger.error(f"Failed to update database: {e}")
            
            logger.debug(f"Workflow completed: analysis_count={self.state['analysis_count']}, message_count={self.state['message_count']}")
            
        except Exception as e:
            logger.error(f"Error in workflow: {e}", exc_info=True)
            self.state["errors"].append(f"Workflow: {str(e)}")
    
    async def generate_final_summary(self) -> Dict[str, Any]:
        """
        会議終了時の最終議事録を生成
        
        Returns:
            Dict[str, Any]: 議事録データ
        """
        logger.info("Generating final meeting summary...")
        
        # 議事録生成フラグを立てる
        self.state["should_generate_summary"] = True
        
        # 議事録生成ノードを直接実行
        from .nodes import generate_meeting_summary
        self.state = generate_meeting_summary(self.state)
        
        # データベースに保存
        try:
            # 会議を更新
            self.db.update_meeting(
                bot_id=self.bot_id,
                end_time=datetime.now(),
                summary=self.state["meeting_summary"],
                transcript_count=len(self.state["transcripts"]),
                participant_count=len(self.state["participants"]),
                analysis_count=self.state["analysis_count"],
                message_count=self.state["message_count"],
                error_count=len(self.state["errors"])
            )
            
            # 決定事項を保存
            for decision in self.state["decisions"]:
                self.db.add_decision(
                    meeting_id=self.meeting_id,
                    content=decision.get("content", ""),
                    timestamp=decision.get("timestamp")
                )
            
            # アクションアイテムを保存
            for action_item in self.state["action_items"]:
                self.db.add_action_item(
                    meeting_id=self.meeting_id,
                    task=action_item.get("task", ""),
                    assignee=action_item.get("assignee"),
                    due_date=action_item.get("due_date"),
                    timestamp=action_item.get("timestamp")
                )
        except Exception as e:
            logger.error(f"Failed to save summary to database: {e}")
        
        # 議事録データを返す
        return {
            "bot_id": self.state["bot_id"],
            "meeting_url": self.state["meeting_url"],
            "meeting_title": self.state["meeting_title"],
            "start_time": self.state["start_time"].isoformat(),
            "end_time": datetime.now().isoformat(),
            "summary": self.state["meeting_summary"],
            "decisions": self.state["decisions"],
            "action_items": self.state["action_items"],
            "transcript_count": len(self.state["transcripts"]),
            "participant_count": len(self.state["participants"]),
            "analysis_count": self.state["analysis_count"],
            "message_count": self.state["message_count"],
            "errors": self.state["errors"]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "bot_id": self.state["bot_id"],
            "transcript_count": len(self.state["transcripts"]),
            "participant_count": len(self.state["participants"]),
            "analysis_count": self.state["analysis_count"],
            "message_count": self.state["message_count"],
            "error_count": len(self.state["errors"]),
            "last_analysis_time": self.state["last_analysis_time"].isoformat() if self.state["last_analysis_time"] else None
        }
    
    def reset(self):
        """状態をリセット"""
        self.state = create_initial_state(
            bot_id=self.bot_id,
            meeting_url=self.meeting_url,
            meeting_title=self.meeting_title
        )
        logger.info("MeetingAnalyzerV2 reset")
