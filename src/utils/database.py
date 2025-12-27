"""
MySQLデータベース接続モジュール

会議データをMySQLデータベースに保存します。
"""

import logging
import pymysql
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

from src.utils.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """MySQLデータベース管理クラス"""
    
    def __init__(self):
        self.connection_params = {
            "host": settings.mysql_host,
            "port": settings.mysql_port,
            "user": settings.mysql_user,
            "password": settings.mysql_password,
            "database": settings.mysql_database,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
            "ssl": {"ssl_mode": "REQUIRED"},
        }
        logger.info(f"DatabaseManager initialized for {settings.mysql_host}:{settings.mysql_port}")
    
    @contextmanager
    def get_connection(self):
        """データベース接続を取得（コンテキストマネージャー）"""
        connection = None
        try:
            connection = pymysql.connect(**self.connection_params)
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def save_meeting(self, bot_id: str, meeting_url: str, title: Optional[str] = None) -> Optional[int]:
        """
        会議データを保存
        
        Args:
            bot_id: ボットID
            meeting_url: 会議URL
            title: 会議タイトル
        
        Returns:
            int: 挿入された会議のID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 既存の会議をチェック
                    cursor.execute(
                        "SELECT id FROM meetings WHERE bot_id = %s",
                        (bot_id,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        logger.info(f"Meeting already exists: bot_id={bot_id}, id={existing['id']}")
                        return existing['id']
                    
                    # 新規会議を挿入
                    cursor.execute(
                        """
                        INSERT INTO meetings (bot_id, meeting_url, title, status, started_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (bot_id, meeting_url, title or "Untitled Meeting", "in_progress", datetime.now())
                    )
                    meeting_id = cursor.lastrowid
                    logger.info(f"Meeting saved: id={meeting_id}, bot_id={bot_id}")
                    return meeting_id
        except Exception as e:
            logger.error(f"Error saving meeting: {e}")
            return None
    
    def save_transcript(
        self,
        meeting_id: int,
        speaker_name: str,
        text: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[int]:
        """
        文字起こしデータを保存
        
        Args:
            meeting_id: 会議ID
            speaker_name: 話者名
            text: 発言内容
            timestamp: タイムスタンプ
        
        Returns:
            int: 挿入された文字起こしのID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO transcripts (meeting_id, speaker_name, text, timestamp)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (meeting_id, speaker_name, text, timestamp or datetime.now())
                    )
                    transcript_id = cursor.lastrowid
                    logger.debug(f"Transcript saved: id={transcript_id}, meeting_id={meeting_id}")
                    return transcript_id
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            return None
    
    def update_meeting_status(
        self,
        meeting_id: int,
        status: str,
        end_time: Optional[datetime] = None
    ) -> bool:
        """
        会議ステータスを更新
        
        Args:
            meeting_id: 会議ID
            status: ステータス（active, completed, error）
            end_time: 終了時刻
        
        Returns:
            bool: 更新成功かどうか
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if end_time:
                        cursor.execute(
                            """
                            UPDATE meetings
                            SET status = %s, end_time = %s
                            WHERE id = %s
                            """,
                            (status, end_time, meeting_id)
                        )
                    else:
                        cursor.execute(
                            """
                            UPDATE meetings
                            SET status = %s
                            WHERE id = %s
                            """,
                            (status, meeting_id)
                        )
                    logger.info(f"Meeting status updated: id={meeting_id}, status={status}")
                    return True
        except Exception as e:
            logger.error(f"Error updating meeting status: {e}")
            return False
    
    def save_agent_message(
        self,
        meeting_id: int,
        agent_type: str,
        message: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[int]:
        """
        AIエージェントメッセージを保存
        
        Args:
            meeting_id: 会議ID
            agent_type: エージェントタイプ（pm, marketer, legal, sales, consultant）
            message: メッセージ内容
            timestamp: タイムスタンプ
        
        Returns:
            int: 挿入されたメッセージのID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO agent_messages (meeting_id, agent_type, message, timestamp)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (meeting_id, agent_type, message, timestamp or datetime.now())
                    )
                    message_id = cursor.lastrowid
                    logger.info(f"Agent message saved: id={message_id}, agent={agent_type}")
                    return message_id
        except Exception as e:
            logger.error(f"Error saving agent message: {e}")
            return None
    
    def update_meeting_status(self, meeting_id: int, status: str) -> bool:
        """
        会議ステータスを更新
        
        Args:
            meeting_id: 会議ID
            status: ステータス（in_progress, completed, error）
        
        Returns:
            bool: 更新成功かどうか
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE meetings
                        SET status = %s, ended_at = %s
                        WHERE id = %s
                        """,
                        (status, datetime.now() if status == "completed" else None, meeting_id)
                    )
                    logger.info(f"Meeting status updated: id={meeting_id}, status={status}")
                    return True
        except Exception as e:
            logger.error(f"Error updating meeting status: {e}")
            return False
    
    def get_meeting_by_bot_id(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """
        ボットIDから会議を取得
        
        Args:
            bot_id: ボットID
        
        Returns:
            Dict: 会議データ
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM meetings WHERE bot_id = %s",
                        (bot_id,)
                    )
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting meeting: {e}")
            return None


# グローバルインスタンス
db_manager = DatabaseManager()
