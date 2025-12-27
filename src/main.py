"""
メインアプリケーション

Webhookサーバーを起動し、Recall.aiからのイベントを受信します。
"""

import asyncio
import uvicorn
import logging
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import settings
from src.utils.logger import setup_logging
from src.bot.webhook_server import app, get_webhook_handler

logger = logging.getLogger(__name__)


async def example_transcript_handler(text: str, participant: dict, is_partial: bool):
    """
    文字起こしイベントハンドラーの例
    
    将来的には、ここでLangGraphのマルチエージェントを呼び出します。
    """
    if not is_partial:
        # 確定した文字起こしのみ処理
        participant_name = participant.get("name", "Unknown")
        logger.info(f"[HANDLER] {participant_name}: {text}")
        
        # TODO: ここでマルチエージェント分析を実行
        # - PMエージェント: リスク検知
        # - マーケターエージェント: 市場機会の指摘
        # - 法務エージェント: コンプライアンスチェック
        # - 営業エージェント: 売上機会の提案
        # - コンサルタントエージェント: 論理構成の評価


async def example_participant_handler(event_type: str, participant: dict):
    """参加者イベントハンドラーの例"""
    participant_name = participant.get("name", "Unknown")
    logger.info(f"[HANDLER] Participant event: {event_type} - {participant_name}")


async def example_chat_handler(message: str, participant: dict):
    """チャットイベントハンドラーの例"""
    participant_name = participant.get("name", "Unknown")
    logger.info(f"[HANDLER] Chat from {participant_name}: {message}")


def main():
    """メイン関数"""
    # ロギング設定
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file
    )
    
    logger.info("=" * 80)
    logger.info("Meeting AI Agent System - Webhook Server")
    logger.info("=" * 80)
    logger.info(f"Webhook URL: {settings.webhook_public_url}/webhook/recall")
    logger.info(f"Status endpoint: {settings.webhook_public_url}/status")
    logger.info(f"Transcript endpoint: {settings.webhook_public_url}/transcript")
    logger.info("=" * 80)
    
    # Webhookハンドラーにカスタムハンドラーを登録
    webhook_handler = get_webhook_handler()
    webhook_handler.register_transcript_handler(example_transcript_handler)
    webhook_handler.register_participant_handler(example_participant_handler)
    webhook_handler.register_chat_handler(example_chat_handler)
    
    # Uvicornサーバーを起動
    uvicorn.run(
        app,
        host=settings.webhook_host,
        port=settings.webhook_port,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
