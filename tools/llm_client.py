from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _groq_key() -> str | None:
    k = (os.getenv("GROQ_API_KEY") or "").strip()
    return k or None


def groq_chat(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.4,
) -> str | None:
    """Call Groq chat completions. Returns None on failure (caller uses template fallback)."""
    api_key = _groq_key()
    if not api_key:
        return None

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    model = (os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        GROQ_CHAT_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "WarungFlow/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices") or []
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content")
        return str(content).strip() if content else None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Groq API call failed: %s", type(exc).__name__)
        return None


def refine_payment_reminder(
    customer_name: str,
    order_id: str,
    amount_expected: Any,
    paid: int,
    template: str,
) -> str:
    system = (
        "Kamu asisten warung kecil di Indonesia. Tulis pesan WhatsApp singkat, "
        "sopan, Bahasa Indonesia, untuk menagih pembayaran tanpa menyalahkan pelanggan."
    )
    user = (
        f"Perbaiki pesan ini untuk pelanggan {customer_name}, pesanan {order_id}, "
        f"total Rp {amount_expected}, sudah dibayar Rp {paid}:\n\n{template}\n\n"
        "Balas hanya teks pesan WhatsApp, tanpa penjelasan."
    )
    refined = groq_chat(user, system_prompt=system, max_tokens=200)
    return refined if refined else template


def refine_financing_narrative(base_narrative: str, score: int) -> str:
    system = (
        "Kamu konsultan UMKM Indonesia. Jelaskan kesiapan pembiayaan dengan bahasa "
        "sederhana, ramah, non-teknis, maksimal 3 kalimat."
    )
    user = (
        f"Skor kesehatan kasflow: {score}/100.\n"
        f"Narasi dasar:\n{base_narrative}\n\n"
        "Tulis ulang narasi untuk pemilik warung."
    )
    refined = groq_chat(user, system_prompt=system, max_tokens=280)
    return refined if refined else base_narrative
