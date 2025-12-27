"""
RAG対応MeetingAnalyzer（V3）

過去の会議履歴を参照した高度な会議分析を実行します。
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from .state import MeetingState, create_initial_state
from .graph import get_workflow
from ..bot.recall_client import RecallAPIClient
from ..database import MeetingDatabase
from ..rag import MeetingVectorStore
from ..utils.config import settings

logger = logging.getLogger(__name__)


class MeetingAnalyzerV3:
    """RAG対応会議分析クラス"""
    
    def __init__(
        self,
        bot_id: str,
        meeting_url: str,
        meeting_title: Optional[str] = None,
        enable_rag: bool = True
    ):
        """
        初期化
        
        Args:
            bot_id: ボットID
            meeting_url: 会議URL
            meeting_title: 会議タイトル
            enable_rag: RAGを有効化するかどうか
        """
        self.bot_id = bot_id
        self.meeting_url = meeting_url
        self.meeting_title = meeting_title
        self.enable_rag = enable_rag
        
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
        
        # ベクトルストア
        self.vector_store = MeetingVectorStore() if enable_rag else None
        
        logger.info(f"MeetingAnalyzerV3 initialized for bot {bot_id}, meeting_id={self.meeting_id}, RAG={'enabled' if enable_rag else 'disabled'}")
    
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
            
            # RAGコンテキストを状態に追加
            if self.enable_rag and self.vector_store:
                try:
                    # 現在の会議内容から類似会議を検索
                    recent_transcripts = [t.get("text", "") for t in self.state["transcripts"][-10:]]
                    rag_context = self.vector_store.get_meeting_context(
                        current_transcripts=recent_transcripts,
                        n_results=3
                    )
                    
                    # 状態にRAGコンテキストを追加
                    if "rag_context" not in self.state:
                        self.state["rag_context"] = ""
                    self.state["rag_context"] = rag_context
                    
                except Exception as e:
                    logger.warning(f"Failed to get RAG context: {e}")
            
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
            
            # ベクトルストアに追加
            if self.enable_rag and self.vector_store and self.state["meeting_summary"]:
                try:
                    transcripts = [t.get("text", "") for t in self.state["transcripts"]]
                    self.vector_store.add_meeting(
                        meeting_id=str(self.meeting_id),
                        bot_id=self.bot_id,
                        meeting_title=self.meeting_title or "Untitled Meeting",
                        summary=self.state["meeting_summary"],
                        transcripts=transcripts,
                        metadata={
                            "start_time": self.state["start_time"].isoformat(),
                            "end_time": datetime.now().isoformat(),
                            "participant_count": len(self.state["participants"])
                        }
                    )
                    logger.info("Meeting added to vector store")
                except Exception as e:
                    logger.error(f"Failed to add meeting to vector store: {e}")
            
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
            "errors": self.state["errors"],
            "rag_enabled": self.enable_rag
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = {
            "bot_id": self.state["bot_id"],
            "transcript_count": len(self.state["transcripts"]),
            "participant_count": len(self.state["participants"]),
            "analysis_count": self.state["analysis_count"],
            "message_count": self.state["message_count"],
            "error_count": len(self.state["errors"]),
            "last_analysis_time": self.state["last_analysis_time"].isoformat() if self.state["last_analysis_time"] else None,
            "rag_enabled": self.enable_rag
        }
        
        # ベクトルストアの統計を追加
        if self.enable_rag and self.vector_store:
            try:
                vector_stats = self.vector_store.get_statistics()
                stats["vector_store"] = vector_stats
            except Exception as e:
                logger.error(f"Failed to get vector store statistics: {e}")
        
        return stats
    
    def reset(self):
        """状態をリセット"""
        self.state = create_initial_state(
            bot_id=self.bot_id,
            meeting_url=self.meeting_url,
            meeting_title=self.meeting_title
        )
        logger.info("MeetingAnalyzerV3 reset")
