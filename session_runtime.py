"""Session persistence, input hashing, and reactive agent run control."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import logging
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from config import RuntimeConfig
from state import AgentState, ExecutionStep

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RUNTIME_DIR = ROOT / "runtime"
SNAPSHOT_VERSION = 1
UI_SESSION_SNAPSHOT_PATH = RUNTIME_DIR / "ui_session_snapshot.json"

_log = logging.getLogger(__name__)

SANDBOX_FINGERPRINT_KEYS = (
    "_order_fingerprints",
    "_payment_fingerprints",
    "_expense_fingerprints",
)

_SET_SESSION_KEYS = frozenset(
    {"webhook_events_seen", *SANDBOX_FINGERPRINT_KEYS}
)

_PERSISTED_SESSION_KEYS = (
    "merchant_profile",
    "raw_orders",
    "payment_transactions",
    "expenses",
    "customers",
    "product_catalogue",
    "catalogue_version",
    "payment_mode_choice",
    "payment_requests_by_order",
    "has_run",
    "run_id",
    "run_token",
    "last_input_hash",
    "loaded_sample_data",
    "auto_refresh_enabled",
    "ui_nav",
    "active_chat_phone",
    "last_export_paths",
    "webhook_events_seen",
    *SANDBOX_FINGERPRINT_KEYS,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def hash_payload_from_session() -> dict[str, Any]:
    from tools import event_store

    return {
        "merchant_profile": st.session_state.get("merchant_profile"),
        "raw_orders": st.session_state.get("raw_orders"),
        "payment_transactions": st.session_state.get("payment_transactions"),
        "expenses": st.session_state.get("expenses"),
        "customers": st.session_state.get("customers"),
        "product_catalogue": st.session_state.get("product_catalogue"),
        "payment_mode": st.session_state.get("payment_mode_choice", "mock"),
        "bot_runtime": event_store.runtime_snapshot_for_hash(),
    }


def compute_session_input_hash() -> str:
    return stable_hash(hash_payload_from_session())


def _serialize_session_value(key: str, val: Any) -> Any:
    if key in _SET_SESSION_KEYS and isinstance(val, set):
        return sorted(val)
    return val


def _deserialize_session_value(key: str, val: Any) -> Any:
    if key in _SET_SESSION_KEYS and isinstance(val, list):
        return set(val)
    return val


def _agent_state_to_snapshot(agent: AgentState) -> dict[str, Any]:
    return asdict(agent)


def _agent_state_from_snapshot(data: dict[str, Any] | None) -> AgentState | None:
    if not data:
        return None
    data = copy.deepcopy(data)
    trace_raw = data.get("execution_trace") or []
    field_names = {f.name for f in fields(AgentState)}
    kwargs = {
        k: v for k, v in data.items() if k in field_names and k != "execution_trace"
    }
    agent = AgentState(**kwargs)
    agent.execution_trace = [
        ExecutionStep(**row) if isinstance(row, dict) else row for row in trace_raw
    ]
    return agent


def save_ui_session_snapshot() -> None:
    """Persist demo session to disk so browser refresh does not reset data."""
    try:
        agent = get_agent_state()
        session_blob: dict[str, Any] = {}
        for key in _PERSISTED_SESSION_KEYS:
            if key in st.session_state:
                session_blob[key] = _serialize_session_value(
                    key, st.session_state[key]
                )
        payload = {
            "version": SNAPSHOT_VERSION,
            "saved_at": _now_iso(),
            "session": session_blob,
            "agent_state": _agent_state_to_snapshot(agent) if agent else None,
        }
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        UI_SESSION_SNAPSHOT_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        _log.debug("ui session snapshot save failed: %s", exc)


def clear_ui_session_snapshot() -> None:
    try:
        UI_SESSION_SNAPSHOT_PATH.unlink(missing_ok=True)
    except OSError as exc:
        _log.debug("ui session snapshot clear failed: %s", exc)


def try_restore_ui_session_snapshot() -> bool:
    """Restore last demo session from disk. Returns True if restored."""
    if not UI_SESSION_SNAPSHOT_PATH.is_file():
        return False
    try:
        payload = json.loads(UI_SESSION_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        if int(payload.get("version") or 0) != SNAPSHOT_VERSION:
            return False
        sess = payload.get("session") or {}
        for key, val in sess.items():
            st.session_state[key] = _deserialize_session_value(key, val)
        agent = _agent_state_from_snapshot(payload.get("agent_state"))
        if agent is not None:
            sync_session_from_agent(agent)
        st.session_state.loaded_sample_data = True
        st.session_state.data_stale = False
        if st.session_state.get("has_run"):
            reconcile_session_freshness()
        return True
    except Exception as exc:
        _log.debug("ui session snapshot restore failed: %s", exc)
        return False


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
        "product_catalogue": None,
        "catalogue_version": "",
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
        "_ui_snapshot_restored": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val if key != "webhook_events_seen" else set()


def load_sample_data_into_session(*, force: bool = False) -> None:
    """Load CSV samples or restore disk snapshot once per browser session."""
    if st.session_state.get("loaded_sample_data") and not force:
        return

    if force:
        st.session_state._ui_snapshot_restored = True
    elif not st.session_state.get("_ui_snapshot_restored"):
        st.session_state._ui_snapshot_restored = True
        if try_restore_ui_session_snapshot():
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

    from tools.catalogue_tools import load_product_catalogue_from_csv, catalogue_version

    st.session_state.product_catalogue = load_product_catalogue_from_csv()
    st.session_state.catalogue_version = catalogue_version(st.session_state.product_catalogue)

    st.session_state.loaded_sample_data = True
    st.session_state.payment_requests_by_order = {}
    st.session_state.webhook_events_seen = set()


def clear_sandbox_duplicate_state(target: dict[str, Any] | None = None) -> None:
    """Clear Live Data Sandbox idempotency sets (plain dict for tests, else Streamlit)."""
    if target is not None:
        for key in SANDBOX_FINGERPRINT_KEYS:
            target[key] = set()
        target["webhook_events_seen"] = set()
        return
    for key in SANDBOX_FINGERPRINT_KEYS:
        st.session_state[key] = set()
    st.session_state.webhook_events_seen = set()


def reset_bot_demo_history() -> None:
    """Clear WhatsApp bot JSONL history (chat, orders, payments) and refresh agent."""
    from tools import event_store

    event_store.reset_runtime_events()
    mark_data_changed("bot_events_reset")


def reset_demo_session() -> None:
    clear_ui_session_snapshot()
    st.session_state._ui_snapshot_restored = False
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
    clear_sandbox_duplicate_state()
    st.session_state._pending_agent_run = True
    st.session_state._pending_trigger = "reset_demo"
    st.session_state.ui_status = "Auto-refreshing"
    st.session_state.ui_status_detail = "Reset demo data"
    load_sample_data_into_session(force=True)


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
    agent.payment_requests_by_order = dict(
        st.session_state.get("payment_requests_by_order") or {}
    )
    agent.product_catalogue = copy.deepcopy(st.session_state.get("product_catalogue") or [])
    agent.catalogue_version = str(st.session_state.get("catalogue_version") or "")
    return agent


def sync_session_from_agent(agent: AgentState) -> None:
    st.session_state.agent_state = agent
    st.session_state.state = agent
    st.session_state.payment_requests_by_order = dict(
        getattr(agent, "payment_requests_by_order", {}) or {}
    )
    if agent.exported_files:
        st.session_state.last_export_paths = dict(agent.exported_files)
    if getattr(agent, "product_catalogue", None):
        st.session_state.product_catalogue = copy.deepcopy(agent.product_catalogue)
        st.session_state.catalogue_version = agent.catalogue_version
    save_ui_session_snapshot()


def get_agent_state() -> AgentState | None:
    return st.session_state.get("agent_state") or st.session_state.get("state")


def _queue_agent_refresh(trigger: str) -> None:
    st.session_state._pending_agent_run = True
    st.session_state._pending_trigger = trigger
    st.session_state.data_stale = False
    st.session_state.ui_status = "Auto-refreshing"
    st.session_state.ui_status_detail = trigger


def reconcile_session_freshness() -> None:
    """
    Align stale UI flags with session/bot input hash.

    When auto-refresh is on (default), queue agent run instead of nagging user.
    """
    current = compute_session_input_hash()
    last = st.session_state.get("last_input_hash")

    if last is not None and current == last:
        st.session_state.data_stale = False
        return

    auto = bool(st.session_state.get("auto_refresh_enabled", True))
    if auto:
        _queue_agent_refresh("session_data_changed")
        return

    st.session_state.data_stale = True
    st.session_state.ui_status = "Data changed, refresh needed"
    st.session_state.ui_status_detail = "Input changed since last run"


def mark_data_changed(trigger: str) -> None:
    new_hash = compute_session_input_hash()
    last = st.session_state.get("last_input_hash")
    if last is not None and new_hash == last:
        save_ui_session_snapshot()
        return
    save_ui_session_snapshot()
    if st.session_state.get("auto_refresh_enabled", True):
        _queue_agent_refresh(trigger)
    else:
        st.session_state.data_stale = True
        st.session_state.ui_status = "Data changed, refresh needed"
        st.session_state.ui_status_detail = trigger


def schedule_initial_run() -> None:
    if not st.session_state.get("has_run"):
        st.session_state._pending_agent_run = True
        st.session_state._pending_trigger = "initial_load"
        st.session_state.data_stale = False
        return
    reconcile_session_freshness()


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
        seed.payment_requests_by_order = dict(
            getattr(prior, "payment_requests_by_order", {})
            or st.session_state.get("payment_requests_by_order")
            or {}
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
    st.session_state._pending_agent_run = False
    st.session_state.run_token = int(st.session_state.get("run_token", 0)) + 1

    if final.final_status == "ERROR":
        st.session_state.ui_status = "Error"
    elif final.final_status == "NEEDS_REVIEW":
        st.session_state.ui_status = "Last run needs review"
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
