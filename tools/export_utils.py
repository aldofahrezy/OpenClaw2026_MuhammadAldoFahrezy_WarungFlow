from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from state import AgentState, ExecutionStep


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def export_all(state: "AgentState") -> dict[str, str]:
    ensure_output_dir()
    paths: dict[str, str] = {}

    dr = OUTPUT_DIR / "daily_report.md"
    dr.write_text(state.daily_report or "", encoding="utf-8")
    paths["daily_report.md"] = str(dr)

    pr = OUTPUT_DIR / "payment_reminders.md"
    lines = [f"## {r.get('order_id')}\n\n{r.get('text')}\n" for r in (state.reminders or [])]
    pr.write_text("\n".join(lines), encoding="utf-8")
    paths["payment_reminders.md"] = str(pr)

    fr = OUTPUT_DIR / "financing_readiness.md"
    fr_md = (state.financing_readiness or {}).get("narrative", "")
    fr.write_text(fr_md, encoding="utf-8")
    paths["financing_readiness.md"] = str(fr)

    vr = OUTPUT_DIR / "validation_report.md"
    import json

    vr.write_text(
        json.dumps(state.validation_report or {}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths["validation_report.md"] = str(vr)

    rec = OUTPUT_DIR / "reconciliation_result.csv"
    with open(rec, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "order_id",
                "status",
                "matched_amount",
                "confidence",
                "notes",
            ],
            extrasaction="ignore",
        )
        w.writeheader()
        for row in state.reconciliation_results or []:
            w.writerow(row)
    paths["reconciliation_result.csv"] = str(rec)

    et = OUTPUT_DIR / "execution_trace.csv"
    with open(et, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "step_number",
                "agent_decision",
                "tool_called",
                "input_summary",
                "output_summary",
                "status",
                "timestamp",
            ],
        )
        w.writeheader()
        for step in state.execution_trace:
            w.writerow(
                {
                    "step_number": step.step_number,
                    "agent_decision": step.agent_decision,
                    "tool_called": step.tool_called,
                    "input_summary": step.input_summary,
                    "output_summary": step.output_summary,
                    "status": step.status,
                    "timestamp": step.timestamp,
                }
            )
    paths["execution_trace.csv"] = str(et)

    return paths
