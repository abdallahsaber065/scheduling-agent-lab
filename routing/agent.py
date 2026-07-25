import os
import json
import time
from typing import Literal, Optional
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel, Field
from typing import Literal
from tools import check_agent_calendar, get_property_access_rules, book_viewing, list_properties

load_dotenv()

BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً ومين الساكن أو المالك بتاعها عشان أتواصل معاه؟ ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

class IntentClassification(BaseModel):
    intent: Literal["BOOK_IMMEDIATE", "SCHEDULE_FLEXIBLE", "DISCOVER_PROPERTIES", "GENERAL_INFO"] = Field(
        ..., description="Classifies the customer request intent."
    )
    property_id: Optional[str] = Field(default=None, description="Target primary property ID (e.g. APT-102)")
    location: Optional[str] = Field(default=None, description="Target location literal for property discovery (e.g. 'سموحة' / 'Smouha' or 'جليم' / 'Gleem')")
    requested_time: Optional[str] = Field(default=None, description="Requested viewing time slot (e.g. Today 17:00 or Today 20:00)")
    reasoning: str = Field(..., description="Brief rationale for classification")

def run_routing_agent(user_input: str = BENCHMARK_INPUT, model_name: Optional[str] = None) -> dict:
    """
    Deterministic Routing Agent:
    Uses 1 constrained LLM call to classify intent, then routes to a fixed Python code path.
    """
    if not model_name:
        model_name = os.getenv("MODEL_NAME", "mistral/mistral-small-2506")
    start_time = time.time()
    trajectory = []

    system_prompt = (
        "You are an intent classifier for Cornerstone Realty Group. "
        "Analyze the customer request and classify it strictly into one of: "
        "BOOK_IMMEDIATE (urgent viewing today), SCHEDULE_FLEXIBLE (inquiry for future viewing), "
        "or GENERAL_INFO (general question about location or price)."
    )

    llm_calls = 1
    total_prompt_tokens = 0
    total_completion_tokens = 0

    try:
        response = completion(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format=IntentClassification,
            temperature=0.0
        )
        usage = getattr(response, "usage", None)
        if usage:
            total_prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            total_completion_tokens = getattr(usage, "completion_tokens", 0) or 0

        parsed_json = json.loads(response.choices[0].message.content)
        classification = IntentClassification.model_validate(parsed_json)
    except Exception as e:
        latency = round(time.time() - start_time, 4)
        return {
            "agent_type": "routing",
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

    trajectory.append({
        "step": 1,
        "thought": f"Single LLM Call Classifier: {classification.reasoning}",
        "action": "classify_intent",
        "action_input": {"intent": classification.intent, "property_id": classification.property_id, "requested_time": classification.requested_time},
        "observation": f"Intent classified as '{classification.intent}'. Routing to fixed workflow code."
    })

    # Fixed Python Code Workflow for BOOK_IMMEDIATE
    if classification.intent == "BOOK_IMMEDIATE":
        # Step 1 in fixed workflow: Check agent availability
        cal_res = check_agent_calendar("AG-01", classification.requested_time)
        trajectory.append({
            "step": 2,
            "thought": "Fixed Workflow Step 1: Check SQLite AG-01 schedule.",
            "action": "check_agent_calendar",
            "action_input": {"agent_id": "AG-01", "time_slot": classification.requested_time},
            "observation": json.dumps(cal_res, ensure_ascii=False)
        })

        # Step 2 in fixed workflow: Check property rules
        rule_res = get_property_access_rules(classification.property_id)
        trajectory.append({
            "step": 3,
            "thought": "Fixed Workflow Step 2: Check SQLite property status & notice requirements.",
            "action": "get_property_access_rules",
            "action_input": {"property_id": classification.property_id},
            "observation": json.dumps(rule_res, ensure_ascii=False)
        })

        # FAILURE POINT IN FIXED CODE:
        # Fixed code cannot adapt dynamically. It hits OCCUPIED status (24h notice rule)
        # and has no dynamic reasoning step to call suggest_alternative_time().
        if rule_res.get("occupancy_status") == "OCCUPIED" and rule_res.get("notice_hours_required", 0) > 0:
            latency = round(time.time() - start_time, 4)
            final_text = (
                f"تعذر تأكيد الحجز الفوري! العقار {classification.property_id} مسكون ويحتاج إذن المالك بـ 24 ساعة."
            )
            return {
                "agent_type": "routing",
                "input": user_input,
                "final_answer": final_text,
                "trajectory": trajectory,
                "llm_calls": llm_calls,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "latency_seconds": latency,
                "status": "failed_due_to_rigid_workflow",
                "failure_reason": "Routing agent classified request as BOOK_IMMEDIATE. When SQLite revealed 24h occupancy restriction, fixed workflow code could not dynamically pivot to suggest alternative slots."
            }

    elif classification.intent == "DISCOVER_PROPERTIES":
        props_res = list_properties(classification.location)
        trajectory.append({
            "step": 2,
            "thought": f"Fixed Workflow Step 1: Query SQLite properties for location '{classification.location}'.",
            "action": "list_properties",
            "action_input": {"location": classification.location},
            "observation": json.dumps(props_res, ensure_ascii=False)
        })
        props_text = "\n".join([f"- {p['title']} (الحالة: {'فيها ساكن' if p['status']=='OCCUPIED' else 'فارغة ومتاحة'})" for p in props_res.get("properties", [])])
        final_text = f"إليك العقارات المتاحة للاكتشاف في {classification.location or 'جميع المناطق'}:\n{props_text}\nأيها ترغب في معاينته؟"
        return {
            "agent_type": "routing",
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

    # Default fallback for other intents
    latency = round(time.time() - start_time, 4)
    return {
        "agent_type": "routing",
        "input": user_input,
        "final_answer": "تم معالجة الطلب عبر الكود الثابت.",
        "trajectory": trajectory,
        "llm_calls": llm_calls,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "latency_seconds": latency,
        "status": "completed",
        "failure_reason": None
    }

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    result = run_routing_agent()
    print("=== ROUTING AGENT RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
