# Cornerstone Realty Group — Viewing Scheduling Agent Lab (Week 1)
**Faculty of Computers and Data Science (FCDS), Alexandria University**  
*Course: Autonomous Agents — Assignment 1*

---

## 🏢 1. Company & Problem Domain Context

### Company Profile
**Cornerstone Realty Group** is a premier real estate brokerage operating across Alexandria and Cairo (Smouha, Gleem, Zamalek, New Cairo). The company manages property viewings for thousands of prospective buyers and tenants.

### The Problem: Property Viewing Scheduling & Access Coordination (تنسيق مواعيد المعاينات)
Prospective clients submit unstructured Egyptian Arabic messages demanding immediate or urgent viewings:
> *"أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً، ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"*

### Why This Genuinely Requires an Agent (Step Dependency)
Confirming a viewing cannot be solved by a simple keyword script because **Step 2 directly depends on Step 1's SQLite DB query result**:
- **Step 1**: Query `properties` for access rules of `APT-102`. Result: **Status = `OCCUPIED`**, requiring a mandatory **24-hour notice** to respect current tenant privacy.
- **Step 2**: Query `agent_schedules` for secondary preference `APT-105` at 8 PM (`Today 20:00`). Result: Agent busy at 8 PM.
- **Step 3 (Decision Pivot)**: Query available slots for `APT-105`. Discovers `Today 21:00` (9 PM - 1 hour after requested 8 PM) and offers it to the customer along with a notice request option for `APT-102`.

---

## 📊 2. Architecture Comparison

Evaluated on the benchmark Egyptian Arabic request across all 4 agent patterns:

| Architecture Pattern | LLM Calls | Approx. Tokens | Latency (sec) | Execution Characteristics & Behavior |
| :--- | :---: | :---: | :---: | :--- |
| **1. Reactive (Rule-Based)** | 0 | 0 | < 0.01s | Regex extracts property ID and time slot, calling `book_viewing()` immediately without querying DB occupancy status. |
| **2. Deterministic Routing** | 1 | 400–900 | 0.8–1.5s | Single LLM call classifies intent into `BOOK_IMMEDIATE`. Control passes to fixed code which checks `APT-102` status (`OCCUPIED`). Rigid code cannot dynamically evaluate secondary preferences. |
| **3. Unconstrained ReAct** | 1–10 | 800–4,500 | 1.3–8.5s | Free-form ReAct loop without strict schema enforcement. When non-existent tools or parameters are called, error messages return as observations to observe self-correction behavior. |
| **4. Constrained ReAct** | 1–5 | 2,000–6,800 | 3.5–6.0s | Governed loop with Pydantic validation schema, explicit tool allow-list, and hard step budget (`MAX_STEPS = 10`). Checks `APT-102` status, checks `APT-105` schedule at 8 PM, discovers same-day 9 PM slot, and formulates response. |

---

## 🛠️ 3. Quick Start & Execution Guide

### Prerequisites
- Python 3.11+
- `uv` package manager (`pnpm` / `uv`)

### Setup Instructions
```bash
# 1. Sync dependencies with uv
uv sync

# 2. Configure Environment Variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY

# 3. Initialize SQLite Database
uv run python init_db.py
```

### Running Individual Agents via CLI

```bash
# 1. Reactive Agent (Rule-Based)
uv run python -m reactive.agent

# 2. Unconstrained ReAct Agent
uv run python -m unconstrained_react.agent

# 3. Deterministic Routing Agent
uv run python -m routing.agent

# 4. Constrained ReAct Agent
uv run python -m constrained_react.agent
```

### Launching the Interactive Web Dashboard
```bash
uv run python server.py
# Open browser at: http://localhost:8000
```

---

## 🛡️ 4. Constrained ReAct Engineering Constraints

In `constrained_react/`, strict engineering controls prevent execution loops and malformed responses:

1. **Pydantic Validation Schema** (`constrained_react/schemas.py`):
   ```python
   class AgentStep(BaseModel):
       thought: str
       action: Literal["check_agent_calendar", "get_property_access_rules", "book_viewing", "suggest_alternative_time", "escalate_to_human_broker", "final_answer"]
       action_input: ActionInput
       is_final: bool
   ```

2. **Explicit Tool Allow-List** (`constrained_react/schemas.py`):
   `ALLOWED_ACTIONS = ["check_agent_calendar", "get_property_access_rules", "book_viewing", "suggest_alternative_time", "escalate_to_human_broker", "final_answer"]`

3. **Hard Step Budget** (`constrained_react/agent.py`):
   `MAX_STEPS = 10`

4. **Bounded Retries with Tenacity** (`constrained_react/agent.py`):
   ```python
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_fixed(0.5),
       retry=retry_if_exception_type((ValueError, Exception)),
       reraise=True
   )
   ```

---

## 📁 5. Repository Structure

```
Week 1/
├── database.db                   # SQLite Database (seeded with properties & schedules)
├── init_db.py                    # Database initialization & seeding script
├── db.py                         # SQLite helper functions
├── tools.py                      # Real estate tool implementations
├── server.py                     # FastAPI backend & web server
├── pyproject.toml                # Project dependencies (uv)
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore file
├── reactive/                     # Reactive Agent implementation
│   ├── agent.py
│   └── README.md
├── routing/                      # Deterministic Routing Agent implementation
│   ├── agent.py
│   └── README.md
├── unconstrained_react/          # Unconstrained ReAct Agent implementation
│   ├── agent.py
│   └── README.md
├── constrained_react/            # Governed Constrained ReAct Agent implementation
│   ├── agent.py
│   ├── schemas.py
│   └── README.md
└── static/                       # Web UI frontend assets
    ├── index.html
    ├── styles.css
    └── app.js
```
