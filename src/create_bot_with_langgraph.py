"""
LangGraphワークフロー対応ボット作成スクリプト

ボットを作成し、LangGraphワークフローを使用した分析を有効化します。
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.bot.recall_client import RecallAPIClient
from src.utils.config import settings
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def create_bot_with_langgraph(
    meeting_url: str,
    bot_name: str = "AI Meeting Assistant (LangGraph)",
    webhook_url: str = None,
    join_delay_minutes: int = 0,
    enable_chat_greeting: bool = True
):
    """
    ボットを作成して会議に参加させる（LangGraphワークフロー対応）
    
    Args:
        meeting_url: 会議URL
        bot_name: ボット名
        webhook_url: Webhook URL（Noneの場合は設定から取得）
        join_delay_minutes: 参加遅延時間（分）
        enable_chat_greeting: 参加時の挨拶メッセージを有効化
    """
    # Webhook URLを決定
    if webhook_url is None:
        webhook_url = f"{settings.webhook_public_url}/webhook/recall"
    
    logger.info("=" * 80)
    logger.info("Creating Recall.ai Bot with LangGraph Workflow")
    logger.info("=" * 80)
    logger.info(f"Meeting URL: {meeting_url}")
    logger.info(f"Bot Name: {bot_name}")
    logger.info(f"Webhook URL: {webhook_url}")
    logger.info("=" * 80)
    logger.info("LangGraph Workflow Features:")
    logger.info("  ✅ Conditional branching (条件分岐)")
    logger.info("  ✅ State management (状態管理)")
    logger.info("  ✅ Multi-agent coordination (マルチエージェント協調)")
    logger.info("  ✅ Automatic meeting summary (自動議事録生成)")
    logger.info("  ✅ Action item extraction (アクションアイテム抽出)")
    logger.info("=" * 80)
    logger.info("Multi-Agent System:")
    logger.info("  📊 PM Agent - プロジェクト管理の視点")
    logger.info("  📈 Marketer Agent - 市場・顧客の視点")
    logger.info("  ⚖️  Legal Agent - 法務・コンプライアンスの視点")
    logger.info("  💼 Sales Agent - 売上・顧客関係の視点")
    logger.info("  💡 Consultant Agent - 論理構成・課題解決の視点")
    logger.info("=" * 80)
    
    # APIクライアントを初期化
    client = RecallAPIClient(
        api_key=settings.recall_api_key,
        base_url=settings.recall_api_base_url
    )
    
    try:
        # 参加時刻を計算
        join_at = None
        if join_delay_minutes > 0:
            join_at = datetime.now() + timedelta(minutes=join_delay_minutes)
            logger.info(f"Scheduled join time: {join_at.isoformat()}")
        
        # 挨拶メッセージ（LangGraphワークフロー版）
        chat_message = None
        if enable_chat_greeting:
            chat_message = (
                "🤖 **AI Meeting Assistant (LangGraph)** が会議に参加しました。\n\n"
                "この会議はLangGraphワークフローを使用した高度なAIシステムによって分析されます：\n\n"
                "**特徴:**\n"
                "✅ 条件分岐による動的な分析\n"
                "✅ ステートフルな会議管理\n"
                "✅ 5つの専門家AIエージェント\n"
                "✅ 自動議事録生成\n"
                "✅ アクションアイテム抽出\n\n"
                "重要な指摘がある場合、適切なタイミングでアドバイスを提供します。"
            )
        
        # ボットを作成
        bot_data = client.create_bot(
            meeting_url=meeting_url,
            bot_name=bot_name,
            webhook_url=webhook_url,
            enable_transcript=True,
            transcript_provider="recallai_streaming",
            language="ja",
            join_at=join_at,
            chat_on_join_message=chat_message
        )
        
        bot_id = bot_data.get("id")
        status = bot_data.get("status", {})
        
        logger.info("=" * 80)
        logger.info("✅ Bot created successfully!")
        logger.info("=" * 80)
        logger.info(f"Bot ID: {bot_id}")
        logger.info(f"Status: {status}")
        logger.info("=" * 80)
        logger.info("次のステップ:")
        logger.info("1. LangGraphワークフロー対応Webhookサーバーが起動していることを確認:")
        logger.info("   python src/main_with_langgraph.py")
        logger.info("")
        logger.info("2. ボットの状態を確認:")
        logger.info(f"   python src/get_bot_status.py {bot_id}")
        logger.info("")
        logger.info("3. 会議で話すと、LangGraphワークフローが自動的に実行されます")
        logger.info("")
        logger.info("4. 統計情報を確認:")
        logger.info(f"   curl {settings.webhook_public_url}/statistics")
        logger.info("")
        logger.info("5. 会議終了後、議事録を生成:")
        logger.info(f"   curl -X POST {settings.webhook_public_url}/generate_summary/{bot_id}")
        logger.info("=" * 80)
        
        # ボットIDをファイルに保存
        bot_id_file = project_root / "config" / "current_bot_id.txt"
        bot_id_file.parent.mkdir(parents=True, exist_ok=True)
        bot_id_file.write_text(bot_id)
        logger.info(f"Bot ID saved to: {bot_id_file}")
        
        return bot_data
        
    except Exception as e:
        logger.error(f"❌ Failed to create bot: {e}")
        raise
    finally:
        client.close()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Create a Recall.ai bot with LangGraph Workflow"
    )
    parser.add_argument(
        "meeting_url",
        help="Meeting URL (Google Meet, Teams, Zoom)"
    )
    parser.add_argument(
        "--name",
        default="AI Meeting Assistant (LangGraph)",
        help="Bot name (default: AI Meeting Assistant (LangGraph))"
    )
    parser.add_argument(
        "--webhook-url",
        help="Webhook URL (default: from config)"
    )
    parser.add_argument(
        "--join-delay",
        type=int,
        default=0,
        help="Delay before joining in minutes (default: 0, join immediately)"
    )
    parser.add_argument(
        "--no-greeting",
        action="store_true",
        help="Disable greeting message on join"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # ロギング設定
    setup_logging(log_level=args.log_level)
    
    # ボットを作成
    create_bot_with_langgraph(
        meeting_url=args.meeting_url,
        bot_name=args.name,
        webhook_url=args.webhook_url,
        join_delay_minutes=args.join_delay,
        enable_chat_greeting=not args.no_greeting
    )


if __name__ == "__main__":
    main()
