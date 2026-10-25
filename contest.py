"""Global test bootstrap.

Forces offline mode so the whole suite runs without any network access and
without needing cloud API keys. This keeps `pytest` and `lockdown_check.py`
hermetic — no real OpenAI/Anthropic/Replicate calls during CI.
"""
import os

# Force the LLM client into deterministic offline mode for every test run.
os.environ["LLM_PROVIDER"] = "openai"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["REPLICATE_API_TOKEN"] = ""

# Speed up the orchestrator DB by using a temp path when tests trigger it.
os.environ.setdefault("ORCHESTRATOR_DB", "./.factory/state.db")
