# main.py
"""
Orchestrator that glues all the modules together for multiple RSS feeds:
1. Load config & set up logging.
2. For each configured feed:
   - Fetch new RSS items and determine which ones are unseen.
   - For each new item:
     * Download & clean the article body.
     * Summarize it with LM Studio (respecting a character limit).
   - Post the resulting summaries to the specified Discord webhook.
   - Persist the processed URLs so we don't repeat work.
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


def process_feed(feed_config: dict) -> None:
    """
    Process a single RSS feed configuration.
    
    Parameters
    ----------
    feed_config : dict
        Feed configuration containing feed_name, url, webhook, max_articles
    """
    log = logging.getLogger(__name__)
    feed_name = feed_config["feed_name"]
    feed_url = feed_config["url"]
    webhook_url = feed_config["webhook"]
    max_articles = feed_config["max_articles"]
    
    log.info(f"=== Processing feed: {feed_name} ===")
    
    # 1. RSS を取得し差分を判定
    new_items, processed = get_new_items(feed_url, feed_name)
    if not new_items:
        log.info(f"No new items for feed: {feed_name}")
        return
    
    log.info(f"Found {len(new_items)} new items for feed: {feed_name}")

    # 2〜4. 各記事を処理
    posts = []
    for entry in new_items[:max_articles]:
        log.info(f"Processing ({feed_name}): {entry.title}")
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
            post_to_webhook(posts, webhook_url)
            log.info(f"Posted {len(posts)} articles to Discord for feed: {feed_name}")
        except Exception as e:
            log.error(f"Discord posting failed for feed {feed_name}: {e}")

    # 6. processed.json を更新
    save_processed(processed, feed_name)
    log.info(f"=== Finished processing feed: {feed_name} ===")


def main() -> None:
    """
    Main entry point of the RSS‑to‑Discord bot.
    Processes all configured feeds sequentially.
    """
    setup_logging()
    log = logging.getLogger(__name__)
    log.info("=== RSS Bot start ===")
    
    feeds = cfg.get("feeds", [])
    if not feeds:
        log.warning("No feeds configured. Exiting.")
        return
    
    log.info(f"Processing {len(feeds)} feed(s)")
    
    # Process each feed
    for feed_config in feeds:
        try:
            process_feed(feed_config)
        except Exception as e:
            feed_name = feed_config.get("feed_name", "unknown")
            log.error(f"Error processing feed {feed_name}: {e}")
            continue
    
    log.info("=== RSS Bot finished ===")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()