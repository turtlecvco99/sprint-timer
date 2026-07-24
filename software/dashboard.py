import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import datetime
import random
import os
import io

from db import (
    get_all_athletes, load_athlete_runs, load_all_runs, load_leaderboard,
    load_athlete_profile, save_athlete_profile, log_run_to_db,
    get_all_athletes_with_stats, add_athlete_to_db, get_global_stats, DB,
    register_user, verify_login, username_exists, get_name_by_username,
    get_user_role, name_has_runs,
)

st.set_page_config(
    page_title="DRIVE PHASE",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None,
                'About': "DRIVE PHASE — Sprint analytics built for athletes."},
)

# ── Session state ──────────────────────────────────────────────────────────────
if 'page' not in st.session_state:
    st.session_state.page = "MY DASHBOARD"
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'
if 'auth_error' not in st.session_state:
    st.session_state.auth_error = ''
if 'auth_success' not in st.session_state:
    st.session_state.auth_success = ''
if 'user_role' not in st.session_state:
    st.session_state.user_role = ''
if 'public_view' not in st.session_state:
    st.session_state.public_view = False
if 'auth_portal' not in st.session_state:
    st.session_state.auth_portal = 'athlete'  # 'athlete' or 'coach'

_here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(_here, '..', 'data'), exist_ok=True)


def _bootstrap():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, athlete TEXT,
        split_0_10 REAL, split_10_30 REAL,
        split_30_60 REAL, total REAL, top_speed REAL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS athletes (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT UNIQUE,
        jersey       TEXT DEFAULT '',
        position     TEXT DEFAULT '',
        age          INTEGER DEFAULT 0,
        height       TEXT DEFAULT '',
        weight       TEXT DEFAULT '',
        school       TEXT DEFAULT '',
        events       TEXT DEFAULT '',
        coach        TEXT DEFAULT '',
        hometown     TEXT DEFAULT '',
        grad_year    TEXT DEFAULT '',
        bio          TEXT DEFAULT '',
        goal_total   REAL DEFAULT 0.0,
        goal_0_10    REAL DEFAULT 0.0,
        goal_10_30   REAL DEFAULT 0.0,
        goal_30_60   REAL DEFAULT 0.0,
        profile_color TEXT DEFAULT '#FC4C02',
        created_at   TEXT
    )''')
    # Migrate existing DBs — add columns that may not exist yet
    for col_def in [
        ('hometown',      "TEXT DEFAULT ''"),
        ('coach',         "TEXT DEFAULT ''"),
        ('grad_year',     "TEXT DEFAULT ''"),
        ('position',      "TEXT DEFAULT ''"),
        ('goal_total',    "REAL DEFAULT 0.0"),
        ('goal_0_10',     "REAL DEFAULT 0.0"),
        ('goal_10_30',    "REAL DEFAULT 0.0"),
        ('goal_30_60',    "REAL DEFAULT 0.0"),
        ('profile_color', "TEXT DEFAULT '#FC4C02'"),
        ('password_hash', "TEXT DEFAULT NULL"),
        ('salt',          "TEXT DEFAULT NULL"),
        ('role',          "TEXT DEFAULT 'athlete'"),
        ('username',      "TEXT DEFAULT NULL"),
    ]:
        try:
            conn.execute(f"ALTER TABLE athletes ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass
    conn.execute("UPDATE athletes SET username = name WHERE username IS NULL AND password_hash IS NOT NULL")
    conn.commit()
    if conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0:
        base = datetime.datetime.now() - datetime.timedelta(days=30)
        for name, b1, b2, b3 in [
            ("Franklin",1.92,2.48,3.20),("Marcus",1.88,2.42,3.12),
            ("Jordan",1.95,2.55,3.30),("Darius",1.90,2.46,3.18),
            ("Tyler",1.97,2.58,3.35),("Zion",1.86,2.39,3.08),
            ("Cameron",1.93,2.50,3.22),("Elijah",1.89,2.44,3.15),
        ]:
            for i in range(20):
                imp = i*0.003; fat = random.uniform(-0.02,0.04)
                s1,s2,s3 = round(b1-imp+fat,3),round(b2-imp+fat,3),round(b3-imp+fat,3)
                total = round(s1+s2+s3,3)
                conn.execute(
                    'INSERT INTO runs (date,athlete,split_0_10,split_10_30,split_30_60,total,top_speed) VALUES (?,?,?,?,?,?,?)',
                    ((base+datetime.timedelta(days=i*1.5)).isoformat(),name,s1,s2,s3,total,round(30/s3*2.237,2)))
        conn.commit()
    conn.close()


_bootstrap()

ACCENT = '#FC4C02'
MUTED = '#6E6E76'
SUCCESS = '#1DDB8B'
DANGER = '#FF4D4D'
SCALE = [[0,ACCENT],[1.0,'#3A3A42']]
CHART_CFG = {'displayModeBar': False, 'staticPlot': False, 'responsive': True}

# ── Fonts ──────────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
* { box-sizing: border-box; }

html, body, [data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {
    background-color: #0A0A0D !important;
    color: #F5F5F7 !important;
}
[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1200px !important;
}

[data-testid="stHeader"] { height:0 !important; visibility:hidden !important; }
[data-testid="stDecoration"] { display:none !important; }
[data-testid="stAppViewContainer"] > section:first-child { padding-top:0 !important; }
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
[data-testid="stToolbar"] { display:none; }

/* ── Force sidebar to always stay expanded — never collapse ── */
section[data-testid="stSidebar"] {
    transform: none !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    min-width: 240px !important;
    width: 240px !important;
    left: 0 !important;
    position: relative !important;
}
section[data-testid="stSidebar"][aria-expanded="false"] {
    transform: none !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    width: 240px !important;
    min-width: 240px !important;
    left: 0 !important;
}
/* Hide only the collapse button inside the sidebar */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button {
    display: none !important;
}
/* Keep the expand button visible so sidebar can always be restored */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: none !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"] {
    background-color: #101013 !important;
    background: #101013 !important;
}
[data-testid="stSidebar"] {
    border-right: 1px solid #1E1E22 !important;
    min-width: 240px !important;
    max-width: 240px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem 1rem !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small {
    color: #C4C4C9 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Main content buttons — flat outline by default, solid accent for primary ── */
[data-testid="stButton"] button {
    background: transparent !important;
    border: 1px solid #26262C !important;
    color: #D0D0D6 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    text-transform: none !important;
    border-radius: 8px !important;
    padding: 8px 20px !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
}
[data-testid="stButton"] button:hover { border-color: #FC4C02 !important; color: #FC4C02 !important; }
[data-testid="stButton"] button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: #FC4C02 !important;
    border: none !important;
    color: #FFFFFF !important;
}
[data-testid="stButton"] button[kind="primary"]:hover { background: #E04500 !important; color: #FFFFFF !important; }

/* ── Form submit buttons — outline style ── */
[data-testid="stFormSubmitButton"] button {
    background: transparent !important;
    background-image: none !important;
    border: 1px solid #33333A !important;
    color: #F5F5F7 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    text-transform: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    transition: all 0.15s ease !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    background: #1A1A1E !important;
    border-color: #FC4C02 !important;
    color: #FC4C02 !important;
}

[data-testid="stDownloadButton"] button {
    background: transparent !important;
    border: 1px solid #33333A !important;
    color: #F5F5F7 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.03em !important;
    text-transform: none !important;
    border-radius: 8px !important;
    padding: 8px 20px !important;
}

/* ── Sidebar buttons — nav style ── */
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: transparent !important;
    background-image: none !important;
    border: 1px solid transparent !important;
    border-left: 2px solid transparent !important;
    color: #9A9AA2 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    text-align: left !important;
    border-radius: 6px !important;
    padding: 9px 12px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    opacity: 1 !important;
    transition: background 0.15s, color 0.15s !important;
}
[data-testid="stSidebar"] button:hover,
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: #17171B !important;
    color: #F5F5F7 !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: rgba(252,76,2,0.10) !important;
    background-image: none !important;
    border: 1px solid transparent !important;
    border-left: 2px solid #FC4C02 !important;
    color: #FC4C02 !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

/* ── Forms / inputs ── */
[data-testid="stTextInput"] input {
    background: #131316 !important;
    border: 1px solid #26262C !important;
    border-radius: 8px !important;
    color: #F5F5F7 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 9px 12px !important;
}
[data-testid="stTextInput"] input:focus { border-color: #FC4C02 !important; box-shadow:none !important; }
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label,
[data-testid="stDateInput"] label {
    font-size: 0.68rem !important; letter-spacing: 0.08em !important;
    text-transform: uppercase !important; color: #6E6E76 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #131316 !important; border: 1px solid #26262C !important;
    color: #F5F5F7 !important; border-radius: 8px !important;
}
[data-testid="stNumberInput"] input {
    background: #131316 !important; border: 1px solid #26262C !important;
    color: #F5F5F7 !important; font-family: 'JetBrains Mono', monospace !important;
}
[data-testid="stTextArea"] textarea {
    background: #131316 !important; border: 1px solid #26262C !important;
    color: #F5F5F7 !important; font-family: 'DM Sans', sans-serif !important;
}

/* ── Charts ── */
[data-testid="stPlotlyChart"] > div {
    background: #131316 !important; border-radius: 10px !important;
    padding: 8px !important; border: 1px solid #1E1E22 !important;
}

/* ── Misc ── */
[data-testid="stAlert"] {
    background: #131316 !important; border: 1px solid #1E1E22 !important;
    border-left: 3px solid #1DDB8B !important; border-radius: 8px !important;
}
[data-testid="stExpander"] {
    background: #131316 !important; border: 1px solid #1E1E22 !important; border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.78rem !important; letter-spacing: 0.06em !important;
    text-transform: uppercase !important; color: #6E6E76 !important;
}
[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
.element-container { margin-bottom: 0.15rem !important; }
[data-testid="stHorizontalBlock"] { gap: 0.75rem !important; align-items: stretch !important; }
hr {
    border: none !important; height: 1px !important;
    background: #1E1E22 !important;
    margin: 16px 0 !important;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0D; }
::-webkit-scrollbar-thumb { background: #26262C; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #FC4C02; }
@keyframes dp-pulse {
    0%,100% { opacity:1; }
    50%      { opacity:0.35; }
}

/* ── Minimal fade-in, used sparingly ── */
@keyframes fadeInUp {
    from { opacity:0; transform:translateY(8px); }
    to   { opacity:1; transform:translateY(0); }
}
[data-testid="stMainBlockContainer"] > div > div {
    animation: fadeInUp 0.25s ease both;
}

/* ── Card hover lift (subtle) ── */
.dp-card { transition: border-color 0.15s ease !important; }
.dp-card:hover { border-color: #33333A !important; }

/* ── Alert animation ── */
[data-testid="stAlert"] { animation: fadeInUp 0.2s ease both; }
[data-testid="stExpander"] { animation: fadeInUp 0.2s ease both; }

/* ── Date input dark ── */
[data-testid="stDateInput"] input {
    background: #131316 !important;
    border: 1px solid #26262C !important;
    color: #F5F5F7 !important;
    border-radius: 8px !important;
}

/* ── Selectbox fully dark ── */
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background-color: #131316 !important;
    border-color: #26262C !important;
    color: #F5F5F7 !important;
}
[data-testid="stSelectbox"] svg { fill: #6E6E76 !important; }

/* ── File uploader dark ── */
[data-testid="stFileUploader"] {
    background: #131316 !important;
    border: 1px dashed #26262C !important;
    border-radius: 10px !important;
    padding: 12px !important;
}
[data-testid="stFileUploader"] label {
    color: #6E6E76 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
}

/* ── Expander header hover ── */
[data-testid="stExpander"] summary:hover { color: #FC4C02 !important; }

/* ── Table row hover ── */
tr:hover { background: #17171B !important; }

/* ── Number input +/- buttons styled ── */
[data-testid="stNumberInput"] > div {
    background: #131316 !important;
    border: 1px solid #26262C !important;
    border-radius: 8px !important;
}
[data-testid="stNumberInput"] button {
    background: #1E1E22 !important;
    border: none !important;
    color: #9A9AA2 !important;
}
[data-testid="stNumberInput"] button:hover {
    background: #FC4C02 !important;
    color: #FFFFFF !important;
}

/* ── Success alert styled ── */
[data-testid="stAlert"][kind="success"] {
    background: #0D1712 !important;
    border: 1px solid rgba(29,219,139,0.3) !important;
    border-left: 3px solid #1DDB8B !important;
    border-radius: 0 8px 8px 0 !important;
    color: #1DDB8B !important;
}

/* ── Error alert styled ── */
[data-testid="stAlert"][kind="error"] {
    background: #1A0D0D !important;
    border: 1px solid rgba(255,77,77,0.3) !important;
    border-left: 3px solid #FF4D4D !important;
    border-radius: 0 8px 8px 0 !important;
}

/* ── Auth form submit buttons — solid accent ── */
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
    background: #FC4C02 !important;
    border: none !important;
    color: #FFFFFF !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    text-transform: none !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    transition: background 0.15s ease !important;
    width: 100% !important;
}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
    background: #E04500 !important;
}

/* ── Auth tab toggle buttons ── */
div[data-testid="stHorizontalBlock"]:has(button[kind="primary"]) button[kind="secondary"] {
    background: transparent !important;
    background-image: none !important;
    border: 1px solid #1E1E22 !important;
    color: #6E6E76 !important;
}
</style>""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def smart_yrange(series, pad=0.02):
    mn, mx = series.min(), series.max()
    margin = (mx - mn) * pad + 0.05
    return [mn - margin, mx + margin]


def style_chart(fig, height=360):
    fig.update_layout(
        paper_bgcolor='#131316', plot_bgcolor='#131316',
        font=dict(family='DM Sans', color='#9A9AA2', size=12),
        height=height, hovermode='x unified',
        hoverlabel=dict(bgcolor='#1A1A1F', bordercolor='#26262C',
                        font=dict(family='DM Sans', color='#F5F5F7', size=12)),
        xaxis=dict(gridcolor='#1E1E22', linecolor='#1E1E22',
                   tickfont=dict(family='DM Sans', size=12, color='#9A9AA2'),
                   showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='#1E1E22', linecolor='#1E1E22',
                   tickfont=dict(family='JetBrains Mono', size=11, color='#6E6E76'),
                   showgrid=True, zeroline=False),
        legend=dict(bgcolor='#0A0A0D', bordercolor='#1E1E22', borderwidth=1,
                    font=dict(family='DM Sans', size=11, color='#9A9AA2')),
        margin=dict(l=16, r=16, t=48, b=60),
    )
    return fig


def page_header(title, subtitle):
    st.markdown(f"""
    <div style="padding:16px 0 20px;border-bottom:1px solid #1E1E22;margin-bottom:24px;
                display:flex;align-items:flex-end;justify-content:space-between;">
        <div>
            <div style="font-family:'DM Sans';font-size:0.7rem;letter-spacing:0.1em;
                        text-transform:uppercase;color:#6E6E76;margin-bottom:6px;">{subtitle}</div>
            <div style="font-family:'DM Sans';font-size:2rem;font-weight:700;
                        letter-spacing:-0.01em;line-height:1;color:#F5F5F7;">{title}</div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;
                     color:#4A4A52;padding-bottom:2px;">
            {datetime.datetime.now().strftime('%a %b %d · %H:%M')}
        </span>
    </div>
    """, unsafe_allow_html=True)


def stat_card(col, label, value, unit='', accent='#FC4C02', sublabel='', size='normal'):
    font_size = '1.7rem' if size == 'normal' else '1.3rem' if size == 'small' else '2.2rem'
    sub_html = f'<div style="font-family:DM Sans;font-size:0.68rem;color:#4A4A52;margin-top:4px;">{sublabel}</div>' if sublabel else ''
    col.markdown(f"""
    <div class="dp-card" style="background:#131316;border:1px solid #1E1E22;
                border-radius:10px;padding:16px 14px;height:100%;">
        <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.1em;
                    text-transform:uppercase;color:#6E6E76;margin-bottom:8px;">{label}</div>
        <div style="font-family:'JetBrains Mono';font-size:{font_size};
                    color:{accent};line-height:1;">
            {value}<span style="font-size:0.8rem;color:#6E6E76;margin-left:3px;">{unit}</span>
        </div>{sub_html}
    </div>
    """, unsafe_allow_html=True)


def section_header(label, accent='blue'):
    st.markdown(f"""
    <div style="margin:24px 0 12px;">
        <span style="font-family:'DM Sans',sans-serif;font-size:0.78rem;font-weight:700;
                     letter-spacing:0.06em;text-transform:uppercase;color:#F5F5F7;">{label}</span>
    </div>""", unsafe_allow_html=True)


def render_rankings_table(lb_df, current_user=''):
    rows = ''
    for _, row in lb_df.iterrows():
        rank = int(row['rank'])
        rc = ACCENT if rank == 1 else '#6E6E76'
        rank_label = f'♛ #{rank}' if rank == 1 else f'#{rank}'
        is_me = row['athlete'] == current_user
        you_badge = f'<span style="font-family:DM Sans;font-size:0.55rem;background:{ACCENT};color:#FFFFFF;border-radius:999px;padding:2px 7px;margin-left:8px;font-weight:600;vertical-align:middle;">YOU</span>' if is_me else ''
        name_color = '#F5F5F7' if is_me else '#D0D0D6'
        row_bg = 'background:#17171B;' if is_me else ''
        rows += f"""<tr style="border-bottom:1px solid #1A1A1F;{row_bg}">
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:{rc};font-size:0.85rem;">{rank_label}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:{name_color};font-size:0.9rem;font-weight:500;">{row['athlete']}{you_badge}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#F5F5F7;font-size:0.85rem;">{row['best_total']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#9A9AA2;font-size:0.85rem;">{row['best_0_10']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#9A9AA2;font-size:0.85rem;">{row['best_10_30']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#9A9AA2;font-size:0.85rem;">{row['best_30_60']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#9A9AA2;font-size:0.85rem;">{row['top_speed']:.1f}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#6E6E76;font-size:0.85rem;">{row['runs']}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#6E6E76;font-size:0.78rem;">{row['last_run']}</td>
        </tr>"""
    # Field averages footer row
    all_runs_df = load_all_runs()
    if not all_runs_df.empty:
        avg_best    = all_runs_df.groupby('athlete')['total'].min().mean()
        avg_0_10    = all_runs_df.groupby('athlete')['split_0_10'].min().mean()
        avg_10_30   = all_runs_df.groupby('athlete')['split_10_30'].min().mean()
        avg_30_60   = all_runs_df.groupby('athlete')['split_30_60'].min().mean()
        avg_speed   = all_runs_df['top_speed'].mean()
        avg_runs_ct = int(all_runs_df.groupby('athlete').size().mean())
        rows += f"""<tr style="border-top:2px solid #26262C;background:#0D0D10;">
            <td style="padding:12px 16px;font-family:'DM Sans',monospace;color:#4A4A52;font-size:0.75rem;font-style:italic;">AVG</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#4A4A52;font-size:0.8rem;font-style:italic;">Field average</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#4A4A52;font-size:0.82rem;">{avg_best:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#4A4A52;font-size:0.82rem;">{avg_0_10:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#4A4A52;font-size:0.82rem;">{avg_10_30:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#4A4A52;font-size:0.82rem;">{avg_30_60:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#4A4A52;font-size:0.82rem;">{avg_speed:.1f}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#4A4A52;font-size:0.82rem;">{avg_runs_ct}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#4A4A52;font-size:0.78rem;">—</td>
        </tr>"""
    th = "padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.1em;text-transform:uppercase;color:#6E6E76;text-align:left;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E22;border-radius:10px;overflow:hidden;margin-top:8px;">
        <table style="width:100%;border-collapse:collapse;background:#131316;">
            <thead><tr style="border-bottom:2px solid #1E1E22;background:#0D0D10;">
                <th style="{th}">Rank</th><th style="{th}">Athlete</th>
                <th style="{th}">Best Total</th><th style="{th}">0–10m</th>
                <th style="{th}">10–30m</th><th style="{th}">30–60m</th>
                <th style="{th}">Top Speed</th><th style="{th}">Runs</th>
                <th style="{th}">Last Run</th>
            </tr></thead><tbody>{rows}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)


def empty_state(icon='◇', title="NO DATA", subtitle="Log some runs to unlock this."):
    st.markdown(f"""
    <div style="background:#131316;border:1px solid #1E1E22;border-radius:10px;
                padding:48px 32px;text-align:center;margin:8px 0;">
        <div style="font-size:2.5rem;margin-bottom:12px;opacity:0.4;">{icon}</div>
        <div style="font-family:'DM Sans';font-size:1.1rem;font-weight:700;
                    color:#6E6E76;margin-bottom:6px;">{title}</div>
        <div style="font-family:'DM Sans';font-size:0.78rem;color:#4A4A52;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    st.markdown("""
    <div style="margin-top:40px;padding:20px 0;border-top:1px solid #1E1E22;
                display:flex;justify-content:space-between;align-items:center;">
        <span style="font-family:'DM Sans',sans-serif;font-size:0.85rem;font-weight:700;
                     color:#4A4A52;">DRIVE PHASE</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;
                     color:#4A4A52;">built by athletes · powered by data</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#4A4A52;">v4.0</span>
    </div>""", unsafe_allow_html=True)


def info_card(text, accent='blue'):
    st.markdown(f"""
    <div style="background:#131316;border:1px solid #1E1E22;border-left:3px solid {ACCENT};
                border-radius:0 8px 8px 0;padding:12px 16px;margin:8px 0;">
        <p style="font-family:'DM Sans',sans-serif;font-size:0.82rem;
                  color:#9A9AA2;margin:0;">{text}</p>
    </div>""", unsafe_allow_html=True)


def quick_stat(label, value, color):
    return f"""<div style="display:flex;justify-content:space-between;align-items:center;
        padding:5px 0;border-bottom:1px solid #1E1E22;">
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;color:#6E6E76;">{label}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:{color};">{value}</span>
    </div>"""


# ══════════════════════════════════════════════════════════════════════════════
# IDENTITY SYSTEM — show fullscreen selector on first visit
# ══════════════════════════════════════════════════════════════════════════════
all_athletes = get_all_athletes()

# ── PUBLIC LEADERBOARD (no login) ────────────────────────────────────────────
if st.session_state.public_view and st.session_state.current_user is None:
    st.markdown("""<style>
    [data-testid="stMainBlockContainer"] { max-width:1100px !important; margin:0 auto !important; }
    [data-testid="stSidebar"] { display:none !important; }
    </style>""", unsafe_allow_html=True)

    # Top bar
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding:16px 0 20px;border-bottom:1px solid #1E1E22;margin-bottom:28px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="font-family:'DM Sans',sans-serif;font-size:1.3rem;font-weight:700;
                        color:#F5F5F7;">DRIVE PHASE</div>
            <span style="font-family:'DM Sans';font-size:0.65rem;letter-spacing:0.1em;
                         text-transform:uppercase;color:#4A4A52;">· Public Leaderboard</span>
        </div>
        <span style="font-family:'JetBrains Mono';font-size:0.68rem;color:#4A4A52;">
            {datetime.datetime.now().strftime('%a %b %d · %H:%M')}
        </span>
    </div>
    """, unsafe_allow_html=True)

    lb_pub = load_leaderboard()
    if lb_pub.empty:
        empty_state("◇", "NO DATA YET", "Check back once athletes have logged runs.")
    else:
        # Global stats strip
        gs = get_global_stats()
        gc1, gc2, gc3, gc4 = st.columns(4)
        stat_card(gc1, "Athletes", str(gs['athlete_count']), accent='#F5F5F7')
        stat_card(gc2, "Total Runs", str(gs['total_runs']), accent='#F5F5F7')
        stat_card(gc3, "Fastest Time", f"{gs['fastest_total']:.2f}", "s", accent=ACCENT)
        stat_card(gc4, "Top Speed", f"{gs['top_speed_ever']:.1f}", "mph", accent=ACCENT)
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

        section_header("FULL RANKINGS")
        render_rankings_table(lb_pub)

        section_header("BEST TOTAL TIME")
        lb_s_pub = lb_pub.sort_values('best_total')
        fig_pub = go.Figure(go.Bar(
            x=lb_s_pub['athlete'], y=lb_s_pub['best_total'],
            marker=dict(color=lb_s_pub['best_total'], colorscale=SCALE, showscale=False,
                        line=dict(color='#0A0A0D', width=1)),
            text=[f"{v:.2f}s" for v in lb_s_pub['best_total']],
            textposition='outside', textfont=dict(family='JetBrains Mono', size=11, color='#F5F5F7'),
            cliponaxis=False,
        ))
        style_chart(fig_pub, height=300)
        fig_pub.update_layout(
            bargap=0.35,
            yaxis=dict(visible=False, range=[lb_s_pub['best_total'].min()*0.97, lb_s_pub['best_total'].max()*1.04]),
            xaxis=dict(tickfont=dict(family='DM Sans', size=12, color='#9A9AA2')),
        )
        st.plotly_chart(fig_pub, use_container_width=True, config=CHART_CFG)

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    col_login, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        if st.button("LOG IN TO YOUR ACCOUNT", use_container_width=True):
            st.session_state.public_view = False
            st.rerun()
    st.markdown("""
    <div style="text-align:center;padding:16px 0;font-family:'JetBrains Mono';
                font-size:0.65rem;color:#26262C;">DRIVE PHASE · v4.0</div>
    """, unsafe_allow_html=True)
    st.stop()


# ── AUTH SCREEN ───────────────────────────────────────────────────────────────
if st.session_state.current_user is None:
    portal = st.session_state.auth_portal   # 'athlete' or 'coach'
    mode   = st.session_state.auth_mode     # 'login' or 'signup'

    is_coach = (portal == 'coach')
    subtitle  = 'team management portal' if is_coach else 'acceleration starts here'
    coach_badge_html = (
        '<div style="margin-top:10px;">'
        '<span style="font-family:DM Sans,sans-serif;font-size:0.62rem;letter-spacing:0.12em;'
        'text-transform:uppercase;background:#1A1A1E;'
        'border:1px solid #26262C;color:#9A9AA2;border-radius:999px;'
        'padding:3px 12px;">COACH PORTAL</span></div>'
    ) if is_coach else '<div></div>'

    st.markdown(
        f'<style>'
        f'[data-testid="stSidebar"]{{display:none!important;}}'
        f'[data-testid="stMainBlockContainer"]{{max-width:440px!important;margin:0 auto!important;padding-top:3rem!important;}}'
        f'</style>',
        unsafe_allow_html=True
    )

    # Brand header — single tight string, no blank lines
    st.markdown(
        f'<div style="text-align:center;padding:36px 0 20px;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:2.4rem;font-weight:800;line-height:1;'
        f'color:#F5F5F7;">DRIVE PHASE</div>'
        f'{coach_badge_html}'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-top:14px;">'
        f'<div style="width:6px;height:6px;border-radius:50%;background:{SUCCESS};flex-shrink:0;animation:dp-pulse 2s infinite;"></div>'
        f'<span style="font-family:DM Sans,sans-serif;font-size:0.68rem;letter-spacing:0.14em;text-transform:uppercase;color:#6E6E76;">{subtitle}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Public leaderboard bypass (athlete portal only) ──
    if portal == 'athlete':
        if st.button("VIEW PUBLIC LEADERBOARD", use_container_width=True, key="pub_lb_btn"):
            st.session_state.public_view = True
            st.rerun()
        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

    # ── Tab strip ──
    _tc1, _tc2 = st.columns(2)
    with _tc1:
        if st.button("LOG IN", key="tab_login", use_container_width=True,
                     type="primary" if mode == "login" else "secondary"):
            st.session_state.auth_mode = 'login'
            st.session_state.auth_error = ''
            st.rerun()
    with _tc2:
        if st.button("SIGN UP", key="tab_signup", use_container_width=True,
                     type="primary" if mode == "signup" else "secondary"):
            st.session_state.auth_mode = 'signup'
            st.session_state.auth_error = ''
            st.rerun()

    st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

    # ── Inline messages ──
    if st.session_state.auth_error:
        st.markdown(f"""
        <div style="background:#1A0D0D;border:1px solid rgba(255,77,106,0.3);
                    border-left:3px solid #FF4D4D;border-radius:0 8px 8px 0;
                    padding:10px 14px;margin-bottom:10px;
                    font-family:'DM Sans';font-size:0.8rem;color:#FF4D4D;">
            {st.session_state.auth_error}
        </div>""", unsafe_allow_html=True)

    if st.session_state.auth_success:
        st.markdown(f"""
        <div style="background:#0D1A0D;border:1px solid rgba(29,219,139,0.3);
                    border-left:3px solid #1DDB8B;border-radius:0 8px 8px 0;
                    padding:10px 14px;margin-bottom:10px;
                    font-family:'DM Sans';font-size:0.8rem;color:#1DDB8B;">
            {st.session_state.auth_success}
        </div>""", unsafe_allow_html=True)

    def _lbl(txt):
        st.markdown(
            f'<div style="font-family:\'DM Sans\';font-size:0.6rem;letter-spacing:0.14em;'
            f'text-transform:uppercase;color:#6E6E76;margin-bottom:2px;margin-top:10px;">{txt}</div>',
            unsafe_allow_html=True)

    # ════════════════════════════════════
    # ATHLETE PORTAL FORMS
    # ════════════════════════════════════
    if portal == 'athlete':
        if mode == 'login':
            with st.form("athlete_login_form", clear_on_submit=False):
                _lbl("Username")
                al_u = st.text_input("u", placeholder="your username", label_visibility="collapsed", key="al_u")
                _lbl("Password")
                al_p = st.text_input("p", type="password", placeholder="••••••••", label_visibility="collapsed", key="al_p")
                st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
                if st.form_submit_button("LOG IN  →", use_container_width=True):
                    u = al_u.strip()
                    if not u or not al_p:
                        st.session_state.auth_error = "Please fill in all fields."
                        st.rerun()
                    elif not username_exists(u):
                        st.session_state.auth_error = f"No account found for '{u}'. Sign up first."
                        st.rerun()
                    elif not verify_login(u, al_p):
                        st.session_state.auth_error = "Incorrect password."
                        st.rerun()
                    elif get_user_role(u) == 'coach':
                        st.session_state.auth_error = "That's a coach account — use the Coach Portal below."
                        st.rerun()
                    else:
                        st.session_state.current_user = get_name_by_username(u)
                        st.session_state.user_role = 'athlete'
                        st.session_state.auth_error = ''
                        st.session_state.auth_success = ''
                        st.rerun()
        else:
            with st.form("athlete_signup_form", clear_on_submit=False):
                _lbl("Athlete Name (shown on leaderboard)")
                as_n = st.text_input("n", placeholder="e.g. Franklin", label_visibility="collapsed", key="as_n")
                _lbl("Username (private login handle)")
                as_u = st.text_input("u", placeholder="e.g. frank24", label_visibility="collapsed", key="as_u")
                _lbl("Password")
                as_p = st.text_input("p", type="password", placeholder="Min 6 characters", label_visibility="collapsed", key="as_p")
                _lbl("Confirm Password")
                as_p2 = st.text_input("p2", type="password", placeholder="••••••••", label_visibility="collapsed", key="as_p2")
                st.markdown("""
                <div style="font-family:'DM Sans';font-size:0.68rem;color:#3A3A42;margin:10px 0 12px;line-height:1.5;">
                    Already have runs logged? Use your exact athlete name to link your history.
                </div>""", unsafe_allow_html=True)
                if st.form_submit_button("CREATE ACCOUNT  →", use_container_width=True):
                    n_c = as_n.strip()
                    u_c = as_u.strip().lower()
                    if not n_c or not u_c:
                        st.session_state.auth_error = "Name and username cannot be empty."
                        st.rerun()
                    elif len(as_p) < 6:
                        st.session_state.auth_error = "Password must be at least 6 characters."
                        st.rerun()
                    elif as_p != as_p2:
                        st.session_state.auth_error = "Passwords do not match."
                        st.rerun()
                    else:
                        ok, reason = register_user(n_c, u_c, as_p, role='athlete')
                        if ok:
                            msg = f"Welcome, {n_c}! History linked — log in now." if name_has_runs(n_c) else "Account created! Log in to get started."
                            st.session_state.auth_success = msg
                            st.session_state.auth_error = ''
                            st.session_state.auth_mode = 'login'
                            st.rerun()
                        else:
                            st.session_state.auth_error = reason
                            st.rerun()

    # ════════════════════════════════════
    # COACH PORTAL FORMS
    # ════════════════════════════════════
    else:
        if mode == 'login':
            with st.form("coach_login_form", clear_on_submit=False):
                _lbl("Coach Username")
                cl_u = st.text_input("cu", placeholder="your coach username", label_visibility="collapsed", key="cl_u")
                _lbl("Password")
                cl_p = st.text_input("cp", type="password", placeholder="••••••••", label_visibility="collapsed", key="cl_p")
                st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
                if st.form_submit_button("ENTER PORTAL  →", use_container_width=True):
                    cu = cl_u.strip()
                    if not cu or not cl_p:
                        st.session_state.auth_error = "Please fill in all fields."
                        st.rerun()
                    elif not username_exists(cu):
                        st.session_state.auth_error = f"No coach account found for '{cu}'."
                        st.rerun()
                    elif not verify_login(cu, cl_p):
                        st.session_state.auth_error = "Incorrect password."
                        st.rerun()
                    elif get_user_role(cu) != 'coach':
                        st.session_state.auth_error = "That's an athlete account — use the Athlete portal."
                        st.rerun()
                    else:
                        st.session_state.current_user = get_name_by_username(cu)
                        st.session_state.user_role = 'coach'
                        st.session_state.auth_error = ''
                        st.session_state.auth_success = ''
                        st.rerun()
        else:
            with st.form("coach_signup_form", clear_on_submit=False):
                _lbl("Choose a Username")
                cs_u = st.text_input("csu", placeholder="e.g. coach_smith", label_visibility="collapsed", key="cs_u")
                _lbl("Password")
                cs_p = st.text_input("csp", type="password", placeholder="Min 6 characters", label_visibility="collapsed", key="cs_p")
                _lbl("Confirm Password")
                cs_p2 = st.text_input("csp2", type="password", placeholder="••••••••", label_visibility="collapsed", key="cs_p2")
                _lbl("Coach Access Code")
                cs_c = st.text_input("csc", type="password", placeholder="Provided by your organization", label_visibility="collapsed", key="cs_c")
                st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
                if st.form_submit_button("CREATE COACH ACCOUNT  →", use_container_width=True):
                    cu2 = cs_u.strip().lower()
                    if not cu2:
                        st.session_state.auth_error = "Username cannot be empty."
                        st.rerun()
                    elif len(cs_p) < 6:
                        st.session_state.auth_error = "Password must be at least 6 characters."
                        st.rerun()
                    elif cs_p != cs_p2:
                        st.session_state.auth_error = "Passwords do not match."
                        st.rerun()
                    elif cs_c.strip() != 'DRIVEPHASE':
                        st.session_state.auth_error = "Invalid coach access code."
                        st.rerun()
                    else:
                        ok2, reason2 = register_user(cu2, cu2, cs_p, role='coach')
                        if ok2:
                            st.session_state.auth_success = "Coach account created. Log in now."
                            st.session_state.auth_error = ''
                            st.session_state.auth_mode = 'login'
                            st.rerun()
                        else:
                            st.session_state.auth_error = reason2
                            st.rerun()

    # ── Portal switcher ──
    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    if portal == 'athlete':
        st.markdown('<div style="text-align:center;"><span style="font-family:DM Sans,sans-serif;font-size:0.7rem;color:#3A3A42;">Are you a coach?</span></div>', unsafe_allow_html=True)
        if st.button("COACH PORTAL", use_container_width=True, key="to_coach"):
            st.session_state.auth_portal = 'coach'
            st.session_state.auth_mode = 'login'
            st.session_state.auth_error = ''
            st.session_state.auth_success = ''
            st.rerun()
    else:
        st.markdown('<div style="text-align:center;"><span style="font-family:DM Sans,sans-serif;font-size:0.7rem;color:#3A3A42;">Are you an athlete?</span></div>', unsafe_allow_html=True)
        if st.button("ATHLETE LOGIN", use_container_width=True, key="to_athlete"):
            st.session_state.auth_portal = 'athlete'
            st.session_state.auth_mode = 'login'
            st.session_state.auth_error = ''
            st.session_state.auth_success = ''
            st.rerun()

    st.markdown("""
    <div style="text-align:center;padding:18px 0 6px;">
        <span style="font-family:'JetBrains Mono';font-size:0.62rem;color:#1E1E22;">
            DRIVE PHASE · v4.0 · built for athletes
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

current_user = st.session_state.current_user

user_role = st.session_state.get('user_role') or 'athlete'
if not st.session_state.get('user_role'):
    st.session_state.user_role = user_role


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
_base_nav = [
    ("▪", "MY DASHBOARD"),
    ("▲", "LEADERBOARD"),
    ("◎", "GLOBAL"),
    ("●", "MY PROFILE"),
    ("↗", "MY PROGRESS"),
]
_coach_nav = [("≡", "SETTINGS")]
NAV_ITEMS = _base_nav + (_coach_nav if st.session_state.get('user_role') == 'coach' else [])

with st.sidebar:
    # Logo
    st.markdown("""
    <div style="padding:8px 0 12px;">
        <div style="font-family:'DM Sans',sans-serif;font-weight:800;font-size:1.3rem;
                    color:#F5F5F7;">DRIVE PHASE</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#6E6E76;margin-top:2px;">acceleration starts here</div>
    </div>""", unsafe_allow_html=True)

    # Identity pill
    role_label = '≡ Coach' if user_role == 'coach' else '● Athlete'
    st.markdown(f"""
    <div style="background:#131316;border:1px solid #1E1E22;
                border-radius:10px;padding:12px 14px;margin-bottom:14px;
                display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;border-radius:50%;background:{ACCENT};
                    display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <span style="font-family:'DM Sans';font-weight:700;font-size:1rem;color:#FFFFFF;">
                {current_user[0].upper()}</span>
        </div>
        <div>
            <div style="font-family:'DM Sans';font-weight:700;font-size:0.9rem;
                        color:#F5F5F7;line-height:1;">{current_user}</div>
            <div style="font-family:'DM Sans';font-size:0.6rem;color:#6E6E76;
                        letter-spacing:0.08em;text-transform:uppercase;margin-top:2px;">{role_label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
    for icon, label in NAV_ITEMS:
        active = st.session_state.page == label
        if st.button(f"{icon}  {label}", key=f"nav_{label}",
                     use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state.page = label
            st.rerun()

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    if st.button("↺  REFRESH DATA", use_container_width=True, key="nav_refresh"):
        st.cache_data.clear()
        st.rerun()

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # Live stats
    stats = get_global_stats()
    st.markdown(f"""
    <div style="background:#0A0A0D;border:1px solid #1E1E22;border-radius:10px;padding:12px 14px;">
        <div style="font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#444455;margin-bottom:8px;">Live snapshot</div>
        {quick_stat('Athletes', str(stats['athlete_count']), '#FC4C02')}
        {quick_stat('Total runs', str(stats['total_runs']), '#FC4C02')}
        {quick_stat('Fastest ever', f"{stats['fastest_total']:.2f}s", '#FC4C02')}
        {quick_stat('Top speed', f"{stats['top_speed_ever']:.1f} mph", '#FC4C02')}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # Switch user
    if st.button("↩  LOG OUT", use_container_width=True, key="nav_switch"):
        st.session_state.current_user = None
        st.session_state.user_role = ''
        st.session_state.public_view = False
        st.session_state.auth_error = ''
        st.session_state.auth_success = ''
        st.session_state.auth_portal = 'athlete'
        st.rerun()

page = st.session_state.page


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "MY DASHBOARD":
    df_me = load_athlete_runs(current_user)
    if df_me.empty:
        page_header("MY DASHBOARD", f"welcome back, {current_user.lower()}")
        empty_state("◇", "NO RUNS YET", "Head to Settings to log your first run.")
        render_footer()
        st.stop()

    best   = df_me.nsmallest(1, 'total').iloc[0]
    latest = df_me.iloc[0]
    all_df = load_all_runs()

    rankings = all_df.groupby('athlete')['total'].min().reset_index()
    rankings = rankings.sort_values('total').reset_index(drop=True)
    my_rank = int(rankings[rankings['athlete'] == current_user].index[0]) + 1
    total_athletes = len(rankings)

    page_header("MY DASHBOARD", f"welcome back, {current_user.lower()}")

    # ── Streak calc ──
    df_me_dates = sorted(df_me['date'].dt.date.unique(), reverse=True)
    streak = 0
    check  = datetime.date.today()
    for d in df_me_dates:
        if d >= check - datetime.timedelta(days=1):
            streak += 1
            check = d
        else:
            break
    streak_emoji = '▲' if streak >= 1 else '–'
    rank_color   = ACCENT if my_rank == 1 else '#F5F5F7'

    # ── 5-card hero strip (rank / PB / speed / runs / streak) ──
    hc1, hc2, hc3, hc4, hc5 = st.columns(5)
    stat_card(hc1, "Team rank", f"#{my_rank}", f"/{total_athletes}", accent=rank_color)
    stat_card(hc2, "Personal best", f"{best['total']:.2f}", "s", accent=ACCENT)
    stat_card(hc3, "Top speed", f"{df_me['top_speed'].max():.1f}", "mph", accent='#F5F5F7')
    stat_card(hc4, "Runs logged", f"{len(df_me)}", "", accent='#F5F5F7')
    stat_card(hc5, "Streak", f"{streak}", streak_emoji, accent=ACCENT if streak >= 1 else '#F5F5F7')
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ── TODAY'S SESSION ──
    last_session_date = df_me['date'].dt.date.iloc[0]
    last_session_runs = df_me[df_me['date'].dt.date == last_session_date]
    is_today = last_session_date == datetime.date.today()
    session_label = "TODAY'S SESSION" if is_today else f"LAST SESSION — {last_session_date.strftime('%b %d')}"
    session_color = SUCCESS if is_today else '#6E6E76'
    pulse_anim = 'animation:dp-pulse 2s infinite;' if is_today else ''
    reps = last_session_runs[::-1].reset_index(drop=True)
    rep_html = ''
    pb_val_sess = df_me['total'].min()
    for i, row in reps.iterrows():
        is_pb_r = abs(row['total'] - pb_val_sess) < 0.001
        pb_tag = f'<span style="font-family:DM Sans;font-size:0.55rem;background:{ACCENT}22;color:{ACCENT};border:1px solid {ACCENT}44;border-radius:999px;padding:1px 6px;margin-left:6px;">PB</span>' if is_pb_r else ''
        rep_html += (
            '<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #1A1A1F;">'
            f'<span style="font-family:\'JetBrains Mono\';font-size:0.72rem;color:#4A4A52;width:30px;">#{i+1}</span>'
            f'<span style="font-family:\'JetBrains Mono\';font-size:0.85rem;color:#D0D0D6;width:60px;">{row["split_0_10"]:.3f}s</span>'
            f'<span style="font-family:\'JetBrains Mono\';font-size:0.85rem;color:#D0D0D6;width:60px;">{row["split_10_30"]:.3f}s</span>'
            f'<span style="font-family:\'JetBrains Mono\';font-size:0.85rem;color:#D0D0D6;width:60px;">{row["split_30_60"]:.3f}s</span>'
            f'<span style="font-family:\'JetBrains Mono\';font-size:1rem;color:#F5F5F7;flex:1;font-weight:500;">{row["total"]:.3f}s{pb_tag}</span>'
            f'<span style="font-family:\'JetBrains Mono\';font-size:0.72rem;color:#6E6E76;">{row["top_speed"]:.1f} mph</span>'
            '</div>'
        )
    split_header_cols = [('#', 30), ('0–10m', 60), ('10–30m', 60), ('30–60m', 60), ('Total', 80), ('Speed', 60)]
    split_header = ''.join([
        f'<span style="font-family:DM Sans;font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#6E6E76;width:{w}px;display:inline-block;">{t}</span>'
        for t, w in split_header_cols
    ])
    reps_label = f"{len(reps)} {'run' if len(reps)==1 else 'reps'}"
    st.markdown(
        '<div style="background:#131316;border:1px solid #1E1E22;border-radius:10px;'
        'padding:20px 20px 8px;margin-bottom:16px;">'
        '<div style="font-family:\'DM Sans\';font-size:0.95rem;font-weight:700;color:#F5F5F7;margin-bottom:14px;">'
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
        f'background:{session_color};'
        f'margin-right:8px;vertical-align:middle;{pulse_anim}"></span>'
        f'{session_label}'
        f'<span style="font-family:\'DM Sans\';font-size:0.68rem;color:#6E6E76;margin-left:8px;font-weight:normal;">{reps_label}</span>'
        '</div>'
        f'<div style="display:flex;gap:12px;padding:0 0 8px;border-bottom:1px solid #1E1E22;margin-bottom:4px;">{split_header}</div>'
        f'{rep_html}'
        '</div>',
        unsafe_allow_html=True
    )

    # ── TIME TO BEAT ──
    my_idx = int(rankings[rankings['athlete'] == current_user].index[0])
    if my_idx > 0:
        athlete_above = rankings.iloc[my_idx - 1]
        gap = float(best['total']) - float(athlete_above['total'])
        st.markdown(f"""
        <div style="background:#131316;border:1px solid #1E1E22;border-radius:10px;
                    padding:16px 20px;margin-bottom:16px;
                    display:flex;align-items:center;gap:20px;">
            <div style="font-size:1.6rem;color:{ACCENT};">◉</div>
            <div style="flex:1;">
                <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#6E6E76;margin-bottom:4px;">Time to beat</div>
                <div style="font-family:'DM Sans';font-size:0.82rem;color:#9A9AA2;">
                    You're <span style="color:{ACCENT};font-family:JetBrains Mono;">+{gap:.3f}s</span> behind
                    <span style="color:#F5F5F7;">{athlete_above['athlete']}</span>
                    (#{my_idx})
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'JetBrains Mono';font-size:1.6rem;color:{ACCENT};">{float(athlete_above['total']):.2f}s</div>
                <div style="font-family:'DM Sans';font-size:0.62rem;color:#6E6E76;">their best</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#131316;border:1px solid #1E1E22;border-radius:10px;
                    padding:16px 20px;margin-bottom:16px;
                    display:flex;align-items:center;gap:20px;">
            <div style="font-size:1.6rem;color:{SUCCESS};">♛</div>
            <div>
                <div style="font-family:'DM Sans';font-size:1rem;font-weight:700;color:{SUCCESS};">You're leading the pack</div>
                <div style="font-family:'DM Sans';font-size:0.8rem;color:#6E6E76;">
                    {current_user} holds the fastest time on the team
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Season insight (compute before columns) ──
    insight_text = None
    if len(df_me) >= 10:
        first_half  = df_me.tail(len(df_me)//2)['total'].mean()
        second_half = df_me.head(len(df_me)//2)['total'].mean()
        improvement = first_half - second_half
        mx_std  = max(df_me['split_0_10'].std(), df_me['split_10_30'].std(), df_me['split_30_60'].std())
        if mx_std == df_me['split_10_30'].std():
            weakest = 'drive phase (10–30m)'
        elif mx_std == df_me['split_30_60'].std():
            weakest = 'max velocity (30–60m)'
        else:
            weakest = 'acceleration (0–10m)'
        if improvement > 0:
            insight_text = f"You're {improvement:.3f}s faster in the second half of your season. Most variable split: {weakest} — focus training here for the biggest gains."
        else:
            insight_text = f"Times up slightly (+{abs(improvement):.3f}s) this season. Focus on recovery and consistency in {weakest}."

    if insight_text:
        st.markdown(f"""
        <div style="background:#131316;border:1px solid #1E1E22;
                    border-left:3px solid {SUCCESS};border-radius:0 10px 10px 0;
                    padding:12px 16px;margin-bottom:12px;">
            <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.1em;
                        text-transform:uppercase;color:{SUCCESS};margin-bottom:4px;">
                ✦ Season insight</div>
            <div style="font-family:'DM Sans';font-size:0.8rem;color:#9A9AA2;
                        line-height:1.55;">{insight_text}</div>
        </div>
        """, unsafe_allow_html=True)

    section_header("LATEST VS PB")
    chips_html = ''
    for lbl, lat_val, pb_val in [
        ('0–10m',  float(latest['split_0_10']),  float(best['split_0_10'])),
        ('10–30m', float(latest['split_10_30']), float(best['split_10_30'])),
        ('30–60m', float(latest['split_30_60']), float(best['split_30_60'])),
        ('Total',  float(latest['total']),        float(best['total'])),
    ]:
        diff = lat_val - pb_val
        sign = '+' if diff > 0 else ''
        dcol = SUCCESS if diff <= 0.001 else DANGER
        chips_html += f"""
        <div style="background:#131316;border:1px solid #1E1E22;
                    border-radius:10px;padding:12px 14px;flex:1;min-width:0;">
            <div style="font-family:'DM Sans';font-size:0.58rem;letter-spacing:0.1em;
                        text-transform:uppercase;color:#6E6E76;
                        margin-bottom:6px;white-space:nowrap;">{lbl}</div>
            <div style="font-family:'JetBrains Mono';font-size:1.3rem;
                        color:#F5F5F7;line-height:1;">{lat_val:.3f}s</div>
            <div style="font-family:'JetBrains Mono';font-size:0.7rem;
                        color:{dcol};margin-top:4px;">{sign}{diff:.3f}s</div>
        </div>"""
    st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:4px;">{chips_html}</div>',
                unsafe_allow_html=True)

    # ── Last 10 runs ──
    section_header("MY LAST 10 RUNS")
    df_recent = df_me[::-1].tail(10).reset_index(drop=True)
    df_recent['run_num'] = range(1, len(df_recent)+1)
    pb_val = df_me['total'].min()
    bar_colors = [ACCENT if abs(v - pb_val) < 0.001 else '#3A3A42' for v in df_recent['total']]
    fig = go.Figure(go.Bar(
        x=df_recent['run_num'], y=df_recent['total'],
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{v:.2f}s" for v in df_recent['total']],
        textposition='outside',
        textfont=dict(family='JetBrains Mono', size=10, color='#9A9AA2'),
        cliponaxis=False,
    ))
    fig.add_hline(y=pb_val, line=dict(color=ACCENT, width=1.5, dash='dot'),
                  annotation_text="PB", annotation_font=dict(color=ACCENT, size=10))
    style_chart(fig, height=260)
    fig.update_layout(
        yaxis=dict(range=[df_me['total'].min()*0.995, df_me['total'].max()*1.015], visible=False),
        xaxis=dict(title='', tickvals=df_recent['run_num'],
                   ticktext=[f"#{i}" for i in df_recent['run_num']]),
        margin=dict(l=8, r=8, t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "LEADERBOARD":
    lb = load_leaderboard()
    page_header("LEADERBOARD", f"{len(get_all_athletes())} athletes ranked · season 2026")

    st.markdown(f"""
    <div style="background:#131316;border:1px solid #1E1E22;border-left:3px solid {ACCENT};
                border-radius:0 8px 8px 0;padding:10px 16px;margin-bottom:16px;
                display:flex;align-items:center;gap:10px;">
        <span style="font-size:1rem;color:{ACCENT};">◎</span>
        <span style="font-family:'DM Sans';font-size:0.78rem;color:#9A9AA2;">
            This is your squad's board. Check <strong style="color:{ACCENT};">GLOBAL</strong> in the sidebar
            for the same rankings shared publicly — anyone can view it without logging in.
        </span>
    </div>
    """, unsafe_allow_html=True)

    if lb.empty:
        empty_state("◇", "NO RUNS LOGGED YET", "Get on the track and break some beams.")
        render_footer()
        st.stop()

    section_header("FULL RANKINGS")
    render_rankings_table(lb, current_user)

    section_header("BEST TOTAL TIME")
    lb_s = lb.sort_values('best_total')
    fig = go.Figure(go.Bar(
        x=lb_s['athlete'], y=lb_s['best_total'],
        marker=dict(color=lb_s['best_total'], colorscale=SCALE, showscale=False,
                    line=dict(color='#0A0A0D', width=1)),
        text=[f"{v:.2f}s" for v in lb_s['best_total']],
        textposition='outside', textfont=dict(family='JetBrains Mono', size=11, color='#F5F5F7'),
        cliponaxis=False,
    ))
    style_chart(fig, height=320)
    fig.update_layout(
        bargap=0.35,
        yaxis=dict(visible=False, range=[lb_s['best_total'].min()*0.97, lb_s['best_total'].max()*1.04]),
        xaxis=dict(tickfont=dict(family='DM Sans', size=12, color='#9A9AA2')),
        margin=dict(l=16, r=16, t=48, b=60),
    )
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT BREAKDOWN")
    fig2 = go.Figure()
    for split, label, color in [
        ('best_30_60','30–60m', ACCENT),
        ('best_10_30','10–30m','#9A9AA2'),
        ('best_0_10', '0–10m', '#4A4A52'),
    ]:
        fig2.add_trace(go.Bar(y=lb['athlete'], x=lb[split], name=label,
            orientation='h', marker_color=color, marker_line=dict(width=0)))
    style_chart(fig2, height=340)
    fig2.update_layout(
        barmode='stack', xaxis_title='Time (s)',
        yaxis=dict(autorange='reversed', tickfont=dict(family='DM Sans', size=12, color='#9A9AA2')),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=16, r=16, t=48, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    section_header("TOP SPEED BY ATHLETE")
    speed_df = load_all_runs().groupby('athlete')['top_speed'].max().reset_index()
    speed_df = speed_df.sort_values('top_speed', ascending=False).reset_index(drop=True)
    spd_colors = [ACCENT if r['athlete'] == current_user else '#3A3A42'
                  for _, r in speed_df.iterrows()]
    fig_spd = go.Figure(go.Bar(
        x=speed_df['athlete'],
        y=speed_df['top_speed'],
        marker=dict(color=spd_colors, line=dict(width=0)),
        text=[f"{v:.1f}" for v in speed_df['top_speed']],
        textposition='outside',
        textfont=dict(family='JetBrains Mono', size=11, color='#9A9AA2'),
        cliponaxis=False
    ))
    style_chart(fig_spd, height=280)
    fig_spd.update_layout(
        yaxis=dict(
            range=[speed_df['top_speed'].min()*0.97, speed_df['top_speed'].max()*1.04],
            visible=False
        ),
        xaxis=dict(tickfont=dict(family='DM Sans', size=12, color='#9A9AA2')),
        bargap=0.35,
    )
    st.plotly_chart(fig_spd, use_container_width=True, config=CHART_CFG)

    # ── HEAD TO HEAD (folded in from the old standalone Compare tab) ──
    section_header("HEAD TO HEAD")
    all_ath = get_all_athletes()
    if len(all_ath) < 2:
        info_card("Add at least one more athlete to unlock head-to-head comparison.")
    else:
        c1, c2 = st.columns(2)
        default_a = all_ath.index(current_user) if current_user in all_ath else 0
        default_b = (default_a + 1) % len(all_ath)
        athlete_a = c1.selectbox("Athlete A", all_ath, index=default_a, key="compare_a")
        athlete_b = c2.selectbox("Athlete B", all_ath, index=default_b, key="compare_b")
        da, db_ = load_athlete_runs(athlete_a), load_athlete_runs(athlete_b)

        metrics = [
            ('Best Total',  'total',       '{:.3f}s', True),
            ('0–10m PB',    'split_0_10',  '{:.3f}s', True),
            ('10–30m PB',   'split_10_30', '{:.3f}s', True),
            ('30–60m PB',   'split_30_60', '{:.3f}s', True),
            ('Top Speed',   'top_speed',   '{:.1f} mph', False),
        ]
        countable = [(col, lib) for _, col, _, lib in metrics if col is not None]
        wins_a = sum(1 for col, lib in countable
                     if (lib and da[col].min() < db_[col].min()) or
                        (not lib and da[col].max() > db_[col].max()))
        wins_b = sum(1 for col, lib in countable
                     if (lib and db_[col].min() < da[col].min()) or
                        (not lib and db_[col].max() > da[col].max()))
        overall_winner = athlete_a if wins_a > wins_b else athlete_b if wins_b > wins_a else None
        wc = ACCENT if overall_winner else '#6E6E76'

        st.markdown(f"""
        <div style="background:#131316;border:1px solid #1E1E22;
                    border-radius:10px;padding:18px 24px;margin:12px 0 20px;text-align:center;">
            <div style="font-family:'DM Sans';font-size:0.65rem;letter-spacing:0.1em;
                        text-transform:uppercase;color:#6E6E76;margin-bottom:8px;">Overall winner</div>
            <div style="font-family:'DM Sans';font-size:1.6rem;font-weight:700;color:{wc};">
                {'TIE' if not overall_winner else overall_winner.upper()}</div>
            <div style="font-family:'JetBrains Mono';font-size:0.8rem;color:#6E6E76;margin-top:4px;">
                {wins_a} vs {wins_b} categories</div>
        </div>""", unsafe_allow_html=True)

        h_l, h_mid, h_r = st.columns([2, 1, 2])
        h_l.markdown(f"""
        <div style="text-align:center;padding:12px;background:#131316;
                    border:1px solid #1E1E22;border-radius:8px;margin-bottom:8px;">
            <div style="font-family:'DM Sans';font-size:1.05rem;font-weight:700;color:{ACCENT};">
                {athlete_a.upper()}</div>
        </div>""", unsafe_allow_html=True)
        h_r.markdown(f"""
        <div style="text-align:center;padding:12px;background:#131316;
                    border:1px solid #1E1E22;border-radius:8px;margin-bottom:8px;">
            <div style="font-family:'DM Sans';font-size:1.05rem;font-weight:700;color:#D0D0D6;">
                {athlete_b.upper()}</div>
        </div>""", unsafe_allow_html=True)

        all_metrics = metrics + [('Runs Logged', None, '{}', False)]
        for label, col, fmt, lib in all_metrics:
            if col is None:
                va, vb = len(da), len(db_)
                wa, wb = va > vb, vb > va
            elif lib:
                va, vb = da[col].min(), db_[col].min()
                wa, wb = va < vb - 0.001, vb < va - 0.001
            else:
                va, vb = da[col].max(), db_[col].max()
                wa, wb = va > vb + 0.001, vb > va + 0.001

            ca     = '#F5F5F7' if wa else '#4A4A52'
            cb     = '#F5F5F7' if wb else '#4A4A52'
            a_tick = f'<span style="font-size:0.7rem;margin-left:6px;color:{SUCCESS};">✓</span>' if wa else ''
            b_tick = f'<span style="font-size:0.7rem;margin-left:6px;color:{SUCCESS};">✓</span>' if wb else ''

            l, mid, r = st.columns([2, 1, 2])
            l.markdown(f"""
            <div style="background:#131316;border:1px solid #1E1E22;border-radius:8px;
                        padding:12px 16px;text-align:right;margin-bottom:6px;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:1.15rem;color:{ca};">
                    {fmt.format(va)}{a_tick}</span>
            </div>""", unsafe_allow_html=True)
            mid.markdown(f"""
            <div style="padding:12px 0;text-align:center;margin-bottom:6px;">
                <div style="font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#4A4A52;margin-top:8px;">{label}</div>
            </div>""", unsafe_allow_html=True)
            r.markdown(f"""
            <div style="background:#131316;border:1px solid #1E1E22;border-radius:8px;
                        padding:12px 16px;text-align:left;margin-bottom:6px;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:1.15rem;color:{cb};">
                    {b_tick}{fmt.format(vb)}</span>
            </div>""", unsafe_allow_html=True)

        fig_h2h = go.Figure()
        for df_x, name, color in [(da,athlete_a,ACCENT),(db_,athlete_b,'#9A9AA2')]:
            df_s = df_x[::-1].reset_index(drop=True)
            df_s['run_num'] = range(1, len(df_s)+1)
            fig_h2h.add_trace(go.Scatter(x=df_s['run_num'], y=df_s['total'],
                mode='lines+markers', name=name,
                line=dict(color=color, width=2), marker=dict(size=5)))
        style_chart(fig_h2h, height=300)
        combined = pd.concat([da['total'], db_['total']])
        fig_h2h.update_layout(yaxis=dict(range=smart_yrange(combined)))
        st.plotly_chart(fig_h2h, use_container_width=True, config=CHART_CFG)

        compare_deltas = [
            ('0–10m',     float(da['split_0_10'].mean()),  float(db_['split_0_10'].mean()),  False),
            ('10–30m',    float(da['split_10_30'].mean()), float(db_['split_10_30'].mean()), False),
            ('30–60m',    float(da['split_30_60'].mean()), float(db_['split_30_60'].mean()), False),
            ('Total avg', float(da['total'].mean()),        float(db_['total'].mean()),       False),
            ('Top speed', float(da['top_speed'].max()),     float(db_['top_speed'].max()),    True),
        ]
        delta_rows = ''
        for label, val_a, val_b, is_speed in compare_deltas:
            a_wins = (val_a > val_b) if is_speed else (val_a < val_b)
            delta  = val_a - val_b
            sign   = '+' if delta > 0 else ''
            dcol   = SUCCESS if (delta < 0 and not is_speed) or (delta > 0 and is_speed) else DANGER
            unit_s = ' mph' if is_speed else 's'
            delta_rows += (
                '<tr style="border-bottom:1px solid #1A1A1F;">'
                f'<td style="padding:10px 14px;font-family:DM Sans;color:#9A9AA2;font-size:0.8rem;">{label}</td>'
                f'<td style="padding:10px 14px;font-family:JetBrains Mono;color:{ACCENT if a_wins else "#6E6E76"};font-size:0.85rem;text-align:right;">{val_a:.3f}{unit_s}</td>'
                f'<td style="padding:10px 14px;font-family:JetBrains Mono;color:{dcol};font-size:0.82rem;text-align:center;">{sign}{delta:.3f}{"s" if not is_speed else ""}</td>'
                f'<td style="padding:10px 14px;font-family:JetBrains Mono;color:{"#D0D0D6" if not a_wins else "#6E6E76"};font-size:0.85rem;text-align:left;">{val_b:.3f}{unit_s}</td>'
                '</tr>'
            )
        th_d = "padding:10px 14px;font-family:DM Sans;font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#6E6E76;font-weight:500;"
        st.markdown(
            '<div style="border:1px solid #1E1E22;border-radius:10px;overflow:hidden;margin-bottom:16px;">'
            '<table style="width:100%;border-collapse:collapse;background:#131316;">'
            '<thead>'
            f'<tr style="background:#0D0D10;border-bottom:2px solid #1E1E22;">'
            f'<th style="{th_d};text-align:left;">Split</th>'
            f'<th style="{th_d};text-align:right;color:{ACCENT};">{athlete_a}</th>'
            f'<th style="{th_d};text-align:center;">Δ</th>'
            f'<th style="{th_d};text-align:left;color:#D0D0D6;">{athlete_b}</th>'
            '</tr>'
            '</thead>'
            f'<tbody>{delta_rows}</tbody>'
            '</table>'
            '</div>',
            unsafe_allow_html=True
        )

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "GLOBAL":
    lb_g = load_leaderboard()
    page_header("GLOBAL", "the same board, shared publicly — no login required to view")

    if lb_g.empty:
        empty_state("◇", "NO DATA YET", "Check back once athletes have logged runs.")
        render_footer()
        st.stop()

    gs = get_global_stats()
    gg1, gg2, gg3, gg4 = st.columns(4)
    stat_card(gg1, "Athletes", str(gs['athlete_count']), accent='#F5F5F7')
    stat_card(gg2, "Total Runs", str(gs['total_runs']), accent='#F5F5F7')
    stat_card(gg3, "Fastest Time", f"{gs['fastest_total']:.2f}", "s", accent=ACCENT)
    stat_card(gg4, "Top Speed", f"{gs['top_speed_ever']:.1f}", "mph", accent=ACCENT)
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    section_header("FULL RANKINGS")
    render_rankings_table(lb_g, current_user)

    section_header("BEST TOTAL TIME")
    lb_gs = lb_g.sort_values('best_total')
    fig_g = go.Figure(go.Bar(
        x=lb_gs['athlete'], y=lb_gs['best_total'],
        marker=dict(color=lb_gs['best_total'], colorscale=SCALE, showscale=False,
                    line=dict(color='#0A0A0D', width=1)),
        text=[f"{v:.2f}s" for v in lb_gs['best_total']],
        textposition='outside', textfont=dict(family='JetBrains Mono', size=11, color='#F5F5F7'),
        cliponaxis=False,
    ))
    style_chart(fig_g, height=300)
    fig_g.update_layout(
        bargap=0.35,
        yaxis=dict(visible=False, range=[lb_gs['best_total'].min()*0.97, lb_gs['best_total'].max()*1.04]),
        xaxis=dict(tickfont=dict(family='DM Sans', size=12, color='#9A9AA2')),
    )
    st.plotly_chart(fig_g, use_container_width=True, config=CHART_CFG)

    info_card("This view is identical to what's shown at the app's public URL — share it with anyone, no account needed.")

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY PROFILE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "MY PROFILE":
    profile      = load_athlete_profile(current_user)
    athlete_data = load_athlete_runs(current_user)

    if athlete_data.empty:
        page_header("MY PROFILE", f"{current_user.lower()}'s athlete card")
        empty_state("◇", "NO RUNS YET")
        render_footer()
        st.stop()

    best     = athlete_data.nsmallest(1, 'total').iloc[0]
    all_df   = load_all_runs()
    rankings = all_df.groupby('athlete')['total'].min().sort_values().reset_index()
    my_rank  = int(rankings[rankings['athlete'] == current_user].index[0]) + 1
    accent   = ACCENT

    page_header("MY PROFILE", f"{current_user.lower()}'s athlete card")

    # ── Build profile tags as plain variables (no nested f-string quotes) ──
    acc_bg  = f'{ACCENT}18'
    acc_bdr = f'{ACCENT}44'

    tag_parts = []
    if profile.get('school'):
        v = profile['school']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:{acc_bg};border:1px solid {acc_bdr};color:{accent};border-radius:999px;padding:3px 10px;letter-spacing:0.08em;">{v}</span>')
    if profile.get('events'):
        v = profile['events']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:#1E1E22;border:1px solid #26262C;color:#D0D0D6;border-radius:999px;padding:3px 10px;">{v}</span>')
    if profile.get('grad_year'):
        v = profile['grad_year']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:#1E1E22;color:#6E6E76;border-radius:999px;padding:3px 10px;">Class of {v}</span>')
    if profile.get('age') and int(profile.get('age') or 0) > 0:
        v = profile['age']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:#1E1E22;color:#6E6E76;border-radius:999px;padding:3px 10px;">Age {v}</span>')
    profile_tags = ' '.join(tag_parts)

    bio_val  = profile.get('bio', '') or ''
    bio_html = f'<div style="font-family:DM Sans;font-size:0.82rem;color:#9A9AA2;margin-top:12px;line-height:1.6;max-width:500px;">{bio_val}</div>' if bio_val else ''

    hero_html = f"""
    <div style="background:#131316;border:1px solid #1E1E22;border-radius:14px;overflow:hidden;
                margin-bottom:28px;">
        <div style="padding:28px 32px;">
            <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
                <div style="width:80px;height:80px;border-radius:50%;flex-shrink:0;
                            background:{accent};
                            display:flex;align-items:center;justify-content:center;
                            font-family:'DM Sans';font-weight:800;font-size:2.2rem;color:#FFFFFF;">
                    {current_user[0].upper()}
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-family:'DM Sans';font-weight:800;font-size:1.8rem;
                                color:#F5F5F7;line-height:1;margin-bottom:8px;">
                        {current_user}
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">{profile_tags}</div>{bio_html}
                </div>
                <div style="display:flex;flex-direction:column;gap:10px;flex-shrink:0;">
                    <div style="text-align:center;background:#0A0A0D;border-radius:10px;
                                padding:14px 20px;border:1px solid #1E1E22;">
                        <div style="font-family:'JetBrains Mono';font-size:1.8rem;color:{accent};line-height:1;">
                            #{my_rank}</div>
                        <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;
                                    text-transform:uppercase;color:#6E6E76;margin-top:4px;">Team rank</div>
                    </div>
                    <div style="text-align:center;background:#0A0A0D;border-radius:10px;
                                padding:14px 20px;border:1px solid #1E1E22;">
                        <div style="font-family:'JetBrains Mono';font-size:1.8rem;color:#F5F5F7;line-height:1;">
                            {best['total']:.2f}s</div>
                        <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;
                                    text-transform:uppercase;color:#6E6E76;margin-top:4px;">Personal best</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)

    # ── Season summary stats row ──
    df_me_p = athlete_data
    total_runs_p = len(df_me_p)
    days_active_p = df_me_p['date'].dt.date.nunique()
    avg_total_p = df_me_p['total'].mean()
    best_total_p = df_me_p['total'].min()
    improvement_p = df_me_p.tail(5)['total'].mean() - df_me_p.head(5)['total'].mean() if len(df_me_p) >= 10 else 0.0
    consistency_p = max(0, 100 - (df_me_p['total'].std() / df_me_p['total'].mean() * 100)) if len(df_me_p) > 1 else 100.0
    impr_color = '#1DDB8B' if improvement_p < 0 else '#FF4D4D'
    summary_items = [
        ('Runs logged',   str(total_runs_p),          '',   '#FC4C02'),
        ('Days active',   str(days_active_p),          '',   '#9A9AA2'),
        ('Avg total',     f'{avg_total_p:.2f}',        's',  '#9A9AA2'),
        ('Personal best', f'{best_total_p:.2f}',       's',  '#FC4C02'),
        ('Season delta',  f'{improvement_p:+.3f}',     's',  impr_color),
        ('Consistency',   f'{consistency_p:.0f}',      '%',  '#FFD700'),
    ]
    border_style = 'border-right:1px solid #1E1E22;'
    items_html = ''.join([f"""
    <div style="flex:1;text-align:center;padding:14px 8px;{border_style if i < len(summary_items)-1 else ''}">
        <div style="font-family:'JetBrains Mono';font-size:1.4rem;color:{color};line-height:1;">
            {val}<span style="font-size:0.8rem;color:#6E6E76;">{unit}</span>
        </div>
        <div style="font-family:'DM Sans';font-size:0.58rem;letter-spacing:0.1em;
                    text-transform:uppercase;color:#6E6E76;margin-top:5px;">{label}</div>
    </div>""" for i, (label, val, unit, color) in enumerate(summary_items)])
    st.markdown(f"""
    <div style="background:#131316;border:1px solid #1E1E22;border-radius:12px;
                display:flex;margin-bottom:20px;overflow:hidden;">
        {items_html}
    </div>
    """, unsafe_allow_html=True)

    # ── Goal progress bars ──
    has_goals = any([
        float(profile.get('goal_total') or 0) > 0,
        float(profile.get('goal_0_10')  or 0) > 0,
        float(profile.get('goal_10_30') or 0) > 0,
        float(profile.get('goal_30_60') or 0) > 0,
    ])
    section_header("SEASON GOALS", accent='blue')
    if has_goals:
        goals = [
            ('Total time goal', float(profile.get('goal_total') or 0), float(best['total']),                        accent,    acc_rgb),
            ('0–10m goal',      float(profile.get('goal_0_10')  or 0), float(athlete_data['split_0_10'].min()),  '#FC4C02', '137,196,225'),
            ('10–30m goal',     float(profile.get('goal_10_30') or 0), float(athlete_data['split_10_30'].min()), '#9A9AA2', '179,157,219'),
            ('30–60m goal',     float(profile.get('goal_30_60') or 0), float(athlete_data['split_30_60'].min()), '#FC4C02', '255,61,138'),
        ]
        for label, goal, current_val, color, crgb in goals:
            if not goal:
                continue
            progress     = min(100, max(0, ((goal - current_val) / (goal * 0.1)) * 100 + 50))
            hit          = current_val <= goal
            status_color = '#1DDB8B' if hit else color
            status_text  = '✓ ACHIEVED' if hit else f'{current_val:.3f}s → {goal:.3f}s target'
            bar_shadow   = f'rgba({crgb},0.38)'
            st.markdown(f"""
            <div style="background:#131316;border:1px solid #1E1E22;border-radius:12px;
                        padding:16px 20px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="font-family:'DM Sans';font-size:0.75rem;letter-spacing:0.08em;
                                 text-transform:uppercase;color:#9A9AA2;">{label}</span>
                    <span style="font-family:'JetBrains Mono';font-size:0.78rem;color:{status_color};">{status_text}</span>
                </div>
                <div style="background:#0A0A0D;border-radius:999px;height:6px;overflow:hidden;">
                    <div style="height:100%;width:{min(100,progress):.0f}%;
                                background:{color};border-radius:999px;
                                box-shadow:0 0 8px {bar_shadow};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#131316;border:1px solid #1E1E22;border-left:3px solid #3A3A42;
                    border-radius:0 10px 10px 0;padding:14px 16px;margin-bottom:16px;">
            <div style="font-family:'DM Sans';font-size:0.8rem;color:#3A3A42;">
                No season goals set — add targets in Edit Profile to track progress here.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Personal records board — 2x2 grid + top speed full-width ──
    section_header("PERSONAL RECORDS", accent='pink')
    pr_splits = [
        ('①', '0–10m',  athlete_data['split_0_10'].min(),  '1st 10 meters — reaction + first step',  '#FC4C02'),
        ('②', '10–30m', athlete_data['split_10_30'].min(), 'Drive phase — peak acceleration window', '#9A9AA2'),
        ('③', '30–60m', athlete_data['split_30_60'].min(), 'Max velocity — highest speed window',    '#FC4C02'),
        ('④', 'Total',  athlete_data['total'].min(),        '60m combined — full sprint',             '#F5F5F7'),
    ]
    pc1, pc2 = st.columns(2)
    for i, (icon, label, val, desc, lcolor) in enumerate(pr_splits):
        col = pc1 if i % 2 == 0 else pc2
        col.markdown(f"""
        <div style="background:#131316;border:1px solid #1E1E22;border-left:3px solid {lcolor};
                    border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:8px;
                    display:flex;align-items:center;gap:14px;transition:transform 0.2s ease;"
             onmouseover="this.style.transform='translateX(4px)'"
             onmouseout="this.style.transform='translateX(0)'">
            <span style="font-size:1.4rem;">{icon}</span>
            <div style="flex:1;">
                <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#6E6E76;">{label}</div>
                <div style="font-family:'DM Sans';font-size:0.7rem;color:#3A3A42;margin-top:1px;">{desc}</div>
            </div>
            <div style="font-family:'JetBrains Mono';font-size:1.5rem;color:#F5F5F7;flex-shrink:0;">{val:.3f}s</div>
        </div>
        """, unsafe_allow_html=True)
    top_spd = athlete_data['top_speed'].max()
    st.markdown(f"""
    <div style="background:#131316;border:1px solid #1E1E22;border-left:3px solid #FFD700;
                border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:8px;
                display:flex;align-items:center;gap:14px;">
        <span style="font-size:1.4rem;color:#FFD700;">▲</span>
        <div style="flex:1;">
            <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.1em;
                        text-transform:uppercase;color:#6E6E76;">Top speed</div>
            <div style="font-family:'DM Sans';font-size:0.7rem;color:#3A3A42;margin-top:1px;">
                Peak speed recorded across all runs</div>
        </div>
        <div style="font-family:'JetBrains Mono';font-size:1.5rem;color:#FFD700;flex-shrink:0;">
            {top_spd:.2f} mph</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Best run breakdown ──
    section_header("PERSONAL BEST RUN BREAKDOWN", accent='blue')
    best_run = athlete_data.nsmallest(1, 'total').iloc[0]
    total_time_br = float(best_run['total'])
    pct_0_10_br  = float(best_run['split_0_10'])  / total_time_br * 100
    pct_10_30_br = float(best_run['split_10_30']) / total_time_br * 100
    pct_30_60_br = float(best_run['split_30_60']) / total_time_br * 100
    br_date = best_run['date']
    br_date_str = br_date.strftime('%b %d, %Y') if hasattr(br_date, 'strftime') else str(br_date)[:10]
    st.markdown(f"""
    <div style="background:#131316;border:1px solid #1E1E22;border-radius:14px;
                padding:20px 24px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:16px;">
            <div style="font-family:'JetBrains Mono';font-size:2.4rem;color:#F5F5F7;">{total_time_br:.3f}s</div>
            <div style="font-family:'DM Sans';font-size:0.7rem;color:#6E6E76;">{br_date_str}</div>
        </div>
        <div style="display:flex;border-radius:6px;overflow:hidden;height:10px;margin-bottom:16px;gap:2px;">
            <div style="width:{pct_0_10_br:.1f}%;background:#FC4C02;border-radius:4px;"></div>
            <div style="width:{pct_10_30_br:.1f}%;background:#9A9AA2;border-radius:4px;"></div>
            <div style="width:{pct_30_60_br:.1f}%;background:#FC4C02;border-radius:4px;"></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
            <div style="text-align:center;">
                <div style="font-family:'JetBrains Mono';font-size:1.3rem;color:#FC4C02;">{float(best_run['split_0_10']):.3f}s</div>
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#6E6E76;margin-top:3px;">0–10m · {pct_0_10_br:.0f}%</div>
            </div>
            <div style="text-align:center;border-left:1px solid #1E1E22;border-right:1px solid #1E1E22;">
                <div style="font-family:'JetBrains Mono';font-size:1.3rem;color:#9A9AA2;">{float(best_run['split_10_30']):.3f}s</div>
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#6E6E76;margin-top:3px;">10–30m · {pct_10_30_br:.0f}%</div>
            </div>
            <div style="text-align:center;">
                <div style="font-family:'JetBrains Mono';font-size:1.3rem;color:#FC4C02;">{float(best_run['split_30_60']):.3f}s</div>
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#6E6E76;margin-top:3px;">30–60m · {pct_30_60_br:.0f}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Athlete info grid ──
    info_items = [
        ('Height',   profile.get('height','')),
        ('Weight',   profile.get('weight','')),
        ('Coach',    profile.get('coach','')),
        ('Hometown', profile.get('hometown','')),
        ('School',   profile.get('school','')),
        ('Events',   profile.get('events','')),
    ]
    visible_info = [(l, v) for l, v in info_items if v]
    if visible_info:
        section_header("ATHLETE INFO", accent='blue')
        ic = st.columns(3)
        for i, (label, val) in enumerate(visible_info):
            ic[i % 3].markdown(f"""
            <div style="background:#131316;border:1px solid #1E1E22;border-radius:10px;
                        padding:14px 16px;margin-bottom:8px;
                        animation:scaleIn 0.3s ease {0.04*i:.2f}s both;">
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                            text-transform:uppercase;color:#3A3A42;margin-bottom:6px;">{label}</div>
                <div style="font-family:'DM Sans';font-size:0.9rem;color:#F5F5F7;">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Edit profile form ──
    section_header("EDIT MY PROFILE", accent='pink')
    with st.expander("Update profile information", expanded=False):
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'DM Sans\';font-weight:700;font-size:0.85rem;letter-spacing:0.06em;color:#9A9AA2;margin-bottom:12px;">IDENTITY</div>', unsafe_allow_html=True)
        ci1, ci2, ci3 = st.columns(3)
        school   = ci1.text_input("School / Team",  value=str(profile.get('school','') or ''))
        hometown = ci2.text_input("Hometown",        value=str(profile.get('hometown','') or ''))
        coach    = ci3.text_input("Coach",           value=str(profile.get('coach','') or ''))
        ci4, ci5, ci6, ci7 = st.columns(4)
        age       = ci4.number_input("Age",      10, 40, int(profile.get('age') or 18))
        height    = ci5.text_input("Height",         value=str(profile.get('height','') or ''))
        weight    = ci6.text_input("Weight",         value=str(profile.get('weight','') or ''))
        grad_year = ci7.text_input("Grad year",      value=str(profile.get('grad_year','') or ''))
        ci8, ci9 = st.columns(2)
        events   = ci8.text_input("Events (e.g. 100m, 200m, 4x1)", value=str(profile.get('events','') or ''))
        position = ci9.text_input("Position / role",               value=str(profile.get('position','') or ''))
        bio      = st.text_area("Bio", value=str(profile.get('bio','') or ''),
                                placeholder="Training philosophy, goals, personal notes...", height=100)

        st.markdown('<div style="font-family:\'DM Sans\';font-weight:700;font-size:0.85rem;letter-spacing:0.06em;color:#9A9AA2;margin:16px 0 12px;">SEASON GOALS</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'DM Sans\';font-size:0.75rem;color:#6E6E76;margin-bottom:12px;">Set target times — progress bars track how close you are</div>', unsafe_allow_html=True)
        cg1, cg2, cg3, cg4 = st.columns(4)
        goal_total = cg1.number_input("Total goal (s)", 0.0, 15.0, float(profile.get('goal_total') or 0.0), step=0.01, format="%.3f")
        goal_0_10  = cg2.number_input("0–10m goal (s)",  0.0, 5.0,  float(profile.get('goal_0_10')  or 0.0), step=0.001, format="%.3f")
        goal_10_30 = cg3.number_input("10–30m goal (s)", 0.0, 5.0,  float(profile.get('goal_10_30') or 0.0), step=0.001, format="%.3f")
        goal_30_60 = cg4.number_input("30–60m goal (s)", 0.0, 5.0,  float(profile.get('goal_30_60') or 0.0), step=0.001, format="%.3f")

        if st.button("SAVE MY PROFILE", use_container_width=True):
            save_athlete_profile(current_user, school, events, age, height, weight, bio,
                                  hometown=hometown, coach=coach, grad_year=grad_year,
                                  position=position, goal_total=goal_total,
                                  goal_0_10=goal_0_10, goal_10_30=goal_10_30,
                                  goal_30_60=goal_30_60)
            st.success("Profile saved.")
            st.rerun()

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY PROGRESS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "MY PROGRESS":
    page_header("MY PROGRESS", f"{current_user.lower()}'s season arc")
    df_p = load_athlete_runs(current_user)
    if df_p.empty:
        empty_state("◇", "NO RUNS YET")
        render_footer()
        st.stop()

    df_p = df_p[::-1].reset_index(drop=True)
    df_p['run_num'] = range(1, len(df_p)+1)

    if len(df_p) >= 5:
        first5 = df_p.head(5)['total'].mean()
        last5  = df_p.tail(5)['total'].mean()
        delta  = first5 - last5
        pct    = (delta / first5) * 100
        st.markdown(f"""
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 20px;">
            <div style="background:#131316;border:1px solid #1DDB8B44;border-left:3px solid #1DDB8B;
                        border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;color:#1DDB8B;">
                    -{delta:.3f}s</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#6E6E76;margin-top:4px;">
                    Time improved (first 5 vs last 5)</div>
            </div>
            <div style="background:#131316;border:1px solid #FC4C0244;border-left:3px solid #FC4C02;
                        border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;color:#FC4C02;">
                    {pct:.1f}%</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#6E6E76;margin-top:4px;">Percentage faster</div>
            </div>
            <div style="background:#131316;border:1px solid #FC4C0244;border-left:3px solid #FC4C02;
                        border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;color:#FC4C02;">
                    {df_p['top_speed'].max():.1f} mph</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#6E6E76;margin-top:4px;">Peak top speed</div>
            </div>
        </div>""", unsafe_allow_html=True)

    section_header("PHASE ANALYSIS", accent='pink')
    all_runs_pa = load_all_runs()
    my_avgs_pa = {
        '0–10m':  df_p['split_0_10'].mean(),
        '10–30m': df_p['split_10_30'].mean(),
        '30–60m': df_p['split_30_60'].mean(),
    }
    field_avgs_pa = {
        '0–10m':  all_runs_pa['split_0_10'].mean(),
        '10–30m': all_runs_pa['split_10_30'].mean(),
        '30–60m': all_runs_pa['split_30_60'].mean(),
    }
    phase_html = ''
    for phase_label, my_val, f_val, p_color in [
        ('0–10m  · Reaction + first step', my_avgs_pa['0–10m'],  field_avgs_pa['0–10m'],  '#FC4C02'),
        ('10–30m · Drive phase',           my_avgs_pa['10–30m'], field_avgs_pa['10–30m'], '#9A9AA2'),
        ('30–60m · Max velocity',          my_avgs_pa['30–60m'], field_avgs_pa['30–60m'], '#FC4C02'),
    ]:
        diff      = my_val - f_val
        diff_pct  = abs(diff / f_val * 100) if f_val else 0
        is_ahead  = diff < -0.005
        is_behind = diff > 0.005
        bar_color = '#1DDB8B' if is_ahead else '#FF4D4D' if is_behind else '#6E6E76'
        status    = f'▲ {diff_pct:.1f}% ahead of field' if is_ahead else f'▼ {diff_pct:.1f}% behind field' if is_behind else 'At field average'
        bar_fill  = min(100, diff_pct * 10)
        phase_html += f"""
        <div style="background:#131316;border:1px solid #1E1E22;border-radius:10px;
                    padding:14px 18px;margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-family:'DM Sans';font-size:0.75rem;color:#9A9AA2;">{phase_label}</span>
                <span style="font-family:'JetBrains Mono';font-size:0.75rem;color:{bar_color};">{status}</span>
            </div>
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-family:'JetBrains Mono';font-size:0.85rem;color:#F5F5F7;width:52px;">{my_val:.3f}s</span>
                <div style="flex:1;background:#0A0A0D;border-radius:999px;height:5px;">
                    <div style="height:100%;width:{bar_fill:.0f}%;background:{bar_color};border-radius:999px;max-width:100%;"></div>
                </div>
                <span style="font-family:'JetBrains Mono';font-size:0.72rem;color:#6E6E76;width:52px;text-align:right;">avg {f_val:.3f}s</span>
            </div>
        </div>"""
    st.markdown(phase_html, unsafe_allow_html=True)

    section_header("PERSONAL BEST TIMELINE", accent='pink')
    df_p['running_pb'] = df_p['total'].expanding().min()
    pb_runs = df_p[df_p['total'] == df_p['running_pb']]
    fig_pb = go.Figure()
    fig_pb.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['total'],
        mode='lines+markers', name='Run time',
        line=dict(color='#1E1E22', width=1), marker=dict(size=4, color='#3A3A42')))
    fig_pb.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['running_pb'],
        mode='lines', name='Personal best',
        line=dict(color='#FC4C02', width=2.5, shape='hv'),
        fill='tozeroy', fillcolor='rgba(255,61,138,0.03)'))
    fig_pb.add_trace(go.Scatter(x=pb_runs['run_num'], y=pb_runs['total'],
        mode='markers+text', name='New PB',
        marker=dict(size=12, color='#FFD700', symbol='star', line=dict(color='#0A0A0D', width=1)),
        text=[f"{v:.2f}s" for v in pb_runs['total']],
        textposition='top center',
        textfont=dict(family='JetBrains Mono', size=10, color='#FFD700')))
    style_chart(fig_pb, height=300)
    fig_pb.update_layout(yaxis=dict(range=smart_yrange(df_p['total'])))
    st.plotly_chart(fig_pb, use_container_width=True, config=CHART_CFG)

    section_header("ROLLING AVERAGE (5-RUN WINDOW)", accent='blue')
    df_p['rolling_avg'] = df_p['total'].rolling(5, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['total'], mode='markers',
        name='Individual runs', marker=dict(color='#1E1E22', size=6, line=dict(color='#FC4C02', width=1.5))))
    fig.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['rolling_avg'], mode='lines',
        name='5-run avg', line=dict(color='#FC4C02', width=2.5)))
    fig.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['running_pb'],
        mode='lines', name='Personal best', line=dict(color='#FC4C02', width=1.5, dash='dot')))
    style_chart(fig, height=320)
    fig.update_layout(yaxis=dict(range=smart_yrange(df_p['total'])))
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT TRENDS", accent='pink')
    fig2 = go.Figure()
    for col, label, color in [
        ('split_0_10','0–10m','#D0D0D6'),('split_10_30','10–30m','#9A9AA2'),
        ('split_30_60','30–60m','#FC4C02'),
    ]:
        fig2.add_trace(go.Scatter(x=df_p['run_num'], y=df_p[col], mode='lines+markers',
            name=label, line=dict(color=color, width=2), marker=dict(size=4)))
    style_chart(fig2, height=300)
    y_min = min(df_p['split_0_10'].min(), df_p['split_10_30'].min(), df_p['split_30_60'].min()) * 0.97
    y_max = df_p['split_30_60'].max() * 1.03
    fig2.update_layout(yaxis=dict(range=[y_min, y_max]))
    for col, label, color in [
        ('split_0_10','0–10m','#D0D0D6'),('split_10_30','10–30m','#9A9AA2'),
        ('split_30_60','30–60m','#FC4C02'),
    ]:
        last_val = df_p[col].iloc[-1]
        last_run = df_p['run_num'].iloc[-1]
        fig2.add_annotation(x=last_run + 0.3, y=last_val,
            text=f"{last_val:.3f}s", showarrow=False, xanchor='left',
            font=dict(family='JetBrains Mono', size=10, color=color))
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    section_header("WEEKLY TRAINING LOAD", accent='blue')
    df_p_orig = load_athlete_runs(current_user).copy()
    df_p_orig['week_label'] = df_p_orig['date'].dt.strftime('W%U')
    weekly_counts = df_p_orig.groupby('week_label').size().reset_index(name='runs')
    fig_wk = go.Figure(go.Bar(
        x=weekly_counts['week_label'], y=weekly_counts['runs'],
        marker=dict(color='#FC4C02', line=dict(width=0)),
        text=weekly_counts['runs'], textposition='outside',
        textfont=dict(family='JetBrains Mono', size=10, color='#9A9AA2'),
        cliponaxis=False,
    ))
    style_chart(fig_wk, height=220)
    fig_wk.update_layout(
        yaxis=dict(visible=False),
        xaxis=dict(tickfont=dict(family='DM Sans', size=11, color='#6E6E76')),
        bargap=0.3,
    )
    st.plotly_chart(fig_wk, use_container_width=True, config=CHART_CFG)

    section_header("TOP 5 RUNS", accent='blue')
    top5 = df_p.nsmallest(5, 'total').reset_index(drop=True)
    t5_rows = ''
    for i, row in top5.iterrows():
        t5_rows += f"""
        <tr style="border-bottom:1px solid #1A1A1F;">
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#FFD700;font-size:0.8rem;">#{i+1}</td>
            <td style="padding:10px 14px;font-family:DM Sans;color:#6E6E76;font-size:0.75rem;">{str(row['date'])[:10]}</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#FC4C02;font-size:0.82rem;">{float(row['split_0_10']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#9A9AA2;font-size:0.82rem;">{float(row['split_10_30']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#FC4C02;font-size:0.82rem;">{float(row['split_30_60']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#F5F5F7;font-size:0.9rem;font-weight:500;">{float(row['total']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#6E6E76;font-size:0.78rem;">{float(row['top_speed']):.1f} mph</td>
        </tr>"""
    th5 = "padding:10px 14px;font-family:DM Sans;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#3A3A42;text-align:left;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E22;border-radius:12px;overflow:hidden;margin-bottom:16px;">
        <table style="width:100%;border-collapse:collapse;background:#131316;">
            <thead>
                <tr style="background:#0D0D10;border-bottom:2px solid #1E1E22;">
                    {''.join([f'<th style="{th5}">{h}</th>' for h in ['#','Date','0–10m','10–30m','30–60m','Total','Speed']])}
                </tr>
            </thead>
            <tbody>{t5_rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    section_header("RECENT RUNS", accent='blue')
    recent = df_p.tail(10)[::-1]
    pb = df_p['total'].min()
    rows = ''
    for _, row in recent.iterrows():
        pb_badge = '<span style="font-family:DM Sans;font-size:0.6rem;background:#FC4C0222;color:#FC4C02;border:1px solid #FC4C0244;border-radius:999px;padding:2px 7px;margin-left:8px;">PB</span>' if row['total'] == pb else ''
        rows += f"""<tr style="border-bottom:1px solid #1A1A1F;">
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#6E6E76;font-size:0.8rem;">#{int(row['run_num'])}</td>
            <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#6E6E76;font-size:0.78rem;">{str(row['date'])[:10]}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#FC4C02;font-size:0.82rem;">{row['split_0_10']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#9A9AA2;font-size:0.82rem;">{row['split_10_30']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#FC4C02;font-size:0.82rem;">{row['split_30_60']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#F5F5F7;font-size:0.9rem;font-weight:500;">{row['total']:.3f}s{pb_badge}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#6E6E76;font-size:0.8rem;">{row['top_speed']:.1f}</td>
        </tr>"""
    th = "padding:10px 14px;font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#3A3A42;text-align:left;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E22;border-radius:12px;overflow:hidden;">
        <table style="width:100%;border-collapse:collapse;background:#131316;">
            <thead><tr style="background:#0D0D10;border-bottom:2px solid #1E1E22;">
                <th style="{th}">#</th><th style="{th}">Date</th>
                <th style="{th}">0–10m</th><th style="{th}">10–30m</th>
                <th style="{th}">30–60m</th><th style="{th}">Total</th><th style="{th}">Speed</th>
            </tr></thead><tbody>{rows}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)
    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "SETTINGS":
    page_header("SETTINGS", "manage athletes and sessions")

    if user_role != 'coach':
        st.markdown("""
        <div style="background:#131316;border:1px solid #1E1E22;border-left:3px solid #FF4D4D;
                    border-radius:0 12px 12px 0;padding:24px 28px;margin:20px 0;text-align:center;">
            <div style="font-size:1.8rem;margin-bottom:10px;color:#FF4D4D;">!</div>
            <div style="font-family:'DM Sans';font-weight:700;font-size:1.2rem;
                        color:#FF4D4D;margin-bottom:8px;">Coach Access Only</div>
            <div style="font-family:'DM Sans';font-size:0.82rem;color:#6E6E76;line-height:1.6;">
                Team management is handled by the coach account.<br>
                To edit your profile, visit <span style="color:#FC4C02;">MY PROFILE</span>.
            </div>
        </div>
        """, unsafe_allow_html=True)
        render_footer()
        st.stop()

    section_header("ADD NEW ATHLETE", accent='blue')
    with st.form("add_athlete"):
        c1, c2 = st.columns(2)
        name   = c1.text_input("Full name")
        school = c2.text_input("School / Team")
        c3, c4, c5 = st.columns(3)
        events = c3.text_input("Events")
        age    = c4.number_input("Age", min_value=10, max_value=40, value=18)
        height = c5.text_input("Height")
        if st.form_submit_button("ADD ATHLETE", use_container_width=True) and name:
            add_athlete_to_db(name, school, events, age, height)
            st.success(f"{name} added to Drive Phase.")
            st.cache_data.clear()

    section_header("LOG A MANUAL RUN", accent='pink')
    with st.form("log_run"):
        c1, c2 = st.columns(2)
        ath_list = get_all_athletes()
        athlete_name = c1.selectbox("Athlete", ath_list if ath_list else ["—"])
        run_date     = c2.date_input("Date")
        c3, c4, c5 = st.columns(3)
        s1 = c3.number_input("0–10m (s)",  min_value=0.0, value=1.85, step=0.001, format="%.3f")
        s2 = c4.number_input("10–30m (s)", min_value=0.0, value=2.40, step=0.001, format="%.3f")
        s3 = c5.number_input("30–60m (s)", min_value=0.0, value=3.10, step=0.001, format="%.3f")
        if st.form_submit_button("LOG RUN", use_container_width=True) and ath_list:
            total = s1 + s2 + s3
            log_run_to_db(athlete_name, str(run_date), s1, s2, s3, total, round(30/s3*2.237, 2))
            st.success(f"Run logged for {athlete_name} — {total:.3f}s")
            st.cache_data.clear()

    section_header("MANAGE ATHLETES", accent='blue')
    athletes_df = get_all_athletes_with_stats()
    if not athletes_df.empty:
        rows = ''.join(f"""<tr style="border-bottom:1px solid #1A1A1F;">
            <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#F5F5F7;font-size:0.85rem;">{row['name']}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#FC4C02;font-size:0.82rem;">{row['runs']}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#FC4C02;font-size:0.82rem;">{row['best']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#6E6E76;font-size:0.78rem;">{str(row['last_run'])[:10]}</td>
        </tr>""" for _, row in athletes_df.iterrows())
        th = "padding:10px 14px;font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#3A3A42;text-align:left;font-weight:500;"
        st.markdown(f"""
        <div style="border:1px solid #1E1E22;border-radius:12px;overflow:hidden;">
            <table style="width:100%;border-collapse:collapse;background:#131316;">
                <thead><tr style="background:#0D0D10;border-bottom:2px solid #1E1E22;">
                    <th style="{th}">Athlete</th><th style="{th}">Runs</th>
                    <th style="{th}">Best Total</th><th style="{th}">Last Run</th>
                </tr></thead><tbody>{rows}</tbody>
            </table>
        </div>""", unsafe_allow_html=True)
    else:
        empty_state("◇", "NO ATHLETES YET", "Use the form above to add your first athlete.")

    section_header("IMPORT RUNS FROM CSV", accent='blue')
    st.markdown("""
    <div style="background:#131316;border:1px solid #1E1E22;border-radius:10px;
                padding:16px 18px;margin-bottom:12px;">
        <div style="font-family:'DM Sans';font-size:0.75rem;color:#9A9AA2;margin-bottom:8px;line-height:1.6;">
            Upload a CSV with columns:
            <span style="font-family:JetBrains Mono;color:#FC4C02;font-size:0.72rem;">
                athlete, date, split_0_10, split_10_30, split_30_60
            </span>
            — total and top_speed will be auto-calculated.
        </div>
    </div>
    """, unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload CSV", type=['csv'], label_visibility="collapsed")
    if uploaded is not None:
        df_import = pd.read_csv(io.BytesIO(uploaded.read()))
        required_cols = ['athlete', 'date', 'split_0_10', 'split_10_30', 'split_30_60']
        if all(c in df_import.columns for c in required_cols):
            df_import['total']     = df_import['split_0_10'] + df_import['split_10_30'] + df_import['split_30_60']
            df_import['top_speed'] = (30 / df_import['split_30_60'] * 2.237).round(2)
            st.markdown(f"""
            <div style="background:#0D1A0D;border:1px solid rgba(29,219,139,0.27);border-radius:8px;
                        padding:12px 16px;margin-bottom:8px;">
                <span style="font-family:DM Sans;font-size:0.8rem;color:#1DDB8B;">
                    ✓ {len(df_import)} runs ready to import for {df_import['athlete'].nunique()} athlete(s)
                </span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("CONFIRM IMPORT", use_container_width=True):
                conn_imp = sqlite3.connect(DB)
                for _, row_imp in df_import.iterrows():
                    conn_imp.execute(
                        'INSERT INTO runs (date,athlete,split_0_10,split_10_30,split_30_60,total,top_speed) VALUES (?,?,?,?,?,?,?)',
                        (str(row_imp['date']), row_imp['athlete'], row_imp['split_0_10'],
                         row_imp['split_10_30'], row_imp['split_30_60'], row_imp['total'], row_imp['top_speed']))
                conn_imp.commit(); conn_imp.close()
                st.cache_data.clear()
                st.success(f"Imported {len(df_import)} runs.")
                st.rerun()
        else:
            missing_cols = [c for c in required_cols if c not in df_import.columns]
            st.error(f"Missing columns: {', '.join(missing_cols)}")

    section_header("DANGER ZONE", accent='pink')
    with st.expander("Delete athlete data", expanded=False):
        del_athletes_list = get_all_athletes()
        if del_athletes_list:
            del_athlete = st.selectbox("Select athlete to clear runs", del_athletes_list, key="del_select")
            st.markdown(f"""
            <div style="background:#1A0D0D;border:1px solid rgba(255,77,106,0.27);border-radius:8px;
                        padding:12px 16px;margin-bottom:12px;">
                <span style="font-family:DM Sans;font-size:0.78rem;color:#FF4D4D;">
                    ! This will permanently delete all runs for {del_athlete}. This cannot be undone.
                </span>
            </div>
            """, unsafe_allow_html=True)
            del_confirm = st.text_input("Type DELETE to confirm", key="del_confirm")
            if st.button("DELETE RUNS", use_container_width=True) and del_confirm == "DELETE":
                conn_del = sqlite3.connect(DB)
                conn_del.execute("DELETE FROM runs WHERE athlete=?", (del_athlete,))
                conn_del.commit(); conn_del.close()
                st.cache_data.clear()
                st.success(f"All runs deleted for {del_athlete}.")
                st.rerun()
        else:
            st.markdown('<div style="color:#6E6E76;font-size:0.8rem;">No athletes yet.</div>', unsafe_allow_html=True)

    render_footer()
    st.stop()
