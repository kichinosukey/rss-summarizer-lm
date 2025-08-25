# config.py
"""
Load configuration from environment variables, supporting multiple feeds.
Docker Compose will inject the values via `env_file: .env`.
"""

import os
import json


def load_config() -> dict:
    """
    Return a dictionary with all required configuration values.
    Raises RuntimeError if any mandatory variable is missing.
    """
    # フィード設定を解析
    feeds_json = os.getenv("FEEDS", "[]")
    try:
        feeds = json.loads(feeds_json)
    except json.JSONDecodeError:
        raise RuntimeError("FEEDS environment variable contains invalid JSON")
    
    cfg = {
        # 1️⃣ フィード設定（複数対応）
        "feeds": feeds,

        # 2️⃣ ログレベル（デフォルト INFO）
        "log_level": os.getenv("LOG_LEVEL", "INFO"),

        # 3️⃣ LM Studio
        "lm_studio_url": os.getenv("LM_STUDIO_URL"),
        "lm_studio_model": os.getenv("LM_STUDIO_MODEL", "llama3"),

        # 4️⃣ 任意の設定（デフォルトを付与）
        "summary_max_chars": int(os.getenv("SUMMARY_MAX_CHARS", 1800)),
    }

    # 必須キーのチェック
    if not cfg.get("lm_studio_url"):
        raise RuntimeError("Missing required env variable: LM_STUDIO_URL")
    
    if not cfg.get("feeds"):
        raise RuntimeError("No feeds configured in FEEDS environment variable")
    
    # 各フィード設定の妥当性チェック
    for i, feed in enumerate(cfg["feeds"]):
        required_feed_keys = ["feed_name", "url", "webhook"]
        missing_keys = [k for k in required_feed_keys if not feed.get(k)]
        if missing_keys:
            raise RuntimeError(f"Feed {i}: Missing required keys: {', '.join(missing_keys)}")
        
        # max_articlesのデフォルト値設定
        if "max_articles" not in feed:
            feed["max_articles"] = 5
        
        # キーワードフィルタのデフォルト値設定
        if "include_keywords" not in feed:
            feed["include_keywords"] = []
        if "exclude_keywords" not in feed:
            feed["exclude_keywords"] = []
        if "keyword_match_mode" not in feed:
            feed["keyword_match_mode"] = "both"

    return cfg