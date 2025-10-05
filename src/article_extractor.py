# article_extractor.py
"""
Utility for downloading a web page and extracting the main article text.
The implementation uses `requests` to fetch the URL and
`readability‑lxml` + BeautifulSoup to isolate the readable content.
"""

import requests
import os
from bs4 import BeautifulSoup
from readability import Document
from src.http_session import build_session, get_default_headers

def fetch_and_clean(url: str) -> str:
    """
    Download the page at *url*, parse it with readability, and return
    a plain‑text version of the article body.

    Parameters
    ----------
    url : str
        URL of the article to fetch.

    Returns
    -------
    str
        Cleaned, plain‑text representation of the article body.
    """
    # タイムアウト設定を環境変数から取得
    timeout = int(os.getenv('ARTICLE_TIMEOUT', '30'))  # デフォルト30秒

    session = build_session()
    headers = get_default_headers()
    resp = session.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    doc = Document(resp.text)
    cleaned_html = doc.summary()
    soup = BeautifulSoup(cleaned_html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return text