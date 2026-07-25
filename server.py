import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from init_db import init_database
from reactive.agent import run_reactive_agent
from unconstrained_react.agent import run_unconstrained_react_agent
from routing.agent import run_routing_agent
from constrained_react.agent import run_constrained_react_agent

app = FastAPI(title="Cornerstone Realty - Agent Design Lab", version="1.0.0")

# Serve static directory for UI assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

class AgentRunRequest(BaseModel):
    user_input: str
    model_name: Optional[str] = None

BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً ومين الساكن أو المالك بتاعها عشان أتواصل معاه؟ ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

@app.get("/")
def get_index():
    """Serves the main web interface dashboard."""
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.post("/api/reset-db")
def reset_db_endpoint():
    """Resets and re-seeds SQLite database database.db."""
    try:
        init_database()
        return {"status": "success", "message": "Database reset & re-seeded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run/{agent_type}")
def run_agent_endpoint(agent_type: str, request: AgentRunRequest):
    """
    Executes a single agent architecture with custom or benchmark input and selected LLM model.
    Agent types: 'reactive', 'routing', 'unconstrained_react', 'constrained_react'.
    """
    input_text = request.user_input or BENCHMARK_INPUT
    model = request.model_name

    if agent_type == "reactive":
        res = run_reactive_agent(input_text)
    elif agent_type == "routing":
        res = run_routing_agent(input_text, model_name=model)
    elif agent_type == "unconstrained_react":
        res = run_unconstrained_react_agent(input_text, model_name=model)
    elif agent_type == "constrained_react":
        res = run_constrained_react_agent(input_text, model_name=model)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown agent type '{agent_type}'")

    return res

@app.post("/api/benchmark")
def run_all_benchmark(request: Optional[AgentRunRequest] = None):
    """
    Executes the benchmark input across ALL 4 agent architectures
    (Non-ReAct pair first, followed by side-by-side ReAct pair)
    """
    model = request.model_name if request else None
    r1 = run_reactive_agent(BENCHMARK_INPUT)
    r2 = run_routing_agent(BENCHMARK_INPUT, model_name=model)
    r3 = run_unconstrained_react_agent(BENCHMARK_INPUT, model_name=model)
    r4 = run_constrained_react_agent(BENCHMARK_INPUT, model_name=model)

    return {
        "benchmark_input": BENCHMARK_INPUT,
        "results": {
            "reactive": r1,
            "routing": r2,
            "unconstrained_react": r3,
            "constrained_react": r4
        }
    }

if __name__ == "__main__":
    import uvicorn
    if not os.path.exists("database.db"):
        init_database()
    should_reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=should_reload)
