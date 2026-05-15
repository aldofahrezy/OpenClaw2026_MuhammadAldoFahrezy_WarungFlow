# WarungFlow

**WarungFlow** bridges the gap between messy digital commerce and formal financial readiness for Indonesian UMKM.

- **Input:** WhatsApp-style orders, QRIS-like payments, and expense notes  
- **Agent work:** Perception → action → reasoning → communication → validation  
- **Output:** A bankable daily business report pack (markdown + CSV)

**Demo tagline:** From messy notes to bankable reports, autonomously.

WarungFlow is deterministic-first: even without an LLM key or DOKU credentials, the autonomous loop still calls tools, reconciles payments, calculates cashflow, validates outputs, and exports reports using local sample data.

## Quick start

Use a **project-local virtual environment** at **`.venv`** in the repository root. Do not install project dependencies into the system Python interpreter.

### 1. Create the virtual environment

```bash
python3 -m venv .venv
```

### 2. Activate the virtual environment

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows (Command Prompt):**

```cmd
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit app

On first setup, copy the environment template (see [Configuration](#configuration)):

```bash
cp .env.example .env
```

Then start the app (with the virtual environment still activated):

```bash
streamlit run app.py
```

### 5. Run smoke tests

In another terminal, activate `.venv` the same way as in step 2, then:

```bash
python smoke_test.py
```

## Configuration

Copy `.env.example` to `.env` for local development. Environment variables are read from `.env` using the same parser as `python-dotenv` (`dotenv.parser`): **valid `KEY=value` lines are applied; invalid lines are skipped without noisy warnings** (for example unquoted multi-line PEM blobs). Do not commit `.env`.

For PEM material, prefer a file path (`MERCHANT_PRIVATE_KEY_PATH`) or a **single-line** quoted value. Raw multi-line certificates in `.env` are not supported by the dotenv format.

If API keys or DOKU credentials are missing, the app uses `LLM_MODE=mock` and `PAYMENT_MODE=mock`, continues the workflow, and surfaces non-blocking warnings in the UI.

## Project layout

- `warungflow/` — agent state, state-driven planner, tools, parser, reconciliation, payment adapters, export  
- `data/` — local sample merchant, orders, payments, expenses  
- `menu_price_catalog.json` — price hints when orders have no explicit total  
- `outputs/` — generated reports (created at runtime)

## Security

Never put real secrets in documentation templates, sample data, or source files. Use environment variables only.
