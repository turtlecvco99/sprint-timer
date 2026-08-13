import sqlite3
import pandas as pd
from datetime import datetime
import os
import hashlib as _hashlib
import os as _os_auth

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
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    return df


def load_all_runs():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM runs ORDER BY date DESC", conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'], format='mixed')
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
    df['last_run'] = pd.to_datetime(df['last_run'], format='mixed').dt.strftime('%b %d, %Y')
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


def save_athlete_profile(name, school, events, age, height, weight, bio,
                         hometown='', coach='', grad_year='', position='',
                         goal_total=0.0, goal_0_10=0.0, goal_10_30=0.0,
                         goal_30_60=0.0, profile_color='#89C4E1',
                         gender='', avatar_type='initial', avatar_emoji='',
                         avatar_image=None):
    conn = get_conn()
    conn.execute('''
        INSERT INTO athletes
            (name,school,events,age,height,weight,bio,hometown,coach,
             grad_year,position,goal_total,goal_0_10,goal_10_30,
             goal_30_60,profile_color,gender,avatar_type,avatar_emoji,
             avatar_image,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET
            school=excluded.school, events=excluded.events,
            age=excluded.age, height=excluded.height,
            weight=excluded.weight, bio=excluded.bio,
            hometown=excluded.hometown, coach=excluded.coach,
            grad_year=excluded.grad_year, position=excluded.position,
            goal_total=excluded.goal_total, goal_0_10=excluded.goal_0_10,
            goal_10_30=excluded.goal_10_30, goal_30_60=excluded.goal_30_60,
            profile_color=excluded.profile_color, gender=excluded.gender,
            avatar_type=excluded.avatar_type, avatar_emoji=excluded.avatar_emoji,
            avatar_image=excluded.avatar_image
    ''', (name, school, events, age, height, weight, bio, hometown,
          coach, grad_year, position, goal_total, goal_0_10,
          goal_10_30, goal_30_60, profile_color, gender, avatar_type,
          avatar_emoji, avatar_image,
          datetime.now().isoformat()))
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


def get_recent_runs(limit=20):
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM runs ORDER BY date DESC, id DESC LIMIT ?", conn, params=(limit,))
    best_df = pd.read_sql("SELECT athlete, MIN(total) as pb FROM runs GROUP BY athlete", conn)
    conn.close()
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.merge(best_df, on='athlete', how='left')
    df['is_pb'] = (df['total'] - df['pb']).abs() < 0.001
    if 'kudos' not in df.columns:
        df['kudos'] = 0
    df['kudos'] = df['kudos'].fillna(0).astype(int)
    return df


def add_kudos(run_id):
    conn = get_conn()
    conn.execute('UPDATE runs SET kudos = COALESCE(kudos, 0) + 1 WHERE id=?', (run_id,))
    conn.commit()
    conn.close()


def update_run(run_id, date, s1, s2, s3, total, top_speed):
    conn = get_conn()
    conn.execute('''UPDATE runs SET date=?, split_0_10=?, split_10_30=?,
        split_30_60=?, total=?, top_speed=? WHERE id=?''',
        (date, s1, s2, s3, total, top_speed, run_id))
    conn.commit()
    conn.close()


def delete_run(run_id):
    conn = get_conn()
    conn.execute('DELETE FROM runs WHERE id=?', (run_id,))
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


def _hash_password(password: str, salt: bytes = None):
    if salt is None:
        salt = _os_auth.urandom(32)
    key = _hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return salt.hex(), key.hex()


def register_user(display_name: str, username: str, password: str, role: str = 'athlete') -> tuple:
    """
    Register a new account.
    display_name: what shows in the leaderboard (athlete name). For coaches, same as username.
    username: private login handle (must be unique).
    role: 'athlete' or 'coach'.
    Returns (True, '') on success, (False, reason_str) on failure.
    """
    conn = get_conn()
    # Check username not taken
    if conn.execute('SELECT 1 FROM athletes WHERE username=?', (username,)).fetchone():
        conn.close()
        return False, 'Username already taken.'
    # Check display_name not already claimed (has password)
    existing = conn.execute('SELECT password_hash FROM athletes WHERE name=?', (display_name,)).fetchone()
    if existing and existing[0]:
        conn.close()
        return False, f'Athlete name "{display_name}" is already claimed.'
    salt_hex, key_hex = _hash_password(password)
    conn.execute('INSERT OR IGNORE INTO athletes (name, created_at) VALUES (?, ?)',
                 (display_name, datetime.now().isoformat()))
    conn.execute('UPDATE athletes SET username=?, password_hash=?, salt=?, role=? WHERE name=?',
                 (username, key_hex, salt_hex, role, display_name))
    conn.commit()
    conn.close()
    return True, ''


def verify_login(username: str, password: str) -> bool:
    """Returns True if username+password is valid."""
    conn = get_conn()
    row = conn.execute('SELECT password_hash, salt FROM athletes WHERE username=?', (username,)).fetchone()
    conn.close()
    if not row or not row[0] or not row[1]:
        return False
    try:
        salt = bytes.fromhex(row[1])
        _, expected = _hash_password(password, salt)
        return expected == row[0]
    except Exception:
        return False


def username_exists(username: str) -> bool:
    """Return True if this username is already registered."""
    conn = get_conn()
    row = conn.execute('SELECT password_hash FROM athletes WHERE username=? AND password_hash IS NOT NULL', (username,)).fetchone()
    conn.close()
    return bool(row)


def get_name_by_username(username: str) -> str:
    """Get the display name (athlete name) from a username."""
    conn = get_conn()
    row = conn.execute('SELECT name FROM athletes WHERE username=?', (username,)).fetchone()
    conn.close()
    return row[0] if row else username


def get_user_role(username: str) -> str:
    """Return 'coach' or 'athlete' for a given username."""
    conn = get_conn()
    row = conn.execute('SELECT role FROM athletes WHERE username=?', (username,)).fetchone()
    conn.close()
    return row[0] if (row and row[0]) else 'athlete'


def name_has_runs(name: str) -> bool:
    """Return True if there are runs logged for this athlete display name."""
    conn = get_conn()
    row = conn.execute('SELECT 1 FROM runs WHERE athlete=? LIMIT 1', (name,)).fetchone()
    conn.close()
    return bool(row)
