"""Session persistence, input hashing, and reactive agent run control."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from config import RuntimeConfig
from state import AgentState

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def hash_payload_from_session() -> dict[str, Any]:
    return {
        "merchant_profile": st.session_state.get("merchant_profile"),
        "raw_orders": st.session_state.get("raw_orders"),
        "payment_transactions": st.session_state.get("payment_transactions"),
        "expenses": st.session_state.get("expenses"),
        "customers": st.session_state.get("customers"),
        "payment_mode": st.session_state.get("payment_mode_choice", "mock"),
    }


def compute_session_input_hash() -> str:
    return stable_hash(hash_payload_from_session())


def init_session_defaults() -> None:
    defaults: dict[str, Any] = {
        "agent_state": None,
        "state": None,
        "has_run": False,
        "run_id": 0,
        "loaded_sample_data": False,
        "raw_orders": None,
        "payment_transactions": None,
        "expenses": None,
        "customers": None,
        "merchant_profile": None,
        "payment_mode_choice": "mock",
        "last_input_hash": None,
        "auto_refresh_enabled": True,
        "data_stale": False,
        "last_export_paths": None,
        "run_token": 0,
        "ui_nav": "dashboard",
        "ui_status": "Fresh",
        "ui_status_detail": "",
        "payment_requests_by_order": {},
        "webhook_events_seen": set(),
        "_pending_agent_run": False,
        "_pending_trigger": "initial_load",
        "_bootstrapped": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val if key != "webhook_events_seen" else set()


def load_sample_data_into_session(*, force: bool = False) -> None:
    if st.session_state.loaded_sample_data and not force:
        return

    with open(DATA_DIR / "merchant_profile.json", encoding="utf-8") as f:
        st.session_state.merchant_profile = json.load(f)

    raw_path = DATA_DIR / "sample_orders_whatsapp.txt"
    st.session_state.raw_orders = [
        ln for ln in raw_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]

    with open(DATA_DIR / "sample_qris_transactions.csv", encoding="utf-8") as f:
        st.session_state.payment_transactions = list(csv.DictReader(f))

    with open(DATA_DIR / "sample_expenses.csv", encoding="utf-8") as f:
        st.session_state.expenses = list(csv.DictReader(f))

    with open(DATA_DIR / "sample_customers.csv", encoding="utf-8") as f:
        st.session_state.customers = [dict(r) for r in csv.DictReader(f)]

    st.session_state.loaded_sample_data = True
    st.session_state.payment_requests_by_order = {}
    st.session_state.webhook_events_seen = set()


def reset_demo_session() -> None:
    st.session_state.agent_state = None
    st.session_state.state = None
    st.session_state.has_run = False
    st.session_state.run_id = 0
    st.session_state.loaded_sample_data = False
    st.session_state.last_input_hash = None
    st.session_state.data_stale = False
    st.session_state.last_export_paths = None
    st.session_state.payment_requests_by_order = {}
    st.session_state.webhook_events_seen = set()
    load_sample_data_into_session(force=True)
    st.session_state._pending_agent_run = True
    st.session_state._pending_trigger = "reset_demo"
    st.session_state.ui_status = "Auto-refreshing"
    st.session_state.ui_status_detail = "Reset demo data"


def build_seed_agent_state(cfg: RuntimeConfig) -> AgentState:
    """Build AgentState from session inputs (does not clear pipeline outputs)."""
    agent = AgentState(
        payment_mode=cfg.payment_mode,
        llm_mode=cfg.llm_mode,
        merchant_profile=copy.deepcopy(st.session_state.merchant_profile),
        raw_orders=list(st.session_state.raw_orders or []),
        payment_transactions=[
            dict(r) for r in (st.session_state.payment_transactions or [])
        ],
        expenses=[dict(r) for r in (st.session_state.expenses or [])],
        customers=[dict(r) for r in (st.session_state.customers or [])],
    )
    return agent


def sync_session_from_agent(agent: AgentState) -> None:
    st.session_state.agent_state = agent
    st.session_state.state = agent
    if agent.exported_files:
        st.session_state.last_export_paths = dict(agent.exported_files)


def get_agent_state() -> AgentState | None:
    return st.session_state.get("agent_state") or st.session_state.get("state")


def mark_data_changed(trigger: str) -> None:
    new_hash = compute_session_input_hash()
    last = st.session_state.get("last_input_hash")
    if last is not None and new_hash == last:
        return
    if st.session_state.get("auto_refresh_enabled", True):
        st.session_state._pending_agent_run = True
        st.session_state._pending_trigger = trigger
        st.session_state.data_stale = False
        st.session_state.ui_status = "Auto-refreshing"
        st.session_state.ui_status_detail = trigger
    else:
        st.session_state.data_stale = True
        st.session_state.ui_status = "Data changed, refresh needed"
        st.session_state.ui_status_detail = trigger


def schedule_initial_run() -> None:
    if not st.session_state.get("has_run"):
        st.session_state._pending_agent_run = True
        st.session_state._pending_trigger = "initial_load"


def run_agent_once(
    cfg: RuntimeConfig,
    *,
    trigger: str,
    on_step: Any | None = None,
) -> AgentState:
    from agents.orchestrator import run_agent_stream

    st.session_state.run_id = int(st.session_state.get("run_id", 0)) + 1
    run_id = st.session_state.run_id
    seed = build_seed_agent_state(cfg)
    if st.session_state.get("agent_state"):
        prior = st.session_state.agent_state
        seed.execution_trace = list(prior.execution_trace)
        seed.payment_requests = list(prior.payment_requests or [])
        if hasattr(prior, "payment_requests_by_order"):
            seed.payment_requests_by_order = dict(
                getattr(prior, "payment_requests_by_order", {}) or {}
            )

    final: AgentState | None = None
    for snapshot in run_agent_stream(
        cfg, seed, run_id=run_id, trigger_reason=trigger, reset_pipeline=True
    ):
        final = snapshot
        if on_step and snapshot.execution_trace:
            on_step(snapshot.execution_trace[-1])

    assert final is not None
    sync_session_from_agent(final)
    st.session_state.has_run = True
    st.session_state.last_input_hash = compute_session_input_hash()
    st.session_state.data_stale = False
    st.session_state.run_token = int(st.session_state.get("run_token", 0)) + 1

    if final.final_status == "NEEDS_REVIEW":
        st.session_state.ui_status = "Last run needs review"
    elif final.errors:
        st.session_state.ui_status = "Error"
    else:
        st.session_state.ui_status = "Last run completed"
    st.session_state.ui_status_detail = (
        f"Run {run_id} · {trigger} · {final.final_status or 'COMPLETE'}"
    )
    return final


def process_pending_agent_run(
    cfg: RuntimeConfig, *, on_step: Any | None = None
) -> bool:
    """Run agent if pending. Returns True if a run was executed."""
    if not st.session_state.get("_pending_agent_run"):
        return False
    trigger = str(st.session_state.get("_pending_trigger") or "refresh")
    st.session_state._pending_agent_run = False
    run_agent_once(cfg, trigger=trigger, on_step=on_step)
    return True
