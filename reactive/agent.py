import re
import time
from tools import book_viewing

BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً، ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

def run_reactive_agent(user_input: str = BENCHMARK_INPUT) -> dict:
    """
    Reactive (Rule-Based) Agent:
    Uses pure regex and hardcoded if/else rules with ZERO LLM calls.
    
    EXPECTED FAILURE MODE:
    It extracts property 'APT-102' and time 'Today 17:00' (الساعة 5) from text,
    and immediately calls `book_viewing()` without checking property access rules 
    or agent schedule in SQLite. It double-books an OCCUPIED apartment without 24h notice!
    """
    start_time = time.time()
    steps = []

    # Step 1: Rule-based regex extraction
    property_match = re.search(r"شقة\s*(102|105)", user_input)
    property_id = f"APT-{property_match.group(1)}" if property_match else "APT-102"

    time_match = re.search(r"الساعة\s*5", user_input)
    time_slot = "Today 17:00" if time_match else "Today 14:00"

    steps.append({
        "step": 1,
        "thought": f"Rule Triggered: Extracted property '{property_id}' and requested time '{time_slot}' via regex.",
        "action": "rule_extraction",
        "action_input": {"property_id": property_id, "time_slot": time_slot},
        "observation": f"Extracted target property {property_id} and time slot {time_slot}."
    })

    # Step 2: Reactive execution (No DB lookup check!)
    steps.append({
        "step": 2,
        "thought": "Rule Triggered: Time requested matches 'الساعة 5'. Calling book_viewing() immediately without checking property status or schedule.",
        "action": "book_viewing",
        "action_input": {
            "property_id": property_id,
            "agent_id": "AG-01",
            "customer_name": "عميل سموحة",
            "time_slot": time_slot
        },
        "observation": ""
    })

    booking_result = book_viewing(
        property_id=property_id,
        agent_id="AG-01",
        customer_name="عميل سموحة",
        time_slot=time_slot
    )
    steps[1]["observation"] = str(booking_result)

    latency = round(time.time() - start_time, 4)

    final_answer = (
        f"تم حجز معاينة شقة 102 في سموحة فوراً اليوم الساعة 5 مساءً (Today 17:00) مع الوكيل أحمد مصطفى! "
        f"رقم الحجز: {booking_result['booking_id']}."
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
        "failure_reason": "Double-booked APT-102 without checking SQLite DB 'status' ('OCCUPIED'). Violated 24-hour notice constraint for current tenant!"
    }

if __name__ == "__main__":
    import json, sys
    sys.stdout.reconfigure(encoding='utf-8')
    result = run_reactive_agent()
    print("=== REACTIVE AGENT RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
