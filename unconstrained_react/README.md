# Unconstrained ReAct Agent

## Overview
Free-form ReAct loop ($Thought \rightarrow Action \rightarrow Observation$). Allows the LLM freedom over reasoning, tool selection, and stopping points up to a maximum budget of 10 steps (`max_loop = 10`).

## Model / Provider Expected
- Primary Model: **`gemini/gemini-3.5-lite`** (configured via `MODEL_NAME` in `.env` using **LiteLLM**).
- Alternate Supported Models: `gemini/gemini-3.6-flash`, `mistral/mistral-small-2506`, `groq/llama-3.3-70b-versatile`, `openai/gpt-4o-mini`.

## How to Run
```bash
# From workspace root:
uv run python -m unconstrained_react.agent

# Or from this folder:
python agent.py
```

## Trajectory Behavior
1. Free-form reasoning loop without Pydantic schema enforcement or explicit tool allow-lists.
2. If an undefined tool or non-matching parameter key is invoked, the backend captures the error and returns a detailed system alert observation back to the model context.
3. The model receives observation feedback and attempts to self-correct, refine property IDs, query alternatives, or escalate across up to 10 reasoning steps.
