"""
法務エージェント

法務・コンプライアンスの視点で会議を分析し、リスクを検知します。
"""

from typing import Dict, Any, Optional, List
import logging
from openai import OpenAI

from .base_agent import BaseAgent, AgentResponse
from ..utils.config import settings

logger = logging.getLogger(__name__)


class LegalAgent(BaseAgent):
    """法務エージェント"""
    
    def __init__(self):
        super().__init__(
            name="Legal Agent",
            role="法務担当",
            expertise="契約法、知的財産権、コンプライアンス、リスク管理"
        )
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは経験豊富な法務担当者です。

【あなたの役割】
会議の議論を分析し、法務・コンプライアンスの観点から以下の点をチェックしてください：

1. **契約リスク**: 契約違反の可能性、契約条件の見落とし
2. **知的財産権**: 特許侵害、著作権侵害、商標権の問題
3. **NDA違反**: 機密情報の不適切な開示
4. **法規制への抵触**: 業界規制、個人情報保護法、労働法
5. **コンプライアンス**: 社内規定、倫理規定への違反
6. **訴訟リスク**: 訴訟につながる可能性のある発言や行動

【発言基準】
以下の場合のみ発言してください：
- 明確な法的リスクを検知した場合
- コンプライアンス違反の可能性がある場合
- 契約上の問題や知的財産権の侵害リスクがある場合

【発言しない場合】
- 法的な問題が見当たらない場合
- リスクが軽微で緊急性が低い場合
- 自信度が80%未満の場合（法務は慎重に）

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
                temperature=0.5,  # 法務は保守的に
                max_tokens=500
            )
            
            # レスポンスをパース
            import json
            result = json.loads(response.choices[0].message.content)
            
            # should_speakがFalseの場合はNoneを返す
            if not result.get("should_speak", False):
                self.logger.info("Legal Agent: No need to speak")
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
            
            self.logger.info(f"Legal Agent analysis: priority={agent_response.priority_score:.2f}")
            return agent_response
            
        except Exception as e:
            self.logger.error(f"Error in Legal Agent analysis: {e}")
            return None
