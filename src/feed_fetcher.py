# feed_fetcher.py
"""
Module that fetches the RSS feed and keeps track of which URLs have already been processed.
All state is persisted in a simple JSON file (`processed.json`) that lives next to this module.

Functions
---------
load_processed() -> list[dict]
    Load the JSON file that contains all already processed URLs.

save_processed(processed: list[dict]) -> None
    Persist the updated list of processed URLs back to disk.

get_new_items(feed_url: str) -> tuple[list[dict], list[dict]]
    Parse the RSS feed, return a list of new entries that have not been processed yet
    along with the current state (so callers can append to it).
"""

import json, logging, feedparser, requests
from pathlib import Path

PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed.json"

def load_processed() -> list[dict]:
    """
    Load the JSON file that contains all already processed URLs.

    Returns
    -------
    list[dict]
        Each dict has keys: url, title, pubdate (as stored by the caller).
    """
    if not PROCESSED_PATH.exists():
        return []
    with open(PROCESSED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_processed(processed: list[dict]) -> None:
    """
    Persist the updated list of processed URLs back to disk.

    Parameters
    ----------
    processed : list[dict]
        Updated list of article metadata that should be stored.
    """
    tmp = PROCESSED_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
    tmp.replace(PROCESSED_PATH)

def save_processed(processed):
    """
    processed.json を直接上書き保存。  
    変更はアトミックではないが、単一プロセスで実行されるので問題なし。
    """
    with open(PROCESSED_PATH, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

def _get_new_items(feed_url: str) -> tuple[list[dict], list[dict]]:
    """
    Parse the RSS feed, return a list of new entries that have not been processed yet
    along with the current state (so callers can append to it).

    Parameters
    ----------
    feed_url : str
        URL of the RSS feed to fetch.

    Returns
    -------
    tuple[list[dict], list[dict]]
        - List of new feed entries (each is a `feedparser` entry object).
        - The current list of processed items as returned by :func:`load_processed`.
    """
    feed = feedparser.parse(feed_url)
    processed = load_processed()
    seen_urls = {p["url"] for p in processed}
    new_items = [e for e in feed.entries if e.link not in seen_urls]
    return new_items, processed

def get_new_items(feed_url: str):
    """requests でヘッダー付きに取得し、feedparser に渡す。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSSBot/1.0)",
        "Accept-Language": "ja-JP, ja;q=0.9",
    }
    try:
        resp = requests.get(feed_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logging.error("RSS 取得失敗: %s", e)
        return [], []

    feed = feedparser.parse(resp.content)

    if not feed.entries:
        logging.warning("RSS フィードから 0 件取得。URL: %s", feed_url)

    processed = load_processed()
    seen_urls = {p["url"] for p in processed}
    new_items = [e for e in feed.entries if e.link not in seen_urls]
    return new_items, processed