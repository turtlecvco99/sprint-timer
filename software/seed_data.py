import sqlite3
import random
from datetime import datetime, timedelta

DB = '../data/sprint_data.db'

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS runs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT,
        athlete     TEXT,
        split_0_10  REAL,
        split_10_30 REAL,
        split_30_60 REAL,
        total       REAL,
        top_speed   REAL
    )''')
    conn.commit()
    conn.close()

# Each athlete has a (base_0_10, base_10_30, base_30_60) representing their speed level
ATHLETES = [
    ("Franklin",  1.92, 2.48, 3.20),
    ("Marcus",    1.88, 2.42, 3.12),
    ("Jordan",    1.95, 2.55, 3.30),
    ("Darius",    1.90, 2.46, 3.18),
    ("Tyler",     1.97, 2.58, 3.35),
    ("Zion",      1.86, 2.39, 3.08),
    ("Cameron",   1.93, 2.50, 3.22),
    ("Elijah",    1.89, 2.44, 3.15),
]

def seed_athlete(conn, name, b1, b2, b3, n=20):
    base_date = datetime.now() - timedelta(days=30)
    for i in range(n):
        improvement = i * 0.003
        fatigue     = random.uniform(-0.02, 0.04)
        s1 = round(b1 - improvement + fatigue, 3)
        s2 = round(b2 - improvement + fatigue, 3)
        s3 = round(b3 - improvement + fatigue, 3)
        total     = round(s1 + s2 + s3, 3)
        top_speed = round(30 / s3 * 2.237, 2)
        date      = (base_date + timedelta(days=i * 1.5)).isoformat()
        conn.execute('''INSERT INTO runs
            (date, athlete, split_0_10, split_10_30, split_30_60, total, top_speed)
            VALUES (?,?,?,?,?,?,?)''',
            (date, name, s1, s2, s3, total, top_speed))

def seed():
    init_db()
    conn = sqlite3.connect(DB)
    conn.execute('DELETE FROM runs')
    for name, b1, b2, b3 in ATHLETES:
        seed_athlete(conn, name, b1, b2, b3)
        print(f"Seeded {name}")
    conn.commit()
    conn.close()
    print(f"\nDone — {len(ATHLETES)} athletes in the database.")

if __name__ == '__main__':
    seed()
