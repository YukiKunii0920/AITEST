"""
Slack通知機能

会議終了時に議事録とアクションアイテムをSlackに投稿します。
"""
import logging
import os
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slack通知クラス"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初期化
        
        Args:
            webhook_url: Slack Webhook URL（環境変数 SLACK_WEBHOOK_URL から取得）
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not set. Slack notifications will be disabled.")
    
    def is_enabled(self) -> bool:
        """Slack通知が有効かどうか"""
        return self.webhook_url is not None
    
    def send_meeting_summary(
        self,
        meeting_title: str,
        meeting_url: str,
        summary: str,
        decisions: List[Dict],
        action_items: List[Dict],
        bot_id: str
    ) -> bool:
        """
        会議議事録をSlackに投稿
        
        Args:
            meeting_title: 会議タイトル
            meeting_url: 会議URL
            summary: 会議の要約
            decisions: 決定事項のリスト
            action_items: アクションアイテムのリスト
            bot_id: ボットID
            
        Returns:
            送信成功の場合True
        """
        if not self.is_enabled():
            logger.warning("Slack notifications are disabled")
            return False
        
        try:
            # Slackメッセージを構築
            blocks = self._build_message_blocks(
                meeting_title=meeting_title,
                meeting_url=meeting_url,
                summary=summary,
                decisions=decisions,
                action_items=action_items,
                bot_id=bot_id
            )
            
            # Slackに投稿
            response = requests.post(
                self.webhook_url,
                json={"blocks": blocks},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent meeting summary to Slack for bot {bot_id}")
                return True
            else:
                logger.error(f"Failed to send to Slack: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending to Slack: {e}", exc_info=True)
            return False
    
    def _build_message_blocks(
        self,
        meeting_title: str,
        meeting_url: str,
        summary: str,
        decisions: List[Dict],
        action_items: List[Dict],
        bot_id: str
    ) -> List[Dict]:
        """
        Slackメッセージブロックを構築
        
        Args:
            meeting_title: 会議タイトル
            meeting_url: 会議URL
            summary: 会議の要約
            decisions: 決定事項のリスト
            action_items: アクションアイテムのリスト
            bot_id: ボットID
            
        Returns:
            Slackメッセージブロックのリスト
        """
        blocks = []
        
        # ヘッダー
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📝 {meeting_title}",
                "emoji": True
            }
        })
        
        # 会議情報
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*会議URL:*\n{meeting_url}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Bot ID:*\n`{bot_id}`"
                }
            ]
        })
        
        blocks.append({"type": "divider"})
        
        # 会議の要約
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📋 会議の要約*\n{summary}"
            }
        })
        
        # 決定事項
        if decisions:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*✅ 決定事項*"
                }
            })
            
            for i, decision in enumerate(decisions[:5], 1):  # 最大5件
                content = decision.get("content", "")
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{i}. {content}"
                    }
                })
        
        # アクションアイテム
        if action_items:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🎯 アクションアイテム*"
                }
            })
            
            for i, item in enumerate(action_items[:5], 1):  # 最大5件
                task = item.get("task", "")
                assignee = item.get("assignee", "未割当")
                due_date = item.get("due_date", "期限未設定")
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{i}. *{task}*\n担当: {assignee} | 期限: {due_date}"
                    }
                })
        
        # フッター
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🤖 AI Meeting Assistant により自動生成されました"
                }
            ]
        })
        
        return blocks
    
    def send_simple_notification(self, message: str) -> bool:
        """
        シンプルな通知を送信
        
        Args:
            message: 通知メッセージ
            
        Returns:
            送信成功の場合True
        """
        if not self.is_enabled():
            logger.warning("Slack notifications are disabled")
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json={"text": message},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Successfully sent notification to Slack")
                return True
            else:
                logger.error(f"Failed to send to Slack: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending to Slack: {e}", exc_info=True)
            return False


# グローバルインスタンス
slack_notifier = SlackNotifier()
