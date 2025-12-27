"""
LangGraphワークフローのノード実装

各ノードは状態を受け取り、更新して返します。
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import logging

from .state import MeetingState
from ..agents import (
    PMAgent,
    MarketerAgent,
    LegalAgent,
    SalesAgent,
    ConsultantAgent,
    AgentResponse
)

logger = logging.getLogger(__name__)


def check_should_analyze(state: MeetingState) -> MeetingState:
    """
    分析を実行すべきかどうかをチェック
    
    Args:
        state: 現在の状態
        
    Returns:
        MeetingState: 更新された状態
    """
    # 最小文字起こし数
    min_transcript_count = 5
    
    # 分析間隔（文字起こし数）
    analysis_interval = 10
    
    # 最小時間間隔（秒）
    min_time_interval = 30
    
    # 文字起こし数をチェック
    transcript_count = len(state["transcripts"])
    if transcript_count < min_transcript_count:
        logger.debug(f"Transcript count too low: {transcript_count} < {min_transcript_count}")
        return {**state, "should_analyze": False}
    
    # 前回の分析からの増加数をチェック
    new_count = transcript_count - (state["analysis_count"] * analysis_interval)
    if new_count < analysis_interval:
        logger.debug(f"Not enough new transcripts: {new_count} < {analysis_interval}")
        return {**state, "should_analyze": False}
    
    # 時間間隔をチェック
    if state["last_analysis_time"]:
        elapsed = (datetime.now() - state["last_analysis_time"]).total_seconds()
        if elapsed < min_time_interval:
            logger.debug(f"Too soon since last analysis: {elapsed}s < {min_time_interval}s")
            return {**state, "should_analyze": False}
    
    logger.info("Should analyze: conditions met")
    return {**state, "should_analyze": True}


def analyze_with_agents(state: MeetingState) -> MeetingState:
    """
    すべてのエージェントで分析
    
    Args:
        state: 現在の状態
        
    Returns:
        MeetingState: 更新された状態
    """
    if not state["should_analyze"]:
        logger.debug("Skipping analysis: should_analyze is False")
        return state
    
    logger.info("Starting analysis with all agents...")
    
    # エージェントを初期化
    agents = [
        PMAgent(),
        MarketerAgent(),
        LegalAgent(),
        SalesAgent(),
        ConsultantAgent()
    ]
    
    # すべてのエージェントで分析
    agent_responses = []
    for agent in agents:
        try:
            response = agent.analyze(
                transcript=state["transcripts"],
                context={"bot_id": state["bot_id"]}
            )
            if response:
                agent_responses.append(response.to_dict())
                logger.info(f"{agent.name} wants to speak: priority={response.priority_score:.2f}")
        except Exception as e:
            logger.error(f"Error in {agent.name}: {e}")
            state["errors"].append(f"{agent.name}: {str(e)}")
    
    # 状態を更新
    return {
        **state,
        "agent_responses": agent_responses,
        "analysis_count": state["analysis_count"] + 1,
        "last_analysis_time": datetime.now()
    }


def select_best_response(state: MeetingState) -> MeetingState:
    """
    最適な発言を選択
    
    Args:
        state: 現在の状態
        
    Returns:
        MeetingState: 更新された状態
    """
    agent_responses = state.get("agent_responses", [])
    
    if not agent_responses:
        logger.info("No agent responses to select from")
        return {**state, "selected_response": None, "should_post_message": False}
    
    # 優先度スコアでソート
    sorted_responses = sorted(
        agent_responses,
        key=lambda r: r.get("priority_score", 0),
        reverse=True
    )
    
    # 最も優先度の高い発言を選択
    best_response = sorted_responses[0]
    
    # 優先度閾値をチェック
    priority_threshold = 0.6
    if best_response["priority_score"] < priority_threshold:
        logger.info(f"Best response priority too low: {best_response['priority_score']:.2f} < {priority_threshold}")
        return {**state, "selected_response": None, "should_post_message": False}
    
    logger.info(f"Selected: {best_response['agent_name']} (priority={best_response['priority_score']:.2f})")
    
    return {
        **state,
        "selected_response": best_response,
        "should_post_message": True
    }


def post_message_to_chat(state: MeetingState) -> MeetingState:
    """
    チャットにメッセージを投稿
    
    Args:
        state: 現在の状態
        
    Returns:
        MeetingState: 更新された状態
    """
    if not state["should_post_message"] or not state["selected_response"]:
        logger.debug("Skipping message post")
        return state
    
    try:
        from ..bot.recall_client import RecallAPIClient
        from ..utils.config import settings
        
        # メッセージを整形
        response = state["selected_response"]
        icons = {
            "PM Agent": "📊",
            "Marketer Agent": "📈",
            "Legal Agent": "⚖️",
            "Sales Agent": "💼",
            "Consultant Agent": "💡"
        }
        icon = icons.get(response["agent_name"], "🤖")
        message = f"{icon} **{response['agent_name']}**\n\n{response['content']}"
        
        # チャットに投稿
        client = RecallAPIClient(
            api_key=settings.recall_api_key,
            base_url=settings.recall_api_base_url
        )
        
        client.send_chat_message(
            bot_id=state["bot_id"],
            message=message,
            to="everyone"
        )
        
        logger.info("Message posted successfully")
        
        return {
            **state,
            "message_count": state["message_count"] + 1
        }
        
    except Exception as e:
        logger.error(f"Failed to post message: {e}")
        state["errors"].append(f"Post message: {str(e)}")
        return state


def generate_meeting_summary(state: MeetingState) -> MeetingState:
    """
    議事録を生成
    
    Args:
        state: 現在の状態
        
    Returns:
        MeetingState: 更新された状態
    """
    if not state["should_generate_summary"]:
        logger.debug("Skipping summary generation")
        return state
    
    logger.info("Generating meeting summary...")
    
    try:
        from openai import OpenAI
        from ..utils.config import settings
        
        client = OpenAI(api_key=settings.openai_api_key)
        
        # 文字起こしを整形
        transcript_text = "\n".join([
            f"[{t.get('timestamp', '')}] {t.get('speaker', 'Unknown')}: {t.get('text', '')}"
            for t in state["transcripts"]
        ])
        
        # システムプロンプト
        system_prompt = """あなたは優秀な議事録作成アシスタントです。

会議の文字起こしから以下の情報を抽出してください：

1. **会議の要約**: 会議の主要なトピックと議論内容を簡潔にまとめる
2. **決定事項**: 会議で決定されたこと
3. **アクションアイテム**: 誰が何をいつまでにするか

以下のJSON形式で回答してください：

```json
{
  "summary": "会議の要約（200-300文字）",
  "decisions": [
    {"content": "決定事項1", "timestamp": "タイムスタンプ"},
    {"content": "決定事項2", "timestamp": "タイムスタンプ"}
  ],
  "action_items": [
    {"task": "タスク内容", "assignee": "担当者", "due_date": "期限", "timestamp": "タイムスタンプ"},
    {"task": "タスク内容", "assignee": "担当者", "due_date": "期限", "timestamp": "タイムスタンプ"}
  ]
}
```

決定事項やアクションアイテムがない場合は空の配列を返してください。"""
        
        # OpenAI APIで議事録を生成
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下の会議の文字起こしから議事録を作成してください：\n\n{transcript_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500
        )
        
        # レスポンスをパース
        import json
        result = json.loads(response.choices[0].message.content)
        
        logger.info("Meeting summary generated successfully")
        
        return {
            **state,
            "meeting_summary": result.get("summary", ""),
            "decisions": result.get("decisions", []),
            "action_items": result.get("action_items", [])
        }
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        state["errors"].append(f"Generate summary: {str(e)}")
        return state
