from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass
class ExecutionStep:
    step_number: int
    agent_decision: str
    tool_called: str
    input_summary: str
    output_summary: str
    status: Literal["ok", "warn", "error"]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class AgentState:
    """Central memory for the autonomous agent."""

    merchant_profile: dict[str, Any] | None = None
    raw_orders: list[str] | None = None
    parsed_orders: list[dict[str, Any]] | None = None
    payment_transactions: list[dict[str, Any]] | None = None
    expenses: list[dict[str, Any]] | None = None
    customers: list[dict[str, Any]] | None = None
    reconciliation_results: list[dict[str, Any]] | None = None
    payment_issues: list[dict[str, Any]] | None = None
    payment_requests: list[dict[str, Any]] | None = None
    cashflow_summary: dict[str, Any] | None = None
    health_score: dict[str, Any] | None = None
    reminders: list[dict[str, Any]] | None = None
    financing_readiness: dict[str, Any] | None = None
    daily_report: str | None = None
    validation_report: dict[str, Any] | None = None
    exported_files: dict[str, str] | None = None
    execution_trace: list[ExecutionStep] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    final_status: Literal["COMPLETE", "NEEDS_REVIEW", "ERROR"] | None = None
    payment_mode: Literal["mock", "doku_sandbox"] = "mock"
    llm_mode: Literal["mock", "live"] = "mock"
    amount_pass_done: bool = False

    def next_step_number(self) -> int:
        return len(self.execution_trace) + 1

    def trace(
        self,
        decision: str,
        tool: str,
        input_summary: str,
        output_summary: str,
        status: Literal["ok", "warn", "error"] = "ok",
    ) -> None:
        self.execution_trace.append(
            ExecutionStep(
                step_number=self.next_step_number(),
                agent_decision=decision,
                tool_called=tool,
                input_summary=input_summary,
                output_summary=output_summary,
                status=status,
            )
        )
