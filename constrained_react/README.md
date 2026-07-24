# Constrained ReAct Agent

## Overview
Governed ReAct loop enforcing strict engineering constraints: Pydantic schema validation for every step (`AgentStep`), explicit tool allow-list (`ALLOWED_ACTIONS`), hard step budget (`MAX_STEPS = 10`), and bounded retries via `tenacity`.

## Key Implementation Locations
- **Validation Schema**: Defined in [`schemas.py`](file:///f:/Collage/Autonomous%20Agents/Week%201/constrained_react/schemas.py) (`AgentStep` and `ActionInput` Pydantic models with `extra="forbid"` for strict schema compliance).
- **Tool Allow-List**: Defined in [`schemas.py`](file:///f:/Collage/Autonomous%20Agents/Week%201/constrained_react/schemas.py) (`ALLOWED_ACTIONS = [...]`).
- **Step Budget**: Defined in [`agent.py`](file:///f:/Collage/Autonomous%20Agents/Week%201/constrained_react/agent.py) (`MAX_STEPS = 10`).
- **Bounded Retries**: Defined in [`agent.py`](file:///f:/Collage/Autonomous%20Agents/Week%201/constrained_react/agent.py) (`@retry(stop=stop_after_attempt(3))`).

## Model / Provider Expected
- Configured via `MODEL_NAME` in `.env` using **LiteLLM**.
- Supported Providers: Gemini (`gemini/gemini-2.5-flash`), Groq (`groq/openai/gpt-oss-120b`), OpenAI (`openai/gpt-4o-mini`), OpenRouter, Ollama.

## How to Run
```bash
# From workspace root:
uv run python -m constrained_react.agent

# Or from this folder:
python agent.py
```

## Trajectory Behavior
Executes structured multi-step reasoning trajectory:
1. Queries access rules for `APT-102` $\rightarrow$ Result: `OCCUPIED` (24h advance notice required).
2. Queries agent calendar for secondary preference `APT-105` at 8 PM (`Today 20:00`) $\rightarrow$ Result: `is_available: false` (Agent busy).
3. Calls `suggest_alternative_time()` for `APT-105` $\rightarrow$ Discovers `Today 21:00` (9 PM - 1 hour after requested 8 PM).
4. Returns polite final answer in Egyptian Arabic proposing 9 PM tonight (`Today 21:00`) for `APT-105` and asking the customer if they wish to submit a 24-hour notice booking request for `APT-102`.
