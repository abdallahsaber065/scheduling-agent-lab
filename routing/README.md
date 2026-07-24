# Deterministic Routing Agent

## Overview
Single constrained LLM call to classify user intent into a fixed set of categories (`BOOK_IMMEDIATE`, `SCHEDULE_FLEXIBLE`, `GENERAL_INFO`). All execution after classification is fixed Python code.

## Model / Provider Expected
- Primary Model: **`gemini/gemini-3.5-lite`** (configured via `MODEL_NAME` in `.env` using **LiteLLM**).
- Alternate Supported Models: `gemini/gemini-3.6-flash`, `mistral/mistral-small-2506`, `groq/llama-3.3-70b-versatile`, `openai/gpt-4o-mini`.

## How to Run
```bash
# From workspace root:
uv run python -m routing.agent

# Or from this folder:
python agent.py
```

## Trajectory Behavior
1. Classifies request intent as `BOOK_IMMEDIATE`.
2. Control flow passes into fixed Python workflow code:
   - Step 1: Checks agent calendar for `AG-01` schedule.
   - Step 2: Checks property access rules for `APT-102` $\rightarrow$ `OCCUPIED` (24h notice required).
3. Fixed workflow code returns: `"تعذر تأكيد الحجز الفوري! العقار APT-102 مسكون ويحتاج إذن المالك بـ 24 ساعة."`. Fixed code cannot dynamically evaluate secondary preferences or pivot to query alternative time slots.
