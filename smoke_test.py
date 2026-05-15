#!/usr/bin/env python3
"""Smoke tests for WarungFlow MVP (no secrets required)."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import sys
from pathlib import Path

# Deterministic CI-style env
os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("PAYMENT_MODE", "mock")

from agents.orchestrator import run_agent, run_agent_stream
from config import RuntimeConfig
from live_sandbox import EXPENSE_CATEGORIES
from session_runtime import (
    SANDBOX_FINGERPRINT_KEYS,
    _agent_state_from_snapshot,
    _agent_state_to_snapshot,
    clear_sandbox_duplicate_state,
    clear_ui_session_snapshot,
    stable_hash,
)
from state import AgentState
from tools.export_utils import OUTPUT_DIR, ROOT
from tools.mock_payment_provider import MockPaymentProvider
from tools.parsers import parse_orders_batch
from tools.report_generator import generate_daily_report, merchant_display_name
from agents.tool_handlers import _append_unpaid_payment_requests
from dashboard import build_action_recommendations

DATA_DIR = ROOT / "data"


def _load_bundle() -> AgentState:
    with open(DATA_DIR / "merchant_profile.json", encoding="utf-8") as f:
        mp = json.load(f)
    raw = [
        ln
        for ln in (DATA_DIR / "sample_orders_whatsapp.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if ln.strip()
    ]
    with open(DATA_DIR / "sample_qris_transactions.csv", encoding="utf-8") as f:
        pay = list(csv.DictReader(f))
    with open(DATA_DIR / "sample_expenses.csv", encoding="utf-8") as f:
        exp = list(csv.DictReader(f))
    with open(DATA_DIR / "sample_customers.csv", encoding="utf-8") as f:
        cust = [dict(r) for r in csv.DictReader(f)]
    return AgentState(
        payment_mode="mock",
        llm_mode="mock",
        merchant_profile=mp,
        raw_orders=raw,
        payment_transactions=pay,
        expenses=exp,
        customers=cust,
    )


def _run_stream(
    seed: AgentState, *, run_id: int = 1, reset_pipeline: bool = True
) -> AgentState:
    cfg = RuntimeConfig.load()
    final: AgentState | None = None
    for snap in run_agent_stream(
        cfg,
        seed,
        run_id=run_id,
        trigger_reason="smoke",
        reset_pipeline=reset_pipeline,
    ):
        final = snap
    assert final is not None
    return final


def _kevin_row(state: AgentState) -> dict | None:
    for o in state.parsed_orders or []:
        if o.get("customer_name") == "Kevin":
            oid = str(o["order_id"])
            return next(
                (r for r in (state.reconciliation_results or []) if r["order_id"] == oid),
                None,
            )
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="WarungFlow smoke tests")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print a short success message (default is silent on success)",
    )
    args = parser.parse_args()

    from tools import event_store

    event_store.reset_runtime_events()

    assert (DATA_DIR / "sample_orders_whatsapp.txt").is_file(), "sample orders missing"

    raw = (DATA_DIR / "sample_orders_whatsapp.txt").read_text(encoding="utf-8").splitlines()
    raw = [ln for ln in raw if ln.strip()]
    parsed = parse_orders_batch(raw)
    assert len(parsed) >= 1, "parser should produce parsed_orders"

    # 1. Initial autonomous run
    state = run_agent(RuntimeConfig.load())
    reco = state.reconciliation_results or []
    statuses = {r.get("status") for r in reco}
    assert "PAID" in statuses, f"expected PAID in {statuses}"
    assert "UNPAID" in statuses, f"expected UNPAID in {statuses}"
    assert "PARTIALLY_PAID" in statuses, f"expected PARTIALLY_PAID in {statuses}"

    assert state.cashflow_summary is not None
    score = int((state.health_score or {}).get("score", -1))
    assert 0 <= score <= 100, f"health score out of range: {score}"

    assert state.validation_report is not None

    mp = state.merchant_profile or {}
    assert merchant_display_name(mp) == "Warung Bu Sari", "merchant display name"
    daily = generate_daily_report(
        mp, state.cashflow_summary or {}, state.health_score or {}, reco
    )
    assert "Warung Bu Sari" in daily, "daily report should name Warung Bu Sari"

    expected_names = {
        "daily_report.md",
        "payment_reminders.md",
        "financing_readiness.md",
        "validation_report.md",
        "reconciliation_result.csv",
        "execution_trace.csv",
    }
    for name in expected_names:
        p = OUTPUT_DIR / name
        assert p.is_file(), f"missing output {p}"

    assert len(state.execution_trace) >= 8, "execution trace should show >= 8 tool calls"

    run_ids = {t.run_id for t in state.execution_trace}
    assert run_ids, "execution trace should include run_id"
    assert all(isinstance(rid, int) and rid >= 1 for rid in run_ids)

    h1 = stable_hash({"a": 1, "b": [2, 3]})
    h2 = stable_hash({"b": [2, 3], "a": 1})
    assert h1 == h2, "stable_hash must be order-independent"
    assert stable_hash({"a": 1}) != stable_hash({"a": 2}), "stable_hash must detect changes"

    # 2. Hash changes when order added
    bundle = _load_bundle()
    raw2 = list(bundle.raw_orders or [])
    raw2.append("Mbak, nasi goreng 2 total 44000, bayar nanti malam - Kevin")
    assert stable_hash({"raw_orders": raw2}) != stable_hash({"raw_orders": bundle.raw_orders})

    # 3–4. Kevin unpaid then PAID
    s2 = _run_stream(
        AgentState(
            payment_mode="mock",
            llm_mode="mock",
            merchant_profile=copy.deepcopy(bundle.merchant_profile),
            raw_orders=raw2,
            payment_transactions=copy.deepcopy(bundle.payment_transactions),
            expenses=copy.deepcopy(bundle.expenses),
            customers=copy.deepcopy(bundle.customers),
        ),
        run_id=2,
    )
    kevin = _kevin_row(s2)
    assert kevin is not None, "Kevin order should exist"
    assert kevin.get("status") == "UNPAID", f"Kevin should be UNPAID, got {kevin}"

    pay2 = list(bundle.payment_transactions or [])
    pay2.append(
        {
            "transaction_id": "p-kevin-smoke",
            "timestamp": "2026-05-15T12:00:00Z",
            "payer_name": "Kevin",
            "amount": "44000",
            "payment_method": "QRIS",
            "reference_note": "nasi goreng Kevin",
        }
    )
    s3 = _run_stream(
        AgentState(
            payment_mode="mock",
            llm_mode="mock",
            merchant_profile=copy.deepcopy(bundle.merchant_profile),
            raw_orders=raw2,
            payment_transactions=pay2,
            expenses=copy.deepcopy(bundle.expenses),
            customers=copy.deepcopy(bundle.customers),
        ),
        run_id=3,
    )
    kevin2 = _kevin_row(s3)
    assert kevin2 is not None
    assert kevin2.get("status") == "PAID", f"Kevin should be PAID, got {kevin2}"

    # 5. Partial payment
    pay_partial = list(bundle.payment_transactions or [])
    pay_partial.append(
        {
            "transaction_id": "p-partial",
            "timestamp": "2026-05-15T12:01:00Z",
            "payer_name": "Joko",
            "amount": "10000",
            "payment_method": "transfer",
            "reference_note": "partial Joko",
        }
    )
    s_partial = _run_stream(
        AgentState(
            payment_mode="mock",
            llm_mode="mock",
            merchant_profile=copy.deepcopy(bundle.merchant_profile),
            raw_orders=list(bundle.raw_orders or []),
            payment_transactions=pay_partial,
            expenses=copy.deepcopy(bundle.expenses),
            customers=copy.deepcopy(bundle.customers),
        ),
        run_id=4,
    )
    assert "PARTIALLY_PAID" in {r.get("status") for r in s_partial.reconciliation_results or []}

    # 6. Expense changes net profit
    exp_base = copy.deepcopy(bundle.expenses)
    s_base = _run_stream(
        AgentState(
            payment_mode="mock",
            llm_mode="mock",
            merchant_profile=copy.deepcopy(bundle.merchant_profile),
            raw_orders=list(bundle.raw_orders or []),
            payment_transactions=list(bundle.payment_transactions or []),
            expenses=exp_base,
            customers=copy.deepcopy(bundle.customers),
        ),
        run_id=5,
    )
    net_before = int((s_base.cashflow_summary or {}).get("net_cash_position") or 0)
    exp_more = list(exp_base)
    exp_more.append(
        {
            "date": "2026-05-15",
            "category": "bahan_baku",
            "description": "Kenaikan harga bahan baku",
            "amount": "125000",
        }
    )
    s_exp = _run_stream(
        AgentState(
            payment_mode="mock",
            llm_mode="mock",
            merchant_profile=copy.deepcopy(bundle.merchant_profile),
            raw_orders=list(bundle.raw_orders or []),
            payment_transactions=list(bundle.payment_transactions or []),
            expenses=exp_more,
            customers=copy.deepcopy(bundle.customers),
        ),
        run_id=6,
    )
    net_after = int((s_exp.cashflow_summary or {}).get("net_cash_position") or 0)
    exp_total_before = int((s_base.cashflow_summary or {}).get("expenses") or 0)
    exp_total_after = int((s_exp.cashflow_summary or {}).get("expenses") or 0)
    assert exp_total_after > exp_total_before, "expenses should increase"
    assert net_after < net_before, "net profit should decrease after expense shock"

    # 6b. Agent state snapshot roundtrip (browser refresh persistence)
    snap_agent = _run_stream(copy.deepcopy(bundle), run_id=61)
    restored = _agent_state_from_snapshot(_agent_state_to_snapshot(snap_agent))
    assert restored is not None
    assert restored.final_status == snap_agent.final_status
    assert len(restored.execution_trace) == len(snap_agent.execution_trace)
    clear_ui_session_snapshot()

    # 7. Reset clears sandbox fingerprints
    session: dict = {k: {"x"} for k in SANDBOX_FINGERPRINT_KEYS}
    session["webhook_events_seen"] = {"wh-1"}
    clear_sandbox_duplicate_state(session)
    for key in SANDBOX_FINGERPRINT_KEYS:
        assert session[key] == set(), f"{key} should be cleared"
    assert session["webhook_events_seen"] == set()

    # 8–9. Payment request idempotency for new unpaid + refresh
    unpaid_seed = AgentState(
        payment_mode="mock",
        llm_mode="mock",
        merchant_profile=copy.deepcopy(bundle.merchant_profile),
        raw_orders=raw2,
        payment_transactions=list(bundle.payment_transactions or []),
        expenses=copy.deepcopy(bundle.expenses),
        customers=copy.deepcopy(bundle.customers),
    )
    s_unpaid = _run_stream(unpaid_seed, run_id=7)
    assert s_unpaid.payment_requests is not None
    count_after_first = len(s_unpaid.payment_requests_by_order)
    assert count_after_first >= 1, "should create payment request for Kevin"

    s_refresh = _run_stream(
        AgentState(
            payment_mode="mock",
            llm_mode="mock",
            merchant_profile=copy.deepcopy(bundle.merchant_profile),
            raw_orders=raw2,
            payment_transactions=list(bundle.payment_transactions or []),
            expenses=copy.deepcopy(bundle.expenses),
            customers=copy.deepcopy(bundle.customers),
            payment_requests_by_order=dict(s_unpaid.payment_requests_by_order),
            execution_trace=list(s_unpaid.execution_trace),
        ),
        run_id=8,
    )
    assert len(s_refresh.payment_requests_by_order) == count_after_first
    assert not any("max_steps" in e for e in (s_refresh.errors or []))

    # Reused payment requests from a prior run must not cause CHECK_PAYMENT_STATUS loops.
    loop_probe = AgentState(
        payment_mode="mock",
        llm_mode="mock",
        merchant_profile=copy.deepcopy(bundle.merchant_profile),
        raw_orders=raw2,
        payment_transactions=list(bundle.payment_transactions or []),
        expenses=copy.deepcopy(bundle.expenses),
        customers=copy.deepcopy(bundle.customers),
        payment_requests_by_order=dict(s_unpaid.payment_requests_by_order),
    )
    s_loop = _run_stream(loop_probe, run_id=9)
    assert not any("max_steps" in e for e in (s_loop.errors or []))

    recs = build_action_recommendations(s_unpaid)
    assert isinstance(recs, list)
    cats = {r.get("category") for r in recs}
    assert "Isu pembayaran" in cats or "Skor kesehatan kas" in cats
    check_steps = [
        t for t in (s_loop.execution_trace or []) if t.tool_called == "CHECK_PAYMENT_STATUS"
    ]
    assert len(check_steps) <= 1, "payment status should be polled at most once per run"

    prov = MockPaymentProvider()
    probe = AgentState(
        payment_mode="mock",
        reconciliation_results=[{"order_id": "ORD-X", "status": "UNPAID", "matched_amount": 0}],
        parsed_orders=[{"order_id": "ORD-X", "amount_expected": 50000}],
        payment_requests=[],
    )
    c1, r1 = _append_unpaid_payment_requests(probe, prov, [prov])
    c2, r2 = _append_unpaid_payment_requests(probe, prov, [prov])
    assert c1 == 1 and r1 == 0
    assert c2 == 0 and r2 == 1

    pr_a = prov.create_payment_request("ORD-Z", 1000, "test")
    pr_b = prov.create_payment_request("ORD-Z", 1000, "test")
    assert pr_a["id"] == pr_b["id"]
    assert pr_b.get("reused") is True

    # --- Product catalogue + WhatsApp bot ---
    from tools import event_store
    from tools.bot_service import process_inbound_message, simulate_mock_payment
    from tools.catalogue_tools import (
        delete_catalogue_item,
        load_product_catalogue_from_csv,
        normalize_catalogue_tool,
        upsert_catalogue_item,
    )
    from tools.parsers import parse_order_message

    assert (DATA_DIR / "product_catalogue.csv").is_file()
    cat = load_product_catalogue_from_csv()
    assert len(cat) >= 5

    p_cat = parse_order_message("nasi goreng 2 es teh 1 - Kevin", catalogue=cat)
    assert p_cat.get("amount_source") == "catalogue"
    assert p_cat.get("amount_expected") == 39000

    p_alias = parse_order_message("nasgor 2 - Kevin", catalogue=cat)
    assert p_alias.get("amount_expected") == 34000

    p_unknown = parse_order_message("ayam kremes 2 - Kevin", catalogue=cat)
    unknown_list = p_unknown.get("unknown_products") or []
    assert any("ayam kremes" in str(u) for u in unknown_list), unknown_list
    assert p_unknown.get("parser_status") == "NEEDS_REVIEW"

    cat2 = normalize_catalogue_tool([dict(r) for r in cat])
    for row in cat2:
        if row.get("product_name") == "Nasi Goreng":
            row["unit_price"] = 20000
    p_reprice = parse_order_message("nasi goreng 2 - Kevin", catalogue=cat2)

    cat_crud = normalize_catalogue_tool([dict(r) for r in cat[:3]])
    cat_crud = upsert_catalogue_item(
        cat_crud,
        {
            "sku": "SKU-TEST",
            "product_name": "Test CRUD",
            "aliases": "test crud",
            "category": "snack",
            "unit_price": 999,
            "unit": "pcs",
            "is_active": True,
        },
    )
    found = next((r for r in cat_crud if r["sku"] == "SKU-TEST"), None)
    assert found is not None and found["unit_price"] == 999
    cat_crud, deleted = delete_catalogue_item(cat_crud, "SKU-TEST")
    assert deleted and not any(r["sku"] == "SKU-TEST" for r in cat_crud)
    assert p_reprice.get("amount_expected") == 40000

    event_store.reset_runtime_events()
    cat_demo = cat2 + [
        {
            "sku": "SKU-PIS",
            "product_name": "Pisang Goreng",
            "aliases": ["pisang goreng", "pisgor"],
            "category": "snack",
            "unit_price": 8000,
            "unit": "pcs",
            "is_active": True,
            "notes": "",
        }
    ]
    bot_res = process_inbound_message(
        from_phone="+628999000",
        message_text="pisgor 3 teh manis 2",
        customer_name="Demo",
        source="smoke_test",
        catalogue=cat_demo,
    )
    assert bot_res.get("intent") == "ORDER"

    confirm_phone = "+628999111"
    pending_res = process_inbound_message(
        from_phone=confirm_phone,
        message_text="pisgor 3 teh manis 2",
        customer_name=None,
        source="smoke_test",
        catalogue=cat_demo,
    )
    assert pending_res.get("intent") == "CONFIRM_PENDING"
    assert pending_res.get("gaps")
    name_res = process_inbound_message(
        from_phone=confirm_phone,
        message_text="Demo Smoke",
        customer_name=None,
        source="smoke_test",
        catalogue=cat_demo,
    )
    assert name_res.get("intent") == "CONFIRM_PENDING"
    assert not name_res.get("gaps")
    confirm_res = process_inbound_message(
        from_phone=confirm_phone,
        message_text="ya",
        customer_name=None,
        source="smoke_test",
        catalogue=cat_demo,
    )
    assert confirm_res.get("intent") == "ORDER"
    assert confirm_res.get("order")
    oid = bot_res["order"]["order_id"]
    assert bot_res["order"]["amount_expected"] == 34000
    assert event_store.list_outbound_messages(3)

    pay_res = simulate_mock_payment(order_id=oid, amount=34000, payer_name="Demo")
    assert pay_res.get("payment_status") == "PAID"

    snap_a = event_store.runtime_snapshot_for_hash()
    event_store.append_bot_order(
        {
            "order_id": "ORD-BOT-9999",
            "amount_expected": 1,
            "payment_status": "AWAITING_PAYMENT",
        }
    )
    snap_b = event_store.runtime_snapshot_for_hash()
    assert snap_a != snap_b

    seed_bot = _load_bundle()
    seed_bot.product_catalogue = None
    seed_bot.bot_runtime_snapshot = None
    raw_m, txn_m = __import__(
        "tools.bot_service", fromlist=["merge_bot_into_agent_inputs"]
    ).merge_bot_into_agent_inputs(seed_bot.raw_orders, seed_bot.payment_transactions)
    seed_bot.raw_orders = raw_m
    seed_bot.payment_transactions = txn_m
    s_bot = _run_stream(seed_bot, run_id=50)
    tools_hit = {t.tool_called for t in s_bot.execution_trace}
    assert "SYNC_BOT_EVENTS" in tools_hit
    assert "PARSE_ORDERS" in tools_hit
    bot_reco = [r for r in (s_bot.reconciliation_results or []) if str(r.get("order_id", "")).startswith("ORD-BOT")]
    assert bot_reco, "bot orders should appear in reconciliation"

    # Mock payment links use deploy URL, not localhost:8000
    os.environ["WARUNGFLOW_ENV"] = "production"
    from tools.doku_signature import build_checkout_signature, minify_json_body
    from tools.public_url import (
        doku_checkout_page_url,
        mock_payment_page_url,
        resolve_public_base_url,
    )

    base = resolve_public_base_url()
    pay_link = mock_payment_page_url("ORD-BOT-10000")
    assert "mock_pay=ORD-BOT-10000" in pay_link
    assert "localhost:8000" not in pay_link
    assert "43.157.208.68:8501" in pay_link or base.endswith(":8501")

    doku_link = doku_checkout_page_url("ORD-BOT-10000")
    assert "doku_pay=ORD-BOT-10000" in doku_link

    body = minify_json_body(
        {"order": {"amount": 10000, "invoice_number": "INV1"}, "payment": {"payment_due_date": 60}}
    )
    sig = build_checkout_signature(
        client_id="cid",
        secret_key="secret",
        request_id="req-1",
        request_timestamp="2020-08-11T08:45:42Z",
        request_target="/checkout/v1/payment",
        request_body=body,
    )
    assert sig.startswith("HMACSHA256=")

    # 10–11. Exports and credentials-free mock
    assert (OUTPUT_DIR / "execution_trace.csv").is_file()
    cfg = RuntimeConfig.load()
    assert cfg.llm_mode == "mock"
    assert cfg.payment_mode == "mock"

    assert "bahan_baku" in EXPENSE_CATEGORIES

    if args.verbose:
        print("smoke_test: OK", file=sys.stdout)


if __name__ == "__main__":
    main()
