# Deploy WarungFlow (live demo link for Devpost)

**Recommended:** [Streamlit Community Cloud](https://share.streamlit.io) — free, built for this stack.

## Prerequisites

1. Push latest code to **public** GitHub: https://github.com/aldofahrezy/Warung-Flow  
2. No API keys required for judges (`PAYMENT_MODE=mock`, `LLM_MODE=mock`).

## Streamlit Community Cloud (≈5 minutes)

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
```

(Or copy from `.streamlit/secrets.toml.example`.)

8. Click **Deploy**. Wait 2–5 minutes for the build.
9. Open the app → click **Run WarungFlow Agent** once.

### Devpost

Paste the live URL in **Live Deployment Link (Optional)** on Devpost.

## Alternative: Render

1. https://dashboard.render.com → **New +** → **Blueprint**  
2. Connect `aldofahrezy/Warung-Flow` (uses `render.yaml` in repo).  
3. Deploy; use the `*.onrender.com` URL on Devpost.

## Verify after deploy

- App loads without errors.
- Mock mode banner visible.
- One agent run completes; reconciliation table and exports appear.
- Agent trace shows **≥8** tool steps.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on deps | Ensure `requirements.txt` is at repo root (4 packages). |
| Agent run errors | Set secrets `PAYMENT_MODE=mock`, `LLM_MODE=mock`. |
| Slow cold start | Normal on free tier; mention in demo video. |

## Team

**OpenClaw2026_MuhammadAldoFahrezy** · WarungFlow
