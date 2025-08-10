# summarizer.py
"""
Module that talks to a local LM Studio instance and asks it to summarize text.
All configuration values (LM Studio URL / model, etc.) are now read from
the environment via `config.load_config()`.  This keeps the module free of
hard‑coded constants and allows Docker / local runs to share the same code.
"""

import requests
from .config import load_config

def summarize(text: str, max_chars: int = 1800) -> tuple[str, bool]:
    """
    Ask LM Studio to summarize *text* into 3–4 sentences and then translate
    that summary into Japanese.  The result is truncated to *max_chars* if it
    would otherwise exceed that length.

    Parameters
    ----------
    text : str
        The article body to be summarized.
    max_chars : int, optional
        Maximum number of characters allowed in the returned summary
        (default 1800).  The caller can override this, but a sensible
        default is supplied via the environment variable
        `SUMMARY_MAX_CHARS`.

    Returns
    -------
    tuple[str, bool]
        *summary_text* – the (possibly truncated) summary in Japanese.
        *truncated*    – True if the output was cut to fit *max_chars*.

    Raises
    ------
    RuntimeError
        If the LM Studio URL or model is missing from the environment.
    """
    cfg = load_config()

    lm_studio_url: str | None = cfg.get("lm_studio_url")
    lm_studio_model: str | None = cfg.get("lm_studio_model")

    if not lm_studio_url or not lm_studio_model:
        raise RuntimeError(
            "LM Studio URL and model must be set in the environment "
            "(e.g. via .env or docker‑compose env_file)."
        )

    # Build the prompt – 3–4 sentences + Japanese translation
    prompt = (
        f"Summarize the following article in 3-4 sentences.\n\n{text}\n\n"
        f"(If it is too long, trim to about {max_chars} characters. "
        "Then after, translate the summary into Japanese.)"
    )

    payload = {
        "model": lm_studio_model,
        "messages": [
            {"role": "system", "content": "You are a concise summarizer."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    resp = requests.post(lm_studio_url, json=payload, timeout=60)
    resp.raise_for_status()
    summary = resp.json()["choices"][0]["message"]["content"].strip()

    # Truncate if necessary
    if len(summary) > max_chars:
        return summary[:max_chars] + "…", True
    return summary, False