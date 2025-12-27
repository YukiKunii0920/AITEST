"""
コンサルタントエージェント

論理構成・課題解決の視点で会議を分析し、改善点を提案します。
"""

from typing import Dict, Any, Optional, List
import logging
from openai import OpenAI

from .base_agent import BaseAgent, AgentResponse
from ..utils.config import settings

logger = logging.getLogger(__name__)


class ConsultantAgent(BaseAgent):
    """コンサルタントエージェント"""
    
    def __init__(self):
        super().__init__(
            name="Consultant Agent",
            role="コンサルタント",
            expertise="論理思考、問題解決、フレームワーク、意思決定"
        )
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは経験豊富なビジネスコンサルタントです。

【あなたの役割】
会議の議論を分析し、コンサルティングの観点から以下の点をチェックしてください：

1. **論理的整合性**: 議論の論理構成、因果関係の妥当性
2. **MECE**: 漏れなくダブりなく、網羅性と排他性
3. **フレームワーク**: 3C、SWOT、5W1H等の活用可能性
4. **意思決定の構造化**: 選択肢の整理、評価基準の明確化
5. **課題の本質**: 表面的な症状ではなく根本原因の特定
6. **優先順位付け**: 重要度と緊急度のマトリクス

【発言基準】
以下の場合のみ発言してください：
- 議論の論理構成に問題がある場合
- 重要な視点や選択肢が抜けている場合（MECE違反）
- 意思決定が構造化されていない場合

【発言しない場合】
- 議論が論理的で構造化されている場合
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
                self.logger.info("Consultant Agent: No need to speak")
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
            
            self.logger.info(f"Consultant Agent analysis: priority={agent_response.priority_score:.2f}")
            return agent_response
            
        except Exception as e:
            self.logger.error(f"Error in Consultant Agent analysis: {e}")
            return None
