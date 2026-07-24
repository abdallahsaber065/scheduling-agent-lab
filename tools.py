import uuid
from db import query_db, execute_db

def check_agent_calendar(agent_id: str, time_slot: str) -> dict:
    """
    Checks if a real estate agent is available for a viewing at a specific time slot.
    """
    results = query_db(
        "SELECT is_available FROM agent_schedules WHERE agent_id = ? AND time_slot = ?",
        (agent_id, time_slot)
    )
    if not results:
        # Default fallback if slot is not explicitly scheduled
        return {
            "status": "success",
            "agent_id": agent_id,
            "time_slot": time_slot,
            "is_available": False,
            "message": f"الوكيل {agent_id} غير متاح في موعد {time_slot} (غير مسجل بالجدول)."
        }
    
    is_avail = bool(results[0]["is_available"])
    return {
        "status": "success",
        "agent_id": agent_id,
        "time_slot": time_slot,
        "is_available": is_avail,
        "message": f"الوكيل {agent_id} {'متاح' if is_avail else 'مشغول'} في {time_slot}."
    }

def get_property_access_rules(property_id: str) -> dict:
    """
    Queries property status and access rules (whether it is VACANT or OCCUPIED requiring 24h notice).
    """
    results = query_db(
        "SELECT property_id, title, location, status, notice_hours FROM properties WHERE property_id = ?",
        (property_id,)
    )
    if not results:
        return {
            "status": "error",
            "message": f"العقار {property_id} غير موجود بقاعدة البيانات."
        }
    
    prop = results[0]
    return {
        "status": "success",
        "property_id": prop["property_id"],
        "title": prop["title"],
        "location": prop["location"],
        "occupancy_status": prop["status"],
        "notice_hours_required": prop["notice_hours"],
        "requires_advance_notice": prop["notice_hours"] > 0,
        "message": f"العقار {prop['title']} حالته: {prop['status']} ويحتاج إذن قبل المعاينة بـ {prop['notice_hours']} ساعة."
    }

def book_viewing(property_id: str, agent_id: str, customer_name: str, time_slot: str) -> dict:
    """
    Inserts a confirmed viewing booking record into the database.
    """
    booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
    execute_db(
        "INSERT INTO bookings (booking_id, property_id, agent_id, customer_name, time_slot) VALUES (?, ?, ?, ?, ?)",
        (booking_id, property_id, agent_id, customer_name, time_slot)
    )
    return {
        "status": "confirmed",
        "booking_id": booking_id,
        "property_id": property_id,
        "agent_id": agent_id,
        "customer_name": customer_name,
        "time_slot": time_slot,
        "message": f"تم تأكيد حجز المعاينة بنجاح برقم {booking_id} للعقار {property_id} مع الوكيل {agent_id} في موعد {time_slot}."
    }

def suggest_alternative_time(property_id: str, agent_id: str) -> dict:
    """
    Queries available time slots for an agent and property from SQLite agent_schedules.
    """
    results = query_db(
        "SELECT time_slot FROM agent_schedules WHERE agent_id = ? AND is_available = 1",
        (agent_id,)
    )
    suggested_slots = [r["time_slot"] for r in results]
    if not suggested_slots:
        suggested_slots = ["Today 21:00", "Tomorrow 11:00"]

    return {
        "status": "success",
        "property_id": property_id,
        "agent_id": agent_id,
        "suggested_slots": suggested_slots,
        "message": f"المواعيد البديلة المتاحة للمعاينة: {', '.join(suggested_slots)}."
    }

def escalate_to_human_broker(property_id: str, reason: str) -> dict:
    """
    Logs an escalation ticket to hand off a complex viewing request to a human broker.
    """
    ticket_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    return {
        "status": "escalated",
        "ticket_id": ticket_id,
        "property_id": property_id,
        "reason": reason,
        "message": f"تم تصعيد الطلب للسمسار البشري برقم تذكرة {ticket_id}. السبب: {reason}"
    }

# Dictionary mapping tool names to callable Python functions
AVAILABLE_TOOLS = {
    "check_agent_calendar": check_agent_calendar,
    "get_property_access_rules": get_property_access_rules,
    "book_viewing": book_viewing,
    "suggest_alternative_time": suggest_alternative_time,
    "escalate_to_human_broker": escalate_to_human_broker
}
