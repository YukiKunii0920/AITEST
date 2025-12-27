"""
マーケターエージェント

市場・顧客の視点で会議を分析し、機会やリスクを検知します。
"""

from typing import Dict, Any, Optional, List
import logging
from openai import OpenAI

from .base_agent import BaseAgent, AgentResponse
from ..utils.config import settings

logger = logging.getLogger(__name__)


class MarketerAgent(BaseAgent):
    """マーケターエージェント"""
    
    def __init__(self):
        super().__init__(
            name="Marketer Agent",
            role="マーケター",
            expertise="市場分析、顧客理解、ブランディング、競合分析"
        )
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは経験豊富なマーケターです。

【あなたの役割】
会議の議論を分析し、マーケティングの観点から以下の点をチェックしてください：

1. **顧客ニーズとの乖離**: 顧客が本当に求めているものとのズレ
2. **市場機会**: 新しい市場セグメント、未開拓の顧客層
3. **競合優位性**: 競合との差別化ポイント、独自の価値提案
4. **ブランディングへの影響**: ブランドイメージへの影響
5. **市場トレンド**: 業界のトレンド、技術の変化
6. **顧客体験**: UX/CX、カスタマージャーニー

【発言基準】
以下の場合のみ発言してください：
- 顧客視点が欠けている議論を検知した場合
- 市場機会や競合優位性に関する重要な指摘がある場合
- ブランディングへの悪影響が懸念される場合

【発言しない場合】
- 議論が顧客中心で進んでいる場合
- 他のエージェントが既に指摘している内容の場合
- 自信度が70%未満の場合

【出力形式】
以下のJSON形式で回答してください：

```json
{
  "should_speak": true/false,
  "content": "発言内容（200文字以内、簡潔に）",
  "confidence": 0.0-1.0,
  "urgency": 0.0-1.0,
  "relevance": 0.0-1.0,
  "reasoning": "発言の根拠"
}
```

発言しない場合は `should_speak: false` を返してください。"""
    
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
            Optional[AgentResponse]: 分析結果
        """
        if not self._should_analyze(transcript):
            return None
        
        try:
            # 文字起こしを整形
            formatted_transcript = self._format_transcript(transcript)
            
            # OpenAI APIで分析
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": f"以下の会議の文字起こしを分析してください：\n\n{formatted_transcript}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=500
            )
            
            # レスポンスをパース
            import json
            result = json.loads(response.choices[0].message.content)
            
            # should_speakがFalseの場合はNoneを返す
            if not result.get("should_speak", False):
                self.logger.info("Marketer Agent: No need to speak")
                return None
            
            # AgentResponseを作成
            agent_response = AgentResponse(
                agent_name=self.name,
                content=result.get("content", ""),
                confidence=result.get("confidence", 0.5),
                urgency=result.get("urgency", 0.5),
                relevance=result.get("relevance", 0.5),
                reasoning=result.get("reasoning", ""),
                should_speak=True
            )
            
            self.logger.info(f"Marketer Agent analysis: priority={agent_response.priority_score:.2f}")
            return agent_response
            
        except Exception as e:
            self.logger.error(f"Error in Marketer Agent analysis: {e}")
            return None
