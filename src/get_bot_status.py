"""
ボット状態確認スクリプト

ボットの現在の状態を取得して表示します。
"""

import sys
import argparse
import logging
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.bot.recall_client import RecallAPIClient
from src.utils.config import settings
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def get_bot_status(bot_id: str):
    """
    ボットの状態を取得
    
    Args:
        bot_id: ボットID
    """
    logger.info(f"Fetching status for bot: {bot_id}")
    
    # APIクライアントを初期化
    client = RecallAPIClient(
        api_key=settings.recall_api_key,
        base_url=settings.recall_api_base_url
    )
    
    try:
        # ボット情報を取得
        bot_data = client.get_bot(bot_id)
        
        # 主要な情報を抽出
        bot_id = bot_data.get("id")
        status = bot_data.get("status_changes", [])
        current_status = status[-1].get("code") if status else "unknown"
        meeting_url = bot_data.get("meeting_url")
        bot_name = bot_data.get("bot_name")
        
        # 結果を表示
        logger.info("=" * 80)
        logger.info("Bot Status")
        logger.info("=" * 80)
        logger.info(f"Bot ID: {bot_id}")
        logger.info(f"Bot Name: {bot_name}")
        logger.info(f"Current Status: {current_status}")
        logger.info(f"Meeting URL: {meeting_url}")
        logger.info("=" * 80)
        logger.info("Status History:")
        for change in status:
            code = change.get("code")
            timestamp = change.get("created_at")
            logger.info(f"  - {timestamp}: {code}")
        logger.info("=" * 80)
        
        # 詳細情報をJSON形式で出力
        logger.debug("Full bot data:")
        logger.debug(json.dumps(bot_data, indent=2, ensure_ascii=False))
        
        return bot_data
        
    except Exception as e:
        logger.error(f"❌ Failed to get bot status: {e}")
        raise
    finally:
        client.close()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Get Recall.ai bot status"
    )
    parser.add_argument(
        "bot_id",
        help="Bot ID"
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
    
    # ボット状態を取得
    get_bot_status(args.bot_id)


if __name__ == "__main__":
    main()
