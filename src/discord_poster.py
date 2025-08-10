# discord_poster.py
"""
Functions for sending messages to a Discord Webhook.
The module takes care of Discord’s character limits and splits long
content into multiple embeds if necessary.
"""

import requests
import time
from typing import List, Dict

def _split_long_text(text: str, limit: int) -> List[str]:
    """
    指定した文字数 (limit) を超えないようにテキストを分割します。
    単語の途中で切れないように最後のスペースまで戻ります。

    Parameters
    ----------
    text : str
        文字列を分割する対象。
    limit : int
        各パートの最大文字数。

    Returns
    -------
    list[str]
        分割されたテキストのリスト。各要素は `limit` 以内。
    """
    parts = []
    while text:
        part = text[:limit]
        if len(text) > limit and not text[limit].isspace():
            last_space = part.rfind(" ")
            if last_space != -1:
                part = part[:last_space]
        parts.append(part)
        text = text[len(part):].lstrip()
    return parts

def post_to_webhook(posts: List[Dict], webhook_url: str,
                    msg_limit: int = 2000, embed_desc_lim: int = 4096):
    """
    posts : [{'title':..., 'summary':..., 'url':...}] のリスト
    webhook_url : Discord の Webhook URL
    msg_limit : content フィールドの最大文字数 (Discord で 2000)
    embed_desc_lim : embed description の最大文字数 (4096)

    Discord へメッセージを送信し、必要に応じて embed を分割します。
    """
    for p in posts:
        # タイトルは 256 文字以内に切り捨てる（Discord の embed title 上限）
        title = p["title"][:256]

        summary = p["summary"]
        if len(summary) <= embed_desc_lim:
            # 1 つの embed に収まる場合
            embeds = [{"title": title, "url": p["url"], "description": summary}]
        else:
            # 1 embed が足りない場合は分割
            parts = _split_long_text(summary, embed_desc_lim)
            embeds = [{"title": title if i==0 else f"{title} ({i+1})",
                       "url": p["url"],
                       "description": part}
                      for i, part in enumerate(parts)]

        # 1 メッセージごとに Webhook に送信
        for embed in embeds:
            payload = {"embeds": [embed]}
            resp = requests.post(webhook_url, json=payload)
            resp.raise_for_status()
            # Discord のレートリミットを回避するため 1 秒待つ
            time.sleep(1)