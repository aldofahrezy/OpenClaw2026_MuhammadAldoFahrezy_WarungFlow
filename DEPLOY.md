# Deploy WarungFlow (live demo link for Devpost)

## Option A — VPS (Sumopod / SSH) — current live

WarungFlow runs on this VPS with Streamlit bound to all interfaces.

### Environment

```bash
cd /root/agenthon
cp .env.example .env
# Edit .env — at minimum for live demo:
#   WARUNGFLOW_ENV=production
#   PUBLIC_BASE_URL=http://<your-host>:8501
#   WARUNGFLOW_LIVE_URL=http://<your-host>:8501
# Optional DOKU Sandbox:
#   DOKU_CLIENT_ID=...
#   DOKU_SECRET_KEY=...
```

**Payment mode** is chosen in the dashboard (**Simulasi → Mode pembayaran**), not via `PAYMENT_MODE` env.

### Quick start (manual)

```bash
cd /root/agenthon
source .venv/bin/activate
export WARUNGFLOW_ENV=production LLM_MODE=mock WHATSAPP_MODE=mock
export PUBLIC_BASE_URL=http://43.157.208.68:8501
streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
```

Or: `./deploy/start.sh`

### Optional WhatsApp bot API

```bash
uvicorn bot_server:app --host 0.0.0.0 --port 8000
```

Set `BOT_SERVER_URL=http://<host>:8000` in `.env` if the dashboard should call a remote API.

### Live URL (this server)

**http://43.157.208.68:8501**

Paste that in Devpost **Live Deployment Link**. Allow **TCP 8501** (and **8000** if exposing the bot API).

### Keep running after logout (systemd)

```bash
sudo cp /root/agenthon/deploy/warungflow.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now warungflow
sudo systemctl status warungflow
```

Logs: `journalctl -u warungflow -f`

`deploy/warungflow.service` sets `PUBLIC_BASE_URL` and `WARUNGFLOW_LIVE_URL` for correct payment deep links.

---

## Option B — Streamlit Community Cloud

**Recommended for judges who only need Mock mode (no DOKU keys in secrets).**

### Prerequisites

1. Push latest code to **public** GitHub: https://github.com/aldofahrezy/Warung-Flow  
2. Mock mode works without API keys.

### Deploy (~5 minutes)

1. Sign in at https://share.streamlit.io with GitHub.
2. **Create app** → Repository `aldofahrezy/Warung-Flow`, branch `main`, main file `app.py`.
3. **Secrets** (Advanced settings):

```toml
WARUNGFLOW_ENV = "production"
LLM_MODE = "mock"
WHATSAPP_MODE = "mock"
PUBLIC_BASE_URL = "https://your-app-name.streamlit.app"
```

4. Deploy. Open the app — sample data loads; first analysis runs automatically.
5. **Simulasi** → **Mode pembayaran** = Mock.

**Note:** Streamlit Cloud does not run `bot_server.py` unless you add a separate service. WhatsApp simulation works in-process on **Simulasi**.

**DOKU on Cloud:** possible if you add `DOKU_CLIENT_ID` / `DOKU_SECRET_KEY` to secrets and set `PUBLIC_BASE_URL` to your Streamlit app URL. Judges can follow [docs/judge_testing_guide.md](docs/judge_testing_guide.md) § Alur B.

---

## Alternative: Render

1. https://dashboard.render.com → **New +** → **Blueprint**  
2. Connect `aldofahrezy/Warung-Flow` (uses `render.yaml` if present).  
3. Use the `*.onrender.com` URL on Devpost.

---

## Verify after deploy

- [ ] App loads without errors.
- [ ] Beranda shows reconciliation after first auto-run.
- [ ] **Jejak agen** shows **≥8** tool steps.
- [ ] **Simulasi** → Mock: WhatsApp order + `mock_pay` link works.
- [ ] **Katalog** and **Laporan** pages load.
- [ ] (Optional) DOKU mode: credentials OK + Check Status sync on `?doku_pay=`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on deps | `requirements.txt` at repo root |
| Agent errors without keys | `LLM_MODE=mock` in secrets/env |
| Payment links point to localhost | Set `PUBLIC_BASE_URL` to public URL |
| DOKU mode falls back to mock | Add `DOKU_CLIENT_ID` + `DOKU_SECRET_KEY` |
| Paid on DOKU, UI still waiting | Open `/?doku_pay=ORD-BOT-xxx` → **Cek status pembayaran DOKU** |
| Agent hits max steps | **Reset riwayat demo**; check unpaid orders |
| Slow cold start | Normal on free tier |

---

## Repo

https://github.com/aldofahrezy/Warung-Flow

Judge testing: [docs/judge_testing_guide.md](docs/judge_testing_guide.md)
