"""
MySQL Client for syncing meeting data to Web UI database.
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logging.warning("mysql-connector-python not installed. MySQL sync will be disabled.")

logger = logging.getLogger(__name__)


class MySQLClient:
    """Client for syncing meeting data to MySQL database."""
    
    def __init__(self):
        """Initialize MySQL client with environment variables."""
        if not MYSQL_AVAILABLE:
            logger.warning("MySQL connector not available")
            self.connection = None
            return
        
        # Get MySQL connection details from environment
        # These should match the Web UI's DATABASE_URL
        self.host = os.getenv("MYSQL_HOST", "localhost")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self.user = os.getenv("MYSQL_USER", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DATABASE", "meeting_dashboard")
        
        self.connection = None
        self.cursor = None
        
        # Try to connect
        self._connect()
    
    def _connect(self):
        """Establish MySQL connection."""
        if not MYSQL_AVAILABLE:
            return
        
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=False
            )
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info(f"Connected to MySQL database: {self.database}")
        except Error as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            self.connection = None
            self.cursor = None
    
    def is_connected(self) -> bool:
        """Check if MySQL connection is active."""
        return self.connection is not None and self.connection.is_connected()
    
    def _ensure_connection(self):
        """Ensure MySQL connection is active, reconnect if needed."""
        if not self.is_connected():
            logger.warning("MySQL connection lost, reconnecting...")
            self._connect()
    
    def create_or_update_meeting(
        self,
        bot_id: str,
        meeting_url: str,
        meeting_title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        summary: Optional[str] = None,
        rag_enabled: bool = True
    ) -> Optional[int]:
        """Create or update meeting record."""
        if not self.is_connected():
            logger.warning("MySQL not connected, skipping meeting sync")
            return None
        
        try:
            self._ensure_connection()
            
            # Check if meeting exists
            self.cursor.execute(
                "SELECT id FROM meetings WHERE botId = %s",
                (bot_id,)
            )
            result = self.cursor.fetchone()
            
            if result:
                # Update existing meeting
                meeting_id = result['id']
                update_fields = []
                update_values = []
                
                if meeting_title:
                    update_fields.append("meetingTitle = %s")
                    update_values.append(meeting_title)
                if end_time:
                    update_fields.append("endTime = %s")
                    update_values.append(end_time)
                if summary:
                    update_fields.append("summary = %s")
                    update_values.append(summary)
                
                if update_fields:
                    update_values.append(meeting_id)
                    query = f"UPDATE meetings SET {', '.join(update_fields)} WHERE id = %s"
                    self.cursor.execute(query, tuple(update_values))
                    self.connection.commit()
                    logger.info(f"Updated meeting {meeting_id} in MySQL")
            else:
                # Insert new meeting
                query = """
                INSERT INTO meetings 
                (botId, meetingUrl, meetingTitle, startTime, endTime, summary, ragEnabled, createdAt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    bot_id,
                    meeting_url,
                    meeting_title,
                    start_time or datetime.now(),
                    end_time,
                    summary,
                    rag_enabled,
                    datetime.now()
                )
                self.cursor.execute(query, values)
                self.connection.commit()
                meeting_id = self.cursor.lastrowid
                logger.info(f"Created meeting {meeting_id} in MySQL")
            
            return meeting_id
        except Error as e:
            logger.error(f"Failed to create/update meeting in MySQL: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def get_meeting_by_bot_id(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get meeting by bot ID."""
        if not self.is_connected():
            return None
        
        try:
            self._ensure_connection()
            self.cursor.execute(
                "SELECT * FROM meetings WHERE botId = %s",
                (bot_id,)
            )
            return self.cursor.fetchone()
        except Error as e:
            logger.error(f"Failed to get meeting from MySQL: {e}")
            return None
    
    def add_transcript(
        self,
        meeting_id: int,
        speaker: str,
        text: str,
        timestamp: datetime,
        is_partial: bool = False
    ) -> bool:
        """Add transcript record."""
        if not self.is_connected():
            logger.warning("MySQL not connected, skipping transcript sync")
            return False
        
        try:
            self._ensure_connection()
            query = """
            INSERT INTO transcripts (meetingId, speaker, text, timestamp, isPartial)
            VALUES (%s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (meeting_id, speaker, text, timestamp, is_partial))
            self.connection.commit()
            
            # Update transcript count
            self.cursor.execute(
                "UPDATE meetings SET transcriptCount = transcriptCount + 1 WHERE id = %s",
                (meeting_id,)
            )
            self.connection.commit()
            
            logger.debug(f"Added transcript to meeting {meeting_id} in MySQL")
            return True
        except Error as e:
            logger.error(f"Failed to add transcript to MySQL: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def add_agent_message(
        self,
        meeting_id: int,
        agent_name: str,
        content: str,
        confidence: float,
        urgency: float,
        relevance: float,
        priority_score: float,
        timestamp: datetime
    ) -> bool:
        """Add agent message record."""
        if not self.is_connected():
            logger.warning("MySQL not connected, skipping agent message sync")
            return False
        
        try:
            self._ensure_connection()
            query = """
            INSERT INTO agentMessages 
            (meetingId, agentName, content, confidence, urgency, relevance, priorityScore, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(
                query,
                (meeting_id, agent_name, content, confidence, urgency, relevance, priority_score, timestamp)
            )
            self.connection.commit()
            
            # Update message count
            self.cursor.execute(
                "UPDATE meetings SET messageCount = messageCount + 1 WHERE id = %s",
                (meeting_id,)
            )
            self.connection.commit()
            
            logger.debug(f"Added agent message to meeting {meeting_id} in MySQL")
            return True
        except Error as e:
            logger.error(f"Failed to add agent message to MySQL: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def add_decision(
        self,
        meeting_id: int,
        content: str,
        timestamp: datetime
    ) -> bool:
        """Add decision record."""
        if not self.is_connected():
            logger.warning("MySQL not connected, skipping decision sync")
            return False
        
        try:
            self._ensure_connection()
            query = """
            INSERT INTO decisions (meetingId, content, timestamp)
            VALUES (%s, %s, %s)
            """
            self.cursor.execute(query, (meeting_id, content, timestamp))
            self.connection.commit()
            logger.debug(f"Added decision to meeting {meeting_id} in MySQL")
            return True
        except Error as e:
            logger.error(f"Failed to add decision to MySQL: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def add_action_item(
        self,
        meeting_id: int,
        task: str,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Add action item record."""
        if not self.is_connected():
            logger.warning("MySQL not connected, skipping action item sync")
            return False
        
        try:
            self._ensure_connection()
            query = """
            INSERT INTO actionItems (meetingId, task, assignee, dueDate, timestamp, completed)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(
                query,
                (meeting_id, task, assignee, due_date, timestamp or datetime.now(), False)
            )
            self.connection.commit()
            logger.debug(f"Added action item to meeting {meeting_id} in MySQL")
            return True
        except Error as e:
            logger.error(f"Failed to add action item to MySQL: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def update_meeting_summary(
        self,
        meeting_id: int,
        summary: str,
        decisions: List[Dict[str, Any]],
        action_items: List[Dict[str, Any]]
    ) -> bool:
        """Update meeting with generated summary, decisions, and action items."""
        if not self.is_connected():
            logger.warning("MySQL not connected, skipping summary sync")
            return False
        
        try:
            self._ensure_connection()
            
            # Update summary
            self.cursor.execute(
                "UPDATE meetings SET summary = %s WHERE id = %s",
                (summary, meeting_id)
            )
            
            # Add decisions
            for decision in decisions:
                self.add_decision(
                    meeting_id,
                    decision.get("content", ""),
                    decision.get("timestamp", datetime.now())
                )
            
            # Add action items
            for item in action_items:
                self.add_action_item(
                    meeting_id,
                    item.get("task", ""),
                    item.get("assignee"),
                    item.get("due_date"),
                    item.get("timestamp", datetime.now())
                )
            
            self.connection.commit()
            logger.info(f"Updated summary for meeting {meeting_id} in MySQL")
            return True
        except Error as e:
            logger.error(f"Failed to update summary in MySQL: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def increment_analysis_count(self, meeting_id: int) -> bool:
        """Increment analysis count for a meeting."""
        if not self.is_connected():
            return False
        
        try:
            self._ensure_connection()
            self.cursor.execute(
                "UPDATE meetings SET analysisCount = analysisCount + 1 WHERE id = %s",
                (meeting_id,)
            )
            self.connection.commit()
            return True
        except Error as e:
            logger.error(f"Failed to increment analysis count in MySQL: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def close(self):
        """Close MySQL connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")
