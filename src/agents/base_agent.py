"""
基底エージェントクラス

すべての専門家エージェントが継承する基底クラスです。
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """エージェントの応答"""
    
    agent_name: str
    """エージェント名"""
    
    content: str
    """発言内容"""
    
    confidence: float
    """自信度（0.0-1.0）"""
    
    urgency: float
    """緊急度（0.0-1.0）"""
    
    relevance: float
    """関連性（0.0-1.0）"""
    
    reasoning: str
    """発言の根拠・理由"""
    
    should_speak: bool = True
    """発言すべきかどうか"""
    
    @property
    def priority_score(self) -> float:
        """
        優先度スコアを計算
        
        Returns:
            float: 優先度スコア（0.0-1.0）
        """
        # 重み付け平均: 自信度40%, 緊急度30%, 関連性30%
        return (self.confidence * 0.4 + self.urgency * 0.3 + self.relevance * 0.3)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "agent_name": self.agent_name,
            "content": self.content,
            "confidence": self.confidence,
            "urgency": self.urgency,
            "relevance": self.relevance,
            "reasoning": self.reasoning,
            "should_speak": self.should_speak,
            "priority_score": self.priority_score
        }


class BaseAgent(ABC):
    """基底エージェントクラス"""
    
    def __init__(self, name: str, role: str, expertise: str):
        """
        初期化
        
        Args:
            name: エージェント名
            role: 役割
            expertise: 専門分野
        """
        self.name = name
        self.role = role
        self.expertise = expertise
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        システムプロンプトを取得
        
        Returns:
            str: システムプロンプト
        """
        pass
    
    @abstractmethod
    def analyze(
        self,
        transcript: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[AgentResponse]:
        """
        会議の文字起こしを分析
        
        Args:
            transcript: 文字起こしのリスト
            context: 追加のコンテキスト情報
            
        Returns:
            Optional[AgentResponse]: 分析結果（発言しない場合はNone）
        """
        pass
    
    def _should_analyze(
        self,
        transcript: List[Dict[str, Any]],
        min_length: int = 3
    ) -> bool:
        """
        分析を実行すべきかどうかを判定
        
        Args:
            transcript: 文字起こしのリスト
            min_length: 最小の文字起こし数
            
        Returns:
            bool: 分析すべきかどうか
        """
        if not transcript or len(transcript) < min_length:
            self.logger.debug(f"Transcript too short: {len(transcript)} < {min_length}")
            return False
        
        return True
    
    def _format_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        """
        文字起こしを整形
        
        Args:
            transcript: 文字起こしのリスト
            
        Returns:
            str: 整形された文字起こし
        """
        formatted = []
        for item in transcript:
            speaker = item.get("speaker", "Unknown")
            text = item.get("text", "")
            timestamp = item.get("timestamp", "")
            formatted.append(f"[{timestamp}] {speaker}: {text}")
        
        return "\n".join(formatted)
    
    def __str__(self) -> str:
        return f"{self.name} ({self.role})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} role={self.role}>"
