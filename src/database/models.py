"""
データベースモデル

SQLiteを使用して会議履歴を保存します。
"""

import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class MeetingDatabase:
    """会議データベース"""
    
    def __init__(self, db_path: str = "data/meetings.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        
        # データディレクトリを作成
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # データベースを初期化
        self._init_database()
        
        logger.info(f"MeetingDatabase initialized: {db_path}")
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 会議テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT UNIQUE NOT NULL,
                meeting_url TEXT NOT NULL,
                meeting_title TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                summary TEXT,
                transcript_count INTEGER DEFAULT 0,
                participant_count INTEGER DEFAULT 0,
                analysis_count INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 文字起こしテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_partial INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id)
            )
        """)
        
        # 決定事項テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id)
            )
        """)
        
        # アクションアイテムテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                task TEXT NOT NULL,
                assignee TEXT,
                due_date TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id)
            )
        """)
        
        # エージェント発言テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL,
                urgency REAL,
                relevance REAL,
                priority_score REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database initialized successfully")
    
    def create_meeting(
        self,
        bot_id: str,
        meeting_url: str,
        meeting_title: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> int:
        """
        会議を作成
        
        Args:
            bot_id: ボットID
            meeting_url: 会議URL
            meeting_title: 会議タイトル
            start_time: 開始時刻
            
        Returns:
            int: 会議ID
        """
        if start_time is None:
            start_time = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO meetings (
                bot_id, meeting_url, meeting_title, start_time,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (bot_id, meeting_url, meeting_title, start_time.isoformat(), now, now))
        
        meeting_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Meeting created: id={meeting_id}, bot_id={bot_id}")
        return meeting_id
    
    def get_meeting_by_bot_id(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """
        ボットIDから会議を取得
        
        Args:
            bot_id: ボットID
            
        Returns:
            Optional[Dict[str, Any]]: 会議データ
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM meetings WHERE bot_id = ?", (bot_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_meeting(
        self,
        bot_id: str,
        end_time: Optional[datetime] = None,
        summary: Optional[str] = None,
        transcript_count: Optional[int] = None,
        participant_count: Optional[int] = None,
        analysis_count: Optional[int] = None,
        message_count: Optional[int] = None,
        error_count: Optional[int] = None
    ):
        """
        会議を更新
        
        Args:
            bot_id: ボットID
            end_time: 終了時刻
            summary: 要約
            transcript_count: 文字起こし数
            participant_count: 参加者数
            analysis_count: 分析回数
            message_count: メッセージ数
            error_count: エラー数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if end_time is not None:
            updates.append("end_time = ?")
            params.append(end_time.isoformat())
        
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        
        if transcript_count is not None:
            updates.append("transcript_count = ?")
            params.append(transcript_count)
        
        if participant_count is not None:
            updates.append("participant_count = ?")
            params.append(participant_count)
        
        if analysis_count is not None:
            updates.append("analysis_count = ?")
            params.append(analysis_count)
        
        if message_count is not None:
            updates.append("message_count = ?")
            params.append(message_count)
        
        if error_count is not None:
            updates.append("error_count = ?")
            params.append(error_count)
        
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        params.append(bot_id)
        
        query = f"UPDATE meetings SET {', '.join(updates)} WHERE bot_id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Meeting updated: bot_id={bot_id}")
    
    def add_transcript(
        self,
        meeting_id: int,
        speaker: str,
        text: str,
        timestamp: Optional[str] = None,
        is_partial: bool = False
    ):
        """
        文字起こしを追加
        
        Args:
            meeting_id: 会議ID
            speaker: 話者
            text: テキスト
            timestamp: タイムスタンプ
            is_partial: 部分的かどうか
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transcripts (
                meeting_id, speaker, text, timestamp, is_partial, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (meeting_id, speaker, text, timestamp, 1 if is_partial else 0, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def add_decision(
        self,
        meeting_id: int,
        content: str,
        timestamp: Optional[str] = None
    ):
        """
        決定事項を追加
        
        Args:
            meeting_id: 会議ID
            content: 内容
            timestamp: タイムスタンプ
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO decisions (
                meeting_id, content, timestamp, created_at
            ) VALUES (?, ?, ?, ?)
        """, (meeting_id, content, timestamp, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def add_action_item(
        self,
        meeting_id: int,
        task: str,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
        timestamp: Optional[str] = None
    ):
        """
        アクションアイテムを追加
        
        Args:
            meeting_id: 会議ID
            task: タスク
            assignee: 担当者
            due_date: 期限
            timestamp: タイムスタンプ
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO action_items (
                meeting_id, task, assignee, due_date, timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (meeting_id, task, assignee, due_date, timestamp, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def add_agent_message(
        self,
        meeting_id: int,
        agent_name: str,
        content: str,
        confidence: float,
        urgency: float,
        relevance: float,
        priority_score: float
    ):
        """
        エージェント発言を追加
        
        Args:
            meeting_id: 会議ID
            agent_name: エージェント名
            content: 内容
            confidence: 自信度
            urgency: 緊急度
            relevance: 関連性
            priority_score: 優先度スコア
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_messages (
                meeting_id, agent_name, content, confidence, urgency,
                relevance, priority_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (meeting_id, agent_name, content, confidence, urgency, relevance, priority_score, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_all_meetings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        すべての会議を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            List[Dict[str, Any]]: 会議リスト
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
