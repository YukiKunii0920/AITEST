"""
設定管理モジュール

環境変数から設定を読み込み、アプリケーション全体で使用できるようにします。
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # Recall.ai API設定
    recall_api_key: str = ""
    recall_api_base_url: str = "https://us-east-1.recall.ai/api/v1"
    
    # Webhook設定
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8000
    webhook_public_url: str = "http://localhost:8000"
    
    # OpenAI API設定
    openai_api_key: Optional[str] = None
    
    # ログ設定
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_settings() -> Settings:
    """
    設定を読み込む
    
    Returns:
        Settings: アプリケーション設定
    """
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / "config" / ".env"
    
    # .envファイルが存在する場合は読み込む
    if env_file.exists():
        return Settings(_env_file=str(env_file))
    else:
        # 環境変数から読み込む
        return Settings()


# グローバル設定インスタンス
settings = load_settings()
