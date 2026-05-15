# AGENTS

This document describes all the agents active in the WarungFlow ecosystem.

## Orchestrator Agent
Controls the autonomous loop, observes the current state, decides the next required action, calls the correct tool, updates the state, logs execution trace, and stops only when the task is complete, blocked, or max_steps reached.

## Data Cleaner Agent
Responsible for parsing messy Indonesian WhatsApp order messages, extracting customer name, items, quantity, amount, and payment hints, and normalizing customer names while flagging unclear messages.

## Payment Reconciliation Agent
Responsible for matching orders to QRIS/payment transactions by customer name, amount, and reference note using fuzzy matching. Detects unpaid orders, partial payments, overpayments, and unmatched payments, and assigns a confidence score.

## Cashflow Analyst Agent
Responsible for calculating total order value, paid revenue, unpaid amount, expenses, net profit, payment completion rate, and generating a cashflow health score.

## Advisor Agent
Responsible for generating polite Bahasa Indonesia payment reminders, explaining cashflow health simply, recommending next actions, generating financing-readiness summaries, and suggesting operational improvements.

## Validator Agent
Responsible for checking the completeness of all outputs, identifying missing inputs, unresolved payment issues, suspicious transactions, and ensuring reports are exported successfully. Returns final status as READY, NEEDS_REVIEW, or MISSING_CRITICAL_DATA.
