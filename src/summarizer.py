# summarizer.py
"""
Module that talks to a local LM Studio instance and asks it to summarize text.
All configuration values (LM Studio URL / model, etc.) are now read from
the environment via `config.load_config()`.  This keeps the module free of
hard‑coded constants and allows Docker / local runs to share the same code.
"""

import requests
import os
from .config import load_config

def summarize(prompt: str, max_chars: int = 1800) -> tuple[str, bool]:
    """
    Ask LM Studio to process text based on the given prompt.
    
    Parameters:
    - prompt: The complete prompt to send to LM Studio
    - max_chars: Maximum characters for truncation if needed
    """

    cfg = load_config()

    lm_studio_url: str | None = cfg.get("lm_studio_url")
    lm_studio_model: str | None = cfg.get("lm_studio_model")

    if not lm_studio_url or not lm_studio_model:
        raise RuntimeError(
            "LM Studio URL and model must be set in the environment "
            "(e.g. via .env or docker-compose env_file)."
        )

    payload = {
        "model": lm_studio_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは簡潔な日本語要約者です。"
                    "出力は必ず日本語のみとし、指定された形式を厳守してください。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,  # ぶれを抑える
    }

    # タイムアウト設定を環境変数から取得
    timeout = int(os.getenv('SUMMARIZE_TIMEOUT', '1200'))  # デフォルト20分
    
    resp = requests.post(lm_studio_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    summary = resp.json()["choices"][0]["message"]["content"].strip()

    # Truncate if necessary
    if len(summary) > max_chars:
        return summary[:max_chars] + "…", True
    return summary, False