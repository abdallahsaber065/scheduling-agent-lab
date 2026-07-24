import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "database.db")

def init_database():
    """Initializes SQLite database and seeds it with realistic Egyptian Real Estate data."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Drop existing tables safely
    cursor.execute("DROP TABLE IF EXISTS bookings;")
    cursor.execute("DROP TABLE IF EXISTS agent_schedules;")
    cursor.execute("DROP TABLE IF EXISTS properties;")
    cursor.execute("DROP TABLE IF EXISTS agents;")

    # 1. Create Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        agent_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        property_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        location TEXT NOT NULL,
        status TEXT NOT NULL,
        notice_hours INTEGER NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_schedules (
        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        is_available INTEGER NOT NULL,
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id TEXT PRIMARY KEY,
        property_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(property_id),
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
    );
    """)

    # 2. Seed Data
    agents_data = [
        ("AG-01", "أحمد مصطفى", "01012345678"),
        ("AG-02", "سارة محمود", "01122334455")
    ]
    cursor.executemany("INSERT INTO agents VALUES (?, ?, ?);", agents_data)

    properties_data = [
        ("APT-102", "شقة 102 - سموحة الإسكندرية", "سموحة", "OCCUPIED", 24),
        ("APT-105", "شقة 105 - جليم على البحر", "جليم", "VACANT", 0)
    ]
    cursor.executemany("INSERT INTO properties VALUES (?, ?, ?, ?, ?);", properties_data)

    schedules_data = [
        ("AG-01", "Today 17:00", 1),
        ("AG-01", "Today 14:00", 0),
        ("AG-01", "Today 20:00", 0),
        ("AG-01", "Today 21:00", 1),
        ("AG-01", "Tomorrow 11:00", 1),
        ("AG-02", "Today 17:00", 1),
        ("AG-02", "Today 20:00", 0),  # 8 PM busy for Apt 105 agent
        ("AG-02", "Today 21:00", 1),  # 9 PM available (just 1h later!)
        ("AG-02", "Tomorrow 15:00", 1)
    ]
    cursor.executemany("INSERT INTO agent_schedules (agent_id, time_slot, is_available) VALUES (?, ?, ?);", schedules_data)

    conn.commit()
    conn.close()
    print("Database `database.db` initialized and seeded successfully.")

if __name__ == "__main__":
    init_database()
