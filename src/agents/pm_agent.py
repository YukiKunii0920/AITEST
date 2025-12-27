"""
PMエージェント

プロジェクト管理の視点で会議を分析し、リスクや課題を検知します。
"""

from typing import Dict, Any, Optional, List
import logging
from openai import OpenAI

from .base_agent import BaseAgent, AgentResponse
from ..utils.config import settings

logger = logging.getLogger(__name__)


class PMAgent(BaseAgent):
    """PMエージェント"""
    
    def __init__(self):
        super().__init__(
            name="PM Agent",
            role="プロジェクトマネージャー",
            expertise="進捗管理、リスク管理、リソース管理、スケジュール管理"
        )
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを取得"""
        return """あなたは経験豊富なプロジェクトマネージャーです。

【あなたの役割】
会議の議論を分析し、プロジェクト管理の観点から以下の点をチェックしてください：

1. **スケジュールリスク**: 遅延の兆候、締め切りへの言及、タスクの積み残し
2. **リソース不足**: 人員不足、予算不足、ツール・設備の不足
3. **スコープクリープ**: 当初の計画からの逸脱、要件の追加
4. **決定事項の未記録**: 重要な決定が曖昧なまま進行
5. **依存関係の問題**: ブロッカー、他チームへの依存
6. **コミュニケーション不足**: 情報共有の欠如、認識のズレ

【発言基準】
以下の場合のみ発言してください：
- 明確なリスクや問題を検知した場合
- 重要な決定事項が曖昧なまま進行している場合
- スケジュールやリソースに関する懸念がある場合

【発言しない場合】
- 議論が順調に進んでいる場合
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
                self.logger.info("PM Agent: No need to speak")
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
            
            self.logger.info(f"PM Agent analysis: priority={agent_response.priority_score:.2f}")
            return agent_response
            
        except Exception as e:
            self.logger.error(f"Error in PM Agent analysis: {e}")
            return None
