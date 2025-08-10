# article_extractor.py
"""
Utility for downloading a web page and extracting the main article text.
The implementation uses `requests` to fetch the URL and
`readability‑lxml` + BeautifulSoup to isolate the readable content.
"""

import requests
from bs4 import BeautifulSoup
from readability import Document

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
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    doc = Document(resp.text)
    cleaned_html = doc.summary()
    soup = BeautifulSoup(cleaned_html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return text