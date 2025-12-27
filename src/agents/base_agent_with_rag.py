"""
RAG対応エージェント基底クラス

過去の会議履歴を参照して分析を行うエージェントの基底クラス。
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from openai import OpenAI

from ..utils.config import settings
from ..rag import MeetingVectorStore

logger = logging.getLogger(__name__)


@dataclass
class AgentResponseWithRAG:
    """エージェントの分析結果（RAG対応）"""
    agent_name: str
    content: str
    confidence: float  # 0.0-1.0
    urgency: float  # 0.0-1.0
    relevance: float  # 0.0-1.0
    priority_score: float  # 0.0-1.0
    referenced_meetings: List[Dict[str, Any]]  # 参照した過去の会議
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "agent_name": self.agent_name,
            "content": self.content,
            "confidence": self.confidence,
            "urgency": self.urgency,
            "relevance": self.relevance,
            "priority_score": self.priority_score,
            "referenced_meetings": self.referenced_meetings
        }


class BaseAgentWithRAG:
    """RAG対応エージェント基底クラス"""
    
    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str = "gpt-4o-mini"
    ):
        """
        初期化
        
        Args:
            name: エージェント名
            role: 役割
            system_prompt: システムプロンプト
            model: 使用するモデル
        """
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        
        # OpenAIクライアント
        self.client = OpenAI(api_key=settings.openai_api_key)
        
        # ベクトルストア
        self.vector_store = MeetingVectorStore()
        
        logger.info(f"{self.name} initialized with RAG support")
    
    def analyze(
        self,
        transcript: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        use_rag: bool = True
    ) -> Optional[AgentResponseWithRAG]:
        """
        会議を分析（RAG対応）
        
        Args:
            transcript: 文字起こしのリスト
            context: 追加のコンテキスト
            use_rag: RAGを使用するかどうか
            
        Returns:
            Optional[AgentResponseWithRAG]: 分析結果
        """
        try:
            # 文字起こしを整形
            transcript_text = self._format_transcript(transcript)
            
            # RAGコンテキストを取得
            rag_context = ""
            referenced_meetings = []
            
            if use_rag:
                try:
                    # 現在の会議内容から類似会議を検索
                    recent_transcripts = [t.get("text", "") for t in transcript[-10:]]
                    similar_meetings = self.vector_store.search_similar_meetings(
                        query="\n".join(recent_transcripts),
                        n_results=3,
                        filter_metadata={"type": "summary"}
                    )
                    
                    if similar_meetings:
                        rag_context = "\n\n## 過去の類似会議:\n"
                        for i, meeting in enumerate(similar_meetings, 1):
                            metadata = meeting['metadata']
                            document = meeting['document']
                            rag_context += (
                                f"\n### {i}. {metadata.get('meeting_title', 'Untitled')}\n"
                                f"{document[:300]}...\n"
                            )
                            referenced_meetings.append({
                                "meeting_id": metadata.get("meeting_id"),
                                "meeting_title": metadata.get("meeting_title"),
                                "summary": document[:200]
                            })
                        
                        logger.info(f"{self.name}: Found {len(similar_meetings)} similar meetings")
                
                except Exception as e:
                    logger.warning(f"{self.name}: Failed to get RAG context: {e}")
            
            # システムプロンプトを構築
            full_system_prompt = self.system_prompt
            if rag_context:
                full_system_prompt += rag_context
            
            # ユーザープロンプトを構築
            user_prompt = f"""以下の会議の文字起こしを分析してください：

{transcript_text}

あなたの役割は「{self.role}」です。

以下の形式で回答してください：

1. **発言すべきかどうか**: Yes/No
2. **自信度**: 0.0-1.0（この分析にどれだけ自信があるか）
3. **緊急度**: 0.0-1.0（この指摘がどれだけ緊急か）
4. **関連性**: 0.0-1.0（この指摘が会議にどれだけ関連しているか）
5. **発言内容**: 具体的なアドバイスや指摘（発言すべき場合のみ）

注意:
- 発言すべきでない場合は、理由を簡潔に述べてください
- 過去の類似会議の情報も参考にしてください
- 自信度が0.7未満の場合は発言を控えてください
"""
            
            # OpenAI APIで分析
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # レスポンスをパース
            content = response.choices[0].message.content
            
            # 発言すべきかどうかを判定
            should_speak = "yes" in content.lower().split("\n")[0].lower()
            
            if not should_speak:
                logger.info(f"{self.name}: Decided not to speak")
                return None
            
            # スコアを抽出（簡易的な実装）
            confidence = self._extract_score(content, "自信度")
            urgency = self._extract_score(content, "緊急度")
            relevance = self._extract_score(content, "関連性")
            
            # 自信度が低い場合は発言しない
            if confidence < 0.7:
                logger.info(f"{self.name}: Confidence too low: {confidence:.2f}")
                return None
            
            # 優先度スコアを計算
            priority_score = (confidence * 0.4 + urgency * 0.3 + relevance * 0.3)
            
            # 発言内容を抽出
            speaking_content = self._extract_speaking_content(content)
            
            return AgentResponseWithRAG(
                agent_name=self.name,
                content=speaking_content,
                confidence=confidence,
                urgency=urgency,
                relevance=relevance,
                priority_score=priority_score,
                referenced_meetings=referenced_meetings
            )
            
        except Exception as e:
            logger.error(f"{self.name}: Analysis failed: {e}")
            return None
    
    def _format_transcript(self, transcript: List[Dict[str, Any]]) -> str:
        """文字起こしを整形"""
        lines = []
        for item in transcript[-20:]:  # 最新20件
            speaker = item.get("speaker", "Unknown")
            text = item.get("text", "")
            lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
    
    def _extract_score(self, content: str, label: str) -> float:
        """スコアを抽出（簡易的な実装）"""
        try:
            for line in content.split("\n"):
                if label in line:
                    # "自信度: 0.8" のような形式から数値を抽出
                    parts = line.split(":")
                    if len(parts) >= 2:
                        score_str = parts[1].strip().split()[0]
                        return float(score_str)
        except:
            pass
        return 0.75  # デフォルト値
    
    def _extract_speaking_content(self, content: str) -> str:
        """発言内容を抽出"""
        # "発言内容:" 以降を抽出
        lines = content.split("\n")
        speaking_lines = []
        in_speaking_section = False
        
        for line in lines:
            if "発言内容" in line:
                in_speaking_section = True
                # "発言内容:" の後の内容も含める
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    speaking_lines.append(parts[1].strip())
                continue
            
            if in_speaking_section:
                speaking_lines.append(line)
        
        if speaking_lines:
            return "\n".join(speaking_lines).strip()
        
        # フォールバック: 全体を返す
        return content
