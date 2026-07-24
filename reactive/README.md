# Reactive (Rule-Based) Agent

## Overview
Pure Python rule-based decision loop using regex pattern matching and hardcoded conditions. Zero LLM calls.

## Model / Provider Expected
- **None** (0 LLM calls). Operates 100% deterministically using Python standard library regex.

## How to Run
```bash
# From workspace root:
uv run python -m reactive.agent

# Or from this folder:
python agent.py
```

## Trajectory Behavior
1. Extracted target property `"APT-102"` and requested time via regex.
2. Directly calls `book_viewing()` immediately without querying SQLite for property status (`OCCUPIED`) or notice requirements, creating a booking over an occupied unit without checking mandatory 24-hour tenant notice rules.
