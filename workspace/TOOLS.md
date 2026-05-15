# TOOLS

This document outlines all callable tools available to the WarungFlow agent.

## Core Data Tools
- `load_merchant_profile_tool()`: Loads the merchant profile JSON.
- `load_orders_tool()`: Loads messy WhatsApp-style orders.
- `parse_orders_tool()`: Parses raw orders into structured objects.
- `load_payments_tool()`: Loads QRIS/bank transfer transactions.
- `load_expenses_tool()`: Loads daily expenses.
- `load_customers_tool()`: Loads the customer CRM data.

## Reconciliation Tools
- `normalize_customer_tool()`: Normalizes and matches customer names.
- `reconcile_payments_tool()`: Matches parsed orders against payment transactions.
- `detect_payment_issues_tool()`: Identifies discrepancies, partial payments, and unpaid orders.

## Cashflow Tools
- `calculate_cashflow_tool()`: Computes revenue, expenses, and net profit.
- `score_cashflow_health_tool()`: Evaluates the business's daily financial health.

## Advisor Tools
- `generate_payment_reminders_tool()`: Creates polite collection messages for unpaid orders.
- `generate_financing_readiness_tool()`: Assesses whether the business is ready for external financing.
- `generate_daily_report_tool()`: Compiles a markdown summary of daily operations.

## Validation & Export Tools
- `validate_outputs_tool()`: Ensures all required reports are complete and accurate.
- `export_reports_tool()`: Writes final artifacts to the filesystem.

## Payment Integration Tools
- `doku_create_payment_request_tool()`: Creates a Sandbox payment link for unpaid orders.
- `doku_check_payment_status_tool()`: Checks if an existing payment link has been fulfilled.
- `doku_list_transactions_tool()`: Fetches DOKU Sandbox transactions.
- `doku_reconcile_transaction_tool()`: Matches DOKU outcomes with WarungFlow state.
- `doku_webhook_simulator_tool()`: Simulates payment webhooks.
