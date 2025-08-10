# main.py
"""
Orchestrator that glues all the modules together:
1. Load config & set up logging.
2. Fetch new RSS items and determine which ones are unseen.
3. For each new item:
   - Download & clean the article body.
   - Summarize it with LM Studio (respecting a character limit).
4. Post the resulting summaries to Discord via webhook.
5. Persist the processed URLs so we don’t repeat work.
"""

import sys
import logging

# ← ここで load_config() をインポート
from src.config import load_config

# Functional modules
from src.feed_fetcher import get_new_items, save_processed
from src.article_extractor import fetch_and_clean
from src.summarizer import summarize
from src.discord_poster import post_to_webhook


# ----------------------------------------------------------------------
# Load configuration once at module import time
cfg = load_config()
# ----------------------------------------------------------------------


def setup_logging() -> None:
    """
    Configure the root logger according to `log_level` from config.
    Logs are emitted to stdout so they can be captured by systemd or cron logs.
    """
    logging.basicConfig(
        level=getattr(logging, cfg["log_level"].upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    """
    Main entry point of the RSS‑to‑Discord bot.
    The function follows the steps outlined in the module docstring
    and logs each major operation for debugging purposes.
    """
    setup_logging()
    log = logging.getLogger(__name__)
    log.info("=== RSS Bot start ===")

    # 1. RSS を取得し差分を判定
    new_items, processed = get_new_items(cfg["feed_url"])
    if not new_items:
        log.info("No new items.")
        return

    # 2〜4. 各記事を処理
    posts = []
    for entry in new_items[: cfg["max_articles_per_batch"]]:
        log.info(f"Processing: {entry.title}")
        try:
            body = fetch_and_clean(entry.link)
            summary, truncated = summarize(
                body, max_chars=cfg["summary_max_chars"]
            )
            if truncated:
                log.warning(f"Summary truncated for {entry.link}")
        except Exception as e:
            log.error(f"Failed to process {entry.link}: {e}")
            continue

        posts.append(
            {"title": entry.title, "summary": summary, "url": entry.link}
        )

        # 既読に追加（差分管理）
        processed.append(
            {
                "url": entry.link,
                "title": entry.title,
                "pubdate": getattr(entry, "published", ""),
            }
        )

    # 5. Discord に投稿
    if posts:
        try:
            post_to_webhook(posts, cfg["discord_webhook_url"])
            log.info(f"Posted {len(posts)} articles to Discord.")
        except Exception as e:
            log.error(f"Discord posting failed: {e}")

    # 6. processed.json を更新
    save_processed(processed)
    log.info("=== RSS Bot finished ===")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()