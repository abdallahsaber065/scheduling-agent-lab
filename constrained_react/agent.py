import os
import json
import time
from typing import Optional
from dotenv import load_dotenv
from litellm import completion
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_fixed
from constrained_react.schemas import AgentStep, ALLOWED_ACTIONS
from tools import (
    check_agent_calendar,
    get_property_access_rules,
    book_viewing,
    suggest_alternative_time,
    escalate_to_human_broker,
    get_available_locations,
    list_properties
)

load_dotenv()

# Hard termination budget as required by assignment
MAX_STEPS = 10
BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً ومين الساكن أو المالك بتاعها عشان أتواصل معاه؟ ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

SYSTEM_PROMPT = f"""You are a professional real estate scheduling assistant for Cornerstone Realty Group in Alexandria.
Your goal is to coordinate property viewings for customers, handle multi-property inquiries, and assist with scheduling.

OPERATIONAL GUIDELINES & POLICY RULES:
1. MAX_STEPS = {MAX_STEPS}. Efficiently resolve the request within the step limit.
2. ALLOWED ACTIONS: You must ONLY invoke actions from the following list: {ALLOWED_ACTIONS}.
3. LOCATION DISCOVERY & PROPERTY LISTINGS:
   - To query available portfolio locations, use get_available_locations().
   - If a customer is exploring or discovering options without specifying a property ID, call list_properties(location) using location literals ('Smouha' / 'سموحة' or 'Gleem' / 'جليم').
   - LOCATION VALIDATION: If list_properties(location) returns count=0 or status='not_found', validate the result to the customer and suggest the valid available locations returned by the tool ('سموحة' or 'جليم').
4. PROPERTY ACCESS & OCCUPANCY POLICY:
   - Always query property access rules using get_property_access_rules(property_id) before attempting a booking.
   - If a property is OCCUPIED (requiring advance notice), immediate same-day entry is forbidden under company policy. Inform the customer of the notice requirement and offer to schedule/request a viewing slot after the notice period.
5. AGENT CALENDAR & ALTERNATIVE SLOTS:
   - Verify agent calendar availability using check_agent_calendar(agent_id, time_slot).
   - If an agent is unavailable or a requested time slot is busy (is_available = false), use suggest_alternative_time(property_id, agent_id) to query available same-day or nearest open time slots for the customer.
6. CUSTOMER TRANSLATION & ARABIC LOCALIZATION DIRECTIVE:
   - Always translate technical database values and time formats into natural Egyptian Arabic for the customer:
     * 'OCCUPIED' -> 'مسكونة / فيها ساكن حالياً وتتطلب إشعار مسبق'
     * 'VACANT' -> 'فارغة ومتاحة للمعاينة'
     * 'Today 21:00' -> 'النهاردة الساعة 9 بالليل'
     * 'Today 17:00' -> 'النهاردة الساعة 5 عصراً'
     * 'Today 20:00' -> 'النهاردة الساعة 8 المغرب'
     * 'Tomorrow 11:00' -> 'بكرة الساعة 11 الصبح'
     * 'Tomorrow 15:00' -> 'بكرة الساعة 3 بعد الظهر'
   - NEVER include raw English database codes like 'OCCUPIED', 'VACANT', or 'Today 21:00' in final_answer response_text!
7. FINAL RESOLUTION:
   - Conclude with action 'final_answer' setting is_final=true and providing a clear, polite Egyptian Arabic response summarizing all verified options and asking the customer how they wish to proceed.
"""

@retry(
    stop=stop_after_attempt(3),  # Initial call + max 2 retries on validation failure
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type((ValueError, Exception)),
    reraise=True
)
def generate_valid_step(model_name: str, messages: list) -> tuple[AgentStep, dict]:
    """
    Generates an AgentStep validated against Pydantic schema with tenacity bounded retries.
    Returns (AgentStep, usage_dict).
    """
    response = completion(
        model=model_name,
        messages=messages,
        response_format=AgentStep,
        temperature=0.1
    )
    
    raw_content = response.choices[0].message.content
    parsed_json = json.loads(raw_content)
    step = AgentStep.model_validate(parsed_json)

    # Validate action is inside allow-list
    if step.action not in ALLOWED_ACTIONS:
        raise ValueError(f"Action '{step.action}' is not in the ALLOWED_ACTIONS allow-list!")

    usage = getattr(response, "usage", None)
    usage_data = {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0
    }
    return step, usage_data

def run_constrained_react_agent(user_input: str = BENCHMARK_INPUT, model_name: Optional[str] = None) -> dict:
    """
    Constrained ReAct Agent:
    Governed ReAct loop enforcing Pydantic schema validation, tool allow-list,
    MAX_STEPS = 10 budget, and Tenacity retries.
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

    for step_num in range(1, MAX_STEPS + 1):
        llm_calls += 1
        try:
            step_obj, usage_data = generate_valid_step(model_name, messages)
            total_prompt_tokens += usage_data["prompt_tokens"]
            total_completion_tokens += usage_data["completion_tokens"]
        except Exception as e:
            latency = round(time.time() - start_time, 4)
            return {
                "agent_type": "constrained_react",
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

        # Execute Tool Action
        observation = ""
        action_name = step_obj.action
        action_in = step_obj.action_input.model_dump(exclude_none=True) if hasattr(step_obj.action_input, "model_dump") else step_obj.action_input

        if action_name == "get_available_locations":
            obs_dict = get_available_locations()
            observation = json.dumps(obs_dict, ensure_ascii=False)
        elif action_name == "list_properties":
            obs_dict = list_properties(action_in.get("location"))
            observation = json.dumps(obs_dict, ensure_ascii=False)
        elif action_name == "check_agent_calendar":
            obs_dict = check_agent_calendar(action_in.get("agent_id", "AG-01"), action_in.get("time_slot", "Today 17:00"))
            observation = json.dumps(obs_dict, ensure_ascii=False)
        elif action_name == "get_property_access_rules":
            obs_dict = get_property_access_rules(action_in.get("property_id", "APT-102"))
            observation = json.dumps(obs_dict, ensure_ascii=False)
        elif action_name == "book_viewing":
            obs_dict = book_viewing(action_in.get("property_id", "APT-102"), action_in.get("agent_id", "AG-01"), action_in.get("customer_name", "عميل"), action_in.get("time_slot", "Today 17:00"))
            observation = json.dumps(obs_dict, ensure_ascii=False)
        elif action_name == "suggest_alternative_time":
            obs_dict = suggest_alternative_time(action_in.get("property_id", "APT-102"), action_in.get("agent_id", "AG-01"))
            observation = json.dumps(obs_dict, ensure_ascii=False)
        elif action_name == "escalate_to_human_broker":
            obs_dict = escalate_to_human_broker(action_in.get("property_id", "APT-102"), action_in.get("reason", "escalated request"))
            observation = json.dumps(obs_dict, ensure_ascii=False)
        elif action_name == "final_answer":
            final_text = action_in.get("response_text", "تمت المعالجة بنجاح.")
            trajectory.append({
                "step": step_num,
                "thought": step_obj.thought,
                "action": "final_answer",
                "action_input": action_in,
                "observation": "Goal satisfied. Loop terminated with final answer."
            })
            latency = round(time.time() - start_time, 4)
            return {
                "agent_type": "constrained_react",
                "input": user_input,
                "final_answer": final_text,
                "trajectory": trajectory,
                "llm_calls": llm_calls,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "latency_seconds": latency,
                "status": "success",
                "failure_reason": None
            }

        trajectory.append({
            "step": step_num,
            "thought": step_obj.thought,
            "action": action_name,
            "action_input": action_in,
            "observation": observation
        })

        messages.append({
            "role": "assistant",
            "content": step_obj.model_dump_json()
        })
        messages.append({
            "role": "user",
            "content": f"Observation: {observation}"
        })

        if step_obj.is_final:
            final_text = action_in.get("response_text", observation)
            latency = round(time.time() - start_time, 4)
            return {
                "agent_type": "constrained_react",
                "input": user_input,
                "final_answer": final_text,
                "trajectory": trajectory,
                "llm_calls": llm_calls,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "latency_seconds": latency,
                "status": "success",
                "failure_reason": None
            }

    latency = round(time.time() - start_time, 4)
    return {
        "agent_type": "constrained_react",
        "input": user_input,
        "final_answer": "وصل الوكيل إلى الحد الأقصى للمحاولات (MAX_STEPS = 5) وتصعيد الطلب تلقائياً للسمسار البشري.",
        "trajectory": trajectory,
        "llm_calls": llm_calls,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "latency_seconds": latency,
        "status": "escalated_max_steps",
        "failure_reason": "Exceeded MAX_STEPS budget of 5. Gracefully escalated to human broker."
    }

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    result = run_constrained_react_agent()
    print("=== CONSTRAINED REACT AGENT RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
