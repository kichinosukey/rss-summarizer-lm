# config.py
"""
Load configuration only from environment variables.
Docker Compose will inject the values via `env_file: .env`.
"""

import os


def load_config() -> dict:
    """
    Return a dictionary with all required configuration values.
    Raises RuntimeError if any mandatory variable is missing.
    """
    cfg = {
        # 1️⃣ RSS フィード
        "feed_url": os.getenv(
            "FEED_URL",
            "https://www.xda-developers.com/tag/raspberry-pi/feed/",
        ),

        # 2️⃣ Discord Webhook
        "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL"),

        # 3️⃣ ログレベル（デフォルト INFO）
        "log_level": os.getenv("LOG_LEVEL", "INFO"),

        # 4️⃣ LM Studio
        "lm_studio_url": os.getenv("LM_STUDIO_URL"),
        "lm_studio_model": os.getenv("LM_STUDIO_MODEL", "llama3"),

        # 5️⃣ 任意の設定（デフォルトを付与）
        "max_articles_per_batch": int(os.getenv("MAX_ARTICLES_PER_BATCH", 5)),
        "summary_max_chars": int(os.getenv("SUMMARY_MAX_CHARS", 1800)),
    }

    # 必須キーのチェック
    missing = [
        k for k in ["feed_url", "discord_webhook_url", "lm_studio_url"] if not cfg.get(k)
    ]
    if missing:
        raise RuntimeError(f"Missing required env variables: {', '.join(missing)}")

    return cfg