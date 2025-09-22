import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("management.db")
cursor = conn.cursor()

start_time = datetime(2025, 6, 1)
end_time = datetime(2025, 9, 22)
interval = timedelta(minutes=5)

appliances = {
    27: (1200, 2000),  # AC
    28: (80, 150),     # Fridge
    29: (1000, 1800),  # AC2
    30: (40, 100),     # Fan
    31: (10, 500),     # Socket1
    32: (10, 500),     # Socket2
    33: (10, 500),     # Socket3
}

user_id = 8
current_time = start_time
batch = []

while current_time < end_time:
    for appliance_id, (min_watt, max_watt) in appliances.items():
        power = round(random.uniform(min_watt, max_watt), 2)
        batch.append((user_id, appliance_id, power, current_time, current_time))

    if len(batch) >= 1000:
        cursor.executemany("""
            INSERT INTO power_logs (user_id, appliance_id, power_consumed, time, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        batch = []

    current_time += interval

if batch:
    cursor.executemany("""
        INSERT INTO power_logs (user_id, appliance_id, power_consumed, time, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
