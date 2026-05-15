# Deploy WarungFlow (live demo link for Devpost)

## Option A — This VPS (Sumopod / SSH) — current live

WarungFlow runs on this VPS with Streamlit bound to all interfaces.

### Quick start (manual)

```bash
cd /root/agenthon
source .venv/bin/activate
export WARUNGFLOW_ENV=production PAYMENT_MODE=mock LLM_MODE=mock WHATSAPP_MODE=mock
streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
```

Or: `./deploy/start.sh`

### Optional WhatsApp bot API

```bash
uvicorn bot_server:app --host 0.0.0.0 --port 8000
```

Set `BOT_SERVER_URL=http://<host>:8000` in `.env` if the dashboard bot page should call a remote API.

### Live URL (this server)

**http://43.157.208.68:8501**

Paste that in Devpost **Live Deployment Link**. Ensure your cloud firewall / security group allows **TCP 8501** (and **8000** if exposing the bot API).

### Keep running after logout (systemd)

```bash
# Stop any manual streamlit on 8501 first, then:
sudo cp /root/agenthon/deploy/warungflow.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now warungflow
sudo systemctl status warungflow
```

Logs: `journalctl -u warungflow -f`

### Background without systemd

```bash
cd /root/agenthon
nohup ./deploy/start.sh > /tmp/warungflow.log 2>&1 &
```

---

## Option B — Streamlit Community Cloud

**Recommended if you do not want to manage a VPS port.**

### Prerequisites

1. Push latest code to **public** GitHub: https://github.com/aldofahrezy/Warung-Flow  
2. No API keys required for judges (`PAYMENT_MODE=mock`, `LLM_MODE=mock`, `WHATSAPP_MODE=mock`).

### Streamlit Community Cloud (≈5 minutes)

1. Sign in at https://share.streamlit.io with GitHub.
2. Click **Create app**.
3. **Repository:** `aldofahrezy/Warung-Flow`  
4. **Branch:** `main`  
5. **Main file path:** `app.py`  
6. **App URL (suggested):** `warungflow-muhammadaldofahrezy`  
   → `https://warungflow-muhammadaldofahrezy.streamlit.app`
7. Open **Advanced settings** → **Secrets** and paste:

```toml
WARUNGFLOW_ENV = "production"
PAYMENT_MODE = "mock"
LLM_MODE = "mock"
WHATSAPP_MODE = "mock"
```

(Or copy from `.streamlit/secrets.toml.example`.)

8. Click **Deploy**. Wait 2–5 minutes for the build.
9. Open the app — sample data loads and the first analysis runs automatically.

**Note:** Streamlit Cloud deploys the dashboard only. The WhatsApp bot API (`bot_server.py`) is not started on Streamlit Cloud unless you add a separate service; the **WhatsApp Bot** page still works in limited mock mode via in-process helpers.

### Devpost

Paste the live URL in **Live Deployment Link (Optional)** on Devpost.

## Alternative: Render

1. https://dashboard.render.com → **New +** → **Blueprint**  
2. Connect `aldofahrezy/Warung-Flow` (uses `render.yaml` in repo).  
3. Deploy; use the `*.onrender.com` URL on Devpost.

## Verify after deploy

- App loads without errors.
- Mock mode banner visible.
- One agent run completes; Beranda shows reconciliation and recommendations.
- Jejak agen shows **≥8** tool steps.
- Katalog and Laporan pages load.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on deps | Ensure `requirements.txt` is at repo root (9 packages: streamlit, pandas, dotenv, rapidfuzz, altair, fastapi, uvicorn, pydantic). |
| Agent run errors | Set secrets `PAYMENT_MODE=mock`, `LLM_MODE=mock`. |
| Agent hits max steps | Check unpaid orders; use **Reset Demo**; ensure `CHECK_PAYMENT_STATUS` runs once per run. |
| Slow cold start | Normal on free tier; mention in demo video. |
| Bot page empty | Start `uvicorn bot_server:app` or use mock mode defaults. |

## Repo

https://github.com/aldofahrezy/Warung-Flow
