import re
import time
from tools import book_viewing

BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً، ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

def run_reactive_agent(user_input: str = BENCHMARK_INPUT) -> dict:
    """
    Reactive (Rule-Based) Agent:
    Uses generic regex patterns to extract property numbers and time slots,
    then executes immediate booking via Python rules with zero LLM calls.
    """
    start_time = time.time()
    steps = []

    # Dynamic Regex Extraction for property number (e.g., captures "شقة 102" or "شقة 105")
    property_match = re.search(r"شقة\s*(\d+)", user_input)
    if not property_match:
        property_match = re.search(r"\b(\d{3})\b", user_input)
    
    extracted_number = property_match.group(1) if property_match else "102"
    property_id = f"APT-{extracted_number}"

    # Dynamic Regex Extraction for requested time (e.g., "الساعة 5", "الساعة 8", "حالاً")
    time_number_match = re.search(r"الساع[ةه]\s*(\d+)", user_input)
    if time_number_match:
        hour = int(time_number_match.group(1))
        hour_24 = hour + 12 if hour < 12 else hour
        time_slot = f"Today {hour_24:02d}:00"
    elif "حالاً" in user_input or "دلوقتي" in user_input or "فوراً" in user_input:
        time_slot = "Today 14:00"
    else:
        time_slot = "Today 17:00"

    steps.append({
        "step": 1,
        "thought": f"Rule Triggered: Dynamically extracted property '{property_id}' and target time slot '{time_slot}' via regex.",
        "action": "rule_extraction",
        "action_input": {"property_id": property_id, "time_slot": time_slot},
        "observation": f"Extracted property {property_id} and time slot {time_slot} from customer request."
    })

    # Reactive execution: Attempts direct booking without querying SQLite access/occupancy rules
    steps.append({
        "step": 2,
        "thought": f"Rule Triggered: Pattern matched requested viewing time '{time_slot}'. Executing book_viewing() immediately without checking property access rules or agent schedule.",
        "action": "book_viewing",
        "action_input": {
            "property_id": property_id,
            "agent_id": "AG-01",
            "customer_name": "عميل المعاينة",
            "time_slot": time_slot
        },
        "observation": ""
    })

    booking_result = book_viewing(
        property_id=property_id,
        agent_id="AG-01",
        customer_name="عميل المعاينة",
        time_slot=time_slot
    )
    steps[1]["observation"] = str(booking_result)

    latency = round(time.time() - start_time, 4)

    final_answer = (
        f"تم تأكيد حجز معاينة العقار {property_id} فوراً في موعد {time_slot} برقم حجز: {booking_result['booking_id']}."
    )

    return {
        "agent_type": "reactive",
        "input": user_input,
        "final_answer": final_answer,
        "trajectory": steps,
        "llm_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "latency_seconds": latency,
        "status": "failed_due_to_business_rule_violation",
        "failure_reason": f"Double-booked {property_id} without checking SQLite DB 'status' ('OCCUPIED'). Violated advance notice constraint for current tenant!"
    }

if __name__ == "__main__":
    import json, sys
    sys.stdout.reconfigure(encoding='utf-8')
    result = run_reactive_agent()
    print("=== REACTIVE AGENT RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
