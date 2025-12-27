"""
会議履歴閲覧スクリプト

データベースに保存された会議履歴を閲覧します。
"""

import sys
from pathlib import Path
import argparse
import logging
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import MeetingDatabase
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def list_meetings(db: MeetingDatabase, limit: int = 10):
    """
    会議リストを表示
    
    Args:
        db: データベース
        limit: 表示件数
    """
    meetings = db.get_all_meetings(limit=limit)
    
    if not meetings:
        print("会議が見つかりませんでした。")
        return
    
    print("=" * 100)
    print(f"会議リスト（最新{limit}件）")
    print("=" * 100)
    
    for i, meeting in enumerate(meetings, 1):
        print(f"\n{i}. {meeting['meeting_title'] or 'Untitled Meeting'}")
        print(f"   Bot ID: {meeting['bot_id']}")
        print(f"   会議URL: {meeting['meeting_url']}")
        print(f"   開始時刻: {meeting['start_time']}")
        print(f"   終了時刻: {meeting['end_time'] or 'N/A'}")
        print(f"   文字起こし数: {meeting['transcript_count']}")
        print(f"   参加者数: {meeting['participant_count']}")
        print(f"   分析回数: {meeting['analysis_count']}")
        print(f"   メッセージ数: {meeting['message_count']}")
        print(f"   エラー数: {meeting['error_count']}")
        
        if meeting['summary']:
            print(f"   要約: {meeting['summary'][:100]}...")
    
    print("=" * 100)


def view_meeting_details(db: MeetingDatabase, bot_id: str):
    """
    会議の詳細を表示
    
    Args:
        db: データベース
        bot_id: ボットID
    """
    import sqlite3
    
    meeting = db.get_meeting_by_bot_id(bot_id)
    
    if not meeting:
        print(f"Bot ID {bot_id} の会議が見つかりませんでした。")
        return
    
    meeting_id = meeting['id']
    
    print("=" * 100)
    print(f"会議詳細: {meeting['meeting_title'] or 'Untitled Meeting'}")
    print("=" * 100)
    print(f"Bot ID: {meeting['bot_id']}")
    print(f"会議URL: {meeting['meeting_url']}")
    print(f"開始時刻: {meeting['start_time']}")
    print(f"終了時刻: {meeting['end_time'] or 'N/A'}")
    print(f"文字起こし数: {meeting['transcript_count']}")
    print(f"参加者数: {meeting['participant_count']}")
    print(f"分析回数: {meeting['analysis_count']}")
    print(f"メッセージ数: {meeting['message_count']}")
    print(f"エラー数: {meeting['error_count']}")
    print("=" * 100)
    
    # 要約
    if meeting['summary']:
        print("\n📝 会議の要約:")
        print(meeting['summary'])
        print("=" * 100)
    
    # 決定事項
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM decisions WHERE meeting_id = ?", (meeting_id,))
    decisions = cursor.fetchall()
    
    if decisions:
        print("\n✅ 決定事項:")
        for i, decision in enumerate(decisions, 1):
            print(f"{i}. {decision['content']}")
            if decision['timestamp']:
                print(f"   タイムスタンプ: {decision['timestamp']}")
        print("=" * 100)
    
    # アクションアイテム
    cursor.execute("SELECT * FROM action_items WHERE meeting_id = ?", (meeting_id,))
    action_items = cursor.fetchall()
    
    if action_items:
        print("\n📋 アクションアイテム:")
        for i, item in enumerate(action_items, 1):
            print(f"{i}. {item['task']}")
            if item['assignee']:
                print(f"   担当: {item['assignee']}")
            if item['due_date']:
                print(f"   期限: {item['due_date']}")
            if item['timestamp']:
                print(f"   タイムスタンプ: {item['timestamp']}")
            print(f"   ステータス: {item['status']}")
        print("=" * 100)
    
    # エージェントメッセージ
    cursor.execute("SELECT * FROM agent_messages WHERE meeting_id = ? ORDER BY created_at", (meeting_id,))
    agent_messages = cursor.fetchall()
    
    if agent_messages:
        print("\n🤖 AIエージェントの発言:")
        for i, msg in enumerate(agent_messages, 1):
            print(f"\n{i}. {msg['agent_name']} (優先度: {msg['priority_score']:.2f})")
            print(f"   {msg['content']}")
            print(f"   自信度: {msg['confidence']:.2f}, 緊急度: {msg['urgency']:.2f}, 関連性: {msg['relevance']:.2f}")
        print("=" * 100)
    
    # 文字起こし（最新10件）
    cursor.execute("SELECT * FROM transcripts WHERE meeting_id = ? AND is_partial = 0 ORDER BY created_at DESC LIMIT 10", (meeting_id,))
    transcripts = cursor.fetchall()
    
    if transcripts:
        print("\n💬 文字起こし（最新10件）:")
        for i, transcript in enumerate(reversed(transcripts), 1):
            print(f"{i}. [{transcript['timestamp']}] {transcript['speaker']}: {transcript['text']}")
        print("=" * 100)
    
    conn.close()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="View meeting history from database"
    )
    parser.add_argument(
        "--bot-id",
        help="Bot ID to view details"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of meetings to list (default: 10)"
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: WARNING)"
    )
    
    args = parser.parse_args()
    
    # ロギング設定
    setup_logging(log_level=args.log_level)
    
    # データベースを初期化
    db = MeetingDatabase()
    
    if args.bot_id:
        # 詳細表示
        view_meeting_details(db, args.bot_id)
    else:
        # リスト表示
        list_meetings(db, limit=args.limit)


if __name__ == "__main__":
    main()
