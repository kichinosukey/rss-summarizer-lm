# feed_fetcher.py
"""
Module that fetches RSS feeds and keeps track of which URLs have already been processed.
All state is persisted in separate JSON files for each feed in the data directory.

Functions
---------
load_processed(feed_name: str) -> list[dict]
    Load the JSON file that contains all already processed URLs for the specified feed.

save_processed(processed: list[dict], feed_name: str) -> None
    Persist the updated list of processed URLs back to disk for the specified feed.

get_new_items(feed_url: str, feed_name: str) -> tuple[list[dict], list[dict]]
    Parse the RSS feed, return a list of new entries that have not been processed yet
    along with the current state (so callers can append to it).
"""

import json, logging, feedparser, requests, os
from pathlib import Path


def _get_processed_path(feed_name: str) -> Path:
    """Get the path for the processed.json file for a specific feed."""
    return Path(__file__).parent.parent / "data" / f"processed_{feed_name}.json"


def load_processed(feed_name: str) -> list[dict]:
    """
    Load the JSON file that contains all already processed URLs for the specified feed.

    Parameters
    ----------
    feed_name : str
        Name of the feed to load processed URLs for.

    Returns
    -------
    list[dict]
        Each dict has keys: url, title, pubdate (as stored by the caller).
    """
    processed_path = _get_processed_path(feed_name)
    if not processed_path.exists():
        return []
    with open(processed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_processed(processed: list[dict], feed_name: str) -> None:
    """
    Persist the updated list of processed URLs back to disk for the specified feed.
    
    Parameters
    ----------
    processed : list[dict]
        Updated list of article metadata that should be stored.
    feed_name : str
        Name of the feed to save processed URLs for.
    """
    processed_path = _get_processed_path(feed_name)
    # Ensure the data directory exists
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)


def get_new_items(feed_url: str, feed_name: str) -> tuple[list[dict], list[dict]]:
    """
    Parse the RSS feed, return a list of new entries that have not been processed yet
    along with the current state (so callers can append to it).

    Parameters
    ----------
    feed_url : str
        URL of the RSS feed to fetch.
    feed_name : str
        Name of the feed for tracking processed items.

    Returns
    -------
    tuple[list[dict], list[dict]]
        - List of new feed entries (each is a `feedparser` entry object).
        - The current list of processed items as returned by :func:`load_processed`.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSSBot/1.0)",
        "Accept-Language": "ja-JP, ja;q=0.9",
    }
    
    try:
        # タイムアウト設定を環境変数から取得
        timeout = int(os.getenv('FEED_TIMEOUT', '10'))  # デフォルト10秒
        resp = requests.get(feed_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logging.error("RSS 取得失敗 (%s): %s", feed_name, e)
        return [], []

    feed = feedparser.parse(resp.content)

    if not feed.entries:
        logging.warning("RSS フィードから 0 件取得。Feed: %s, URL: %s", feed_name, feed_url)

    processed = load_processed(feed_name)
    seen_urls = {p["url"] for p in processed}
    new_items = [e for e in feed.entries if e.link not in seen_urls]
    
    logging.info("Feed %s: %d new items, %d already processed", 
                 feed_name, len(new_items), len(processed))
    
    return new_items, processed