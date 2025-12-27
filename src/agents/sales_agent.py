"""
営業エージェント

売上・顧客関係の視点で会議を分析し、機会やリスクを検知します。
"""

from typing import Dict, Any, Optional, List
import logging
from openai import OpenAI

from .base_agent import BaseAgent, AgentResponse
from ..utils.config import settings

logger = logging.getLogger(__name__)


class SalesAgent(BaseAgent):
    """営業エージェント"""
    
    def __init__(self):
        super().__init__(
            name="Sales Agent",
            role="営業担当",
            expertise="売上管理、顧客関係、商談、クロージング"
        )
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは経験豊富な営業担当者です。

【あなたの役割】
会議の議論を分析し、営業の観点から以下の点をチェックしてください：

1. **売上機会**: アップセル、クロスセル、新規案件の可能性
2. **顧客満足度**: 顧客の不満、期待とのギャップ
3. **競合との差別化**: 競合優位性、独自の価値提案
4. **価格戦略**: 価格設定、値引き、ROI
5. **顧客関係**: 信頼関係、長期的なパートナーシップ
6. **チャーンリスク**: 解約の兆候、顧客離れの可能性

【発言基準】
以下の場合のみ発言してください：
- 明確な売上機会を発見した場合
- 顧客満足度への悪影響が懸念される場合
- チャーンリスクや競合への流出リスクがある場合

【発言しない場合】
- 議論が顧客満足度を重視して進んでいる場合
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
                self.logger.info("Sales Agent: No need to speak")
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
            
            self.logger.info(f"Sales Agent analysis: priority={agent_response.priority_score:.2f}")
            return agent_response
            
        except Exception as e:
            self.logger.error(f"Error in Sales Agent analysis: {e}")
            return None
