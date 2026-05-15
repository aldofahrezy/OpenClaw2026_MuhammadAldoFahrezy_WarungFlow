# Devpost submission checklist — Muhammad Aldo Fahrezy

**Team ID:** `OpenClaw2026_MuhammadAldoFahrezy`  
**Project:** `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow`  
**Devpost:** https://openclawagenthon.devpost.com/

## Before 15 Mei 2026, 23:00 WIB

- [ ] Public GitHub repo pushed (no `.env` committed)
- [ ] Devpost: project description (use `docs/devpost_submission.md`)
- [ ] Devpost: GitHub URL — https://github.com/aldofahrezy/Warung-Flow
- [ ] Devpost: **Best Payment Use Case** track selected
- [ ] YouTube demo (**Unlisted**, ≤2 min): `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow`
- [ ] Pitch deck PDF (≤5 slides): `docs/OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.pdf`
- [ ] AI tools/models listed on Devpost
- [ ] **Live URL** on Devpost — http://43.157.208.68:8501 (or Streamlit Cloud — see `DEPLOY.md`)
- [ ] **Stop all commits after deadline**

## Judge testing (documented)

| Mode | Guide |
|------|--------|
| Mock (no API keys) | [docs/judge_testing_guide.md](docs/judge_testing_guide.md) — Alur A |
| DOKU Sandbox | [docs/judge_testing_guide.md](docs/judge_testing_guide.md) — Alur B |

## Demo video shot list (2 min)

See [docs/demo_script.md](docs/demo_script.md).

1. Problem (15s) — WhatsApp + QRIS chaos.
2. Solution (15s) — WarungFlow agent + six dashboard pages.
3. Live demo (65s) — Beranda → Simulasi (WhatsApp + Mock pay) → optional DOKU checkout → Katalog → Laporan.
4. Architecture (25s) — state loop, 20 tools, DOKU Check Status sync.
5. Impact (10s) — UMKM cashflow + payment track.

## Verify locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python smoke_test.py -v
streamlit run app.py
```

Optional: `uvicorn bot_server:app --port 8000`

## Feature checklist (for judges)

- [x] Auto-run on first load + input-hash reactive refresh
- [x] 20-tool autonomous loop with execution trace (`run_id`)
- [x] Humanized reconciliation (Tagihan / Terbayar / Sisa-kelebihan)
- [x] Langkah yang disarankan recommendations
- [x] Product catalogue CRUD + CSV
- [x] WhatsApp bot on **Simulasi** (rooms per phone, form + plain chat)
- [x] Mock payment mode + `?mock_pay=` deep links
- [x] DOKU Sandbox checkout + Check Status sync (`?doku_pay=`, `doku_payment_sync`)
- [x] Session persistence across refresh (`ui_session_snapshot.json`)
- [x] `python smoke_test.py -v` passes
