"""
LangGraphワークフローの統合テスト

ワークフローが正しく動作するかをテストします。
"""

import sys
from pathlib import Path
import asyncio
import logging

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow import MeetingState, create_initial_state, get_workflow
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def test_workflow():
    """ワークフローをテスト"""
    
    logger.info("=" * 80)
    logger.info("Testing LangGraph Workflow")
    logger.info("=" * 80)
    
    # 初期状態を作成
    state = create_initial_state(
        bot_id="test_bot_123",
        meeting_url="https://meet.google.com/test",
        meeting_title="Test Meeting"
    )
    
    # テスト用の文字起こしを追加
    test_transcripts = [
        {"speaker": "Alice", "text": "新機能の開発、いつまでに完成しますか？", "timestamp": "2024-01-01T10:00:00"},
        {"speaker": "Bob", "text": "うーん、まだ決まってないですね", "timestamp": "2024-01-01T10:00:10"},
        {"speaker": "Alice", "text": "じゃあ、とりあえず進めましょう", "timestamp": "2024-01-01T10:00:20"},
        {"speaker": "Bob", "text": "はい、わかりました", "timestamp": "2024-01-01T10:00:30"},
        {"speaker": "Alice", "text": "この機能、技術的には実装できます", "timestamp": "2024-01-01T10:01:00"},
        {"speaker": "Bob", "text": "じゃあ、追加しましょう", "timestamp": "2024-01-01T10:01:10"},
        {"speaker": "Alice", "text": "顧客は何を求めているんでしょうか？", "timestamp": "2024-01-01T10:01:20"},
        {"speaker": "Bob", "text": "それは考えていませんでした", "timestamp": "2024-01-01T10:01:30"},
        {"speaker": "Alice", "text": "競合のデザインを参考にしましょう", "timestamp": "2024-01-01T10:02:00"},
        {"speaker": "Bob", "text": "そのまま真似してもいいですか？", "timestamp": "2024-01-01T10:02:10"},
        {"speaker": "Alice", "text": "はい、問題ないと思います", "timestamp": "2024-01-01T10:02:20"},
    ]
    
    state["transcripts"] = test_transcripts
    
    logger.info(f"Added {len(test_transcripts)} test transcripts")
    
    # ワークフローを取得
    workflow = get_workflow()
    
    logger.info("Running workflow...")
    
    # ワークフローを実行
    try:
        result = workflow.invoke(state)
        
        logger.info("=" * 80)
        logger.info("Workflow completed successfully!")
        logger.info("=" * 80)
        logger.info(f"Analysis count: {result['analysis_count']}")
        logger.info(f"Message count: {result['message_count']}")
        logger.info(f"Should analyze: {result['should_analyze']}")
        logger.info(f"Should post message: {result['should_post_message']}")
        
        if result.get("selected_response"):
            response = result["selected_response"]
            logger.info("=" * 80)
            logger.info("Selected Response:")
            logger.info(f"  Agent: {response['agent_name']}")
            logger.info(f"  Content: {response['content']}")
            logger.info(f"  Confidence: {response['confidence']:.2f}")
            logger.info(f"  Urgency: {response['urgency']:.2f}")
            logger.info(f"  Relevance: {response['relevance']:.2f}")
            logger.info(f"  Priority Score: {response['priority_score']:.2f}")
            logger.info("=" * 80)
        else:
            logger.info("No response selected")
        
        if result.get("errors"):
            logger.warning("=" * 80)
            logger.warning("Errors:")
            for error in result["errors"]:
                logger.warning(f"  - {error}")
            logger.warning("=" * 80)
        
        # 議事録生成をテスト
        logger.info("Testing meeting summary generation...")
        result["should_generate_summary"] = True
        
        from src.workflow.nodes import generate_meeting_summary
        result = generate_meeting_summary(result)
        
        if result.get("meeting_summary"):
            logger.info("=" * 80)
            logger.info("Meeting Summary:")
            logger.info(result["meeting_summary"])
            logger.info("=" * 80)
            
            if result.get("decisions"):
                logger.info("Decisions:")
                for i, decision in enumerate(result["decisions"], 1):
                    logger.info(f"  {i}. {decision.get('content', '')}")
                logger.info("=" * 80)
            
            if result.get("action_items"):
                logger.info("Action Items:")
                for i, item in enumerate(result["action_items"], 1):
                    logger.info(f"  {i}. {item.get('task', '')} (担当: {item.get('assignee', 'N/A')}, 期限: {item.get('due_date', 'N/A')})")
                logger.info("=" * 80)
        
        logger.info("✅ All tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}", exc_info=True)
        raise


def main():
    """メイン関数"""
    # ロギング設定
    setup_logging(log_level="INFO")
    
    # テストを実行
    asyncio.run(test_workflow())


if __name__ == "__main__":
    main()
