"""
RAG対応ボット作成スクリプト

Google MeetまたはTeamsの会議にボットを参加させます。
"""

import sys
import asyncio
import logging
from pathlib import Path

from bot.recall_client import RecallAPIClient
from utils.config import settings
from utils.logger import setup_logging

# ロギング設定
setup_logging()
logger = logging.getLogger(__name__)


async def create_bot(meeting_url: str, bot_name: str = "AI Meeting Assistant"):
    """
    ボットを作成して会議に参加
    
    Args:
        meeting_url: 会議URL
        bot_name: ボット名
    """
    try:
        # Recall.ai APIクライアント
        client = RecallAPIClient(
            api_key=settings.recall_api_key,
            base_url=settings.recall_api_base_url
        )
        
        logger.info(f"Creating bot for meeting: {meeting_url}")
        
        # ボットを作成
        bot = await client.create_bot(
            meeting_url=meeting_url,
            bot_name=bot_name,
            transcription_options={
                "provider": "meeting_captions"
            },
            chat={
                "on_bot_join": {
                    "send_to": "everyone",
                    "message": f"こんにちは！{bot_name}です。会議の議論を分析して、専門家の視点からアドバイスを提供します。RAG（検索拡張生成）により、過去の類似会議も参照します。"
                }
            },
            automatic_leave={
                "waiting_room_timeout": 600,
                "noone_joined_timeout": 600
            },
            real_time_transcription={
                "destination_url": f"{settings.webhook_public_url}/webhook/bot.transcript",
                "partial_results": False
            },
            automatic_video_output={
                "in_call_recording": {
                    "kind": "in_call_recording",
                    "b64_data": ""  # オプション: カスタム画像
                }
            }
        )
        
        bot_id = bot.get("id")
        logger.info(f"Bot created successfully: {bot_id}")
        logger.info(f"Bot status: {bot.get('status_changes', [])[-1] if bot.get('status_changes') else 'unknown'}")
        
        # ボットIDをファイルに保存
        bot_id_file = Path("config/current_bot_id.txt")
        bot_id_file.parent.mkdir(parents=True, exist_ok=True)
        bot_id_file.write_text(bot_id)
        logger.info(f"Bot ID saved to {bot_id_file}")
        
        # ボットを登録（Webhookサーバーに通知）
        import httpx
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"http://localhost:{settings.webhook_port}/bot/register",
                    params={
                        "bot_id": bot_id,
                        "meeting_url": meeting_url,
                        "meeting_title": f"Meeting {bot_id[:8]}"
                    }
                )
                if response.status_code == 200:
                    logger.info("Bot registered with webhook server")
                else:
                    logger.warning(f"Failed to register bot with webhook server: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not register bot with webhook server: {e}")
        
        print("\n" + "="*80)
        print("✅ ボットが会議に参加しました！")
        print("="*80)
        print(f"Bot ID: {bot_id}")
        print(f"会議URL: {meeting_url}")
        print(f"ボット名: {bot_name}")
        print(f"RAG: 有効")
        print("\n次のステップ:")
        print("1. 会議で話してください")
        print("2. AIエージェントが自動的に分析してアドバイスを投稿します")
        print("3. 過去の類似会議も参照されます")
        print(f"4. 統計情報を確認: curl http://localhost:{settings.webhook_port}/statistics")
        print(f"5. 議事録を生成: curl -X POST http://localhost:{settings.webhook_port}/generate_summary/{bot_id}")
        print(f"6. ボット状態を確認: python src/get_bot_status.py {bot_id}")
        print("="*80 + "\n")
        
        return bot_id
        
    except Exception as e:
        logger.error(f"Failed to create bot: {e}", exc_info=True)
        print(f"\n❌ エラー: {e}\n")
        return None


async def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("Usage: python src/create_bot_with_rag.py <meeting_url> [bot_name]")
        print("\nExample:")
        print("  python src/create_bot_with_rag.py https://meet.google.com/xxx-yyyy-zzz")
        print("  python src/create_bot_with_rag.py https://meet.google.com/xxx-yyyy-zzz 'My AI Assistant'")
        sys.exit(1)
    
    meeting_url = sys.argv[1]
    bot_name = sys.argv[2] if len(sys.argv) > 2 else "AI Meeting Assistant with RAG"
    
    # Webhook URLを確認
    if not settings.webhook_public_url:
        print("\n⚠️  警告: WEBHOOK_PUBLIC_URLが設定されていません")
        print("config/.envファイルでWEBHOOK_PUBLIC_URLを設定してください")
        print("\n例:")
        print("  WEBHOOK_PUBLIC_URL=https://xxxx-xx-xx-xxx-xxx.ngrok-free.app")
        print("\nngrokを使用する場合:")
        print("  1. 別のターミナルで: ngrok http 8000")
        print("  2. 表示されたURLをconfig/.envに設定")
        print("  3. このスクリプトを再実行\n")
        sys.exit(1)
    
    await create_bot(meeting_url, bot_name)


if __name__ == "__main__":
    asyncio.run(main())
