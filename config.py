from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv.parser import parse_stream

_REPO_ROOT = Path(__file__).resolve().parent


def _load_streamlit_secrets_into_environ() -> None:
    """Map Streamlit Community Cloud secrets to os.environ for RuntimeConfig."""
    try:
        import streamlit as st  # noqa: PLC0415

        for key, value in st.secrets.items():
            if isinstance(value, (str, int, float, bool)):
                os.environ.setdefault(str(key), str(value))
    except Exception:
        return


def _load_dotenv_best_effort(
    dotenv_path: Path | None = None, *, override: bool = False
) -> None:
    """Load .env without logging warnings for invalid lines (e.g. unquoted multi-line PEM).

    Valid KEY=value lines are applied; malformed lines are skipped. Matches
    load_dotenv(override=False) semantics: existing os.environ entries win unless override.
    """
    path = dotenv_path or _REPO_ROOT / ".env"
    if not path.is_file():
        return
    try:
        with open(path, encoding="utf-8") as stream:
            for binding in parse_stream(stream):
                if binding.error or binding.key is None:
                    continue
                key, val = binding.key, binding.value
                if val is None:
                    continue
                if key in os.environ and not override:
                    continue
                os.environ[key] = val
    except OSError:
        return


_load_dotenv_best_effort()


def mask_secret(name: str, value: str | None) -> str:
    """Mask a secret for logs/UI. Never print full values."""
    if not value or not value.strip():
        return f"{name}=(not set)"
    v = value.strip()
    if len(v) <= 8:
        return f"{name}=********"
    return f"{name}={v[:3]}********{v[-4:]}"


def _has_any_llm_key() -> bool:
    keys = ("OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY")
    return any((os.getenv(k) or "").strip() for k in keys)


def has_doku_credentials() -> bool:
    """True when DOKU sandbox keys are present in env (always loaded from .env)."""
    cid = (os.getenv("DOKU_CLIENT_ID") or "").strip()
    sec = (os.getenv("DOKU_SECRET_KEY") or "").strip()
    return bool(cid and sec)


def resolve_payment_mode(
    choice: str | None,
    *,
    warnings: list[str] | None = None,
) -> Literal["mock", "doku_sandbox"]:
    """
    Resolve payment provider from UI selection (Mode pembayaran).

    Env only supplies credentials (DOKU_*); not PAYMENT_MODE switches.
    """
    raw = (choice or "mock").strip().lower()
    if raw not in {"mock", "doku_sandbox"}:
        raw = "mock"
    if raw == "doku_sandbox":
        if has_doku_credentials():
            return "doku_sandbox"
        if warnings is not None:
            warnings.append(
                "Mode DOKU Sandbox dipilih tetapi kredensial DOKU belum lengkap; memakai Mock."
            )
        return "mock"
    return "mock"


@dataclass
class RuntimeConfig:
    """Resolved runtime flags. Secrets are never stored on this object as plain attrs for logging."""

    llm_mode: Literal["mock", "live"]
    payment_mode: Literal["mock", "doku_sandbox"]
    warungflow_env: str
    warnings: list[str] = field(default_factory=list)

    @staticmethod
    def load(*, payment_mode_choice: str | None = None) -> "RuntimeConfig":
        _load_streamlit_secrets_into_environ()
        _load_dotenv_best_effort()
        warnings: list[str] = []
        wf_env = (os.getenv("WARUNGFLOW_ENV") or "local").strip()

        requested_llm = (os.getenv("LLM_MODE") or "auto").strip().lower()
        if requested_llm == "live" and not _has_any_llm_key():
            warnings.append(
                "LLM_MODE was live but no LLM API keys were found; using mock LLM."
            )
            llm_mode: Literal["mock", "live"] = "mock"
        elif requested_llm == "mock" or not _has_any_llm_key():
            llm_mode = "mock"
            if requested_llm != "mock" and not _has_any_llm_key():
                warnings.append("No LLM API key configured; LLM_MODE set to mock.")
        else:
            llm_mode = "live"

        payment_mode = resolve_payment_mode(payment_mode_choice, warnings=warnings)

        return RuntimeConfig(
            llm_mode=llm_mode,
            payment_mode=payment_mode,
            warungflow_env=wf_env,
            warnings=warnings,
        )

    def env_summary_masked(self) -> list[str]:
        doku_ready = "ready" if has_doku_credentials() else "missing"
        lines = [
            f"LLM_MODE={self.llm_mode}",
            f"PAYMENT_MODE={self.payment_mode} (UI)",
            f"DOKU_CREDENTIALS={doku_ready}",
            f"WARUNGFLOW_ENV={self.warungflow_env}",
            mask_secret("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
            mask_secret("GROQ_API_KEY", os.getenv("GROQ_API_KEY")),
            mask_secret("DOKU_CLIENT_ID", os.getenv("DOKU_CLIENT_ID")),
            mask_secret("DOKU_SECRET_KEY", os.getenv("DOKU_SECRET_KEY")),
        ]
        return lines
