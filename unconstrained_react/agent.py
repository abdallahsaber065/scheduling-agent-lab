import os
import json
import time
from typing import Optional
from dotenv import load_dotenv
from litellm import completion
from tools import check_agent_calendar, get_property_access_rules, book_viewing, suggest_alternative_time, escalate_to_human_broker

load_dotenv()

BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً، ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

SYSTEM_PROMPT = """You are a real estate scheduling assistant for Cornerstone Realty Group in Alexandria.
Your goal is to assist customers with property viewing requests in Egyptian Arabic.

You operate using a Reasoning and Action (ReAct) loop:
- Thought: Describe your reasoning about the customer's request and what information or action is needed next.
- Action: The function/tool to invoke.
- Action Input: Parameters for the action as a JSON object or string.

Available real estate functions:
- check_agent_calendar(agent_id, time_slot): Check agent availability for a time slot.
- get_property_access_rules(property_id): Verify property occupancy status and required notice period.
- book_viewing(property_id, agent_id, customer_name, time_slot): Reserve a viewing slot.
- suggest_alternative_time(property_id, agent_id): Query alternative available viewing slots when requested times are unavailable.
- escalate_to_human_broker(property_id, reason): Escalate complex cases to a human broker.
- final_answer(response_text): Provide the final response to the customer.

General Guidelines:
- Check property access rules and agent schedule availability before confirming bookings.
- If a property is occupied or an agent is unavailable, check for alternative available time slots.
- Always translate raw system codes into friendly Egyptian Arabic for the customer (e.g., 'OCCUPIED' -> 'فيها ساكن حالياً', 'Today 21:00' -> 'النهاردة الساعة 9 بالليل'). Never output raw English database codes to the customer.
"""

def run_unconstrained_react_agent(user_input: str = BENCHMARK_INPUT, max_loop: int = 10, model_name: Optional[str] = None) -> dict:
    """
    Unconstrained LLM-Powered Agent:
    Free-form ReAct loop without strict schema enforcement.
    If an undefined tool is called, returns an observation error message back to the LLM to observe self-correction.
    """
    if not model_name:
        model_name = os.getenv("MODEL_NAME", "mistral/mistral-small-2506")
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
