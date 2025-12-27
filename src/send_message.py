"""
チャットメッセージ送信スクリプト

ボットから会議のチャットにメッセージを送信します。
"""

import sys
import argparse
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.bot.recall_client import RecallAPIClient
from src.utils.config import settings
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def send_message(bot_id: str, message: str, to: str = "everyone", pin: bool = False):
    """
    チャットメッセージを送信
    
    Args:
        bot_id: ボットID
        message: メッセージ内容
        to: 送信先（"everyone", "host", participant_id）
        pin: メッセージをピン留めするか
    """
    logger.info(f"Sending message from bot: {bot_id}")
    logger.info(f"Message: {message}")
    logger.info(f"To: {to}")
    logger.info(f"Pin: {pin}")
    
    # APIクライアントを初期化
    client = RecallAPIClient(
        api_key=settings.recall_api_key,
        base_url=settings.recall_api_base_url
    )
    
    try:
        # メッセージを送信
        result = client.send_chat_message(
            bot_id=bot_id,
            message=message,
            to=to,
            pin=pin
        )
        
        logger.info("=" * 80)
        logger.info("✅ Message sent successfully!")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}")
        raise
    finally:
        client.close()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Send a chat message from Recall.ai bot"
    )
    parser.add_argument(
        "bot_id",
        help="Bot ID"
    )
    parser.add_argument(
        "message",
        help="Message to send"
    )
    parser.add_argument(
        "--to",
        default="everyone",
        help="Recipient (default: everyone)"
    )
    parser.add_argument(
        "--pin",
        action="store_true",
        help="Pin the message (Google Meet and Teams only)"
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
    
    # メッセージを送信
    send_message(
        bot_id=args.bot_id,
        message=args.message,
        to=args.to,
        pin=args.pin
    )


if __name__ == "__main__":
    main()
