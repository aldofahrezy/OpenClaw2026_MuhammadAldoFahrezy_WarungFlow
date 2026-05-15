#!/usr/bin/env python3
"""Smoke tests for WarungFlow MVP (no secrets required)."""

from __future__ import annotations

import os
from pathlib import Path

# Deterministic CI-style env
os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("PAYMENT_MODE", "mock")

from warungflow.agent_loop import run_agent
from warungflow.config import RuntimeConfig
from warungflow.export import OUTPUT_DIR, ROOT
from warungflow.parser import parse_orders_batch


def main() -> None:
    data_dir = ROOT / "data"
    assert (data_dir / "sample_orders.txt").is_file(), "sample orders missing"

    raw = (data_dir / "sample_orders.txt").read_text(encoding="utf-8").splitlines()
    raw = [ln for ln in raw if ln.strip()]
    parsed = parse_orders_batch(raw)
    assert len(parsed) >= 1, "parser should produce parsed_orders"

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

    print("smoke_test: OK")


if __name__ == "__main__":
    main()
