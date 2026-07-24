import os
import json
import time
from dotenv import load_dotenv
from litellm import completion
from tools import check_agent_calendar, get_property_access_rules, book_viewing, suggest_alternative_time, escalate_to_human_broker

load_dotenv()

BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً، ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

SYSTEM_PROMPT = """You are an unconstrained real estate assistant for Cornerstone Realty Group in Alexandria.
You are given a customer request in Egyptian Arabic.
You can reason freely using Thought, Action, and Action Input.

Available real estate actions you can call:
- check_agent_calendar(agent_id, time_slot)
- get_property_access_rules(property_id)
- book_viewing(property_id, agent_id, customer_name, time_slot)
- suggest_alternative_time(property_id, agent_id)
- escalate_to_human_broker(property_id, reason)
- final_answer(response_text)

You may also call any other tools or actions you think might be needed to solve the customer's request!

Output format for each step must be:
Thought: <your detailed reasoning>
Action: <action_name>
Action Input: <json_object_or_string>
"""

def run_unconstrained_react_agent(user_input: str = BENCHMARK_INPUT, max_loop: int = 10) -> dict:
    """
    Unconstrained LLM-Powered Agent:
    Free-form ReAct loop without strict schema enforcement.
    If an undefined tool is called, returns an observation error message back to the LLM to observe self-correction.
    """
    model_name = os.getenv("MODEL_NAME", "gemini/gemini-2.5-flash")
    start_time = time.time()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Customer Request: {user_input}"}
    ]

    trajectory = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    llm_calls = 0

    for step_idx in range(1, max_loop + 1):
        llm_calls += 1
        try:
            response = completion(
                model=model_name,
                messages=messages,
                temperature=0.3
            )
        except Exception as e:
            latency = round(time.time() - start_time, 4)
            return {
                "agent_type": "unconstrained_react",
                "input": user_input,
                "final_answer": f"خطأ في الاتصال بالنموذج الذكي: {str(e)}",
                "trajectory": trajectory,
                "llm_calls": llm_calls,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "latency_seconds": latency,
                "status": "error",
                "failure_reason": f"API / Model Error: {str(e)}"
            }

        usage = getattr(response, "usage", None)
        if usage:
            total_prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            total_completion_tokens += getattr(usage, "completion_tokens", 0) or 0

        raw_text = response.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": raw_text})

        # Parse Thought, Action, Action Input
        thought = ""
        action = ""
        action_input = {}

        for line in raw_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("Thought:"):
                thought = line_str.replace("Thought:", "").strip()
            elif line_str.startswith("Action:"):
                action = line_str.replace("Action:", "").strip()
            elif line_str.startswith("Action Input:"):
                raw_input = line_str.replace("Action Input:", "").strip()
                try:
                    action_input = json.loads(raw_input)
                except Exception:
                    action_input = {"input": raw_input}

        if isinstance(action_input, str):
            action_input = {"property_id": action_input, "agent_id": "AG-01", "time_slot": action_input, "response_text": action_input}
        elif not isinstance(action_input, dict):
            action_input = {}

        if not action:
            action = "unknown_action"

        observation = ""
        is_hallucinated = False

        # Execute known tools or log hallucination failure
        if action == "check_agent_calendar":
            obs = check_agent_calendar(action_input.get("agent_id", "AG-01"), action_input.get("time_slot", "Today 17:00"))
            observation = json.dumps(obs, ensure_ascii=False)
        elif action == "get_property_access_rules":
            obs = get_property_access_rules(action_input.get("property_id", "APT-102"))
            observation = json.dumps(obs, ensure_ascii=False)
        elif action == "book_viewing":
            obs = book_viewing(action_input.get("property_id", "APT-102"), action_input.get("agent_id", "AG-01"), action_input.get("customer_name", "عميل"), action_input.get("time_slot", "Today 17:00"))
            observation = json.dumps(obs, ensure_ascii=False)
        elif action == "suggest_alternative_time":
            obs = suggest_alternative_time(action_input.get("property_id", "APT-102"), action_input.get("agent_id", "AG-01"))
            observation = json.dumps(obs, ensure_ascii=False)
        elif action == "escalate_to_human_broker":
            obs = escalate_to_human_broker(action_input.get("property_id", "APT-102"), action_input.get("reason", "manual escalation"))
            observation = json.dumps(obs, ensure_ascii=False)
        elif action == "final_answer":
            final_text = action_input.get("response_text", raw_text)
            trajectory.append({
                "step": step_idx,
                "thought": thought or raw_text,
                "action": "final_answer",
                "action_input": action_input,
                "observation": "Terminated by final_answer."
            })
            return {
                "agent_type": "unconstrained_react",
                "input": user_input,
                "final_answer": final_text,
                "trajectory": trajectory,
                "llm_calls": llm_calls,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "latency_seconds": round(time.time() - start_time, 4),
                "status": "completed",
                "failure_reason": None
            }
        else:
            # Undefined tool call: Return error message observation back to model instead of killing loop
            is_hallucinated = True
            observation = f"ERROR: Tool '{action}' is invalid or non-existent in backend system! Available registered tools are: check_agent_calendar, get_property_access_rules, book_viewing, suggest_alternative_time, escalate_to_human_broker, final_answer."

        trajectory.append({
            "step": step_idx,
            "thought": thought or raw_text,
            "action": action,
            "action_input": action_input,
            "observation": observation,
            "is_hallucinated": is_hallucinated
        })

        messages.append({"role": "user", "content": f"Observation: {observation}"})

    latency = round(time.time() - start_time, 4)
    last_text = raw_text if 'raw_text' in locals() else "تجاوز الحد الأقصى للمحاولات (10 steps) دون الوصول لقرار نهائي."
    return {
        "agent_type": "unconstrained_react",
        "input": user_input,
        "final_answer": last_text,
        "trajectory": trajectory,
        "llm_calls": llm_calls,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "latency_seconds": latency,
        "status": "failed_max_steps_exceeded",
        "failure_reason": "Unconstrained loop exceeded maximum steps due to re-transmission context growth."
    }

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    result = run_unconstrained_react_agent()
    print("=== UNCONSTRAINED REACT AGENT RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
