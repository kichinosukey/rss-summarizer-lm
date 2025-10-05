import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def get_default_headers() -> dict:
    """
    Build default HTTP headers, overridable via environment variables.
    Env vars:
      - HTTP_UA
      - HTTP_ACCEPT_LANGUAGE
      - HTTP_ACCEPT
    """
    ua = os.getenv(
        "HTTP_UA",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124 Safari/537.36",
    )
    accept_language = os.getenv("HTTP_ACCEPT_LANGUAGE", "ja-JP, ja;q=0.9")
    accept = os.getenv(
        "HTTP_ACCEPT",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    )
    return {
        "User-Agent": ua,
        "Accept-Language": accept_language,
        "Accept": accept,
    }


def build_session() -> requests.Session:
    """
    Create a requests Session with light retries and backoff.
    Configurable via:
      - HTTP_RETRY_TOTAL (int, default 3)
      - HTTP_RETRY_BACKOFF (float, default 0.5)
    """
    total = int(os.getenv("HTTP_RETRY_TOTAL", "3"))
    backoff = float(os.getenv("HTTP_RETRY_BACKOFF", "0.5"))

    retry = Retry(
        total=total,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.headers.update(get_default_headers())
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session