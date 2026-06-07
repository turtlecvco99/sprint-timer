import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sqlite3
import datetime
import random
import os

from db import (
    get_all_athletes, load_athlete_runs, load_all_runs, load_leaderboard,
    load_athlete_profile, save_athlete_profile, log_run_to_db,
    get_all_athletes_with_stats, add_athlete_to_db, get_global_stats, DB,
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
        profile_color TEXT DEFAULT '#89C4E1',
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
        ('profile_color', "TEXT DEFAULT '#89C4E1'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE athletes ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass
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

SCALE = [[0,'#89C4E1'],[0.5,'#B39DDB'],[1.0,'#FF3D8A']]
CHART_CFG = {'displayModeBar': False, 'staticPlot': False, 'responsive': True}

# ── Fonts ──────────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
* { box-sizing: border-box; }

html, body, [data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {
    background-color: #0A0A0F !important;
    color: #F0F0F0 !important;
}
[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
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
    min-width: 260px !important;
    width: 260px !important;
    left: 0 !important;
    position: relative !important;
}
section[data-testid="stSidebar"][aria-expanded="false"] {
    transform: none !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    width: 260px !important;
    min-width: 260px !important;
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
    background-color: #0D0D14 !important;
    background: #0D0D14 !important;
}
[data-testid="stSidebar"] {
    border-right: 1px solid #1E1E2E !important;
    min-width: 260px !important;
    max-width: 260px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem 1rem !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small {
    color: #C8C8D8 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Main content buttons (gradient) ── */
[data-testid="stButton"] button {
    background: linear-gradient(135deg, #89C4E1, #FF3D8A) !important;
    border: none !important;
    color: #0A0A0F !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    transition: opacity 0.2s ease !important;
}
[data-testid="stButton"] button:hover { opacity: 0.85 !important; }

/* ── Form submit buttons — outline style ── */
[data-testid="stFormSubmitButton"] button {
    background: transparent !important;
    background-image: none !important;
    border: 1px solid #89C4E1 !important;
    color: #89C4E1 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    background: #89C4E1 !important;
    color: #0A0A0F !important;
}

/* ── Second form submit (LOG RUN) — pink accent ── */
[data-testid="stForm"]:nth-of-type(2) [data-testid="stFormSubmitButton"] button {
    border-color: #FF3D8A !important;
    color: #FF3D8A !important;
}
[data-testid="stForm"]:nth-of-type(2) [data-testid="stFormSubmitButton"] button:hover {
    background: #FF3D8A !important;
    color: #0A0A0F !important;
}

[data-testid="stDownloadButton"] button {
    background: transparent !important;
    border: 1px solid #89C4E1 !important;
    color: #89C4E1 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
}

/* ── Sidebar buttons — nav style (after gradient rule, same specificity → later wins) ── */
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: #1A1A2A !important;
    background-image: none !important;
    border: 1px solid #2A2A3E !important;
    color: #9090A8 !important;
    font-size: 0.74rem !important;
    font-weight: 400 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    border-radius: 7px !important;
    padding: 9px 12px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    opacity: 1 !important;
    transition: border-color 0.15s, color 0.15s !important;
}
[data-testid="stSidebar"] button:hover,
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: rgba(137,196,225,0.07) !important;
    border-color: #89C4E1 !important;
    color: #89C4E1 !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: rgba(137,196,225,0.12) !important;
    background-image: none !important;
    border: 1px solid #89C4E1 !important;
    color: #89C4E1 !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

/* ── Forms / inputs ── */
[data-testid="stTextInput"] input {
    background: #12121A !important;
    border: none !important;
    border-bottom: 2px solid #89C4E1 !important;
    border-radius: 0 !important;
    color: #F0F0F0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 8px 4px !important;
}
[data-testid="stTextInput"] input:focus { border-bottom-color: #FF3D8A !important; box-shadow:none !important; }
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label,
[data-testid="stDateInput"] label {
    font-size: 0.7rem !important; letter-spacing: 0.12em !important;
    text-transform: uppercase !important; color: #555566 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #12121A !important; border: 1px solid #1E1E2E !important; color: #F0F0F0 !important;
}
[data-testid="stNumberInput"] input {
    background: #12121A !important; border: 1px solid #1E1E2E !important;
    color: #F0F0F0 !important; font-family: 'JetBrains Mono', monospace !important;
}
[data-testid="stTextArea"] textarea {
    background: #12121A !important; border: 1px solid #1E1E2E !important;
    color: #F0F0F0 !important; font-family: 'DM Sans', sans-serif !important;
}

/* ── Charts ── */
[data-testid="stPlotlyChart"] > div {
    background: #12121A !important; border-radius: 10px !important;
    padding: 8px !important; border: 1px solid #1E1E2E !important;
}

/* ── Misc ── */
[data-testid="stAlert"] {
    background: #12121A !important; border: 1px solid #1E1E2E !important;
    border-left: 3px solid #1DDB8B !important; border-radius: 8px !important;
}
[data-testid="stExpander"] {
    background: #12121A !important; border: 1px solid #1E1E2E !important; border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.78rem !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important; color: #555566 !important;
}
[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
.element-container { margin-bottom: 0.15rem !important; }
[data-testid="stHorizontalBlock"] { gap: 0.75rem !important; align-items: stretch !important; }
hr {
    border: none !important; height: 1px !important;
    background: linear-gradient(90deg, transparent, #89C4E1 30%, #FF3D8A 70%, transparent) !important;
    margin: 16px 0 !important; opacity: 0.4 !important;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0F; }
::-webkit-scrollbar-thumb { background: #1E1E2E; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #89C4E1; }
@keyframes dp-pulse {
    0%,100% { opacity:1; box-shadow:0 0 8px rgba(29,219,139,0.8); }
    50%      { opacity:0.4; box-shadow:0 0 4px rgba(29,219,139,0.3); }
}

/* ── Animation library ── */
@keyframes fadeInUp {
    from { opacity:0; transform:translateY(20px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes fadeInLeft {
    from { opacity:0; transform:translateX(-20px); }
    to   { opacity:1; transform:translateX(0); }
}
@keyframes fadeInRight {
    from { opacity:0; transform:translateX(20px); }
    to   { opacity:1; transform:translateX(0); }
}
@keyframes scaleIn {
    from { opacity:0; transform:scale(0.94); }
    to   { opacity:1; transform:scale(1); }
}
@keyframes gradientShift {
    0%   { background-position:0% 50%; }
    50%  { background-position:100% 50%; }
    100% { background-position:0% 50%; }
}
@keyframes borderGlow {
    0%,100% { box-shadow:0 0 8px rgba(137,196,225,0.2); }
    50%      { box-shadow:0 0 24px rgba(137,196,225,0.5); }
}
@keyframes shimmer {
    0%   { background-position:-200% center; }
    100% { background-position:200% center; }
}

/* ── Apply to main content blocks ── */
[data-testid="stMainBlockContainer"] > div > div {
    animation: fadeInUp 0.4s ease both;
}
[data-testid="stHorizontalBlock"] > div:nth-child(1) { animation: fadeInLeft 0.35s ease both; }
[data-testid="stHorizontalBlock"] > div:nth-child(2) { animation: fadeInUp 0.4s ease 0.05s both; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) { animation: fadeInRight 0.35s ease 0.1s both; }
[data-testid="stHorizontalBlock"] > div:nth-child(4) { animation: fadeInRight 0.35s ease 0.15s both; }

/* ── Staggered metric card animations ── */
.dp-metric-1 { animation: scaleIn 0.3s ease 0.05s both; }
.dp-metric-2 { animation: scaleIn 0.3s ease 0.10s both; }
.dp-metric-3 { animation: scaleIn 0.3s ease 0.15s both; }
.dp-metric-4 { animation: scaleIn 0.3s ease 0.20s both; }

/* ── Card hover lifts ── */
.dp-card { transition: transform 0.2s ease, box-shadow 0.2s ease !important; }
.dp-card:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 32px rgba(137,196,225,0.12) !important;
}

/* ── Animated gradient title ── */
.dp-gradient-title {
    background: linear-gradient(135deg,#89C4E1,#B39DDB,#FF3D8A,#89C4E1);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientShift 6s ease infinite;
}

/* ── Alert animation ── */
[data-testid="stAlert"] { animation: fadeInUp 0.25s ease both; }
[data-testid="stExpander"] { animation: fadeInUp 0.3s ease both; }

/* ── Selectbox dark ── */
[data-testid="stSelectbox"] > div > div {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    color: #F0F0F0 !important;
    border-radius: 8px !important;
}

/* ── Number input dark ── */
[data-testid="stNumberInput"] input {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    color: #F0F0F0 !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Date input dark ── */
[data-testid="stDateInput"] input {
    background: #12121A !important;
    border-bottom: 2px solid #89C4E1 !important;
    color: #F0F0F0 !important;
    border-radius: 0 !important;
}

/* ── Selectbox fully dark ── */
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background-color: #12121A !important;
    border-color: #1E1E2E !important;
    color: #F0F0F0 !important;
}
[data-testid="stSelectbox"] svg { fill: #555566 !important; }

/* ── File uploader dark ── */
[data-testid="stFileUploader"] {
    background: #12121A !important;
    border: 1px dashed #1E1E2E !important;
    border-radius: 10px !important;
    padding: 12px !important;
}
[data-testid="stFileUploader"] label {
    color: #555566 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
}

/* ── Expander header hover ── */
[data-testid="stExpander"] summary:hover { color: #89C4E1 !important; }

/* ── Table row hover ── */
tr:hover { background: #1A1A26 !important; }

/* ── Number input +/- buttons styled ── */
[data-testid="stNumberInput"] > div {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    border-radius: 8px !important;
}
[data-testid="stNumberInput"] button {
    background: #1E1E2E !important;
    border: none !important;
    color: #8A8A9A !important;
}
[data-testid="stNumberInput"] button:hover {
    background: #89C4E1 !important;
    color: #0A0A0F !important;
}

/* ── Success alert styled ── */
[data-testid="stAlert"][kind="success"] {
    background: #0D1A0D !important;
    border: 1px solid rgba(29,219,139,0.3) !important;
    border-left: 3px solid #1DDB8B !important;
    border-radius: 0 8px 8px 0 !important;
    color: #1DDB8B !important;
}

/* ── Error alert styled ── */
[data-testid="stAlert"][kind="error"] {
    background: #1A0D0D !important;
    border: 1px solid rgba(255,77,106,0.3) !important;
    border-left: 3px solid #FF4D6A !important;
    border-radius: 0 8px 8px 0 !important;
}
</style>""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def smart_yrange(series, pad=0.02):
    mn, mx = series.min(), series.max()
    margin = (mx - mn) * pad + 0.05
    return [mn - margin, mx + margin]


def style_chart(fig, height=360):
    fig.update_layout(
        paper_bgcolor='#12121A', plot_bgcolor='#12121A',
        font=dict(family='DM Sans', color='#8A8A9A', size=12),
        height=height, hovermode='x unified',
        hoverlabel=dict(bgcolor='#1A1A26', bordercolor='#2A2A3E',
                        font=dict(family='DM Sans', color='#F0F0F0', size=12)),
        xaxis=dict(gridcolor='#1E1E2E', linecolor='#1E1E2E',
                   tickfont=dict(family='DM Sans', size=12, color='#8A8A9A'),
                   showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='#1E1E2E', linecolor='#1E1E2E',
                   tickfont=dict(family='JetBrains Mono', size=11, color='#555566'),
                   showgrid=True, zeroline=False),
        legend=dict(bgcolor='#0A0A0F', bordercolor='#1E1E2E', borderwidth=1,
                    font=dict(family='DM Sans', size=11, color='#8A8A9A')),
        margin=dict(l=16, r=16, t=48, b=60),
    )
    return fig


def view_header(title, subtitle=None):
    sub = f"""<div style="display:flex;align-items:center;gap:10px;margin-top:6px;">
        <div style="width:6px;height:6px;border-radius:50%;background:#1DDB8B;
                    box-shadow:0 0 8px rgba(29,219,139,0.8);
                    animation:dp-pulse 2s infinite;flex-shrink:0;"></div>
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;
                     letter-spacing:0.14em;text-transform:uppercase;color:#555566;">{subtitle}</span>
    </div>""" if subtitle else ''
    st.markdown(f"""
    <div style="padding:20px 0 16px;border-bottom:1px solid #1E1E2E;margin-bottom:20px;
                display:flex;align-items:flex-end;justify-content:space-between;">
        <div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:3.6rem;
                        letter-spacing:0.06em;line-height:1;
                        background:linear-gradient(135deg,#89C4E1 0%,#B39DDB 50%,#FF3D8A 100%);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;">{title}</div>{sub}
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                     color:#2A2A3E;padding-bottom:4px;">
            {datetime.datetime.now().strftime('%a %b %d · %H:%M')}
        </span>
    </div>""", unsafe_allow_html=True)


def page_header(title, subtitle, icon, accent='blue'):
    color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    st.markdown(f"""
    <div style="padding:20px 0 24px;border-bottom:1px solid #1E1E2E;margin-bottom:28px;">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">
            <div style="width:40px;height:40px;border-radius:10px;
                        background:rgba(137,196,225,0.08);border:1px solid rgba(137,196,225,0.2);
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.3rem;flex-shrink:0;">{icon}</div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:2.8rem;
                        letter-spacing:0.06em;line-height:1;
                        background:linear-gradient(135deg,{color},#FF3D8A);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;">{title}</div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;margin-left:54px;">
            <div style="width:5px;height:5px;border-radius:50%;background:#1DDB8B;
                        box-shadow:0 0 6px rgba(29,219,139,0.8);flex-shrink:0;"></div>
            <span style="font-family:'DM Sans';font-size:0.7rem;letter-spacing:0.14em;
                         text-transform:uppercase;color:#555566;">{subtitle}</span>
            <span style="margin-left:auto;font-family:'JetBrains Mono';
                         font-size:0.68rem;color:#2A2A3E;">
                {__import__('datetime').datetime.now().strftime('%a %b %d · %H:%M')}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def stat_card(col, label, value, unit='', accent='#89C4E1', sublabel='', size='normal'):
    font_size = '2rem' if size == 'normal' else '1.4rem' if size == 'small' else '2.6rem'
    sub_html = f'<div style="font-family:DM Sans;font-size:0.68rem;color:#2A2A3E;margin-top:4px;">{sublabel}</div>' if sublabel else ''
    col.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;
                border-top:3px solid {accent};border-radius:12px;
                padding:16px 14px;height:100%;
                box-shadow:0 0 20px rgba(137,196,225,0.04);">
        <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#555566;margin-bottom:8px;">{label}</div>
        <div style="font-family:'JetBrains Mono';font-size:{font_size};
                    color:#F0F0F0;line-height:1;">
            {value}<span style="font-size:0.85rem;color:#555566;margin-left:3px;">{unit}</span>
        </div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def section_header(label, accent='blue'):
    color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    glow  = 'rgba(137,196,225,0.4)' if accent == 'blue' else 'rgba(255,61,138,0.4)'
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:14px;margin:20px 0 12px;">
        <div style="width:4px;height:24px;background:{color};border-radius:2px;
                    box-shadow:0 0 10px {glow};flex-shrink:0;"></div>
        <span style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;
                     letter-spacing:0.1em;color:#F0F0F0;">{label}</span>
    </div>""", unsafe_allow_html=True)


def metric_card(col, icon, label, value, accent='blue'):
    bc = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    gl = 'rgba(137,196,225,0.08)' if accent == 'blue' else 'rgba(255,61,138,0.08)'
    col.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;
                border-top:3px solid {bc};border-radius:12px;
                padding:16px 14px;box-shadow:0 0 24px {gl};height:100%;">
        <div style="font-family:'DM Sans',sans-serif;font-size:0.62rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#555566;margin-bottom:6px;">{icon}&nbsp; {label}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.8rem;
                    color:#F0F0F0;line-height:1.1;white-space:nowrap;
                    overflow:hidden;text-overflow:ellipsis;">{value}</div>
    </div>""", unsafe_allow_html=True)


def podium_card(col, rank, name, total, runs, top_speed):
    c = {
        1:{'border':'#FFD700','glow':'rgba(255,215,0,0.15)',
           'bg':'linear-gradient(160deg,#1A1600 0%,#12121A 60%)',
           'nc':'#FFD700','medal':'🥇','sz':'2.6rem','badge':'FASTEST','bc':'#FFD700'},
        2:{'border':'#89C4E1','glow':'rgba(137,196,225,0.10)',
           'bg':'linear-gradient(160deg,#0A1520 0%,#12121A 60%)',
           'nc':'#89C4E1','medal':'🥈','sz':'2.2rem','badge':'2ND','bc':'#89C4E1'},
        3:{'border':'#CD7F32','glow':'rgba(205,127,50,0.10)',
           'bg':'linear-gradient(160deg,#160E00 0%,#12121A 60%)',
           'nc':'#CD7F32','medal':'🥉','sz':'2.0rem','badge':'3RD','bc':'#CD7F32'},
    }[rank]
    col.markdown(f"""
    <div style="background:{c['bg']};border:1px solid {c['border']};
                border-top:3px solid {c['border']};border-radius:14px;
                padding:28px 20px 24px;text-align:center;
                box-shadow:0 0 40px {c['glow']};position:relative;min-height:200px;">
        <div style="position:absolute;top:12px;right:14px;font-family:'DM Sans',sans-serif;
                    font-size:0.6rem;letter-spacing:0.16em;text-transform:uppercase;
                    color:{c['bc']};background:{c['bc']}18;border:1px solid {c['bc']}44;
                    border-radius:999px;padding:3px 10px;">{c['badge']}</div>
        <div style="font-size:2.4rem;margin-bottom:8px;">{c['medal']}</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:0.1em;
                    color:{c['nc']};margin-bottom:6px;">{name.upper()}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:{c['sz']};
                    color:#F0F0F0;font-weight:500;line-height:1;margin-bottom:12px;">{total:.2f}s</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.75rem;color:#555566;">
            {runs} runs &nbsp;·&nbsp; {top_speed:.1f} mph top speed</div>
    </div>""", unsafe_allow_html=True)


def render_rankings_table(lb_df, current_user=''):
    MEDALS = {1:'🥇',2:'🥈',3:'🥉'}
    RANK_COLORS = {1:'#FFD700',2:'#C0C0C0',3:'#CD7F32'}
    rows = ''
    for _, row in lb_df.iterrows():
        rank = int(row['rank']); rc = RANK_COLORS.get(rank,'#555566')
        is_me = row['athlete'] == current_user
        you_badge = '<span style="font-family:DM Sans;font-size:0.55rem;background:#89C4E1;color:#0A0A0F;border-radius:999px;padding:2px 7px;margin-left:8px;font-weight:600;vertical-align:middle;">YOU</span>' if is_me else ''
        name_color = '#F0F0F0' if is_me else '#8A8A9A'
        row_bg = 'background:#1A1A2A;' if is_me else ''
        rows += f"""<tr style="border-bottom:1px solid #1A1A26;{row_bg}">
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:{rc};font-size:0.85rem;">{MEDALS.get(rank,f'#{rank}')}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:{name_color};font-size:0.9rem;font-weight:500;">{row['athlete']}{you_badge}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#89C4E1;font-size:0.85rem;">{row['best_total']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#8A8A9A;font-size:0.85rem;">{row['best_0_10']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#8A8A9A;font-size:0.85rem;">{row['best_10_30']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#FF3D8A;font-size:0.85rem;">{row['best_30_60']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#8A8A9A;font-size:0.85rem;">{row['top_speed']:.1f}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#555566;font-size:0.85rem;">{row['runs']}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#555566;font-size:0.78rem;">{row['last_run']}</td>
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
        rows += f"""<tr style="border-top:2px solid #2A2A3E;background:#0D0D14;">
            <td style="padding:12px 16px;font-family:'DM Sans',monospace;color:#2A2A3E;font-size:0.75rem;font-style:italic;">AVG</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#2A2A3E;font-size:0.8rem;font-style:italic;">Field average</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#2A2A3E;font-size:0.82rem;">{avg_best:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#2A2A3E;font-size:0.82rem;">{avg_0_10:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#2A2A3E;font-size:0.82rem;">{avg_10_30:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#2A2A3E;font-size:0.82rem;">{avg_30_60:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#2A2A3E;font-size:0.82rem;">{avg_speed:.1f}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#2A2A3E;font-size:0.82rem;">{avg_runs_ct}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#2A2A3E;font-size:0.78rem;">—</td>
        </tr>"""
    th = "padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.14em;text-transform:uppercase;color:#555566;text-align:left;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E2E;border-radius:12px;overflow:hidden;margin-top:8px;">
        <table style="width:100%;border-collapse:collapse;background:#12121A;">
            <thead><tr style="border-bottom:2px solid #1E1E2E;background:#0D0D14;">
                <th style="{th}">Rank</th><th style="{th}">Athlete</th>
                <th style="{th}">Best Total</th><th style="{th}">0–10m</th>
                <th style="{th}">10–30m</th><th style="{th}">30–60m</th>
                <th style="{th}">Top Speed</th><th style="{th}">Runs</th>
                <th style="{th}">Last Run</th>
            </tr></thead><tbody>{rows}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)


def empty_state(icon='📭', title="NO DATA", subtitle="Log some runs to unlock this."):
    st.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:14px;
                padding:48px 32px;text-align:center;margin:8px 0;">
        <div style="font-size:2.5rem;margin-bottom:12px;opacity:0.4;">{icon}</div>
        <div style="font-family:'Bebas Neue';font-size:1.4rem;letter-spacing:0.08em;
                    color:#2A2A3E;margin-bottom:6px;">{title}</div>
        <div style="font-family:'DM Sans';font-size:0.78rem;color:#2A2A3E;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    st.markdown("""
    <div style="margin-top:40px;padding:20px 0;border-top:1px solid #1E1E2E;
                display:flex;justify-content:space-between;align-items:center;">
        <span style="font-family:'Bebas Neue',sans-serif;font-size:1rem;
                     letter-spacing:0.1em;color:#2A2A3E;">DRIVE PHASE</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;
                     color:#555566;letter-spacing:0.08em;">built by athletes · powered by data</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#555566;">v3.0</span>
    </div>""", unsafe_allow_html=True)


def info_card(text, accent='blue'):
    color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    st.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;border-left:3px solid {color};
                border-radius:0 8px 8px 0;padding:12px 16px;margin:8px 0;">
        <p style="font-family:'DM Sans',sans-serif;font-size:0.82rem;
                  color:#8A8A9A;margin:0;font-style:italic;">{text}</p>
    </div>""", unsafe_allow_html=True)


def quick_stat(label, value, color):
    return f"""<div style="display:flex;justify-content:space-between;align-items:center;
        padding:5px 0;border-bottom:1px solid #1E1E2E;">
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;color:#666677;">{label}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:{color};">{value}</span>
    </div>"""


# ══════════════════════════════════════════════════════════════════════════════
# IDENTITY SYSTEM — show fullscreen selector on first visit
# ══════════════════════════════════════════════════════════════════════════════
all_athletes = get_all_athletes()

if st.session_state.current_user is None:
    st.markdown("""
    <style>
    @keyframes titleEntrance {
        0%   { opacity:0; transform:translateY(-30px) scale(0.95); }
        60%  { opacity:1; transform:translateY(4px) scale(1.01); }
        100% { opacity:1; transform:translateY(0) scale(1); }
    }
    @keyframes subtitleEntrance {
        from { opacity:0; letter-spacing:0.4em; }
        to   { opacity:1; letter-spacing:0.2em; }
    }
    @keyframes cardEntrance {
        from { opacity:0; transform:translateY(30px); }
        to   { opacity:1; transform:translateY(0); }
    }
    </style>
    <div style="padding:60px 40px 20px;text-align:center;">
        <div class="dp-gradient-title" style="font-family:'Bebas Neue',sans-serif;font-size:5.5rem;
                    letter-spacing:0.06em;line-height:0.9;margin-bottom:12px;text-align:center;
                    animation:titleEntrance 0.8s ease both;">
            DRIVE<br>PHASE
        </div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.75rem;
                    letter-spacing:0.2em;text-transform:uppercase;
                    color:#555566;margin-bottom:64px;
                    animation:subtitleEntrance 1s ease 0.4s both;">
            acceleration starts here
        </div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.72rem;
                    letter-spacing:0.16em;text-transform:uppercase;
                    color:#444455;margin-bottom:24px;
                    animation:fadeInUp 0.5s ease 0.6s both;">
            Select your profile to continue
        </div>
    </div>
    """, unsafe_allow_html=True)

    if all_athletes:
        stats      = get_all_athletes_with_stats()
        stats_dict = {row['name']: row for _, row in stats.iterrows()}

        def render_identity_card(name, delay):
            s    = stats_dict.get(name, {})
            best = s.get('best', 0)
            runs = int(s.get('runs', 0))
            pb_text = f'{best:.2f}s PB' if best else '—'
            run_text = f'{runs} run{"s" if runs != 1 else ""} logged'
            st.markdown(f"""
            <div style="background:#12121A;border:1px solid #1E1E2E;
                        border-radius:14px;padding:0 0 4px;overflow:hidden;
                        animation:cardEntrance 0.5s ease {delay:.2f}s both;
                        transition:all 0.25s ease;"
                 onmouseover="this.style.borderColor='#89C4E1';this.style.transform='translateY(-4px)';this.style.boxShadow='0 12px 40px rgba(137,196,225,0.15)'"
                 onmouseout="this.style.borderColor='#1E1E2E';this.style.transform='translateY(0)';this.style.boxShadow='none'">
                <div style="height:4px;background:linear-gradient(90deg,#89C4E1,#FF3D8A);"></div>
                <div style="padding:20px 16px;text-align:center;">
                    <div style="width:52px;height:52px;border-radius:50%;
                                background:linear-gradient(135deg,#89C4E1,#FF3D8A);
                                display:flex;align-items:center;justify-content:center;
                                margin:0 auto 14px;font-family:'Bebas Neue';
                                font-size:1.6rem;color:#0A0A0F;">
                        {name[0].upper()}
                    </div>
                    <div style="font-family:'Bebas Neue';font-size:1.3rem;
                                letter-spacing:0.08em;color:#F0F0F0;margin-bottom:8px;">
                        {name.upper()}
                    </div>
                    <div style="font-family:'JetBrains Mono';font-size:0.8rem;
                                color:#89C4E1;margin-bottom:4px;">{pb_text}</div>
                    <div style="font-family:'DM Sans';font-size:0.68rem;color:#2A2A3E;">
                        {run_text}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"ENTER AS {name.upper()}", key=f"id_{name}", use_container_width=True):
                st.session_state.current_user = name
                st.rerun()

        # Split into rows of 4 so second row is never cropped
        rows = [all_athletes[i:i+4] for i in range(0, len(all_athletes), 4)]
        for row_idx, row_athletes in enumerate(rows):
            cols = st.columns(len(row_athletes))
            for ci, name in enumerate(row_athletes):
                delay = 0.7 + (row_idx * 4 + ci) * 0.08
                with cols[ci]:
                    render_identity_card(name, delay)
            st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;color:#555566;font-family:'DM Sans',sans-serif;font-size:0.85rem;">
            No athletes yet. Add athletes in Settings first.
        </div>""", unsafe_allow_html=True)
    st.stop()

current_user = st.session_state.current_user


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
NAV_ITEMS = [
    ("⚡", "MY DASHBOARD"),
    ("🏆", "LEADERBOARD"),
    ("👤", "MY PROFILE"),
    ("📈", "MY PROGRESS"),
    ("⚔️",  "COMPARE"),
    ("⚙️",  "SETTINGS"),
]

with st.sidebar:
    # Logo
    st.markdown("""
    <div style="padding:8px 0 12px;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.9rem;letter-spacing:0.1em;
                    background:linear-gradient(135deg,#89C4E1,#FF3D8A);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;">DRIVE PHASE</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.18em;
                    text-transform:uppercase;color:#555566;margin-top:2px;">acceleration starts here</div>
    </div>""", unsafe_allow_html=True)

    # Identity pill
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#89C4E1,#FF3D8A);
                border-radius:10px;padding:12px 14px;margin-bottom:14px;
                display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;border-radius:50%;background:#0A0A0F;
                    display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <span style="font-family:'Bebas Neue';font-size:1rem;color:#F0F0F0;">
                {current_user[0].upper()}</span>
        </div>
        <div>
            <div style="font-family:'Bebas Neue';font-size:1rem;letter-spacing:0.08em;
                        color:#0A0A0F;line-height:1;">{current_user.upper()}</div>
            <div style="font-family:'DM Sans';font-size:0.6rem;color:#0A0A0F99;
                        letter-spacing:0.1em;text-transform:uppercase;">Active athlete</div>
        </div>
    </div>
    <div style="height:1px;background:linear-gradient(90deg,#89C4E1,#FF3D8A);
                margin-bottom:12px;opacity:0.25;"></div>
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
    <div style="background:#0A0A0F;border:1px solid #1E1E2E;border-radius:10px;padding:12px 14px;">
        <div style="font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#444455;margin-bottom:8px;">Live snapshot</div>
        {quick_stat('Athletes', str(stats['athlete_count']), '#89C4E1')}
        {quick_stat('Total runs', str(stats['total_runs']), '#89C4E1')}
        {quick_stat('Fastest ever', f"{stats['fastest_total']:.2f}s", '#FF3D8A')}
        {quick_stat('Top speed', f"{stats['top_speed_ever']:.1f} mph", '#FF3D8A')}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # Switch user
    if st.button("↩  SWITCH ATHLETE", use_container_width=True, key="nav_switch"):
        st.session_state.current_user = None
        st.rerun()

page = st.session_state.page


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "MY DASHBOARD":
    df_me = load_athlete_runs(current_user)
    if df_me.empty:
        page_header("MY DASHBOARD", f"welcome back, {current_user.lower()}", "⚡", "blue")
        empty_state("🏃", "NO RUNS YET", "Head to Settings to log your first run.")
        render_footer()
        st.stop()

    best   = df_me.nsmallest(1, 'total').iloc[0]
    latest = df_me.iloc[0]
    all_df = load_all_runs()

    rankings = all_df.groupby('athlete')['total'].min().reset_index()
    rankings = rankings.sort_values('total').reset_index(drop=True)
    my_rank = int(rankings[rankings['athlete'] == current_user].index[0]) + 1
    total_athletes = len(rankings)

    page_header("MY DASHBOARD", f"welcome back, {current_user.lower()}", "⚡", "blue")

    # ── Streak calc ──
    from datetime import date, timedelta
    df_me_dates = sorted(df_me['date'].dt.date.unique(), reverse=True)
    streak = 0
    check  = date.today()
    for d in df_me_dates:
        if d >= check - timedelta(days=1):
            streak += 1
            check = d
        else:
            break
    streak_emoji = '🔥' if streak >= 3 else '⚡' if streak >= 1 else '—'
    rank_color   = '#FFD700' if my_rank == 1 else '#89C4E1' if my_rank <= 3 else '#8A8A9A'

    # ── 5-card hero strip (rank / PB / speed / runs / streak) ──
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px;">
        <div style="background:#12121A;border:1px solid #1E1E2E;border-top:3px solid {rank_color};
                    border-radius:12px;padding:16px 14px;">
            <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                        text-transform:uppercase;color:#555566;margin-bottom:6px;">Team rank</div>
            <div style="font-family:'JetBrains Mono';font-size:1.8rem;color:{rank_color};line-height:1;">
                #{my_rank}<span style="font-size:0.9rem;color:#2A2A3E;">/{total_athletes}</span></div>
        </div>
        <div style="background:#12121A;border:1px solid #1E1E2E;border-top:3px solid #89C4E1;
                    border-radius:12px;padding:16px 14px;">
            <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                        text-transform:uppercase;color:#555566;margin-bottom:6px;">Personal best</div>
            <div style="font-family:'JetBrains Mono';font-size:1.8rem;color:#89C4E1;line-height:1;">
                {best['total']:.2f}s</div>
        </div>
        <div style="background:#12121A;border:1px solid #1E1E2E;border-top:3px solid #FF3D8A;
                    border-radius:12px;padding:16px 14px;">
            <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                        text-transform:uppercase;color:#555566;margin-bottom:6px;">Top speed</div>
            <div style="font-family:'JetBrains Mono';font-size:1.8rem;color:#FF3D8A;line-height:1;">
                {df_me['top_speed'].max():.1f}<span style="font-size:0.9rem;color:#555566;"> mph</span></div>
        </div>
        <div style="background:#12121A;border:1px solid #1E1E2E;border-top:3px solid #B39DDB;
                    border-radius:12px;padding:16px 14px;">
            <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                        text-transform:uppercase;color:#555566;margin-bottom:6px;">Runs logged</div>
            <div style="font-family:'JetBrains Mono';font-size:1.8rem;color:#B39DDB;line-height:1;">
                {len(df_me)}</div>
        </div>
        <div style="background:#12121A;border:1px solid #1E1E2E;border-top:3px solid #FFD700;
                    border-radius:12px;padding:16px 14px;">
            <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                        text-transform:uppercase;color:#555566;margin-bottom:6px;">Streak</div>
            <div style="font-family:'JetBrains Mono';font-size:1.8rem;color:#FFD700;line-height:1;">
                {streak}<span style="font-size:1rem;margin-left:4px;">{streak_emoji}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TODAY'S SESSION ──
    from datetime import date as _date, timedelta as _timedelta
    last_session_date = df_me['date'].dt.date.iloc[0]
    last_session_runs = df_me[df_me['date'].dt.date == last_session_date]
    is_today = last_session_date == _date.today()
    session_label = "TODAY'S SESSION" if is_today else f"LAST SESSION — {last_session_date.strftime('%b %d')}"
    session_color = '#1DDB8B' if is_today else '#555566'
    pulse_anim = 'animation:dp-pulse 2s infinite;' if is_today else ''
    reps = last_session_runs[::-1].reset_index(drop=True)
    rep_html = ''
    pb_val_sess = df_me['total'].min()
    for i, row in reps.iterrows():
        is_pb_r = abs(row['total'] - pb_val_sess) < 0.001
        pb_tag = '<span style="font-family:DM Sans;font-size:0.55rem;background:#FFD70022;color:#FFD700;border:1px solid #FFD70044;border-radius:999px;padding:1px 6px;margin-left:6px;">PB</span>' if is_pb_r else ''
        rep_html += f"""
        <div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #1A1A26;">
            <span style="font-family:'JetBrains Mono';font-size:0.72rem;color:#2A2A3E;width:30px;">#{i+1}</span>
            <span style="font-family:'JetBrains Mono';font-size:0.85rem;color:#89C4E1;width:60px;">{row['split_0_10']:.3f}s</span>
            <span style="font-family:'JetBrains Mono';font-size:0.85rem;color:#B39DDB;width:60px;">{row['split_10_30']:.3f}s</span>
            <span style="font-family:'JetBrains Mono';font-size:0.85rem;color:#FF3D8A;width:60px;">{row['split_30_60']:.3f}s</span>
            <span style="font-family:'JetBrains Mono';font-size:1rem;color:#F0F0F0;flex:1;font-weight:500;">{row['total']:.3f}s{pb_tag}</span>
            <span style="font-family:'JetBrains Mono';font-size:0.72rem;color:#555566;">{row['top_speed']:.1f} mph</span>
        </div>"""
    split_header_cols = [('#', 30), ('0–10m', 60), ('10–30m', 60), ('30–60m', 60), ('Total', 80), ('Speed', 60)]
    split_header = ''.join([
        f'<span style="font-family:DM Sans;font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#555566;width:{w}px;display:inline-block;">{t}</span>'
        for t, w in split_header_cols
    ])
    st.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:14px;
                padding:20px 20px 8px;margin-bottom:16px;">
        <div style="font-family:'Bebas Neue';font-size:1.1rem;letter-spacing:0.1em;
                    color:#F0F0F0;margin-bottom:14px;">
            <span style="display:inline-block;width:7px;height:7px;border-radius:50%;
                         background:{session_color};box-shadow:0 0 6px {session_color};
                         margin-right:8px;vertical-align:middle;{pulse_anim}"></span>
            {session_label}
            <span style="font-family:'DM Sans';font-size:0.68rem;color:#555566;margin-left:8px;font-weight:normal;">
                {len(reps)} {'run' if len(reps)==1 else 'reps'}
            </span>
        </div>
        <div style="display:flex;gap:12px;padding:0 0 8px;border-bottom:1px solid #1E1E2E;margin-bottom:4px;">{split_header}</div>
        {rep_html}
    </div>
    """, unsafe_allow_html=True)

    # ── TIME TO BEAT ──
    my_idx = int(rankings[rankings['athlete'] == current_user].index[0])
    if my_idx > 0:
        athlete_above = rankings.iloc[my_idx - 1]
        gap = float(best['total']) - float(athlete_above['total'])
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0D0D14,#12121A);
                    border:1px solid rgba(255,61,138,0.27);border-radius:12px;
                    padding:16px 20px;margin-bottom:16px;
                    display:flex;align-items:center;gap:20px;">
            <div style="font-size:1.8rem;">🎯</div>
            <div style="flex:1;">
                <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.14em;
                            text-transform:uppercase;color:#555566;margin-bottom:4px;">Time to beat</div>
                <div style="font-family:'DM Sans';font-size:0.82rem;color:#8A8A9A;">
                    You're <span style="color:#FF3D8A;font-family:JetBrains Mono;">+{gap:.3f}s</span> behind
                    <span style="color:#F0F0F0;">{athlete_above['athlete']}</span>
                    (#{my_idx})
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'JetBrains Mono';font-size:1.6rem;color:#FF3D8A;">{float(athlete_above['total']):.2f}s</div>
                <div style="font-family:'DM Sans';font-size:0.62rem;color:#555566;">their best</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0D1A0D,#12121A);
                    border:1px solid rgba(29,219,139,0.27);border-radius:12px;
                    padding:16px 20px;margin-bottom:16px;
                    display:flex;align-items:center;gap:20px;">
            <div style="font-size:1.8rem;">👑</div>
            <div>
                <div style="font-family:'Bebas Neue';font-size:1.2rem;
                            letter-spacing:0.08em;color:#1DDB8B;">You're leading the pack</div>
                <div style="font-family:'DM Sans';font-size:0.8rem;color:#555566;">
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

    # ── Two-column body ──
    left, right = st.columns([1.55, 1])

    with left:
        if insight_text:
            st.markdown(f"""
            <div style="background:#0D1A12;border:1px solid rgba(29,219,139,0.2);
                        border-left:3px solid #1DDB8B;border-radius:0 10px 10px 0;
                        padding:12px 16px;margin-bottom:12px;">
                <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.12em;
                            text-transform:uppercase;color:#1DDB8B;margin-bottom:4px;">
                    💡 Season insight</div>
                <div style="font-family:'DM Sans';font-size:0.8rem;color:#8A8A9A;
                            line-height:1.55;">{insight_text}</div>
            </div>
            """, unsafe_allow_html=True)

        section_header("LATEST VS PB", accent='blue')
        chips_html = ''
        for lbl, lat_val, pb_val, color in [
            ('0–10m',  float(latest['split_0_10']),  float(best['split_0_10']),  '#89C4E1'),
            ('10–30m', float(latest['split_10_30']), float(best['split_10_30']), '#B39DDB'),
            ('30–60m', float(latest['split_30_60']), float(best['split_30_60']), '#FF3D8A'),
            ('Total',  float(latest['total']),        float(best['total']),       '#F0F0F0'),
        ]:
            diff = lat_val - pb_val
            sign = '+' if diff > 0 else ''
            dcol = '#1DDB8B' if diff <= 0.001 else '#FF4D6A'
            chips_html += f"""
            <div style="background:#12121A;border:1px solid #1E1E2E;border-top:2px solid {color};
                        border-radius:10px;padding:12px 14px;flex:1;min-width:0;">
                <div style="font-family:'DM Sans';font-size:0.58rem;letter-spacing:0.12em;
                            text-transform:uppercase;color:#555566;
                            margin-bottom:6px;white-space:nowrap;">{lbl}</div>
                <div style="font-family:'JetBrains Mono';font-size:1.3rem;
                            color:#F0F0F0;line-height:1;">{lat_val:.3f}s</div>
                <div style="font-family:'JetBrains Mono';font-size:0.7rem;
                            color:{dcol};margin-top:4px;">{sign}{diff:.3f}s</div>
            </div>"""
        st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:4px;">{chips_html}</div>',
                    unsafe_allow_html=True)

    with right:
        section_header("WHERE I STAND", accent='pink')
        roster_html = ''
        for rank_idx, row in rankings.iterrows():
            rank_n  = rank_idx + 1
            is_me   = row['athlete'] == current_user
            you_tag = '<span style="background:#89C4E1;color:#0A0A0F;font-size:0.55rem;font-family:DM Sans;padding:2px 6px;border-radius:999px;margin-left:6px;font-weight:600;vertical-align:middle;">YOU</span>' if is_me else ''
            rcolor  = '#FFD700' if rank_n == 1 else '#C0C0C0' if rank_n == 2 else '#CD7F32' if rank_n == 3 else '#2A2A3E'
            medal   = '🥇' if rank_n == 1 else '🥈' if rank_n == 2 else '🥉' if rank_n == 3 else f'#{rank_n}'
            bg      = 'background:#12121A;border:1px solid rgba(137,196,225,0.27);' if is_me else 'background:transparent;border:1px solid transparent;'
            ncolor  = '#F0F0F0' if is_me else '#555566'
            vcolor  = '#89C4E1' if is_me else '#2A2A3E'
            roster_html += f"""
            <div style="{bg}border-radius:8px;padding:8px 12px;margin-bottom:3px;
                        display:flex;align-items:center;gap:10px;">
                <span style="font-family:'JetBrains Mono';font-size:0.75rem;color:{rcolor};
                             width:22px;flex-shrink:0;">{medal}</span>
                <span style="font-family:'DM Sans';font-size:0.82rem;color:{ncolor};flex:1;">
                    {row['athlete']}{you_tag}</span>
                <span style="font-family:'JetBrains Mono';font-size:0.78rem;color:{vcolor};">
                    {row['total']:.2f}s</span>
            </div>"""
        st.markdown(f'<div style="margin-bottom:8px;">{roster_html}</div>', unsafe_allow_html=True)

    # ── Full-width last 10 runs ──
    section_header("MY LAST 10 RUNS", accent='blue')
    df_recent = df_me[::-1].tail(10).reset_index(drop=True)
    df_recent['run_num'] = range(1, len(df_recent)+1)
    pb_val = df_me['total'].min()
    bar_colors = ['#FFD700' if abs(v - pb_val) < 0.001 else '#89C4E1' for v in df_recent['total']]
    fig = go.Figure(go.Bar(
        x=df_recent['run_num'], y=df_recent['total'],
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{v:.2f}s" for v in df_recent['total']],
        textposition='outside',
        textfont=dict(family='JetBrains Mono', size=10, color='#8A8A9A'),
        cliponaxis=False,
    ))
    fig.add_hline(y=pb_val, line=dict(color='#FFD700', width=1.5, dash='dot'),
                  annotation_text="PB", annotation_font=dict(color='#FFD700', size=10))
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
    page_header("LEADERBOARD", f"{len(get_all_athletes())} athletes ranked · season 2026", "🏆", "pink")

    if lb.empty:
        empty_state("🏟️", "NO RUNS LOGGED YET", "Get on the track and break some beams.")
        render_footer()
        st.stop()

    section_header("PODIUM", accent='blue')
    top3 = lb.head(3).to_dict('records')
    p1, p2, p3 = st.columns([1.15, 1, 1])
    if len(top3) > 0: podium_card(p1,1,top3[0]['athlete'],top3[0]['best_total'],top3[0]['runs'],top3[0]['top_speed'])
    if len(top3) > 1: podium_card(p2,2,top3[1]['athlete'],top3[1]['best_total'],top3[1]['runs'],top3[1]['top_speed'])
    if len(top3) > 2: podium_card(p3,3,top3[2]['athlete'],top3[2]['best_total'],top3[2]['runs'],top3[2]['top_speed'])

    section_header("FULL RANKINGS", accent='pink')
    render_rankings_table(lb, current_user)

    section_header("BEST TOTAL TIME", accent='blue')
    lb_s = lb.sort_values('best_total')
    fig = go.Figure(go.Bar(
        x=lb_s['athlete'], y=lb_s['best_total'],
        marker=dict(color=lb_s['best_total'], colorscale=SCALE, showscale=False,
                    line=dict(color='#0A0A0F', width=1)),
        text=[f"{v:.2f}s" for v in lb_s['best_total']],
        textposition='outside', textfont=dict(family='JetBrains Mono', size=11, color='#F0F0F0'),
        cliponaxis=False,
    ))
    style_chart(fig, height=320)
    fig.update_layout(
        bargap=0.35,
        yaxis=dict(visible=False, range=[lb_s['best_total'].min()*0.97, lb_s['best_total'].max()*1.04]),
        xaxis=dict(tickfont=dict(family='DM Sans', size=12, color='#8A8A9A')),
        margin=dict(l=16, r=16, t=48, b=60),
    )
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT BREAKDOWN", accent='pink')
    fig2 = go.Figure()
    for split, label, color in [
        ('best_30_60','30–60m','#FF3D8A'),
        ('best_10_30','10–30m','#B39DDB'),
        ('best_0_10', '0–10m', '#89C4E1'),
    ]:
        fig2.add_trace(go.Bar(y=lb['athlete'], x=lb[split], name=label,
            orientation='h', marker_color=color, marker_line=dict(width=0)))
    style_chart(fig2, height=340)
    fig2.update_layout(
        barmode='stack', xaxis_title='Time (s)',
        yaxis=dict(autorange='reversed', tickfont=dict(family='DM Sans', size=12, color='#8A8A9A')),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=16, r=16, t=48, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    section_header("TOP SPEED BY ATHLETE", accent='pink')
    speed_df = load_all_runs().groupby('athlete')['top_speed'].max().reset_index()
    speed_df = speed_df.sort_values('top_speed', ascending=False).reset_index(drop=True)
    spd_colors = ['#FFD700' if r['athlete'] == current_user else '#FF3D8A'
                  for _, r in speed_df.iterrows()]
    fig_spd = go.Figure(go.Bar(
        x=speed_df['athlete'],
        y=speed_df['top_speed'],
        marker=dict(color=spd_colors, line=dict(width=0)),
        text=[f"{v:.1f}" for v in speed_df['top_speed']],
        textposition='outside',
        textfont=dict(family='JetBrains Mono', size=11, color='#8A8A9A'),
        cliponaxis=False
    ))
    style_chart(fig_spd, height=280)
    fig_spd.update_layout(
        yaxis=dict(
            range=[speed_df['top_speed'].min()*0.97, speed_df['top_speed'].max()*1.04],
            visible=False
        ),
        xaxis=dict(tickfont=dict(family='DM Sans', size=12, color='#8A8A9A')),
        bargap=0.35,
    )
    st.plotly_chart(fig_spd, use_container_width=True, config=CHART_CFG)

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY PROFILE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "MY PROFILE":
    profile      = load_athlete_profile(current_user)
    athlete_data = load_athlete_runs(current_user)

    if athlete_data.empty:
        page_header("MY PROFILE", f"{current_user.lower()}'s athlete card", "👤", "blue")
        empty_state("🏃", "NO RUNS YET")
        render_footer()
        st.stop()

    best     = athlete_data.nsmallest(1, 'total').iloc[0]
    all_df   = load_all_runs()
    rankings = all_df.groupby('athlete')['total'].min().sort_values().reset_index()
    my_rank  = int(rankings[rankings['athlete'] == current_user].index[0]) + 1
    accent   = profile.get('profile_color', '#89C4E1') or '#89C4E1'

    page_header("MY PROFILE", f"{current_user.lower()}'s athlete card", "👤", "blue")

    # ── Build profile tags as plain variables (no nested f-string quotes) ──
    accent_rgb = {'#89C4E1':'137,196,225','#FF3D8A':'255,61,138','#B39DDB':'179,157,219',
                  '#1DDB8B':'29,219,139','#FFD700':'255,215,0','#FF6B6B':'255,107,107'}
    acc_rgb = accent_rgb.get(accent, '137,196,225')
    acc_bg  = f'rgba({acc_rgb},0.09)'
    acc_bdr = f'rgba({acc_rgb},0.27)'

    tag_parts = []
    if profile.get('school'):
        v = profile['school']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:{acc_bg};border:1px solid {acc_bdr};color:{accent};border-radius:999px;padding:3px 10px;letter-spacing:0.08em;">{v}</span>')
    if profile.get('events'):
        v = profile['events']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:rgba(255,61,138,0.09);border:1px solid rgba(255,61,138,0.27);color:#FF3D8A;border-radius:999px;padding:3px 10px;">{v}</span>')
    if profile.get('grad_year'):
        v = profile['grad_year']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:#1E1E2E;color:#555566;border-radius:999px;padding:3px 10px;">Class of {v}</span>')
    if profile.get('age') and int(profile.get('age') or 0) > 0:
        v = profile['age']
        tag_parts.append(f'<span style="font-family:DM Sans;font-size:0.68rem;background:#1E1E2E;color:#555566;border-radius:999px;padding:3px 10px;">Age {v}</span>')
    profile_tags = ' '.join(tag_parts)

    bio_val  = profile.get('bio', '') or ''
    bio_html = f'<div style="font-family:DM Sans;font-size:0.82rem;color:#8A8A9A;margin-top:12px;line-height:1.6;max-width:500px;">{bio_val}</div>' if bio_val else ''

    hero_html = f"""
    <div style="background:linear-gradient(135deg,#12121A 0%,#1A1A26 100%);
                border:1px solid {accent};border-radius:20px;overflow:hidden;
                margin-bottom:28px;animation:scaleIn 0.4s ease both;
                box-shadow:0 0 60px rgba({acc_rgb},0.09);">
        <div style="height:6px;background:linear-gradient(90deg,{accent},#FF3D8A);"></div>
        <div style="padding:32px;">
            <div style="display:flex;align-items:center;gap:28px;flex-wrap:wrap;">
                <div style="width:96px;height:96px;border-radius:50%;flex-shrink:0;
                            background:linear-gradient(135deg,{accent},#FF3D8A);
                            display:flex;align-items:center;justify-content:center;
                            box-shadow:0 0 30px rgba({acc_rgb},0.25);
                            font-family:'Bebas Neue';font-size:3rem;color:#0A0A0F;">
                    {current_user[0].upper()}
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-family:'Bebas Neue';font-size:2.8rem;
                                letter-spacing:0.06em;color:#F0F0F0;line-height:0.95;margin-bottom:8px;">
                        {current_user.upper()}
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">{profile_tags}</div>
                    {bio_html}
                </div>
                <div style="display:flex;flex-direction:column;gap:10px;flex-shrink:0;">
                    <div style="text-align:center;background:#0A0A0F;border-radius:12px;
                                padding:14px 20px;border:1px solid #1E1E2E;">
                        <div style="font-family:'JetBrains Mono';font-size:2rem;color:{accent};line-height:1;">
                            #{my_rank}</div>
                        <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.12em;
                                    text-transform:uppercase;color:#555566;margin-top:4px;">Team rank</div>
                    </div>
                    <div style="text-align:center;background:#0A0A0F;border-radius:12px;
                                padding:14px 20px;border:1px solid #1E1E2E;">
                        <div style="font-family:'JetBrains Mono';font-size:2rem;color:#FF3D8A;line-height:1;">
                            {best['total']:.2f}s</div>
                        <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.12em;
                                    text-transform:uppercase;color:#555566;margin-top:4px;">Personal best</div>
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
    impr_color = '#1DDB8B' if improvement_p < 0 else '#FF4D6A'
    summary_items = [
        ('Runs logged',   str(total_runs_p),          '',   '#89C4E1'),
        ('Days active',   str(days_active_p),          '',   '#B39DDB'),
        ('Avg total',     f'{avg_total_p:.2f}',        's',  '#8A8A9A'),
        ('Personal best', f'{best_total_p:.2f}',       's',  '#FF3D8A'),
        ('Season delta',  f'{improvement_p:+.3f}',     's',  impr_color),
        ('Consistency',   f'{consistency_p:.0f}',      '%',  '#FFD700'),
    ]
    border_style = 'border-right:1px solid #1E1E2E;'
    items_html = ''.join([f"""
    <div style="flex:1;text-align:center;padding:14px 8px;{border_style if i < len(summary_items)-1 else ''}">
        <div style="font-family:'JetBrains Mono';font-size:1.4rem;color:{color};line-height:1;">
            {val}<span style="font-size:0.8rem;color:#555566;">{unit}</span>
        </div>
        <div style="font-family:'DM Sans';font-size:0.58rem;letter-spacing:0.1em;
                    text-transform:uppercase;color:#555566;margin-top:5px;">{label}</div>
    </div>""" for i, (label, val, unit, color) in enumerate(summary_items)])
    st.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:12px;
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
            ('0–10m goal',      float(profile.get('goal_0_10')  or 0), float(athlete_data['split_0_10'].min()),  '#89C4E1', '137,196,225'),
            ('10–30m goal',     float(profile.get('goal_10_30') or 0), float(athlete_data['split_10_30'].min()), '#B39DDB', '179,157,219'),
            ('30–60m goal',     float(profile.get('goal_30_60') or 0), float(athlete_data['split_30_60'].min()), '#FF3D8A', '255,61,138'),
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
            <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:12px;
                        padding:16px 20px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <span style="font-family:'DM Sans';font-size:0.75rem;letter-spacing:0.08em;
                                 text-transform:uppercase;color:#8A8A9A;">{label}</span>
                    <span style="font-family:'JetBrains Mono';font-size:0.78rem;color:{status_color};">{status_text}</span>
                </div>
                <div style="background:#0A0A0F;border-radius:999px;height:6px;overflow:hidden;">
                    <div style="height:100%;width:{min(100,progress):.0f}%;
                                background:{color};border-radius:999px;
                                box-shadow:0 0 8px {bar_shadow};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#12121A;border:1px solid #1E1E2E;border-left:3px solid #2A2A3E;
                    border-radius:0 10px 10px 0;padding:14px 16px;margin-bottom:16px;">
            <div style="font-family:'DM Sans';font-size:0.8rem;color:#2A2A3E;">
                No season goals set — add targets in Edit Profile to track progress here.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Personal records board — 2x2 grid + top speed full-width ──
    section_header("PERSONAL RECORDS", accent='pink')
    pr_splits = [
        ('⚡', '0–10m',  athlete_data['split_0_10'].min(),  '1st 10 meters — reaction + first step',  '#89C4E1'),
        ('🔥', '10–30m', athlete_data['split_10_30'].min(), 'Drive phase — peak acceleration window', '#B39DDB'),
        ('💨', '30–60m', athlete_data['split_30_60'].min(), 'Max velocity — highest speed window',    '#FF3D8A'),
        ('🏁', 'Total',  athlete_data['total'].min(),        '60m combined — full sprint',             '#F0F0F0'),
    ]
    pc1, pc2 = st.columns(2)
    for i, (icon, label, val, desc, lcolor) in enumerate(pr_splits):
        col = pc1 if i % 2 == 0 else pc2
        col.markdown(f"""
        <div style="background:#12121A;border:1px solid #1E1E2E;border-left:3px solid {lcolor};
                    border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:8px;
                    display:flex;align-items:center;gap:14px;transition:transform 0.2s ease;"
             onmouseover="this.style.transform='translateX(4px)'"
             onmouseout="this.style.transform='translateX(0)'">
            <span style="font-size:1.4rem;">{icon}</span>
            <div style="flex:1;">
                <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#555566;">{label}</div>
                <div style="font-family:'DM Sans';font-size:0.7rem;color:#2A2A3E;margin-top:1px;">{desc}</div>
            </div>
            <div style="font-family:'JetBrains Mono';font-size:1.5rem;color:#F0F0F0;flex-shrink:0;">{val:.3f}s</div>
        </div>
        """, unsafe_allow_html=True)
    top_spd = athlete_data['top_speed'].max()
    st.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;border-left:3px solid #FFD700;
                border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:8px;
                display:flex;align-items:center;gap:14px;">
        <span style="font-size:1.4rem;">🚀</span>
        <div style="flex:1;">
            <div style="font-family:'DM Sans';font-size:0.62rem;letter-spacing:0.1em;
                        text-transform:uppercase;color:#555566;">Top speed</div>
            <div style="font-family:'DM Sans';font-size:0.7rem;color:#2A2A3E;margin-top:1px;">
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
    <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:14px;
                padding:20px 24px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:16px;">
            <div style="font-family:'JetBrains Mono';font-size:2.4rem;color:#F0F0F0;">{total_time_br:.3f}s</div>
            <div style="font-family:'DM Sans';font-size:0.7rem;color:#555566;">{br_date_str}</div>
        </div>
        <div style="display:flex;border-radius:6px;overflow:hidden;height:10px;margin-bottom:16px;gap:2px;">
            <div style="width:{pct_0_10_br:.1f}%;background:#89C4E1;border-radius:4px;"></div>
            <div style="width:{pct_10_30_br:.1f}%;background:#B39DDB;border-radius:4px;"></div>
            <div style="width:{pct_30_60_br:.1f}%;background:#FF3D8A;border-radius:4px;"></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
            <div style="text-align:center;">
                <div style="font-family:'JetBrains Mono';font-size:1.3rem;color:#89C4E1;">{float(best_run['split_0_10']):.3f}s</div>
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#555566;margin-top:3px;">0–10m · {pct_0_10_br:.0f}%</div>
            </div>
            <div style="text-align:center;border-left:1px solid #1E1E2E;border-right:1px solid #1E1E2E;">
                <div style="font-family:'JetBrains Mono';font-size:1.3rem;color:#B39DDB;">{float(best_run['split_10_30']):.3f}s</div>
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#555566;margin-top:3px;">10–30m · {pct_10_30_br:.0f}%</div>
            </div>
            <div style="text-align:center;">
                <div style="font-family:'JetBrains Mono';font-size:1.3rem;color:#FF3D8A;">{float(best_run['split_30_60']):.3f}s</div>
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;color:#555566;margin-top:3px;">30–60m · {pct_30_60_br:.0f}%</div>
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
            <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:10px;
                        padding:14px 16px;margin-bottom:8px;
                        animation:scaleIn 0.3s ease {0.04*i:.2f}s both;">
                <div style="font-family:'DM Sans';font-size:0.6rem;letter-spacing:0.14em;
                            text-transform:uppercase;color:#2A2A3E;margin-bottom:6px;">{label}</div>
                <div style="font-family:'DM Sans';font-size:0.9rem;color:#F0F0F0;">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Edit profile form ──
    section_header("EDIT MY PROFILE", accent='pink')
    with st.expander("✏️  Update profile information", expanded=False):
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Bebas Neue\';font-size:1rem;letter-spacing:0.1em;color:#555566;margin-bottom:12px;">IDENTITY</div>', unsafe_allow_html=True)
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

        st.markdown('<div style="font-family:\'Bebas Neue\';font-size:1rem;letter-spacing:0.1em;color:#555566;margin:16px 0 12px;">SEASON GOALS</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'DM Sans\';font-size:0.75rem;color:#555566;margin-bottom:12px;">Set target times — progress bars track how close you are</div>', unsafe_allow_html=True)
        cg1, cg2, cg3, cg4 = st.columns(4)
        goal_total = cg1.number_input("Total goal (s)", 0.0, 15.0, float(profile.get('goal_total') or 0.0), step=0.01, format="%.3f")
        goal_0_10  = cg2.number_input("0–10m goal (s)",  0.0, 5.0,  float(profile.get('goal_0_10')  or 0.0), step=0.001, format="%.3f")
        goal_10_30 = cg3.number_input("10–30m goal (s)", 0.0, 5.0,  float(profile.get('goal_10_30') or 0.0), step=0.001, format="%.3f")
        goal_30_60 = cg4.number_input("30–60m goal (s)", 0.0, 5.0,  float(profile.get('goal_30_60') or 0.0), step=0.001, format="%.3f")

        st.markdown('<div style="font-family:\'Bebas Neue\';font-size:1rem;letter-spacing:0.1em;color:#555566;margin:16px 0 12px;">PROFILE COLOR</div>', unsafe_allow_html=True)
        color_options = {
            'Powder Blue': '#89C4E1', 'Hot Pink': '#FF3D8A', 'Lavender': '#B39DDB',
            'Mint': '#1DDB8B', 'Gold': '#FFD700', 'Coral': '#FF6B6B',
        }
        selected_color = profile.get('profile_color','#89C4E1') or '#89C4E1'
        cc = st.columns(len(color_options))
        for i, (cname, cval) in enumerate(color_options.items()):
            is_active = selected_color == cval
            cc[i].markdown(f"""
            <div style="background:{cval}22;border:2px solid {'#F0F0F0' if is_active else cval+'55'};
                        border-radius:8px;padding:8px 4px;text-align:center;cursor:pointer;
                        transition:all 0.2s ease;">
                <div style="width:20px;height:20px;border-radius:50%;background:{cval};
                            margin:0 auto 6px;{'box-shadow:0 0 10px '+cval if is_active else ''}"></div>
                <div style="font-family:'DM Sans';font-size:0.6rem;color:{cval};letter-spacing:0.06em;">
                    {cname.split()[0].upper()}</div>
            </div>""", unsafe_allow_html=True)
            if cc[i].button("●", key=f"color_{cname}", use_container_width=True):
                selected_color = cval

        if st.button("💾  SAVE MY PROFILE", use_container_width=True):
            save_athlete_profile(current_user, school, events, age, height, weight, bio,
                                  hometown=hometown, coach=coach, grad_year=grad_year,
                                  position=position, goal_total=goal_total,
                                  goal_0_10=goal_0_10, goal_10_30=goal_10_30,
                                  goal_30_60=goal_30_60, profile_color=selected_color)
            st.success("Profile saved.")
            st.rerun()

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY PROGRESS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "MY PROGRESS":
    page_header("MY PROGRESS", f"{current_user.lower()}'s season arc", "📈", "pink")
    df_p = load_athlete_runs(current_user)
    if df_p.empty:
        empty_state("🏃", "NO RUNS YET")
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
            <div style="background:#12121A;border:1px solid #1DDB8B44;border-left:3px solid #1DDB8B;
                        border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;color:#1DDB8B;">
                    -{delta:.3f}s</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#555566;margin-top:4px;">
                    Time improved (first 5 vs last 5)</div>
            </div>
            <div style="background:#12121A;border:1px solid #89C4E144;border-left:3px solid #89C4E1;
                        border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;color:#89C4E1;">
                    {pct:.1f}%</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#555566;margin-top:4px;">Percentage faster</div>
            </div>
            <div style="background:#12121A;border:1px solid #FF3D8A44;border-left:3px solid #FF3D8A;
                        border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;color:#FF3D8A;">
                    {df_p['top_speed'].max():.1f} mph</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.1em;
                            text-transform:uppercase;color:#555566;margin-top:4px;">Peak top speed</div>
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
        ('0–10m  · Reaction + first step', my_avgs_pa['0–10m'],  field_avgs_pa['0–10m'],  '#89C4E1'),
        ('10–30m · Drive phase',           my_avgs_pa['10–30m'], field_avgs_pa['10–30m'], '#B39DDB'),
        ('30–60m · Max velocity',          my_avgs_pa['30–60m'], field_avgs_pa['30–60m'], '#FF3D8A'),
    ]:
        diff      = my_val - f_val
        diff_pct  = abs(diff / f_val * 100) if f_val else 0
        is_ahead  = diff < -0.005
        is_behind = diff > 0.005
        bar_color = '#1DDB8B' if is_ahead else '#FF4D6A' if is_behind else '#555566'
        status    = f'▲ {diff_pct:.1f}% ahead of field' if is_ahead else f'▼ {diff_pct:.1f}% behind field' if is_behind else 'At field average'
        bar_fill  = min(100, diff_pct * 10)
        phase_html += f"""
        <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:10px;
                    padding:14px 18px;margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-family:'DM Sans';font-size:0.75rem;color:#8A8A9A;">{phase_label}</span>
                <span style="font-family:'JetBrains Mono';font-size:0.75rem;color:{bar_color};">{status}</span>
            </div>
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-family:'JetBrains Mono';font-size:0.85rem;color:#F0F0F0;width:52px;">{my_val:.3f}s</span>
                <div style="flex:1;background:#0A0A0F;border-radius:999px;height:5px;">
                    <div style="height:100%;width:{bar_fill:.0f}%;background:{bar_color};border-radius:999px;max-width:100%;"></div>
                </div>
                <span style="font-family:'JetBrains Mono';font-size:0.72rem;color:#555566;width:52px;text-align:right;">avg {f_val:.3f}s</span>
            </div>
        </div>"""
    st.markdown(phase_html, unsafe_allow_html=True)

    section_header("PERSONAL BEST TIMELINE", accent='pink')
    df_p['running_pb'] = df_p['total'].expanding().min()
    pb_runs = df_p[df_p['total'] == df_p['running_pb']]
    fig_pb = go.Figure()
    fig_pb.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['total'],
        mode='lines+markers', name='Run time',
        line=dict(color='#1E1E2E', width=1), marker=dict(size=4, color='#2A2A3E')))
    fig_pb.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['running_pb'],
        mode='lines', name='Personal best',
        line=dict(color='#FF3D8A', width=2.5, shape='hv'),
        fill='tozeroy', fillcolor='rgba(255,61,138,0.03)'))
    fig_pb.add_trace(go.Scatter(x=pb_runs['run_num'], y=pb_runs['total'],
        mode='markers+text', name='New PB',
        marker=dict(size=12, color='#FFD700', symbol='star', line=dict(color='#0A0A0F', width=1)),
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
        name='Individual runs', marker=dict(color='#1E1E2E', size=6, line=dict(color='#89C4E1', width=1.5))))
    fig.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['rolling_avg'], mode='lines',
        name='5-run avg', line=dict(color='#89C4E1', width=2.5)))
    fig.add_trace(go.Scatter(x=df_p['run_num'], y=df_p['running_pb'],
        mode='lines', name='Personal best', line=dict(color='#FF3D8A', width=1.5, dash='dot')))
    style_chart(fig, height=320)
    fig.update_layout(yaxis=dict(range=smart_yrange(df_p['total'])))
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT TRENDS", accent='pink')
    fig2 = go.Figure()
    for col, label, color in [
        ('split_0_10','0–10m','#89C4E1'),('split_10_30','10–30m','#B39DDB'),
        ('split_30_60','30–60m','#FF3D8A'),
    ]:
        fig2.add_trace(go.Scatter(x=df_p['run_num'], y=df_p[col], mode='lines+markers',
            name=label, line=dict(color=color, width=2), marker=dict(size=4)))
    style_chart(fig2, height=300)
    y_min = min(df_p['split_0_10'].min(), df_p['split_10_30'].min(), df_p['split_30_60'].min()) * 0.97
    y_max = df_p['split_30_60'].max() * 1.03
    fig2.update_layout(yaxis=dict(range=[y_min, y_max]))
    for col, label, color in [
        ('split_0_10','0–10m','#89C4E1'),('split_10_30','10–30m','#B39DDB'),
        ('split_30_60','30–60m','#FF3D8A'),
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
        marker=dict(color='#89C4E1', line=dict(width=0)),
        text=weekly_counts['runs'], textposition='outside',
        textfont=dict(family='JetBrains Mono', size=10, color='#8A8A9A'),
        cliponaxis=False,
    ))
    style_chart(fig_wk, height=220)
    fig_wk.update_layout(
        yaxis=dict(visible=False),
        xaxis=dict(tickfont=dict(family='DM Sans', size=11, color='#555566')),
        bargap=0.3,
    )
    st.plotly_chart(fig_wk, use_container_width=True, config=CHART_CFG)

    section_header("TOP 5 RUNS", accent='blue')
    top5 = df_p.nsmallest(5, 'total').reset_index(drop=True)
    t5_rows = ''
    for i, row in top5.iterrows():
        t5_rows += f"""
        <tr style="border-bottom:1px solid #1A1A26;">
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#FFD700;font-size:0.8rem;">#{i+1}</td>
            <td style="padding:10px 14px;font-family:DM Sans;color:#555566;font-size:0.75rem;">{str(row['date'])[:10]}</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#89C4E1;font-size:0.82rem;">{float(row['split_0_10']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#B39DDB;font-size:0.82rem;">{float(row['split_10_30']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#FF3D8A;font-size:0.82rem;">{float(row['split_30_60']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#F0F0F0;font-size:0.9rem;font-weight:500;">{float(row['total']):.3f}s</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:#555566;font-size:0.78rem;">{float(row['top_speed']):.1f} mph</td>
        </tr>"""
    th5 = "padding:10px 14px;font-family:DM Sans;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#2A2A3E;text-align:left;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E2E;border-radius:12px;overflow:hidden;margin-bottom:16px;">
        <table style="width:100%;border-collapse:collapse;background:#12121A;">
            <thead>
                <tr style="background:#0D0D14;border-bottom:2px solid #1E1E2E;">
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
        pb_badge = '<span style="font-family:DM Sans;font-size:0.6rem;background:#FF3D8A22;color:#FF3D8A;border:1px solid #FF3D8A44;border-radius:999px;padding:2px 7px;margin-left:8px;">PB</span>' if row['total'] == pb else ''
        rows += f"""<tr style="border-bottom:1px solid #1A1A26;">
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#555566;font-size:0.8rem;">#{int(row['run_num'])}</td>
            <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#555566;font-size:0.78rem;">{str(row['date'])[:10]}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#89C4E1;font-size:0.82rem;">{row['split_0_10']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#B39DDB;font-size:0.82rem;">{row['split_10_30']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#FF3D8A;font-size:0.82rem;">{row['split_30_60']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#F0F0F0;font-size:0.9rem;font-weight:500;">{row['total']:.3f}s{pb_badge}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#555566;font-size:0.8rem;">{row['top_speed']:.1f}</td>
        </tr>"""
    th = "padding:10px 14px;font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#2A2A3E;text-align:left;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E2E;border-radius:12px;overflow:hidden;">
        <table style="width:100%;border-collapse:collapse;background:#12121A;">
            <thead><tr style="background:#0D0D14;border-bottom:2px solid #1E1E2E;">
                <th style="{th}">#</th><th style="{th}">Date</th>
                <th style="{th}">0–10m</th><th style="{th}">10–30m</th>
                <th style="{th}">30–60m</th><th style="{th}">Total</th><th style="{th}">Speed</th>
            </tr></thead><tbody>{rows}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)
    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COMPARE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "COMPARE":
    page_header("HEAD TO HEAD", "measure yourself against the field", "⚔️", "blue")
    all_ath = get_all_athletes()
    if len(all_ath) < 2:
        empty_state("⚔️", "NEED AT LEAST 2 ATHLETES", "Add more athletes in Settings.")
        render_footer()
        st.stop()

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
    wc = '#89C4E1' if overall_winner == athlete_a else '#FF3D8A' if overall_winner == athlete_b else '#555566'

    # Overall winner card
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#12121A,#1A1A26);border:1px solid {wc};
                border-radius:14px;padding:20px 24px;margin:12px 0 20px;text-align:center;">
        <div style="font-family:'DM Sans';font-size:0.65rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#555566;margin-bottom:8px;">Overall winner</div>
        <div style="font-family:'Bebas Neue';font-size:2.4rem;letter-spacing:0.08em;color:{wc};">
            {'TIE' if not overall_winner else overall_winner.upper()}</div>
        <div style="font-family:'JetBrains Mono';font-size:0.8rem;color:#555566;margin-top:4px;">
            {wins_a} vs {wins_b} categories</div>
    </div>""", unsafe_allow_html=True)

    # Athlete name headers
    h_l, h_mid, h_r = st.columns([2, 1, 2])
    h_l.markdown(f"""
    <div style="text-align:center;padding:12px;background:#12121A;
                border:1px solid #89C4E1;border-radius:10px;margin-bottom:8px;">
        <div style="font-family:'Bebas Neue';font-size:1.4rem;letter-spacing:0.08em;color:#89C4E1;">
            {athlete_a.upper()}</div>
    </div>""", unsafe_allow_html=True)
    h_r.markdown(f"""
    <div style="text-align:center;padding:12px;background:#12121A;
                border:1px solid #FF3D8A;border-radius:10px;margin-bottom:8px;">
        <div style="font-family:'Bebas Neue';font-size:1.4rem;letter-spacing:0.08em;color:#FF3D8A;">
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

        ca     = '#F0F0F0' if wa else '#2A2A3E'
        cb     = '#F0F0F0' if wb else '#2A2A3E'
        a_bg   = '#12121A' if wa else '#0D0D14'
        b_bg   = '#12121A' if wb else '#0D0D14'
        a_tick = '<span style="font-size:0.7rem;margin-left:6px;color:#1DDB8B;">✓</span>' if wa else ''
        b_tick = '<span style="font-size:0.7rem;margin-left:6px;color:#1DDB8B;">✓</span>' if wb else ''

        l, mid, r = st.columns([2, 1, 2])
        l.markdown(f"""
        <div style="background:{a_bg};border:1px solid #1E1E2E;border-radius:8px;
                    padding:12px 16px;text-align:right;margin-bottom:6px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:1.2rem;color:{ca};">
                {fmt.format(va)}{a_tick}</span>
        </div>""", unsafe_allow_html=True)
        mid.markdown(f"""
        <div style="padding:12px 0;text-align:center;margin-bottom:6px;">
            <div style="font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.12em;
                        text-transform:uppercase;color:#2A2A3E;margin-top:8px;">{label}</div>
        </div>""", unsafe_allow_html=True)
        r.markdown(f"""
        <div style="background:{b_bg};border:1px solid #1E1E2E;border-radius:8px;
                    padding:12px 16px;text-align:left;margin-bottom:6px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:1.2rem;color:{cb};">
                {b_tick}{fmt.format(vb)}</span>
        </div>""", unsafe_allow_html=True)

    section_header("TOTAL TIME — SEASON OVERLAP", accent='blue')
    fig = go.Figure()
    for df_x, name, color in [(da,athlete_a,'#89C4E1'),(db_,athlete_b,'#FF3D8A')]:
        df_s = df_x[::-1].reset_index(drop=True)
        df_s['run_num'] = range(1, len(df_s)+1)
        fig.add_trace(go.Scatter(x=df_s['run_num'], y=df_s['total'],
            mode='lines+markers', name=name,
            line=dict(color=color, width=2), marker=dict(size=5)))
    style_chart(fig, height=320)
    combined = pd.concat([da['total'], db_['total']])
    fig.update_layout(yaxis=dict(range=smart_yrange(combined)))
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT PROFILE OVERLAY", accent='pink')
    cats = ['0–10m', '10–30m', '30–60m']
    fig2 = go.Figure()
    for df_x, name, color, fc in [
        (da,athlete_a,'#89C4E1','rgba(137,196,225,0.1)'),
        (db_,athlete_b,'#FF3D8A','rgba(255,61,138,0.1)'),
    ]:
        v = [df_x['split_0_10'].mean(), df_x['split_10_30'].mean(), df_x['split_30_60'].mean()]
        fig2.add_trace(go.Scatterpolar(r=v+[v[0]], theta=cats+[cats[0]],
            fill='toself', name=name, line=dict(color=color, width=2), fillcolor=fc))
    fig2.update_layout(
        polar=dict(bgcolor='#12121A',
            radialaxis=dict(showticklabels=False, gridcolor='#1E1E2E'),
            angularaxis=dict(gridcolor='#1E1E2E', tickfont=dict(color='#8A8A9A', family='DM Sans'))),
        paper_bgcolor='#12121A', height=320,
        legend=dict(bgcolor='#0A0A0F', bordercolor='#1E1E2E', borderwidth=1,
                    font=dict(color='#8A8A9A', family='DM Sans')),
        margin=dict(l=40,r=40,t=40,b=40))
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT DELTA BREAKDOWN", accent='blue')
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
        dcol   = '#1DDB8B' if (delta < 0 and not is_speed) or (delta > 0 and is_speed) else '#FF4D6A'
        unit_s = ' mph' if is_speed else 's'
        delta_rows += f"""
        <tr style="border-bottom:1px solid #1A1A26;">
            <td style="padding:10px 14px;font-family:DM Sans;color:#8A8A9A;font-size:0.8rem;">{label}</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:{'#89C4E1' if a_wins else '#555566'};font-size:0.85rem;text-align:right;">{val_a:.3f}{unit_s}</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:{dcol};font-size:0.82rem;text-align:center;">{sign}{delta:.3f}{'s' if not is_speed else ''}</td>
            <td style="padding:10px 14px;font-family:JetBrains Mono;color:{'#FF3D8A' if not a_wins else '#555566'};font-size:0.85rem;text-align:left;">{val_b:.3f}{unit_s}</td>
        </tr>"""
    th_d = "padding:10px 14px;font-family:DM Sans;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#2A2A3E;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E2E;border-radius:12px;overflow:hidden;margin-bottom:16px;">
        <table style="width:100%;border-collapse:collapse;background:#12121A;">
            <thead>
                <tr style="background:#0D0D14;border-bottom:2px solid #1E1E2E;">
                    <th style="{th_d};text-align:left;">Split</th>
                    <th style="{th_d};text-align:right;color:#89C4E1;">{athlete_a}</th>
                    <th style="{th_d};text-align:center;">Δ</th>
                    <th style="{th_d};text-align:left;color:#FF3D8A;">{athlete_b}</th>
                </tr>
            </thead>
            <tbody>{delta_rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "SETTINGS":
    page_header("SETTINGS", "manage athletes and sessions", "⚙️", "pink")

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
        rows = ''.join(f"""<tr style="border-bottom:1px solid #1A1A26;">
            <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#F0F0F0;font-size:0.85rem;">{row['name']}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#89C4E1;font-size:0.82rem;">{row['runs']}</td>
            <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#FF3D8A;font-size:0.82rem;">{row['best']:.3f}s</td>
            <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#555566;font-size:0.78rem;">{str(row['last_run'])[:10]}</td>
        </tr>""" for _, row in athletes_df.iterrows())
        th = "padding:10px 14px;font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#2A2A3E;text-align:left;font-weight:500;"
        st.markdown(f"""
        <div style="border:1px solid #1E1E2E;border-radius:12px;overflow:hidden;">
            <table style="width:100%;border-collapse:collapse;background:#12121A;">
                <thead><tr style="background:#0D0D14;border-bottom:2px solid #1E1E2E;">
                    <th style="{th}">Athlete</th><th style="{th}">Runs</th>
                    <th style="{th}">Best Total</th><th style="{th}">Last Run</th>
                </tr></thead><tbody>{rows}</tbody>
            </table>
        </div>""", unsafe_allow_html=True)
    else:
        empty_state("👥", "NO ATHLETES YET", "Use the form above to add your first athlete.")

    section_header("IMPORT RUNS FROM CSV", accent='blue')
    st.markdown("""
    <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:10px;
                padding:16px 18px;margin-bottom:12px;">
        <div style="font-family:'DM Sans';font-size:0.75rem;color:#8A8A9A;margin-bottom:8px;line-height:1.6;">
            Upload a CSV with columns:
            <span style="font-family:JetBrains Mono;color:#89C4E1;font-size:0.72rem;">
                athlete, date, split_0_10, split_10_30, split_30_60
            </span>
            — total and top_speed will be auto-calculated.
        </div>
    </div>
    """, unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload CSV", type=['csv'], label_visibility="collapsed")
    if uploaded is not None:
        import io as _io
        df_import = pd.read_csv(_io.BytesIO(uploaded.read()))
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
                import sqlite3 as _sq
                conn_imp = _sq.connect(DB)
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
    with st.expander("⚠️  Delete athlete data", expanded=False):
        del_athletes_list = get_all_athletes()
        if del_athletes_list:
            del_athlete = st.selectbox("Select athlete to clear runs", del_athletes_list, key="del_select")
            st.markdown(f"""
            <div style="background:#1A0D0D;border:1px solid rgba(255,77,106,0.27);border-radius:8px;
                        padding:12px 16px;margin-bottom:12px;">
                <span style="font-family:DM Sans;font-size:0.78rem;color:#FF4D6A;">
                    ⚠️ This will permanently delete all runs for {del_athlete}. This cannot be undone.
                </span>
            </div>
            """, unsafe_allow_html=True)
            del_confirm = st.text_input("Type DELETE to confirm", key="del_confirm")
            if st.button("DELETE RUNS", use_container_width=True) and del_confirm == "DELETE":
                import sqlite3 as _sq2
                conn_del = _sq2.connect(DB)
                conn_del.execute("DELETE FROM runs WHERE athlete=?", (del_athlete,))
                conn_del.commit(); conn_del.close()
                st.cache_data.clear()
                st.success(f"All runs deleted for {del_athlete}.")
                st.rerun()
        else:
            st.markdown('<div style="color:#555566;font-size:0.8rem;">No athletes yet.</div>', unsafe_allow_html=True)

    render_footer()
    st.stop()
