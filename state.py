from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass
class ExecutionStep:
    run_id: int
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
    current_run_id: int = 0
    trigger_reason: str = ""
    latest_run_at: str = ""
    payment_requests_by_order: dict[str, dict[str, Any]] = field(default_factory=dict)

    def reset_pipeline_outputs(self) -> None:
        """Clear derived artifacts before a new autonomous run; keep session inputs."""
        self.parsed_orders = None
        self.reconciliation_results = None
        self.payment_issues = None
        self.cashflow_summary = None
        self.health_score = None
        self.reminders = None
        self.financing_readiness = None
        self.daily_report = None
        self.validation_report = None
        self.exported_files = None
        self.amount_pass_done = False
        self.final_status = None
        self.errors = []

    def begin_run(self, run_id: int, trigger_reason: str) -> None:
        self.current_run_id = run_id
        self.trigger_reason = trigger_reason
        self.latest_run_at = datetime.now(timezone.utc).isoformat()
        self._run_step = 0

    def trace(
        self,
        decision: str,
        tool: str,
        input_summary: str,
        output_summary: str,
        status: Literal["ok", "warn", "error"] = "ok",
        *,
        run_id: int | None = None,
    ) -> None:
        self._run_step = getattr(self, "_run_step", 0) + 1
        rid = run_id if run_id is not None else self.current_run_id
        prefix = f"[Run {rid}] " if self.trigger_reason else ""
        self.execution_trace.append(
            ExecutionStep(
                run_id=rid,
                step_number=self._run_step,
                agent_decision=f"{prefix}{decision}".strip(),
                tool_called=tool,
                input_summary=input_summary,
                output_summary=output_summary,
                status=status,
            )
        )
