"""
ロギング設定モジュール

アプリケーション全体で使用するロガーを設定します。
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot.log"):
    """
    ロギングを設定
    
    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: ログファイルパス
    """
    # ログレベルを設定
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # ルートロガーを取得
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 既存のハンドラーをクリア
    root_logger.handlers.clear()
    
    # コンソールハンドラー（標準出力）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # コンソール用フォーマッター（人間が読みやすい形式）
    console_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー（JSON形式）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        
        # JSON形式のフォーマッター
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    
    logging.info(f"Logging configured: level={log_level}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    名前付きロガーを取得
    
    Args:
        name: ロガー名（通常は __name__ を使用）
        
    Returns:
        logging.Logger: ロガーインスタンス
    """
    return logging.getLogger(name)
