# TOOLS

Callable tools registered in `agents/tool_handlers.py` (`TOOL_REGISTRY`).

## Core data

| Tool | Description |
|------|-------------|
| `LOAD_MERCHANT_PROFILE` | Loads `data/merchant_profile.json` |
| `LOAD_PRODUCT_CATALOGUE` | Loads `data/product_catalogue.csv` for pricing |
| `SYNC_BOT_EVENTS` | Merges WhatsApp bot orders from `runtime/events.jsonl` |
| `LOAD_ORDERS` | Loads messy WhatsApp-style order lines |
| `PARSE_ORDERS` | Structures orders; strips internal `<!-- bot:… -->` meta |
| `ESTIMATE_OR_FLAG_UNKNOWN_AMOUNTS` | Catalogue-based price estimates |
| `LOAD_PAYMENTS` | QRIS / bank transfer CSV |
| `LOAD_EXPENSES` | Daily expense CSV |
| `LOAD_CUSTOMERS` | CRM + names from parsed orders |

## Reconciliation & payments

| Tool | Description |
|------|-------------|
| `RECONCILE_PAYMENTS` | Fuzzy match + order-ID priority in bank notes |
| `DETECT_PAYMENT_ISSUES` | UNPAID, PARTIALLY_PAID, OVERPAID, NEEDS_REVIEW |
| `RESOLVE_PAYMENT_REQUESTS` | Create mock/DOKU payment links for unpaid orders |
| `CHECK_PAYMENT_STATUS` | Poll provider once per run (`payment_status_poll_done`) |
| `SIMULATE_DOKU_WEBHOOK` | Sandbox webhook simulation |

## Cashflow & advisor

| Tool | Description |
|------|-------------|
| `CALCULATE_CASHFLOW` | Revenue, expenses, net profit |
| `SCORE_CASHFLOW_HEALTH` | 0–100 health score |
| `GENERATE_REMINDERS` | Bahasa Indonesia collection messages |
| `GENERATE_FINANCING_READINESS` | Financing snapshot |
| `GENERATE_DAILY_REPORT` | Markdown daily summary |

## Validation & export

| Tool | Description |
|------|-------------|
| `VALIDATE_OUTPUTS` | Completeness checks on generated reports |
| `EXPORT_REPORTS` | Writes artifacts to `outputs/` |

## Supporting modules (not always separate tools)

- `tools/catalogue_tools.py` — CRUD, CSV import, line-item matching
- `tools/bot_service.py` — mock WhatsApp order flow
- `tools/mock_payment_provider.py` / `tools/doku_sandbox_provider.py` — payment adapters
- `tools/doku_payment_sync.py` — poll DOKU Check Status → mark bot order PAID
- `tools/payment_links.py` / `tools/public_url.py` — mock_pay & doku_pay deep links
- `tools/parsers.py` — `strip_internal_meta()`, order parsing
