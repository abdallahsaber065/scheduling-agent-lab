import re
import time
from tools import book_viewing, get_property_access_rules, list_properties

BENCHMARK_INPUT = "أنا واقف قدام العمارة بتاعة شقة 102 في سموحة وعايز أدخل أشوفها حالاً ومين الساكن أو المالك بتاعها عشان أتواصل معاه؟ ولو غير متاحة أو محتاجة إذن الساكن احجزلي شقة 105 في جليم الساعة 8 المغرب النهاردة، أو قولّي أقرب ميعاد لشقة 102 عشان مسافر القاهرة!"

def run_reactive_agent(user_input: str = BENCHMARK_INPUT) -> dict:
    """
    Reactive (Rule-Based) Agent:
    Uses generic regex patterns to extract property numbers and time slots,
    queries property access rules for occupation checks via Python rules (0 LLM calls).
    """
    start_time = time.time()
    steps = []

    # Check for general discovery request without specific property ID number
    has_specific_number = re.search(r"شقة\s*\d+", user_input) or re.search(r"\b\d{3}\b", user_input)
    if not has_specific_number and ("شقق" in user_input or "اكتشف" in user_input or "المتاحة" in user_input or "سموحة" in user_input or "جليم" in user_input):
        loc_match = re.search(r"(سموحة|جليم)", user_input)
        location = loc_match.group(1) if loc_match else None
        props_res = list_properties(location)
        steps.append({
            "step": 1,
            "thought": f"Rule Triggered: Discovery keyword matched. Invoking list_properties('{location or 'All'}').",
            "action": "list_properties",
            "action_input": {"location": location},
            "observation": str(props_res)
        })
        props_text = "\n".join([f"- {p['title']} (الحالة: {'فيها ساكن' if p['status']=='OCCUPIED' else 'فارغة ومتاحة'})" for p in props_res.get("properties", [])])
        final_answer = f"إليك الشقق المتاحة في {location or 'جميع المناطق'}:\n{props_text}\nاختر رقم الشقة للبدء بالحجز."
        return {
            "agent_type": "reactive",
            "input": user_input,
            "final_answer": final_answer,
            "trajectory": steps,
            "llm_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_seconds": round(time.time() - start_time, 4),
            "status": "completed",
            "failure_reason": None
        }

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

    # Rule Step 2: Occupation Rule Check
    access_info = get_property_access_rules(property_id)
    steps.append({
        "step": 2,
        "thought": f"Rule Triggered: Executing occupation check for property {property_id} in SQLite DB.",
        "action": "get_property_access_rules",
        "action_input": {"property_id": property_id},
        "observation": str(access_info)
    })

    # Rule Step 3: Evaluate occupation status
    if access_info.get("occupancy_status") == "OCCUPIED" and access_info.get("notice_hours_required", 0) > 0:
        latency = round(time.time() - start_time, 4)
        final_answer = (
            f"تعذر حجز معاينة فورية لشقة {property_id}! الشقة فيها ساكن حالياً وتتطلب إشعار مسبق قبل المعاينة بـ {access_info.get('notice_hours_required')} ساعة."
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
            "status": "failed_due_to_rigid_rules",
            "failure_reason": f"Reactive rule caught OCCUPIED status for {property_id}, but rigid rule logic cannot evaluate secondary preferences (APT-105) or suggest alternative agent times."
        }

    # If vacant, proceed to book
    booking_result = book_viewing(
        property_id=property_id,
        agent_id="AG-01",
        customer_name="عميل المعاينة",
        time_slot=time_slot
    )
    steps.append({
        "step": 3,
        "thought": f"Rule Triggered: Property {property_id} is VACANT. Executing book_viewing() immediately.",
        "action": "book_viewing",
        "action_input": {"property_id": property_id, "agent_id": "AG-01", "time_slot": time_slot},
        "observation": str(booking_result)
    })

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
        "status": "completed",
        "failure_reason": None
    }

if __name__ == "__main__":
    import json, sys
    sys.stdout.reconfigure(encoding='utf-8')
    result = run_reactive_agent()
    print("=== REACTIVE AGENT RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
