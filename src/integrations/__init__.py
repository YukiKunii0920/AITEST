"""
統合機能モジュール
"""
from .slack_notifier import SlackNotifier, slack_notifier

__all__ = ["SlackNotifier", "slack_notifier"]
