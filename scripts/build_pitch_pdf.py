#!/usr/bin/env python3
"""Build pitch deck PDF (5 slides) for Devpost submission."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.pdf"

SLIDES = [
    (
        "Slide 1 - Problem Statement",
        [
            "Indonesian UMKM and warung owners take orders via WhatsApp.",
            "They accept QRIS, bank transfer, cash, and pay-later (kasbon).",
            "At end of day: who paid, who owes, and net profit are unclear.",
            "Matching chats to bank mutations is slow and error-prone.",
        ],
    ),
    (
        "Slide 2 - Solution Overview",
        [
            "WarungFlow: autonomous finance operations agent for Indonesian UMKM.",
            "Tagline: From messy notes to bankable reports, autonomously.",
            "Parses orders, reconciles QRIS payments, flags issues, scores cashflow.",
            "Generates Bahasa reminders and financing-readiness summaries.",
            "Not a chatbot: one button runs the full autonomous tool loop.",
        ],
    ),
    (
        "Slide 3 - AI Agent Workflow",
        [
            "Orchestrator: state-driven loop (max 20 steps).",
            "Agents: Data Cleaner, Reconciliation, Cashflow, Advisor, Validator.",
            "Memory: AgentState + execution_trace (visible to judges).",
            "Tools: 18+ real Python functions (load, parse, reconcile, export).",
            "Optional DOKU Sandbox payment requests with mock fallback.",
        ],
    ),
    (
        "Slide 4 - Key Features and Tech Stack",
        [
            "QRIS-style reconciliation with Indonesian fuzzy name matching.",
            "Order-ID priority in bank reference notes.",
            "Payment issues: UNPAID, PARTIAL, OVERPAID detection.",
            "Cashflow health score and CSV/MD exports.",
            "Stack: Python, Streamlit, pandas, rapidfuzz, DOKU adapter.",
        ],
    ),
    (
        "Slide 5 - Future Development and Impact",
        [
            "WhatsApp Business API for live order intake.",
            "Live QRIS / DOKU webhook synchronization.",
            "POS integration and bank-ready ledger exports.",
            "Impact: financial inclusion and daily clarity for millions of UMKM.",
        ],
    ),
]


def main() -> None:
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    w = pdf.epw

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(w, 10, "OpenClaw2026_MuhammadAldoFahrezy_WarungFlow")
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(w, 8, "Team: Muhammad Aldo Fahrezy")
    pdf.multi_cell(w, 8, "Track: Best Payment Use Case")

    for title, bullets in SLIDES:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(w, 10, title)
        pdf.ln(4)
        pdf.set_font("Helvetica", size=11)
        for b in bullets:
            pdf.multi_cell(w, 7, f"- {b}")
        pdf.ln(2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
