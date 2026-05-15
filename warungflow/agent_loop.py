from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from warungflow.cashflow import calculate_cashflow, score_cashflow_health
from warungflow.config import RuntimeConfig
from warungflow.export import export_all
from warungflow.narratives import generate_financing_readiness, generate_reminders
from warungflow.parser import parse_orders_batch
from warungflow.providers.doku import DokuSandboxProvider
from warungflow.providers.mock import MockPaymentProvider
from warungflow.reconciliation import detect_payment_issues, reconcile_orders
from warungflow.reports import generate_daily_report, validate_outputs
from warungflow.state import AgentState

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


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
        return "BUILD_CUSTOMERS"
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


def _has_unpaid(state: AgentState) -> bool:
    for r in state.reconciliation_results or []:
        if r.get("status") in {"UNPAID", "PARTIALLY_PAID"}:
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
    """Dispatch tool; must append execution trace."""
    prov = provider_box[0]

    if name == "LOAD_MERCHANT_PROFILE":
        path = DATA_DIR / "merchant_profile.json"
        with open(path, encoding="utf-8") as f:
            state.merchant_profile = json.load(f)
        state.trace(
            decision="Merchant context missing; load local profile.",
            tool=name,
            input_summary=str(path.name),
            output_summary=f"loaded keys={list(state.merchant_profile.keys())}",
        )
        return

    if name == "LOAD_ORDERS":
        path = DATA_DIR / "sample_orders.txt"
        raw = path.read_text(encoding="utf-8").splitlines()
        state.raw_orders = [ln for ln in raw if ln.strip()]
        state.trace(
            decision="No raw orders in state; ingest sample WhatsApp lines.",
            tool=name,
            input_summary=str(path.name),
            output_summary=f"lines={len(state.raw_orders)}",
        )
        return

    if name == "PARSE_ORDERS":
        state.parsed_orders = parse_orders_batch(state.raw_orders or [])
        state.trace(
            decision="Parsed orders empty or stale; run deterministic parser.",
            tool=name,
            input_summary=f"{len(state.raw_orders or [])} lines",
            output_summary=f"parsed={len(state.parsed_orders)}",
        )
        return

    if name == "ESTIMATE_OR_FLAG_UNKNOWN_AMOUNTS":
        updated = 0
        for row in state.parsed_orders or []:
            if row.get("amount_expected") is None:
                row["status"] = "NEEDS_REVIEW"
                row["parser_note"] = (row.get("parser_note") or "") + "; flagged_unknown_amount"
                updated += 1
        state.amount_pass_done = True
        state.trace(
            decision="Unknown amounts detected after parse; flag for review.",
            tool=name,
            input_summary="parsed_orders",
            output_summary=f"rows_flagged={updated}",
            status="warn" if updated else "ok",
        )
        return

    if name == "LOAD_PAYMENTS":
        path = DATA_DIR / "sample_payments.json"
        with open(path, encoding="utf-8") as f:
            state.payment_transactions = json.load(f)
        state.trace(
            decision="Payment pool missing; load transactions.",
            tool=name,
            input_summary=str(path.name),
            output_summary=f"txns={len(state.payment_transactions)}",
        )
        return

    if name == "LOAD_EXPENSES":
        path = DATA_DIR / "sample_expenses.json"
        with open(path, encoding="utf-8") as f:
            state.expenses = json.load(f)
        state.trace(
            decision="Expense ledger missing; load notes.",
            tool=name,
            input_summary=str(path.name),
            output_summary=f"rows={len(state.expenses)}",
        )
        return

    if name == "BUILD_CUSTOMERS":
        customers: list[dict[str, Any]] = []
        seen: set[str] = set()
        for o in state.parsed_orders or []:
            for key in ("customer_name", "payer_name"):
                n = o.get(key)
                if n and n not in seen:
                    seen.add(n)
                    customers.append({"name": n, "source": key})
        state.customers = customers
        state.trace(
            decision="Customer index missing; derive from parsed orders.",
            tool=name,
            input_summary="parsed_orders",
            output_summary=f"unique={len(customers)}",
        )
        return

    if name == "RECONCILE_PAYMENTS":
        state.reconciliation_results = reconcile_orders(
            state.parsed_orders or [], state.payment_transactions or []
        )
        state.trace(
            decision="Reconciliation not computed; match payments to orders.",
            tool=name,
            input_summary="orders+payments",
            output_summary=f"rows={len(state.reconciliation_results)}",
        )
        return

    if name == "DETECT_PAYMENT_ISSUES":
        state.payment_issues = detect_payment_issues(
            state.parsed_orders or [], state.reconciliation_results or []
        )
        state.trace(
            decision="Issue list uninitialized; scan reconciliation outcomes.",
            tool=name,
            input_summary="reconciliation_results",
            output_summary=f"issues={len(state.payment_issues)}",
        )
        return

    if name == "RESOLVE_PAYMENT_REQUESTS":
        state.payment_requests = []
        if state.payment_mode == "doku_sandbox" and _has_unpaid(state):
            try:
                for r in state.reconciliation_results or []:
                    if r.get("status") not in {"UNPAID", "PARTIALLY_PAID"}:
                        continue
                    oid = str(r.get("order_id"))
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
                    pr = prov.create_payment_request(
                        oid, remaining, f"Bill {oid}"
                    )
                    state.payment_requests.append(pr)
            except Exception as e:  # noqa: BLE001
                logger.warning("Payment provider failed; falling back to mock: %s", e)
                state.errors.append(str(e))
                state.payment_mode = "mock"
                provider_box[0] = MockPaymentProvider()
                prov = provider_box[0]
                state.payment_requests = []
                for r in state.reconciliation_results or []:
                    if r.get("status") not in {"UNPAID", "PARTIALLY_PAID"}:
                        continue
                    oid = str(r.get("order_id"))
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
                    pr = prov.create_payment_request(
                        oid, remaining, f"Bill {oid}"
                    )
                    state.payment_requests.append(pr)
                state.trace(
                    decision="DOKU path failed; mock payment requests created.",
                    tool=name,
                    input_summary="unpaid/partial",
                    output_summary=f"requests={len(state.payment_requests)}",
                    status="warn",
                )
                return
        elif state.payment_mode == "mock" and _has_unpaid(state):
            for r in state.reconciliation_results or []:
                if r.get("status") not in {"UNPAID", "PARTIALLY_PAID"}:
                    continue
                oid = str(r.get("order_id"))
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
                state.payment_requests.append(pr)
        state.trace(
            decision="Payment request phase; create or skip based on mode and unpaid balance.",
            tool=name,
            input_summary=f"mode={state.payment_mode}",
            output_summary=f"requests={len(state.payment_requests)}",
        )
        return

    if name == "CHECK_PAYMENT_STATUS":
        updated = 0
        for pr in state.payment_requests or []:
            rid = str(pr.get("id") or "")
            st = prov.check_payment_status(rid)
            pr["status"] = st.get("status", pr.get("status"))
            updated += 1
        state.trace(
            decision="Outstanding payment requests need status refresh.",
            tool=name,
            input_summary=f"count={len(state.payment_requests or [])}",
            output_summary=f"polled={updated}",
        )
        return

    if name == "CALCULATE_CASHFLOW":
        state.cashflow_summary = calculate_cashflow(
            state.reconciliation_results or [],
            state.parsed_orders or [],
            state.expenses or [],
        )
        state.trace(
            decision="Cashflow summary absent; aggregate collections vs expenses.",
            tool=name,
            input_summary="reco+expenses",
            output_summary=f"net={state.cashflow_summary.get('net_cash_position')}",
        )
        return

    if name == "SCORE_CASHFLOW_HEALTH":
        state.health_score = score_cashflow_health(state.cashflow_summary or {})
        state.trace(
            decision="Health score missing; derive from cashflow KPIs.",
            tool=name,
            input_summary="cashflow_summary",
            output_summary=f"score={state.health_score.get('score')}",
        )
        return

    if name == "GENERATE_REMINDERS":
        state.reminders = generate_reminders(
            state.parsed_orders or [],
            state.reconciliation_results or [],
            state.llm_mode,
        )
        state.trace(
            decision="Reminders not generated; draft follow-up messages.",
            tool=name,
            input_summary="unpaid/partial",
            output_summary=f"reminders={len(state.reminders)}",
        )
        return

    if name == "GENERATE_FINANCING_READINESS":
        state.financing_readiness = generate_financing_readiness(
            state.health_score or {},
            state.validation_report or {"ok": True},
            state.llm_mode,
        )
        state.trace(
            decision="Financing narrative missing; compose readiness note.",
            tool=name,
            input_summary="health+validation",
            output_summary="narrative_ready",
        )
        return

    if name == "GENERATE_DAILY_REPORT":
        state.daily_report = generate_daily_report(
            state.merchant_profile or {},
            state.cashflow_summary or {},
            state.health_score or {},
            state.reconciliation_results or [],
        )
        state.trace(
            decision="Daily report missing; render markdown summary.",
            tool=name,
            input_summary="merchant+cashflow",
            output_summary=f"chars={len(state.daily_report)}",
        )
        return

    if name == "VALIDATE_OUTPUTS":
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
            tool=name,
            input_summary="key_artifacts",
            output_summary=f"ok={state.validation_report.get('ok')}",
        )
        return

    if name == "EXPORT_REPORTS":
        state.exported_files = export_all(state)
        state.trace(
            decision="Exports missing; write artifacts to outputs/.",
            tool=name,
            input_summary="state snapshot",
            output_summary=f"files={len(state.exported_files)}",
        )
        return

    raise ValueError(f"Unknown tool: {name}")


def run_agent(cfg: RuntimeConfig | None = None) -> AgentState:
    cfg = cfg or RuntimeConfig.load()
    state = AgentState(payment_mode=cfg.payment_mode, llm_mode=cfg.llm_mode)

    if cfg.payment_mode == "doku_sandbox":
        import os

        provider: Any = DokuSandboxProvider(
            (os.getenv("DOKU_CLIENT_ID") or "").strip(),
            (os.getenv("DOKU_SECRET_KEY") or "").strip(),
            (os.getenv("DOKU_SANDBOX_BASE_URL") or "").strip() or None,
        )
    else:
        provider = MockPaymentProvider()

    max_steps = 64
    provider_box: list[Any] = [provider]
    for _ in range(max_steps):
        action = decide_next_action(state)
        if action is None:
            break
        execute_tool(action, state, provider_box)

    if state.errors:
        state.final_status = "NEEDS_REVIEW"
    else:
        state.final_status = "COMPLETE"
    return state
