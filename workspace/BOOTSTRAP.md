# BOOTSTRAP

**Startup Instructions for Agent Workspace**

To initialize the WarungFlow agent environment:
1. Ensure the Python virtual environment is activated (`source .venv/bin/activate`).
2. Verify that `data/` contains all the required merchant data CSV/JSON files.
3. Configure API keys in `.env` (optional). If missing, the agent will gracefully fallback to `mock` modes.
4. Execute the orchestrator loop by running the Streamlit app:
   `streamlit run app.py`
5. The agent initializes when the UI loads; sample data loads automatically and the autonomous loop runs on first open (and on input-hash changes when auto-refresh is enabled).
6. Optional: start the WhatsApp bot API with `uvicorn bot_server:app --port 8000` for the **WhatsApp Bot** dashboard page.
