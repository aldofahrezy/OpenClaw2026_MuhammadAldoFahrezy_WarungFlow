"""Individual tool handlers for the orchestrator registry."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Callable

from tools.cashflow_tools import calculate_cashflow, score_cashflow_health
from tools.export_utils import export_all
from tools.report_generator import (
    generate_daily_report,
    generate_financing_readiness,
    generate_reminders,
    validate_outputs,
)
from tools.parsers import parse_orders_batch
from tools.mock_payment_provider import MockPaymentProvider
from tools.reconciliation_tools import detect_payment_issues, reconcile_orders
from state import AgentState

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

ToolHandler = Callable[[AgentState, list[Any]], None]


def _has_unpaid(state: AgentState) -> bool:
    for r in state.reconciliation_results or []:
        if r.get("status") in {"UNPAID", "PARTIALLY_PAID"}:
            return True
    return False


def _append_unpaid_payment_requests(
    state: AgentState, prov: Any, provider_box: list[Any]
) -> None:
    if state.payment_requests is None:
        state.payment_requests = []
    for r in state.reconciliation_results or []:
        if r.get("status") not in {"UNPAID", "PARTIALLY_PAID"}:
            continue
        oid = str(r.get("order_id"))
        if oid in state.payment_requests_by_order:
            state.payment_requests.append(state.payment_requests_by_order[oid])
            continue
        order = next(
            (o for o in (state.parsed_orders or []) if str(o.get("order_id")) == oid),
            None,
        )
        amt = order.get("amount_expected") if order else None
        if not isinstance(amt, int):
            continue
        remaining = max(0, amt - int(r.get("matched_amount") or 0))
        if remaining <= 0:
            continue
        pr = prov.create_payment_request(oid, remaining, f"Bill {oid}")
        state.payment_requests_by_order[oid] = pr
        state.payment_requests.append(pr)


def tool_load_merchant_profile(state: AgentState, provider_box: list[Any]) -> None:
    if state.merchant_profile:
        state.trace(
            decision="Merchant context present; use session profile.",
            tool="LOAD_MERCHANT_PROFILE",
            input_summary="session",
            output_summary=f"keys={list(state.merchant_profile.keys())}",
        )
        return
    path = DATA_DIR / "merchant_profile.json"
    with open(path, encoding="utf-8") as f:
        state.merchant_profile = json.load(f)
    state.trace(
        decision="Merchant context missing; load local profile.",
        tool="LOAD_MERCHANT_PROFILE",
        input_summary=str(path.name),
        output_summary=f"loaded keys={list(state.merchant_profile.keys())}",
    )


def tool_load_orders(state: AgentState, provider_box: list[Any]) -> None:
    if state.raw_orders is not None:
        state.trace(
            decision="Raw orders present; use session WhatsApp lines.",
            tool="LOAD_ORDERS",
            input_summary="session",
            output_summary=f"lines={len(state.raw_orders)}",
        )
        return
    path = DATA_DIR / "sample_orders_whatsapp.txt"
    raw = path.read_text(encoding="utf-8").splitlines()
    state.raw_orders = [ln for ln in raw if ln.strip()]
    state.trace(
        decision="No raw orders in state; ingest sample WhatsApp lines.",
        tool="LOAD_ORDERS",
        input_summary=str(path.name),
        output_summary=f"lines={len(state.raw_orders)}",
    )


def tool_parse_orders(state: AgentState, provider_box: list[Any]) -> None:
    state.parsed_orders = parse_orders_batch(state.raw_orders or [])
    state.trace(
        decision="Parsed orders empty or stale; run deterministic parser.",
        tool="PARSE_ORDERS",
        input_summary=f"{len(state.raw_orders or [])} lines",
        output_summary=f"parsed={len(state.parsed_orders)}",
    )


def tool_estimate_or_flag_unknown_amounts(
    state: AgentState, provider_box: list[Any]
) -> None:
    updated = 0
    for row in state.parsed_orders or []:
        if row.get("amount_expected") is None:
            row["status"] = "NEEDS_REVIEW"
            row["parser_note"] = (row.get("parser_note") or "") + "; flagged_unknown_amount"
            updated += 1
    state.amount_pass_done = True
    state.trace(
        decision="Unknown amounts detected after parse; flag for review.",
        tool="ESTIMATE_OR_FLAG_UNKNOWN_AMOUNTS",
        input_summary="parsed_orders",
        output_summary=f"rows_flagged={updated}",
        status="warn" if updated else "ok",
    )


def tool_load_payments(state: AgentState, provider_box: list[Any]) -> None:
    if state.payment_transactions is not None:
        state.trace(
            decision="Payments present; use session transaction pool.",
            tool="LOAD_PAYMENTS",
            input_summary="session",
            output_summary=f"txns={len(state.payment_transactions)}",
        )
        return
    path = DATA_DIR / "sample_qris_transactions.csv"
    with open(path, encoding="utf-8") as f:
        state.payment_transactions = list(csv.DictReader(f))
    state.trace(
        decision="Payment pool missing; load transactions.",
        tool="LOAD_PAYMENTS",
        input_summary=str(path.name),
        output_summary=f"txns={len(state.payment_transactions)}",
    )


def tool_load_expenses(state: AgentState, provider_box: list[Any]) -> None:
    if state.expenses is not None:
        state.trace(
            decision="Expenses present; use session ledger.",
            tool="LOAD_EXPENSES",
            input_summary="session",
            output_summary=f"rows={len(state.expenses)}",
        )
        return
    path = DATA_DIR / "sample_expenses.csv"
    with open(path, encoding="utf-8") as f:
        state.expenses = list(csv.DictReader(f))
    state.trace(
        decision="Expense ledger missing; load notes.",
        tool="LOAD_EXPENSES",
        input_summary=str(path.name),
        output_summary=f"rows={len(state.expenses)}",
    )


def tool_load_customers(state: AgentState, provider_box: list[Any]) -> None:
    path = DATA_DIR / "sample_customers.csv"
    customers: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            customers.append(dict(row))
    seen = {c.get("customer_name") for c in customers}
    for o in state.parsed_orders or []:
        for key in ("customer_name", "payer_name"):
            n = o.get(key)
            if n and n not in seen:
                seen.add(n)
                customers.append(
                    {
                        "customer_name": n,
                        "phone": "",
                        "customer_type": "from_order",
                        "usual_payment_behavior": key,
                    }
                )
    state.customers = customers
    state.trace(
        decision="Customer index missing; load CSV and merge order names.",
        tool="LOAD_CUSTOMERS",
        input_summary=str(path.name),
        output_summary=f"customers={len(customers)}",
    )


def tool_reconcile_payments(state: AgentState, provider_box: list[Any]) -> None:
    state.reconciliation_results = reconcile_orders(
        state.parsed_orders or [], state.payment_transactions or []
    )
    state.trace(
        decision="Reconciliation not computed; match payments to orders.",
        tool="RECONCILE_PAYMENTS",
        input_summary="orders+payments",
        output_summary=f"rows={len(state.reconciliation_results)}",
    )


def tool_detect_payment_issues(state: AgentState, provider_box: list[Any]) -> None:
    state.payment_issues = detect_payment_issues(
        state.parsed_orders or [], state.reconciliation_results or []
    )
    state.trace(
        decision="Issue list uninitialized; scan reconciliation outcomes.",
        tool="DETECT_PAYMENT_ISSUES",
        input_summary="reconciliation_results",
        output_summary=f"issues={len(state.payment_issues)}",
    )


def tool_simulate_doku_webhook(state: AgentState, provider_box: list[Any]) -> None:
    """Idempotent webhook simulation — payment row added via session sandbox."""
    state.trace(
        decision="Simulate DOKU webhook (idempotent by event_id in session).",
        tool="DOKU_WEBHOOK_SIMULATOR",
        input_summary="mock",
        output_summary="handled in UI sandbox before refresh",
        status="ok",
    )


def tool_resolve_payment_requests(state: AgentState, provider_box: list[Any]) -> None:
    prov = provider_box[0]
    if state.payment_requests is None:
        state.payment_requests = []
    if state.payment_mode == "doku_sandbox" and _has_unpaid(state):
        try:
            _append_unpaid_payment_requests(state, prov, provider_box)
        except Exception as e:  # noqa: BLE001
            logger.warning("Payment provider failed; falling back to mock: %s", e)
            state.errors.append(str(e))
            state.payment_mode = "mock"
            provider_box[0] = MockPaymentProvider()
            prov = provider_box[0]
            state.payment_requests = list(state.payment_requests_by_order.values())
            _append_unpaid_payment_requests(state, prov, provider_box)
            state.trace(
                decision="DOKU path failed; mock payment requests created.",
                tool="RESOLVE_PAYMENT_REQUESTS",
                input_summary="unpaid/partial",
                output_summary=f"requests={len(state.payment_requests)}",
                status="warn",
            )
            return
    elif state.payment_mode == "mock" and _has_unpaid(state):
        _append_unpaid_payment_requests(state, prov, provider_box)
    state.trace(
        decision="Payment request phase; create or skip based on mode and unpaid balance.",
        tool="RESOLVE_PAYMENT_REQUESTS",
        input_summary=f"mode={state.payment_mode}",
        output_summary=f"requests={len(state.payment_requests)}",
    )


def tool_check_payment_status(state: AgentState, provider_box: list[Any]) -> None:
    prov = provider_box[0]
    updated = 0
    for pr in state.payment_requests or []:
        rid = str(pr.get("id") or "")
        result = prov.check_payment_status(rid)
        pr["status"] = result.get("status", pr.get("status"))
        updated += 1
    state.trace(
        decision="Outstanding payment requests need status refresh.",
        tool="CHECK_PAYMENT_STATUS",
        input_summary=f"count={len(state.payment_requests or [])}",
        output_summary=f"polled={updated}",
    )


def tool_calculate_cashflow(state: AgentState, provider_box: list[Any]) -> None:
    state.cashflow_summary = calculate_cashflow(
        state.reconciliation_results or [],
        state.parsed_orders or [],
        state.expenses or [],
    )
    state.trace(
        decision="Cashflow summary absent; aggregate collections vs expenses.",
        tool="CALCULATE_CASHFLOW",
        input_summary="reco+expenses",
        output_summary=f"net={state.cashflow_summary.get('net_cash_position')}",
    )


def tool_score_cashflow_health(state: AgentState, provider_box: list[Any]) -> None:
    state.health_score = score_cashflow_health(state.cashflow_summary or {})
    state.trace(
        decision="Health score missing; derive from cashflow KPIs.",
        tool="SCORE_CASHFLOW_HEALTH",
        input_summary="cashflow_summary",
        output_summary=f"score={state.health_score.get('score')}",
    )


def tool_generate_reminders(state: AgentState, provider_box: list[Any]) -> None:
    state.reminders = generate_reminders(
        state.parsed_orders or [],
        state.reconciliation_results or [],
        state.llm_mode,
    )
    state.trace(
        decision="Reminders not generated; draft follow-up messages.",
        tool="GENERATE_REMINDERS",
        input_summary="unpaid/partial",
        output_summary=f"reminders={len(state.reminders)}",
    )


def tool_generate_financing_readiness(state: AgentState, provider_box: list[Any]) -> None:
    state.financing_readiness = generate_financing_readiness(
        state.health_score or {},
        state.validation_report or {"ok": True},
        state.llm_mode,
    )
    state.trace(
        decision="Financing narrative missing; compose readiness note.",
        tool="GENERATE_FINANCING_READINESS",
        input_summary="health+validation",
        output_summary="narrative_ready",
    )


def tool_generate_daily_report(state: AgentState, provider_box: list[Any]) -> None:
    state.daily_report = generate_daily_report(
        state.merchant_profile or {},
        state.cashflow_summary or {},
        state.health_score or {},
        state.reconciliation_results or [],
    )
    state.trace(
        decision="Daily report missing; render markdown summary.",
        tool="GENERATE_DAILY_REPORT",
        input_summary="merchant+cashflow",
        output_summary=f"chars={len(state.daily_report)}",
    )


def tool_validate_outputs(state: AgentState, provider_box: list[Any]) -> None:
    state.validation_report = validate_outputs(
        {
            "parsed_orders": bool(state.parsed_orders),
            "reconciliation": bool(state.reconciliation_results),
            "cashflow": bool(state.cashflow_summary),
            "health": bool(state.health_score),
            "daily_report": bool(state.daily_report),
        }
    )
    state.trace(
        decision="Validation report missing; run output checks.",
        tool="VALIDATE_OUTPUTS",
        input_summary="key_artifacts",
        output_summary=f"ok={state.validation_report.get('ok')}",
    )


def tool_export_reports(state: AgentState, provider_box: list[Any]) -> None:
    state.exported_files = export_all(state)
    state.trace(
        decision="Exports missing; write artifacts to outputs/.",
        tool="EXPORT_REPORTS",
        input_summary="state snapshot",
        output_summary=f"files={len(state.exported_files)}",
    )


TOOL_REGISTRY: dict[str, ToolHandler] = {
    "LOAD_MERCHANT_PROFILE": tool_load_merchant_profile,
    "LOAD_ORDERS": tool_load_orders,
    "PARSE_ORDERS": tool_parse_orders,
    "ESTIMATE_OR_FLAG_UNKNOWN_AMOUNTS": tool_estimate_or_flag_unknown_amounts,
    "LOAD_PAYMENTS": tool_load_payments,
    "LOAD_EXPENSES": tool_load_expenses,
    "LOAD_CUSTOMERS": tool_load_customers,
    "RECONCILE_PAYMENTS": tool_reconcile_payments,
    "DETECT_PAYMENT_ISSUES": tool_detect_payment_issues,
    "RESOLVE_PAYMENT_REQUESTS": tool_resolve_payment_requests,
    "CHECK_PAYMENT_STATUS": tool_check_payment_status,
    "CALCULATE_CASHFLOW": tool_calculate_cashflow,
    "SCORE_CASHFLOW_HEALTH": tool_score_cashflow_health,
    "GENERATE_REMINDERS": tool_generate_reminders,
    "GENERATE_FINANCING_READINESS": tool_generate_financing_readiness,
    "GENERATE_DAILY_REPORT": tool_generate_daily_report,
    "VALIDATE_OUTPUTS": tool_validate_outputs,
    "EXPORT_REPORTS": tool_export_reports,
    "DOKU_WEBHOOK_SIMULATOR": tool_simulate_doku_webhook,
}
