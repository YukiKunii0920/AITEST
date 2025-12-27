"""
LangGraphワークフローのグラフ定義

会議分析ワークフローをLangGraphで構築します。
"""

from typing import Literal
import logging
from langgraph.graph import StateGraph, END

from .state import MeetingState, create_initial_state
from .nodes import (
    check_should_analyze,
    analyze_with_agents,
    select_best_response,
    post_message_to_chat,
    generate_meeting_summary
)

logger = logging.getLogger(__name__)


def should_analyze_router(state: MeetingState) -> Literal["analyze", "end"]:
    """
    分析を実行すべきかどうかをルーティング
    
    Args:
        state: 現在の状態
        
    Returns:
        str: 次のノード名
    """
    if state["should_analyze"]:
        return "analyze"
    else:
        return "end"


def should_post_router(state: MeetingState) -> Literal["post", "end"]:
    """
    メッセージを投稿すべきかどうかをルーティング
    
    Args:
        state: 現在の状態
        
    Returns:
        str: 次のノード名
    """
    if state["should_post_message"]:
        return "post"
    else:
        return "end"


def create_meeting_workflow() -> StateGraph:
    """
    会議分析ワークフローを作成
    
    Returns:
        StateGraph: ワークフローグラフ
    """
    # グラフを作成
    workflow = StateGraph(MeetingState)
    
    # ノードを追加
    workflow.add_node("check", check_should_analyze)
    workflow.add_node("analyze", analyze_with_agents)
    workflow.add_node("select", select_best_response)
    workflow.add_node("post", post_message_to_chat)
    workflow.add_node("summary", generate_meeting_summary)
    
    # エッジを追加
    workflow.set_entry_point("check")
    
    # 条件分岐: 分析すべきかどうか
    workflow.add_conditional_edges(
        "check",
        should_analyze_router,
        {
            "analyze": "analyze",
            "end": END
        }
    )
    
    # 分析 -> 選択
    workflow.add_edge("analyze", "select")
    
    # 条件分岐: 投稿すべきかどうか
    workflow.add_conditional_edges(
        "select",
        should_post_router,
        {
            "post": "post",
            "end": END
        }
    )
    
    # 投稿 -> 終了
    workflow.add_edge("post", END)
    
    logger.info("Meeting workflow created")
    
    return workflow


def compile_workflow() -> StateGraph:
    """
    ワークフローをコンパイル
    
    Returns:
        StateGraph: コンパイル済みワークフロー
    """
    workflow = create_meeting_workflow()
    compiled = workflow.compile()
    logger.info("Workflow compiled successfully")
    return compiled


# グローバル変数としてコンパイル済みワークフローを保持
_compiled_workflow = None


def get_workflow() -> StateGraph:
    """
    コンパイル済みワークフローを取得（シングルトン）
    
    Returns:
        StateGraph: コンパイル済みワークフロー
    """
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = compile_workflow()
    return _compiled_workflow
