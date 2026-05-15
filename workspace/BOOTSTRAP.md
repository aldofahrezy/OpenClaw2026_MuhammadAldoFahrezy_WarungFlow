# BOOTSTRAP

**Startup Instructions for Agent Workspace**

To initialize the WarungFlow agent environment:
1. Ensure the Python virtual environment is activated (`source .venv/bin/activate`).
2. Verify that `data/` contains all the required merchant data CSV/JSON files.
3. Configure API keys in `.env` (optional). If missing, the agent will gracefully fallback to `mock` modes.
4. Execute the orchestrator loop by running the Streamlit app:
   `streamlit run app.py`
5. The agent is initialized when the UI loads, and the autonomous loop triggers when "Run WarungFlow Agent" is clicked.
