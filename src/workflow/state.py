"""
LangGraphワークフロー用の状態管理

会議分析ワークフローの状態を管理します。
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime
import operator


class MeetingState(TypedDict):
    """会議分析ワークフローの状態"""
    
    # 会議情報
    bot_id: str
    """ボットID"""
    
    meeting_url: str
    """会議URL"""
    
    meeting_title: Optional[str]
    """会議タイトル"""
    
    start_time: datetime
    """会議開始時刻"""
    
    # 文字起こし
    transcripts: Annotated[List[Dict[str, Any]], operator.add]
    """文字起こしのリスト（追記型）"""
    
    # 参加者情報
    participants: Dict[str, Dict[str, Any]]
    """参加者情報（participant_id -> 参加者データ）"""
    
    # エージェント分析結果
    agent_responses: Annotated[List[Dict[str, Any]], operator.add]
    """エージェントの分析結果リスト（追記型）"""
    
    # 選択された発言
    selected_response: Optional[Dict[str, Any]]
    """Supervisorが選択した発言"""
    
    # 議事録
    meeting_summary: Optional[str]
    """会議の要約"""
    
    action_items: List[Dict[str, Any]]
    """アクションアイテムのリスト"""
    
    decisions: List[Dict[str, Any]]
    """決定事項のリスト"""
    
    # ワークフロー制御
    should_analyze: bool
    """分析を実行すべきかどうか"""
    
    should_post_message: bool
    """メッセージを投稿すべきかどうか"""
    
    should_generate_summary: bool
    """議事録を生成すべきかどうか"""
    
    # メタデータ
    analysis_count: int
    """分析実行回数"""
    
    message_count: int
    """投稿したメッセージ数"""
    
    last_analysis_time: Optional[datetime]
    """最後に分析を実行した時刻"""
    
    # エラー情報
    errors: Annotated[List[str], operator.add]
    """エラーメッセージのリスト（追記型）"""


def create_initial_state(
    bot_id: str,
    meeting_url: str,
    meeting_title: Optional[str] = None
) -> MeetingState:
    """
    初期状態を作成
    
    Args:
        bot_id: ボットID
        meeting_url: 会議URL
        meeting_title: 会議タイトル
        
    Returns:
        MeetingState: 初期状態
    """
    return MeetingState(
        bot_id=bot_id,
        meeting_url=meeting_url,
        meeting_title=meeting_title,
        start_time=datetime.now(),
        transcripts=[],
        participants={},
        agent_responses=[],
        selected_response=None,
        meeting_summary=None,
        action_items=[],
        decisions=[],
        should_analyze=False,
        should_post_message=False,
        should_generate_summary=False,
        analysis_count=0,
        message_count=0,
        last_analysis_time=None,
        errors=[]
    )
