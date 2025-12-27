"""
マルチエージェント統合版メインアプリケーション

Webhookサーバーを起動し、マルチエージェントシステムと統合します。
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
from src.agents import MeetingAnalyzer

logger = logging.getLogger(__name__)


# グローバル変数（ボットIDごとのMeetingAnalyzer）
meeting_analyzers: dict[str, MeetingAnalyzer] = {}


def auto_register_bot_id():
    """保存されたボットIDを自動登録"""
    bot_id_file = Path(__file__).parent.parent / "config" / "current_bot_id.txt"
    if bot_id_file.exists():
        bot_id = bot_id_file.read_text().strip()
        if bot_id:
            register_meeting_analyzer(bot_id)
            logger.info(f"Auto-registered bot ID from file: {bot_id}")
        else:
            logger.warning("Bot ID file is empty")
    else:
        logger.warning(f"Bot ID file not found: {bot_id_file}")


async def transcript_handler_with_agents(text: str, participant: dict, is_partial: bool):
    """
    マルチエージェント統合版の文字起こしハンドラー
    
    Args:
        text: 文字起こしテキスト
        participant: 話者情報
        is_partial: 部分的な文字起こしかどうか
    """
    # 確定した文字起こしのみログ出力
    if not is_partial:
        participant_name = participant.get("name", "Unknown")
        logger.info(f"[TRANSCRIPT] {participant_name}: {text}")
    
    # ボットIDを取得（contextから取得する必要があるが、ここでは簡略化）
    # 実際の実装では、Webhookペイロードからbot_idを取得
    # 今回は環境変数または最初に作成したボットIDを使用
    
    # すべてのMeetingAnalyzerに処理させる
    for bot_id, analyzer in meeting_analyzers.items():
        try:
            await analyzer.process_transcript(text, participant, is_partial)
        except Exception as e:
            logger.error(f"Error in MeetingAnalyzer for bot {bot_id}: {e}")


async def participant_handler(event_type: str, participant: dict):
    """参加者イベントハンドラー"""
    participant_name = participant.get("name", "Unknown")
    logger.info(f"[PARTICIPANT] {event_type}: {participant_name}")


async def chat_handler(message: str, participant: dict):
    """チャットイベントハンドラー"""
    participant_name = participant.get("name", "Unknown")
    logger.info(f"[CHAT] {participant_name}: {message}")


def register_meeting_analyzer(bot_id: str):
    """
    MeetingAnalyzerを登録
    
    Args:
        bot_id: ボットID
    """
    if bot_id not in meeting_analyzers:
        analyzer = MeetingAnalyzer(
            bot_id=bot_id,
            min_transcript_count=5,  # 最低5件の発言で分析開始
            analysis_interval=10  # 10件ごとに分析
        )
        meeting_analyzers[bot_id] = analyzer
        logger.info(f"Registered MeetingAnalyzer for bot {bot_id}")
    else:
        logger.warning(f"MeetingAnalyzer already registered for bot {bot_id}")


def main():
    """メイン関数"""
    # ロギング設定
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file
    )
    
    logger.info("=" * 80)
    logger.info("Meeting AI Agent System - Multi-Agent Webhook Server")
    logger.info("=" * 80)
    logger.info(f"Webhook URL: {settings.webhook_public_url}/webhook/recall")
    logger.info(f"Status endpoint: {settings.webhook_public_url}/status")
    logger.info(f"Transcript endpoint: {settings.webhook_public_url}/transcript")
    logger.info("=" * 80)
    logger.info("Multi-Agent System:")
    logger.info("  - PM Agent (プロジェクト管理)")
    logger.info("  - Marketer Agent (市場・顧客)")
    logger.info("  - Legal Agent (法務・コンプライアンス)")
    logger.info("  - Sales Agent (売上・顧客関係)")
    logger.info("  - Consultant Agent (論理構成・課題解決)")
    logger.info("=" * 80)
    
    # Webhookハンドラーにカスタムハンドラーを登録
    webhook_handler = get_webhook_handler()
    webhook_handler.register_transcript_handler(transcript_handler_with_agents)
    webhook_handler.register_participant_handler(participant_handler)
    webhook_handler.register_chat_handler(chat_handler)
    
    # 保存されたボットIDを自動登録
    auto_register_bot_id()
    
    if not meeting_analyzers:
        logger.warning("=" * 80)
        logger.warning("警告: MeetingAnalyzerが登録されていません")
        logger.warning("先にボットを作成してください:")
        logger.warning("  python src/create_bot_with_agents.py <meeting_url>")
        logger.warning("=" * 80)
    
    # Uvicornサーバーを起動
    uvicorn.run(
        app,
        host=settings.webhook_host,
        port=settings.webhook_port,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
