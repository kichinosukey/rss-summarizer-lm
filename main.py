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
import os
import time
import re

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

# 要約処理の制御変数
SUMMARIZE_MAX_CALLS = int(os.getenv('SUMMARIZE_MAX_CALLS', '0'))  # 0 = 無制限
SUMMARIZE_INTERVAL = float(os.getenv('SUMMARIZE_INTERVAL', '1.0'))  # 秒

# グローバル変数
summarize_call_count = 0
# ----------------------------------------------------------------------


def should_process_article_url_only(entry, feed_config: dict) -> bool:
    """
    URL/creatorベースのキーワードフィルタリングのみを実行
    記事本文をダウンロードする前の早期チェック用
    """
    include_keywords = feed_config.get("include_keywords", [])
    exclude_keywords = feed_config.get("exclude_keywords", [])
    match_mode = feed_config.get("keyword_match_mode", "both")
    
    # URL/creator/organization/subject/description以外のモードまたはキーワード未設定の場合は通す
    if match_mode not in ["url", "creator", "organization", "subject", "description"] or (not include_keywords and not exclude_keywords):
        return True
    
    if match_mode == "url":
        search_text = entry.link.lower()
    elif match_mode == "creator":
        # dc:creatorフィールドから検索テキストを取得
        creator = getattr(entry, 'author', '') or getattr(entry, 'dc_creator', '')
        search_text = creator.lower()
    elif match_mode == "organization":
        # cms:orgShortNameフィールドから検索テキストを取得
        org_name = getattr(entry, 'cms_orgshortname', '') or getattr(entry, 'orgshortname', '')
        search_text = org_name.lower()
    elif match_mode == "subject":
        # dc:subjectフィールドから検索テキストを取得
        subject = getattr(entry, 'dc_subject', '') or getattr(entry, 'subject', '')
        search_text = subject.lower()
    elif match_mode == "description":
        # descriptionフィールドからHTMLタグを除去して検索テキストを取得
        description = getattr(entry, 'description', '') or getattr(entry, 'summary', '')
        clean_description = re.sub(r'<[^>]+>', '', description)
        search_text = clean_description.lower()
    
    # include_keywords チェック
    if include_keywords:
        if not any(keyword.lower() in search_text for keyword in include_keywords):
            return False
    
    # exclude_keywords チェック  
    if exclude_keywords:
        if any(keyword.lower() in search_text for keyword in exclude_keywords):
            return False
    
    return True


def should_process_article(entry, body: str, feed_config: dict) -> bool:
    """
    記事がキーワードフィルタを通過するかチェック
    
    Parameters
    ----------
    entry : feedparser.FeedParserDict
        RSS記事のエントリ
    body : str
        記事本文
    feed_config : dict
        フィード設定
    
    Returns
    -------
    bool
        処理すべき記事の場合True
    """
    include_keywords = feed_config.get("include_keywords", [])
    exclude_keywords = feed_config.get("exclude_keywords", [])
    match_mode = feed_config.get("keyword_match_mode", "both")
    
    # キーワードフィルタが設定されていない場合は通す
    if not include_keywords and not exclude_keywords:
        return True
    
    # 検索対象テキスト決定
    if match_mode == "title":
        search_text = entry.title.lower()
    elif match_mode == "content":
        search_text = body.lower()
    elif match_mode == "category":
        # カテゴリタグから検索テキストを構築
        categories = []
        if hasattr(entry, 'tags') and entry.tags:
            categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
        search_text = " ".join(categories).lower()
    elif match_mode == "url":
        search_text = entry.link.lower()
    elif match_mode == "creator":
        # dc:creatorフィールドから検索テキストを取得
        creator = getattr(entry, 'author', '') or getattr(entry, 'dc_creator', '')
        search_text = creator.lower()
    elif match_mode == "organization":
        # cms:orgShortNameフィールドから検索テキストを取得
        org_name = getattr(entry, 'cms_orgshortname', '') or getattr(entry, 'orgshortname', '')
        search_text = org_name.lower()
    elif match_mode == "subject":
        # dc:subjectフィールドから検索テキストを取得
        subject = getattr(entry, 'dc_subject', '') or getattr(entry, 'subject', '')
        search_text = subject.lower()
    elif match_mode == "description":
        # descriptionフィールドからHTMLタグを除去して検索テキストを取得
        description = getattr(entry, 'description', '') or getattr(entry, 'summary', '')
        clean_description = re.sub(r'<[^>]+>', '', description)
        search_text = clean_description.lower()
    else:  # "both"
        search_text = f"{entry.title} {body}".lower()
    
    # include_keywords チェック
    if include_keywords:
        if not any(keyword.lower() in search_text for keyword in include_keywords):
            return False
    
    # exclude_keywords チェック
    if exclude_keywords:
        if any(keyword.lower() in search_text for keyword in exclude_keywords):
            return False
    
    return True


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
            # URL早期キーワードフィルタチェック
            if not should_process_article_url_only(entry, feed_config):
                log.info(f"Skipped by URL keyword filter ({feed_name}): {entry.title}")
                processed.append({
                    "url": entry.link,
                    "title": entry.title,
                    "pubdate": getattr(entry, "published", ""),
                })
                continue
            
            # 要約処理の上限チェック
            global summarize_call_count
            if SUMMARIZE_MAX_CALLS > 0 and summarize_call_count >= SUMMARIZE_MAX_CALLS:
                log.info(f"Reached maximum summarize calls limit ({SUMMARIZE_MAX_CALLS}). Stopping article processing.")
                break
            
            body = fetch_and_clean(entry.link)
            
            # 追加のキーワードフィルタチェック（title/content/both モード用）
            if not should_process_article(entry, body, feed_config):
                log.info(f"Skipped by content keyword filter ({feed_name}): {entry.title}")
                processed.append({
                    "url": entry.link,
                    "title": entry.title,
                    "pubdate": getattr(entry, "published", ""),
                })
                continue
            
            # 要約処理間の間隔制御
            if summarize_call_count > 0 and SUMMARIZE_INTERVAL > 0:
                log.debug(f"Waiting {SUMMARIZE_INTERVAL}s before next summarize call")
                time.sleep(SUMMARIZE_INTERVAL)
            
            # 第1段階: 通常の要約生成
            regular_prompt = (
                f"以下の本文を日本語で3～4文に要約してください。"
                f"最大でもおよそ{cfg['summary_max_chars']}文字に収めてください。"
                "出力は必ず日本語のみとし、英語や見出し、説明は一切書かないでください。\n\n"
                f"本文:\n{body}"
            )
            regular_summary, truncated = summarize(
                regular_prompt, max_chars=cfg["summary_max_chars"]
            )
            summarize_call_count += 1
            
            # 第2段階: 小学生向け要約生成
            if SUMMARIZE_INTERVAL > 0:
                log.debug(f"Waiting {SUMMARIZE_INTERVAL}s before next summarize call")
                time.sleep(SUMMARIZE_INTERVAL)
            
            kids_prompt = (
                f"以下の要約を小学5年生でも理解できるように、やさしい日本語に言い換えてください。"
                "難しい言葉は簡単な言葉に変えて、1～2文でまとめてください。"
                "出力は必ず日本語のみとし、英語や見出し、説明は一切書かないでください。\n\n"
                f"要約:\n{regular_summary}"
            )
            kids_summary, kids_truncated = summarize(
                kids_prompt, max_chars=500
            )
            summarize_call_count += 1
            
            # 両方の要約を結合
            summary = f"{regular_summary}\n\n【小学生向け】\n{kids_summary}"
            truncated = truncated or kids_truncated
            
            if truncated:
                log.warning(f"Summary truncated for {entry.link}")
        except Exception as e:
            log.error(f"Failed to process {entry.link}: {e}")
            continue

        posts.append(
            {
                "title": entry.title, 
                "summary": summary, 
                "url": entry.link,
                "pubdate": getattr(entry, "published", "")
            }
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
    log.info(f"Summarize config: max_calls={SUMMARIZE_MAX_CALLS}, interval={SUMMARIZE_INTERVAL}s")
    
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
    
    log.info(f"Total summarize calls made: {summarize_call_count}")
    log.info("=== RSS Bot finished ===")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()