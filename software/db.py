import sqlite3
import pandas as pd
from datetime import datetime
import os

_here = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_here, '..', 'data', 'sprint_data.db')


def get_conn():
    return sqlite3.connect(DB)


def get_all_athletes():
    conn = get_conn()
    df = pd.read_sql("SELECT DISTINCT athlete FROM runs ORDER BY athlete", conn)
    conn.close()
    return df['athlete'].tolist()


def load_athlete_runs(name):
    conn = get_conn()
    df = pd.read_sql(
        "SELECT * FROM runs WHERE athlete=? ORDER BY date DESC", conn, params=(name,))
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    return df


def load_all_runs():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM runs ORDER BY date DESC", conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    return df


def load_leaderboard():
    conn = get_conn()
    df = pd.read_sql('''
        SELECT athlete,
            MIN(total)       AS best_total,
            MIN(split_0_10)  AS best_0_10,
            MIN(split_10_30) AS best_10_30,
            MIN(split_30_60) AS best_30_60,
            MAX(top_speed)   AS top_speed,
            COUNT(*)         AS runs,
            MAX(date)        AS last_run
        FROM runs
        GROUP BY athlete
        ORDER BY best_total ASC
    ''', conn)
    conn.close()
    if df.empty:
        return df
    df['rank'] = range(1, len(df) + 1)
    df['last_run'] = pd.to_datetime(df['last_run']).dt.strftime('%b %d, %Y')
    return df


def load_athlete_profile(name):
    conn = get_conn()
    try:
        df = pd.read_sql(
            "SELECT * FROM athletes WHERE name=?", conn, params=(name,))
        conn.close()
        return df.iloc[0].to_dict() if not df.empty else {}
    except Exception:
        return {}


def save_athlete_profile(name, school, events, age, height, weight, bio):
    conn = get_conn()
    conn.execute('''INSERT INTO athletes (name,school,events,age,height,weight,bio,created_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET
        school=excluded.school, events=excluded.events, age=excluded.age,
        height=excluded.height, weight=excluded.weight, bio=excluded.bio''',
        (name, school, events, age, height, weight, bio, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def log_run_to_db(athlete, date, s1, s2, s3, total, top_speed):
    conn = get_conn()
    conn.execute('''INSERT INTO runs
        (date,athlete,split_0_10,split_10_30,split_30_60,total,top_speed)
        VALUES (?,?,?,?,?,?,?)''',
        (date, athlete, s1, s2, s3, total, top_speed))
    conn.commit()
    conn.close()


def get_all_athletes_with_stats():
    conn = get_conn()
    df = pd.read_sql('''SELECT athlete as name,
        COUNT(*) as runs,
        MIN(total) as best,
        MAX(date) as last_run
        FROM runs GROUP BY athlete ORDER BY best''', conn)
    conn.close()
    return df


def add_athlete_to_db(name, school, events, age, height):
    conn = get_conn()
    conn.execute('''INSERT OR IGNORE INTO athletes
        (name,school,events,age,height,created_at)
        VALUES (?,?,?,?,?,?)''',
        (name, school, events, age, height, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_global_stats():
    conn = get_conn()
    try:
        row = conn.execute('''SELECT
            COUNT(DISTINCT athlete) as athlete_count,
            COUNT(*) as total_runs,
            MIN(total) as fastest_total,
            MAX(top_speed) as top_speed_ever
            FROM runs''').fetchone()
        conn.close()
        return {
            'athlete_count': row[0] or 0,
            'total_runs': row[1] or 0,
            'fastest_total': row[2] or 0.0,
            'top_speed_ever': row[3] or 0.0,
        }
    except Exception:
        conn.close()
        return {'athlete_count': 0, 'total_runs': 0, 'fastest_total': 0.0, 'top_speed_ever': 0.0}
