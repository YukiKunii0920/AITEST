"""
Supervisor Agent

複数の専門家エージェントを統括し、発言権を制御します。
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from .base_agent import AgentResponse
from .pm_agent import PMAgent
from .marketer_agent import MarketerAgent
from .legal_agent import LegalAgent
from .sales_agent import SalesAgent
from .consultant_agent import ConsultantAgent

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """Supervisor Agent"""
    
    def __init__(
        self,
        min_interval_seconds: int = 30,
        max_responses_per_agent: int = 3,
        priority_threshold: float = 0.6
    ):
        """
        初期化
        
        Args:
            min_interval_seconds: 最小発言間隔（秒）
            max_responses_per_agent: エージェントごとの最大発言回数
            priority_threshold: 発言を許可する最小優先度スコア
        """
        self.min_interval_seconds = min_interval_seconds
        self.max_responses_per_agent = max_responses_per_agent
        self.priority_threshold = priority_threshold
        
        # 専門家エージェントを初期化
        self.agents = [
            PMAgent(),
            MarketerAgent(),
            LegalAgent(),
            SalesAgent(),
            ConsultantAgent()
        ]
        
        # 発言履歴
        self.last_response_time: Optional[datetime] = None
        self.response_count: Dict[str, int] = {agent.name: 0 for agent in self.agents}
        self.recent_contents: List[str] = []  # 重複チェック用
        
        logger.info(f"Supervisor initialized with {len(self.agents)} agents")
    
    async def analyze_and_select(
        self,
        transcript: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[AgentResponse]:
        """
        すべてのエージェントに分析させ、最適な発言を選択
        
        Args:
            transcript: 文字起こしのリスト
            context: 追加のコンテキスト情報
            
        Returns:
            Optional[AgentResponse]: 選択された発言（なければNone）
        """
        # 最小発言間隔チェック
        if not self._can_speak_now():
            logger.debug("Too soon to speak again")
            return None
        
        # すべてのエージェントに並列で分析させる
        logger.info("Starting analysis by all agents...")
        responses: List[AgentResponse] = []
        
        for agent in self.agents:
            try:
                response = agent.analyze(transcript, context)
                if response:
                    responses.append(response)
                    logger.info(f"{agent.name} wants to speak: priority={response.priority_score:.2f}")
            except Exception as e:
                logger.error(f"Error in {agent.name}: {e}")
        
        if not responses:
            logger.info("No agent wants to speak")
            return None
        
        # 最適な発言を選択
        selected = self._select_best_response(responses)
        
        if selected:
            # 発言履歴を更新
            self.last_response_time = datetime.now()
            self.response_count[selected.agent_name] += 1
            self.recent_contents.append(selected.content)
            
            # 古い履歴を削除（最新10件のみ保持）
            if len(self.recent_contents) > 10:
                self.recent_contents = self.recent_contents[-10:]
            
            logger.info(f"Selected: {selected.agent_name} (priority={selected.priority_score:.2f})")
        
        return selected
    
    def _can_speak_now(self) -> bool:
        """
        今発言できるかどうかをチェック
        
        Returns:
            bool: 発言可能かどうか
        """
        if self.last_response_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_response_time).total_seconds()
        return elapsed >= self.min_interval_seconds
    
    def _select_best_response(
        self,
        responses: List[AgentResponse]
    ) -> Optional[AgentResponse]:
        """
        最適な発言を選択
        
        Args:
            responses: 候補となる発言のリスト
            
        Returns:
            Optional[AgentResponse]: 選択された発言
        """
        # フィルタリング
        filtered = []
        
        for response in responses:
            # 優先度スコアが閾値未満の場合は除外
            if response.priority_score < self.priority_threshold:
                logger.debug(f"Filtered out {response.agent_name}: priority too low")
                continue
            
            # 発言回数が上限に達している場合は除外
            if self.response_count.get(response.agent_name, 0) >= self.max_responses_per_agent:
                logger.debug(f"Filtered out {response.agent_name}: max responses reached")
                continue
            
            # 重複チェック（類似した内容を既に発言している場合は除外）
            if self._is_duplicate(response.content):
                logger.debug(f"Filtered out {response.agent_name}: duplicate content")
                continue
            
            filtered.append(response)
        
        if not filtered:
            logger.info("All responses filtered out")
            return None
        
        # 優先度スコアが最も高いものを選択
        best = max(filtered, key=lambda r: r.priority_score)
        
        return best
    
    def _is_duplicate(self, content: str, similarity_threshold: float = 0.7) -> bool:
        """
        重複チェック（簡易版）
        
        Args:
            content: チェックする内容
            similarity_threshold: 類似度の閾値
            
        Returns:
            bool: 重複しているかどうか
        """
        # 簡易的な重複チェック（キーワードベース）
        # 本格的にはembeddingベースの類似度計算を使用
        
        content_lower = content.lower()
        for recent in self.recent_contents:
            recent_lower = recent.lower()
            
            # 共通のキーワード数をカウント
            content_words = set(content_lower.split())
            recent_words = set(recent_lower.split())
            
            if not content_words or not recent_words:
                continue
            
            intersection = content_words & recent_words
            union = content_words | recent_words
            
            # Jaccard類似度
            similarity = len(intersection) / len(union) if union else 0
            
            if similarity >= similarity_threshold:
                return True
        
        return False
    
    def reset_history(self):
        """発言履歴をリセット"""
        self.last_response_time = None
        self.response_count = {agent.name: 0 for agent in self.agents}
        self.recent_contents = []
        logger.info("Supervisor history reset")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "total_responses": sum(self.response_count.values()),
            "response_count_by_agent": self.response_count.copy(),
            "last_response_time": self.last_response_time.isoformat() if self.last_response_time else None,
            "recent_contents_count": len(self.recent_contents)
        }
