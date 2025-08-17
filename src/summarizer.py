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

def summarize(text: str, max_chars: int = 1800) -> tuple[str, bool]:
    """
    Ask LM Studio to summarize *text* into Japanese (3–4 sentences),
    and then append one extra sentence as an easy-to-understand version
    for elementary school students.
    """

    cfg = load_config()

    lm_studio_url: str | None = cfg.get("lm_studio_url")
    lm_studio_model: str | None = cfg.get("lm_studio_model")

    if not lm_studio_url or not lm_studio_model:
        raise RuntimeError(
            "LM Studio URL and model must be set in the environment "
            "(e.g. via .env or docker-compose env_file)."
        )

    # Build the prompt – Japanese only + easy version
    prompt = (
        f"以下の本文を日本語で3～4文に要約してください。"
        f"最大でもおよそ{max_chars}文字に収めてください。"
        "出力は必ず日本語のみとし、英語や見出し、説明は一切書かないでください。\n\n"
        "次に、その要約の直後に『小学生にも理解できる要約』を一文だけ追記してください。"
        "この一文は、難しい言葉を使わず、小学5年生が理解できる程度のやさしい日本語にしてください。\n\n"
        "本文:\n"
        f"{text}\n\n"
        "出力形式:\n"
        "[要約]\n"
        "[小学生にも理解できる要約]"
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