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
from tools.bot_service import merge_bot_into_agent_inputs
from tools.catalogue_tools import (
    catalogue_version,
    load_product_catalogue_from_csv,
    load_product_catalogue_tool,
    validate_catalogue_tool,
)
from tools import event_store
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


def _payment_request_id(pr: dict[str, Any]) -> str:
    return str(pr.get("id") or pr.get("payment_request_id") or "")


def _seed_provider_from_state(state: AgentState, prov: Any) -> None:
    if not hasattr(prov, "restore_request"):
        return
    for pr in (state.payment_requests_by_order or {}).values():
        if isinstance(pr, dict):
            prov.restore_request(pr)


def _append_unpaid_payment_requests(
    state: AgentState, prov: Any, provider_box: list[Any]
) -> tuple[int, int]:
    """Create or reuse payment requests for unpaid/partial orders. Returns (created, reused)."""
    if state.payment_requests is None:
        state.payment_requests = []
    created = 0
    reused = 0
    for r in state.reconciliation_results or []:
        if r.get("status") not in {"UNPAID", "PARTIALLY_PAID"}:
            continue
        oid = str(r.get("order_id"))
        if oid in state.payment_requests_by_order:
            state.payment_requests.append(state.payment_requests_by_order[oid])
            reused += 1
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
        created += 1
    return created, reused


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


def tool_load_product_catalogue(state: AgentState, provider_box: list[Any]) -> None:
    cat = load_product_catalogue_tool(state)
    val = validate_catalogue_tool(cat)
    state.catalogue_warnings = list(val.get("warnings") or [])
    state.catalogue_version = catalogue_version(cat)
    state.trace(
        decision="Load merchant product catalogue for pricing.",
        tool="LOAD_PRODUCT_CATALOGUE",
        input_summary="product_catalogue.csv",
        output_summary=f"products={len(cat)} warnings={len(state.catalogue_warnings)}",
        status="warn" if state.catalogue_warnings else "ok",
    )


def tool_sync_bot_events(state: AgentState, provider_box: list[Any]) -> None:
    state.bot_orders = event_store.get_recent_bot_orders(200)
    state.bot_payments = event_store.get_recent_payments(200)
    state.bot_runtime_snapshot = event_store.runtime_snapshot_for_hash()
    raw, txns = merge_bot_into_agent_inputs(
        state.raw_orders,
        state.payment_transactions,
    )
    if raw:
        state.raw_orders = raw
    if txns:
        state.payment_transactions = txns
    state.trace(
        decision="Merge WhatsApp bot orders and mock payments from event store.",
        tool="SYNC_BOT_EVENTS",
        input_summary="runtime/",
        output_summary=f"bot_orders={len(state.bot_orders)} lines={len(raw)} txns={len(txns)}",
    )


def tool_load_orders(state: AgentState, provider_box: list[Any]) -> None:
    if state.raw_orders is None:
        path = DATA_DIR / "sample_orders_whatsapp.txt"
        raw = path.read_text(encoding="utf-8").splitlines()
        state.raw_orders = [ln for ln in raw if ln.strip()]
        source = str(path.name)
    else:
        source = "session"
    raw, _ = merge_bot_into_agent_inputs(state.raw_orders, state.payment_transactions)
    state.raw_orders = raw
    state.trace(
        decision="Load WhatsApp order lines (sample + bot).",
        tool="LOAD_ORDERS",
        input_summary=source,
        output_summary=f"lines={len(state.raw_orders)}",
    )


def tool_parse_orders(state: AgentState, provider_box: list[Any]) -> None:
    cat = state.product_catalogue or load_product_catalogue_from_csv()
    state.parsed_orders = parse_orders_batch(state.raw_orders or [], catalogue=cat)
    unknown: list[str] = []
    for row in state.parsed_orders or []:
        unknown.extend(row.get("unknown_products") or [])
    state.unknown_products = list(dict.fromkeys(unknown))
    state.trace(
        decision="Parse orders using product catalogue pricing.",
        tool="PARSE_ORDERS",
        input_summary=f"{len(state.raw_orders or [])} lines catalogue={len(cat)}",
        output_summary=f"parsed={len(state.parsed_orders)} unknown={len(state.unknown_products)}",
        status="warn" if state.unknown_products else "ok",
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
    _seed_provider_from_state(state, prov)
    if state.payment_requests is None:
        state.payment_requests = []
    created, reused = 0, 0
    if state.payment_mode == "doku_sandbox" and _has_unpaid(state):
        try:
            created, reused = _append_unpaid_payment_requests(state, prov, provider_box)
        except Exception as e:  # noqa: BLE001
            logger.warning("Payment provider failed; falling back to mock: %s", e)
            state.errors.append(str(e))
            state.payment_mode = "mock"
            provider_box[0] = MockPaymentProvider()
            prov = provider_box[0]
            state.payment_requests = []
            created, reused = _append_unpaid_payment_requests(state, prov, provider_box)
            state.trace(
                decision="DOKU path failed; mock payment requests created.",
                tool="RESOLVE_PAYMENT_REQUESTS",
                input_summary="unpaid/partial",
                output_summary=(
                    f"requests={len(state.payment_requests)} "
                    f"created={created} reused={reused}"
                ),
                status="warn",
            )
            return
    elif state.payment_mode == "mock" and _has_unpaid(state):
        created, reused = _append_unpaid_payment_requests(state, prov, provider_box)
    summary = f"requests={len(state.payment_requests or [])} created={created} reused={reused}"
    if reused and not created:
        decision = "Reused existing payment requests for unpaid orders."
    elif created and reused:
        decision = "Created and reused payment requests for unpaid orders."
    elif created:
        decision = "Created new payment requests for unpaid orders."
    else:
        decision = "Payment request phase; no unpaid orders needing requests."
    state.trace(
        decision=decision,
        tool="RESOLVE_PAYMENT_REQUESTS",
        input_summary=f"mode={state.payment_mode}",
        output_summary=summary,
    )


def tool_check_payment_status(state: AgentState, provider_box: list[Any]) -> None:
    prov = provider_box[0]
    _seed_provider_from_state(state, prov)
    updated = 0
    still_open = 0
    for pr in state.payment_requests or []:
        rid = _payment_request_id(pr)
        if not rid:
            pr["status"] = "AWAITING_PAYMENT"
            still_open += 1
            continue
        result = prov.check_payment_status(rid)
        new_status = str(result.get("status") or pr.get("status") or "UNKNOWN").upper()
        if new_status in {"", "UNKNOWN"}:
            oid = str(pr.get("order_id") or "")
            reco = next(
                (
                    r
                    for r in (state.reconciliation_results or [])
                    if str(r.get("order_id")) == oid
                ),
                None,
            )
            if reco and str(reco.get("status") or "").upper() == "PAID":
                new_status = "COMPLETED"
            else:
                new_status = "AWAITING_PAYMENT"
        pr["status"] = new_status
        updated += 1
        if new_status not in {
            "COMPLETED",
            "PAID",
            "SUCCESS",
            "SETTLED",
            "FAILED",
            "EXPIRED",
            "CANCELLED",
        }:
            still_open += 1
    state.payment_status_poll_done = True
    state.trace(
        decision="One-time payment link status refresh (unpaid links stay open).",
        tool="CHECK_PAYMENT_STATUS",
        input_summary=f"count={len(state.payment_requests or [])}",
        output_summary=f"polled={updated} still_open={still_open}",
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
    "LOAD_PRODUCT_CATALOGUE": tool_load_product_catalogue,
    "SYNC_BOT_EVENTS": tool_sync_bot_events,
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
