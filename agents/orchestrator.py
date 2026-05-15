from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from typing import Any

from agents.tool_handlers import TOOL_REGISTRY
from config import RuntimeConfig
from tools.doku_sandbox_provider import DokuSandboxProvider
from tools.mock_payment_provider import MockPaymentProvider
from state import AgentState

logger = logging.getLogger(__name__)

MAX_STEPS = 20


def decide_next_action(state: AgentState) -> str | None:
    """State-driven planner: next action depends on gaps and validation needs."""
    if state.merchant_profile is None:
        return "LOAD_MERCHANT_PROFILE"
    if state.raw_orders is None:
        return "LOAD_ORDERS"
    if state.parsed_orders is None:
        return "PARSE_ORDERS"
    if _parsed_has_unknown_amounts(state) and not state.amount_pass_done:
        return "ESTIMATE_OR_FLAG_UNKNOWN_AMOUNTS"
    if state.payment_transactions is None:
        return "LOAD_PAYMENTS"
    if state.expenses is None:
        return "LOAD_EXPENSES"
    if state.customers is None:
        return "LOAD_CUSTOMERS"
    if state.reconciliation_results is None:
        return "RECONCILE_PAYMENTS"
    if state.payment_issues is None:
        return "DETECT_PAYMENT_ISSUES"
    if state.payment_requests is None:
        return "RESOLVE_PAYMENT_REQUESTS"
    if _payment_requests_need_status_poll(state):
        return "CHECK_PAYMENT_STATUS"
    if state.cashflow_summary is None:
        return "CALCULATE_CASHFLOW"
    if state.health_score is None:
        return "SCORE_CASHFLOW_HEALTH"
    if state.reminders is None:
        return "GENERATE_REMINDERS"
    if state.financing_readiness is None:
        return "GENERATE_FINANCING_READINESS"
    if state.daily_report is None:
        return "GENERATE_DAILY_REPORT"
    if state.validation_report is None:
        return "VALIDATE_OUTPUTS"
    if state.exported_files is None:
        return "EXPORT_REPORTS"
    return None


def _parsed_has_unknown_amounts(state: AgentState) -> bool:
    for row in state.parsed_orders or []:
        if row.get("amount_expected") is None:
            return True
    return False


def _payment_requests_need_status_poll(state: AgentState) -> bool:
    reqs = state.payment_requests or []
    if not reqs:
        return False
    for pr in reqs:
        st = str(pr.get("status", "")).upper()
        if st in {"PENDING", "UNKNOWN", ""}:
            return True
    return False


def execute_tool(name: str, state: AgentState, provider_box: list[Any]) -> None:
    """Dispatch tool via registry; must append execution trace."""
    handler = TOOL_REGISTRY.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    handler(state, provider_box)


def _build_provider_box(cfg: RuntimeConfig) -> list[Any]:
    if cfg.payment_mode == "doku_sandbox":
        provider: Any = DokuSandboxProvider(
            (os.getenv("DOKU_CLIENT_ID") or "").strip(),
            (os.getenv("DOKU_SECRET_KEY") or "").strip(),
            (os.getenv("DOKU_SANDBOX_BASE_URL") or "").strip() or None,
        )
    else:
        provider = MockPaymentProvider()
    return [provider]


def _finalize_state(state: AgentState) -> None:
    if state.errors:
        state.final_status = "NEEDS_REVIEW"
    else:
        state.final_status = "COMPLETE"


def run_agent_stream(
    cfg: RuntimeConfig,
    state: AgentState | None = None,
) -> Iterator[AgentState]:
    """
    Generator that yields AgentState after each tool execution.
    Yields once more after final_status is set.
    """
    state = state or AgentState(
        payment_mode=cfg.payment_mode,
        llm_mode=cfg.llm_mode,
    )
    provider_box = _build_provider_box(cfg)

    steps_run = 0
    for _ in range(MAX_STEPS):
        action = decide_next_action(state)
        if action is None:
            break
        steps_run += 1
        try:
            execute_tool(action, state, provider_box)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tool %s failed", action)
            state.errors.append(f"{action}: {exc}")
            state.final_status = "NEEDS_REVIEW"
            yield state
            return
        yield state

    if decide_next_action(state) is not None:
        state.errors.append(f"max_steps ({MAX_STEPS}) reached")
        state.final_status = "NEEDS_REVIEW"
    elif state.final_status is None:
        _finalize_state(state)

    yield state


def run_agent(cfg: RuntimeConfig | None = None) -> AgentState:
    """Run full loop and return final state (for smoke tests / non-streaming callers)."""
    cfg = cfg or RuntimeConfig.load()
    final: AgentState | None = None
    for snapshot in run_agent_stream(cfg):
        final = snapshot
    assert final is not None
    return final
