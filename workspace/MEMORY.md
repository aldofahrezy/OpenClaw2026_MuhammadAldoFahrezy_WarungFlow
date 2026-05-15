# MEMORY

**Persistent Context Storage**

The agent stores context across its workflow execution in an `AgentState` object.
Key variables stored in memory:
- `merchant_profile`: Warung Bu Sari, including business type and goals.
- `product_catalogue`: Menu items and prices for parsing and bot orders.
- `raw_orders` & `parsed_orders`: Raw WhatsApp chats and their structured counterparts.
- `bot_events`: Orders ingested via mock/live WhatsApp bot (`SYNC_BOT_EVENTS`).
- `payment_transactions` & `expenses`: Cash inflows and outflows.
- `customers`: Known customers and typical payment behaviors.
- `reconciliation_results`: Mapped outcomes of orders vs. payments.
- `payment_issues` & `payment_requests`: Discrepancies and active payment link states.
- `cashflow_summary` & `health_score`: Real-time financial analysis.
- `reminders` & `financing_readiness`: Actionable generated text.
- `daily_report` & `validation_report`: Output artifacts.
- `execution_trace`: Step-by-step history of tool calls.
- `payment_mode`: Tracks whether using `mock` or `doku_sandbox`.
- `payment_status_poll_done`: Ensures `CHECK_PAYMENT_STATUS` runs at most once per agent run.
