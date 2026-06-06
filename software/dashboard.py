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

_here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(_here, '..', 'data'), exist_ok=True)


def _bootstrap():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, athlete TEXT,
        split_0_10 REAL, split_10_30 REAL,
        split_30_60 REAL, total REAL, top_speed REAL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS athletes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT UNIQUE,
        jersey      TEXT,
        position    TEXT,
        age         INTEGER,
        height      TEXT,
        weight      TEXT,
        school      TEXT,
        events      TEXT,
        bio         TEXT,
        created_at  TEXT
    )''')
    conn.commit()
    if conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0:
        base = datetime.datetime.now() - datetime.timedelta(days=30)
        for name, b1, b2, b3 in [
            ("Franklin", 1.92, 2.48, 3.20), ("Marcus",  1.88, 2.42, 3.12),
            ("Jordan",   1.95, 2.55, 3.30), ("Darius",  1.90, 2.46, 3.18),
            ("Tyler",    1.97, 2.58, 3.35), ("Zion",    1.86, 2.39, 3.08),
            ("Cameron",  1.93, 2.50, 3.22), ("Elijah",  1.89, 2.44, 3.15),
        ]:
            for i in range(20):
                imp = i * 0.003
                fat = random.uniform(-0.02, 0.04)
                s1, s2, s3 = round(b1-imp+fat, 3), round(b2-imp+fat, 3), round(b3-imp+fat, 3)
                total = round(s1+s2+s3, 3)
                conn.execute(
                    'INSERT INTO runs (date,athlete,split_0_10,split_10_30,split_30_60,total,top_speed) VALUES (?,?,?,?,?,?,?)',
                    ((base + datetime.timedelta(days=i*1.5)).isoformat(),
                     name, s1, s2, s3, total, round(30/s3*2.237, 2))
                )
        conn.commit()
    conn.close()


_bootstrap()

COLORS = {
    'bg': '#0A0A0F', 'surface': '#12121A', 'surface2': '#1A1A26',
    'border': '#1E1E2E', 'border_light': '#2A2A3E',
    'blue': '#89C4E1', 'blue_dim': '#5A9AB8',
    'pink': '#FF3D8A', 'pink_dim': '#CC2E6E',
    'lavender': '#B39DDB', 'white': '#F0F0F0',
    'gray': '#8A8A9A', 'gray_dim': '#555566',
    'green': '#1DDB8B', 'red': '#FF4D6A',
}
SPLIT_COLORS = [COLORS['blue'], COLORS['lavender'], COLORS['pink']]
SCALE = [[0, COLORS['blue']], [0.5, COLORS['lavender']], [1.0, COLORS['pink']]]
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

[data-testid="stHeader"] {
    background: #0A0A0F !important;
    height: 0px !important; min-height: 0px !important;
    visibility: hidden !important;
}
[data-testid="stDecoration"] { display: none !important; height: 0 !important; }
[data-testid="stAppViewContainer"] > section:first-child { padding-top: 0 !important; }

html, body, #root, [data-testid="stApp"],
[data-testid="stAppViewContainer"], .main {
    background-color: #0A0A0F !important;
}
[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {
    background-color: #0A0A0F !important;
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
}

[data-testid="stSidebar"] {
    background: #0D0D14 !important;
    border-right: 1px solid #1E1E2E !important;
    min-width: 240px !important;
    max-width: 280px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 20px 16px !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label {
    color: #8A8A9A !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #F0F0F0 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    margin-bottom: 4px !important;
    display: block !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #8A8A9A !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    border-color: #89C4E1 !important;
    color: #89C4E1 !important;
}

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
[data-testid="stTextInput"] input:focus {
    border-bottom-color: #FF3D8A !important;
    box-shadow: none !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label,
[data-testid="stDateInput"] label {
    font-size: 0.7rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #555566 !important;
    font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stSelectbox"] > div > div {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    color: #F0F0F0 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stNumberInput"] input {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    color: #F0F0F0 !important;
    font-family: 'JetBrains Mono', monospace !important;
}
[data-testid="stTextArea"] textarea {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    color: #F0F0F0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stPlotlyChart"] > div {
    background: #12121A !important;
    border-radius: 10px !important;
    padding: 8px !important;
    border: 1px solid #1E1E2E !important;
}

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

[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #89C4E1, #FF3D8A) !important;
    border: none !important;
    color: #0A0A0F !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    padding: 10px 20px !important;
}

[data-testid="stAlert"] {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    border-left: 3px solid #1DDB8B !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.78rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #555566 !important;
}

[data-testid="stVerticalBlock"] > div { gap: 0.4rem !important; }
.element-container { margin-bottom: 0.2rem !important; }
[data-testid="stHorizontalBlock"] { gap: 1rem !important; }
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, #89C4E1 30%, #FF3D8A 70%, transparent 100%) !important;
    margin: 20px 0 !important;
    opacity: 0.4 !important;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0F; }
::-webkit-scrollbar-thumb { background: #1E1E2E; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #89C4E1; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

@keyframes dp-pulse {
    0%, 100% { opacity:1; box-shadow:0 0 8px rgba(29,219,139,0.8); }
    50%       { opacity:0.4; box-shadow:0 0 4px rgba(29,219,139,0.3); }
}
</style>""", unsafe_allow_html=True)


# ── Chart helper ───────────────────────────────────────────────────────────────
def style_chart(fig, height=360):
    fig.update_layout(
        paper_bgcolor='#12121A', plot_bgcolor='#12121A',
        font=dict(family='DM Sans', color='#8A8A9A', size=12),
        height=height,
        hovermode='x unified',
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


# ── UI components ──────────────────────────────────────────────────────────────
def view_header(title, subtitle=None):
    sub_html = f"""
    <div style="display:flex;align-items:center;gap:10px;margin-top:6px;">
        <div style="width:6px;height:6px;border-radius:50%;background:#1DDB8B;
                    box-shadow:0 0 8px rgba(29,219,139,0.8);
                    animation:dp-pulse 2s infinite;flex-shrink:0;"></div>
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;
                     letter-spacing:0.14em;text-transform:uppercase;
                     color:#555566;">{subtitle}</span>
    </div>""" if subtitle else ''
    st.markdown(f"""
    <div style="padding:20px 0 16px;border-bottom:1px solid #1E1E2E;margin-bottom:24px;
                display:flex;align-items:flex-end;justify-content:space-between;">
        <div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:3.6rem;
                        letter-spacing:0.06em;line-height:1;
                        background:linear-gradient(135deg,#89C4E1 0%,#B39DDB 50%,#FF3D8A 100%);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;">{title}</div>
            {sub_html}
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                     color:#2A2A3E;padding-bottom:4px;">
            {datetime.datetime.now().strftime('%a %b %d · %H:%M')}
        </span>
    </div>""", unsafe_allow_html=True)


def section_header(label, accent='blue'):
    color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    glow  = 'rgba(137,196,225,0.4)' if accent == 'blue' else 'rgba(255,61,138,0.4)'
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:14px;margin:28px 0 14px;">
        <div style="width:4px;height:24px;background:{color};border-radius:2px;
                    box-shadow:0 0 10px {glow};flex-shrink:0;"></div>
        <span style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;
                     letter-spacing:0.1em;color:#F0F0F0;">{label}</span>
    </div>""", unsafe_allow_html=True)


def metric_card(col, icon, label, value, accent='blue'):
    border_color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    glow = 'rgba(137,196,225,0.08)' if accent == 'blue' else 'rgba(255,61,138,0.08)'
    col.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;
                border-top:3px solid {border_color};border-radius:12px;
                padding:16px 14px;box-shadow:0 0 24px {glow};height:100%;">
        <div style="font-family:'DM Sans',sans-serif;font-size:0.62rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#555566;margin-bottom:6px;">
            {icon}&nbsp; {label}
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.8rem;
                    color:#F0F0F0;line-height:1.1;white-space:nowrap;
                    overflow:hidden;text-overflow:ellipsis;">{value}</div>
    </div>""", unsafe_allow_html=True)


def podium_card(col, rank, name, total, runs, top_speed):
    configs = {
        1: {'border': '#FFD700', 'glow': 'rgba(255,215,0,0.15)',
            'bg': 'linear-gradient(160deg,#1A1600 0%,#12121A 60%)',
            'name_color': '#FFD700', 'medal': '🥇', 'size': '2.6rem',
            'badge': 'FASTEST', 'badge_color': '#FFD700'},
        2: {'border': '#89C4E1', 'glow': 'rgba(137,196,225,0.10)',
            'bg': 'linear-gradient(160deg,#0A1520 0%,#12121A 60%)',
            'name_color': '#89C4E1', 'medal': '🥈', 'size': '2.2rem',
            'badge': '2ND', 'badge_color': '#89C4E1'},
        3: {'border': '#CD7F32', 'glow': 'rgba(205,127,50,0.10)',
            'bg': 'linear-gradient(160deg,#160E00 0%,#12121A 60%)',
            'name_color': '#CD7F32', 'medal': '🥉', 'size': '2.0rem',
            'badge': '3RD', 'badge_color': '#CD7F32'},
    }
    c = configs[rank]
    col.markdown(f"""
    <div style="background:{c['bg']};border:1px solid {c['border']};
                border-top:3px solid {c['border']};border-radius:14px;
                padding:28px 20px 24px;text-align:center;
                box-shadow:0 0 40px {c['glow']};position:relative;min-height:200px;">
        <div style="position:absolute;top:12px;right:14px;
                    font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.16em;
                    text-transform:uppercase;color:{c['badge_color']};
                    background:{c['badge_color']}18;border:1px solid {c['badge_color']}44;
                    border-radius:999px;padding:3px 10px;">{c['badge']}</div>
        <div style="font-size:2.4rem;margin-bottom:8px;">{c['medal']}</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;
                    letter-spacing:0.1em;color:{c['name_color']};margin-bottom:6px;">
            {name.upper()}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:{c['size']};
                    color:#F0F0F0;font-weight:500;line-height:1;margin-bottom:12px;">
            {total:.2f}s</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.75rem;
                    color:#555566;letter-spacing:0.04em;">
            {runs} runs &nbsp;·&nbsp; {top_speed:.1f} mph top speed</div>
    </div>""", unsafe_allow_html=True)


def render_rankings_table(lb_df):
    MEDALS = {1: '🥇', 2: '🥈', 3: '🥉'}
    RANK_COLORS = {1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32'}
    rows = ''
    for _, row in lb_df.iterrows():
        rank = int(row['rank'])
        medal = MEDALS.get(rank, f"#{rank}")
        rc = RANK_COLORS.get(rank, '#555566')
        rows += f"""
        <tr style="border-bottom:1px solid #1A1A26;">
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:{rc};font-size:0.85rem;">{medal}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#F0F0F0;font-size:0.9rem;font-weight:500;">{row['athlete']}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#89C4E1;font-size:0.85rem;">{row['best_total']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#8A8A9A;font-size:0.85rem;">{row['best_0_10']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#8A8A9A;font-size:0.85rem;">{row['best_10_30']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#FF3D8A;font-size:0.85rem;">{row['best_30_60']:.3f}s</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#8A8A9A;font-size:0.85rem;">{row['top_speed']:.1f}</td>
            <td style="padding:12px 16px;font-family:'JetBrains Mono',monospace;color:#555566;font-size:0.85rem;">{row['runs']}</td>
            <td style="padding:12px 16px;font-family:'DM Sans',sans-serif;color:#555566;font-size:0.78rem;">{row['last_run']}</td>
        </tr>"""
    th = "padding:12px 16px;font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.14em;text-transform:uppercase;color:#555566;text-align:left;font-weight:500;"
    st.markdown(f"""
    <div style="border:1px solid #1E1E2E;border-radius:12px;overflow:hidden;margin-top:8px;">
        <table style="width:100%;border-collapse:collapse;background:#12121A;">
            <thead>
                <tr style="border-bottom:2px solid #1E1E2E;background:#0D0D14;">
                    <th style="{th}">Rank</th><th style="{th}">Athlete</th>
                    <th style="{th}">Best Total</th><th style="{th}">0–10m</th>
                    <th style="{th}">10–30m</th><th style="{th}">30–60m</th>
                    <th style="{th}">Top Speed</th><th style="{th}">Runs</th>
                    <th style="{th}">Last Run</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)


def empty_state(message="NO DATA", sub="Log some runs to unlock this analysis."):
    st.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;border-radius:12px;
                padding:60px 40px;text-align:center;margin:16px 0;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2.2rem;
                    letter-spacing:0.06em;color:#1E1E2E;">{message}</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.8rem;
                    color:#555566;margin-top:10px;letter-spacing:0.06em;">{sub}</div>
    </div>""", unsafe_allow_html=True)


def render_footer():
    st.markdown("""
    <div style="margin-top:48px;padding:20px 0;border-top:1px solid #1E1E2E;
                display:flex;justify-content:space-between;align-items:center;">
        <span style="font-family:'Bebas Neue',sans-serif;font-size:1rem;
                     letter-spacing:0.1em;color:#2A2A3E;">DRIVE PHASE</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;
                     color:#555566;letter-spacing:0.08em;">
            built by athletes · powered by data
        </span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                     color:#555566;">v2.0</span>
    </div>""", unsafe_allow_html=True)


def quick_stat(label, value, color):
    return f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                padding:5px 0;border-bottom:1px solid #1A1A26;">
        <span style="font-family:'DM Sans',sans-serif;font-size:0.72rem;color:#555566;">{label}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:{color};">{value}</span>
    </div>"""


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 20px;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;
                    letter-spacing:0.1em;
                    background:linear-gradient(135deg,#89C4E1,#FF3D8A);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;">DRIVE PHASE</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:0.62rem;
                    letter-spacing:0.18em;text-transform:uppercase;
                    color:#555566;margin-top:2px;">acceleration starts here</div>
    </div>
    <div style="height:1px;background:linear-gradient(90deg,#89C4E1,#FF3D8A);
                margin-bottom:20px;opacity:0.3;"></div>
    """, unsafe_allow_html=True)

    page_raw = st.radio("", [
        "🏆  LEADERBOARD",
        "👤  ATHLETE PROFILES",
        "📊  COMPARE",
        "📈  PROGRESS TRACKER",
        "⚙️  SETTINGS",
    ], label_visibility="collapsed")
    page = page_raw.split("  ")[1]

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    if st.button("↺  REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    stats = get_global_stats()
    st.markdown(f"""
    <div style="background:#0A0A0F;border:1px solid #1E1E2E;border-radius:10px;
                padding:14px 16px;">
        <div style="font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#2A2A3E;margin-bottom:10px;">
            Live snapshot
        </div>
        {quick_stat('Athletes', str(stats['athlete_count']), '#89C4E1')}
        {quick_stat('Total runs', str(stats['total_runs']), '#89C4E1')}
        {quick_stat('Fastest ever', f"{stats['fastest_total']:.2f}s", '#FF3D8A')}
        {quick_stat('Top speed', f"{stats['top_speed_ever']:.1f} mph", '#FF3D8A')}
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "LEADERBOARD":
    lb = load_leaderboard()
    view_header("DRIVE PHASE", f"{len(lb)} athletes ranked · auto-updates every 5s")

    if lb.empty:
        empty_state("NO RUNS LOGGED YET", "Get on the track and break some beams.")
        render_footer()
        st.stop()

    section_header("PODIUM", accent='blue')
    top3 = lb.head(3).to_dict('records')
    p1, p2, p3 = st.columns([1.15, 1, 1])
    if len(top3) > 0:
        podium_card(p1, 1, top3[0]['athlete'], top3[0]['best_total'], top3[0]['runs'], top3[0]['top_speed'])
    if len(top3) > 1:
        podium_card(p2, 2, top3[1]['athlete'], top3[1]['best_total'], top3[1]['runs'], top3[1]['top_speed'])
    if len(top3) > 2:
        podium_card(p3, 3, top3[2]['athlete'], top3[2]['best_total'], top3[2]['runs'], top3[2]['top_speed'])

    section_header("FULL RANKINGS", accent='pink')
    render_rankings_table(lb)

    section_header("BEST TOTAL TIME", accent='blue')
    lb_sorted = lb.sort_values('best_total')
    y_min = lb_sorted['best_total'].min() * 0.97
    y_max = lb_sorted['best_total'].max() * 1.04
    fig = go.Figure(go.Bar(
        x=lb_sorted['athlete'],
        y=lb_sorted['best_total'],
        marker=dict(color=lb_sorted['best_total'], colorscale=SCALE, showscale=False,
                    line=dict(color='#0A0A0F', width=1)),
        text=[f"{v:.2f}s" for v in lb_sorted['best_total']],
        textposition='outside',
        textfont=dict(family='JetBrains Mono', size=11, color='#F0F0F0'),
        cliponaxis=False,
    ))
    style_chart(fig, height=320)
    fig.update_layout(
        bargap=0.35,
        yaxis=dict(visible=False, range=[y_min, y_max]),
        xaxis=dict(tickfont=dict(family='DM Sans', size=12, color='#8A8A9A')),
        margin=dict(l=16, r=16, t=48, b=60),
    )
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT BREAKDOWN BY ATHLETE", accent='pink')
    avg_splits = lb[['athlete', 'best_0_10', 'best_10_30', 'best_30_60']].copy()
    fig2 = go.Figure()
    for split, label, color in [
        ('best_30_60', '30–60m', '#FF3D8A'),
        ('best_10_30', '10–30m', '#B39DDB'),
        ('best_0_10',  '0–10m',  '#89C4E1'),
    ]:
        fig2.add_trace(go.Bar(
            y=avg_splits['athlete'],
            x=avg_splits[split],
            name=label,
            orientation='h',
            marker_color=color,
            marker_line=dict(width=0),
        ))
    style_chart(fig2, height=340)
    fig2.update_layout(
        barmode='stack',
        xaxis_title='Time (s)',
        yaxis=dict(autorange='reversed', tickfont=dict(family='DM Sans', size=12, color='#8A8A9A')),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=16, r=16, t=48, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ATHLETE PROFILES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "ATHLETE PROFILES":
    view_header("ATHLETE PROFILES", "individual athlete data and performance history")

    all_athletes = get_all_athletes()
    if not all_athletes:
        empty_state("NO ATHLETES YET", "Add athletes in Settings first.")
        render_footer()
        st.stop()

    selected = st.selectbox("Select athlete", all_athletes, label_visibility="collapsed",
                            key="profile_select")

    athlete_data = load_athlete_runs(selected)
    profile = load_athlete_profile(selected)

    if athlete_data.empty:
        empty_state("NO RUNS FOR THIS ATHLETE", "Log some runs to see their profile.")
        render_footer()
        st.stop()

    best = athlete_data.nsmallest(1, 'total').iloc[0]

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#12121A 0%,#1A1A26 100%);
                border:1px solid #1E1E2E;border-radius:16px;
                padding:28px 32px;margin-bottom:16px;
                display:flex;align-items:center;gap:32px;flex-wrap:wrap;">
        <div style="width:72px;height:72px;border-radius:50%;
                    background:linear-gradient(135deg,#89C4E1,#FF3D8A);
                    display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <span style="font-family:'Bebas Neue',sans-serif;font-size:2.2rem;
                         color:#0A0A0F;">{selected[0].upper()}</span>
        </div>
        <div style="flex:1;min-width:160px;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:2.4rem;
                        letter-spacing:0.08em;color:#F0F0F0;line-height:1;">
                {selected.upper()}</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:0.75rem;
                        color:#555566;margin-top:4px;letter-spacing:0.06em;">
                {profile.get('school','—')} · {profile.get('events','—')} · Age {profile.get('age','—')}
            </div>
        </div>
        <div style="display:flex;gap:32px;flex-wrap:wrap;">
            <div style="text-align:center;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.8rem;
                            color:#89C4E1;">{best['total']:.2f}s</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.62rem;
                            letter-spacing:0.12em;text-transform:uppercase;
                            color:#555566;">Personal Best</div>
            </div>
            <div style="text-align:center;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.8rem;
                            color:#FF3D8A;">{athlete_data['top_speed'].max():.1f}</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.62rem;
                            letter-spacing:0.12em;text-transform:uppercase;
                            color:#555566;">Top Speed mph</div>
            </div>
            <div style="text-align:center;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.8rem;
                            color:#B39DDB;">{len(athlete_data)}</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.62rem;
                            letter-spacing:0.12em;text-transform:uppercase;
                            color:#555566;">Total Runs</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    section_header("SPLIT PERSONAL BESTS", accent='blue')
    s1, s2, s3, s4 = st.columns(4)
    metric_card(s1, '🚀', '0–10m PB',  f"{athlete_data['split_0_10'].min():.3f}s",  accent='blue')
    metric_card(s2, '⚡', '10–30m PB', f"{athlete_data['split_10_30'].min():.3f}s", accent='pink')
    metric_card(s3, '💨', '30–60m PB', f"{athlete_data['split_30_60'].min():.3f}s", accent='blue')
    metric_card(s4, '🏁', 'Total PB',  f"{athlete_data['total'].min():.3f}s",        accent='pink')

    section_header("TOTAL TIME OVER SEASON", accent='blue')
    df_asc = athlete_data[::-1].reset_index(drop=True)
    df_asc['run_num'] = range(1, len(df_asc)+1)
    df_asc['pb_line'] = df_asc['total'].cummin()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_asc['run_num'], y=df_asc['total'],
        mode='lines+markers', name='Run time',
        line=dict(color='#89C4E1', width=2),
        marker=dict(size=5, color='#89C4E1'),
        fill='tozeroy', fillcolor='rgba(137,196,225,0.04)',
    ))
    fig.add_trace(go.Scatter(
        x=df_asc['run_num'], y=df_asc['pb_line'],
        mode='lines', name='Personal best',
        line=dict(color='#FF3D8A', width=1.5, dash='dot'),
    ))
    style_chart(fig, height=300)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT PROFILE vs FIELD AVERAGE", accent='pink')
    all_runs = load_all_runs()
    field_avg = {
        '0-10m':  all_runs['split_0_10'].mean(),
        '10-30m': all_runs['split_10_30'].mean(),
        '30-60m': all_runs['split_30_60'].mean(),
    }
    athlete_avg = {
        '0-10m':  athlete_data['split_0_10'].mean(),
        '10-30m': athlete_data['split_10_30'].mean(),
        '30-60m': athlete_data['split_30_60'].mean(),
    }
    categories = list(field_avg.keys())
    fig2 = go.Figure()
    fig2.add_trace(go.Scatterpolar(
        r=[field_avg[c] for c in categories] + [field_avg[categories[0]]],
        theta=categories + [categories[0]],
        fill='toself', name='Field average',
        line=dict(color='#555566', width=1),
        fillcolor='rgba(85,85,102,0.15)',
    ))
    fig2.add_trace(go.Scatterpolar(
        r=[athlete_avg[c] for c in categories] + [athlete_avg[categories[0]]],
        theta=categories + [categories[0]],
        fill='toself', name=selected,
        line=dict(color='#89C4E1', width=2),
        fillcolor='rgba(137,196,225,0.12)',
    ))
    fig2.update_layout(
        polar=dict(
            bgcolor='#12121A',
            radialaxis=dict(visible=True, showticklabels=False,
                            gridcolor='#1E1E2E', linecolor='#1E1E2E'),
            angularaxis=dict(gridcolor='#1E1E2E', linecolor='#1E1E2E',
                             tickfont=dict(family='DM Sans', color='#8A8A9A')),
        ),
        paper_bgcolor='#12121A', plot_bgcolor='#12121A',
        height=320,
        legend=dict(bgcolor='#0A0A0F', bordercolor='#1E1E2E', borderwidth=1,
                    font=dict(family='DM Sans', color='#8A8A9A')),
        margin=dict(l=40, r=40, t=40, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    section_header("EDIT PROFILE", accent='pink')
    with st.expander("Update athlete information", expanded=False):
        c1, c2 = st.columns(2)
        school = c1.text_input("School / Team", value=str(profile.get('school', '') or ''))
        events = c2.text_input("Events (e.g. 100m, 200m)", value=str(profile.get('events', '') or ''))
        c3, c4, c5 = st.columns(3)
        age    = c3.number_input("Age", min_value=10, max_value=40,
                                  value=int(profile.get('age') or 18))
        height = c4.text_input("Height", value=str(profile.get('height', '') or ''))
        weight = c5.text_input("Weight", value=str(profile.get('weight', '') or ''))
        bio    = st.text_area("Bio / Notes", value=str(profile.get('bio', '') or ''),
                               placeholder="Training notes, goals, injury history...")
        if st.button("SAVE PROFILE", use_container_width=True):
            save_athlete_profile(selected, school, events, age, height, weight, bio)
            st.success("Profile updated.")

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COMPARE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "COMPARE":
    view_header("HEAD TO HEAD", "select two athletes to compare")

    all_athletes = get_all_athletes()
    if len(all_athletes) < 2:
        empty_state("NEED AT LEAST 2 ATHLETES", "Add more athletes in Settings.")
        render_footer()
        st.stop()

    c1, c2 = st.columns(2)
    athlete_a = c1.selectbox("Athlete A", all_athletes, key="compare_a")
    athlete_b = c2.selectbox("Athlete B", all_athletes,
                              index=min(1, len(all_athletes)-1), key="compare_b")

    da = load_athlete_runs(athlete_a)
    db_ = load_athlete_runs(athlete_b)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    metrics = [
        ('Best Total',  'total',       '{:.3f}s', True),
        ('0–10m PB',    'split_0_10',  '{:.3f}s', True),
        ('10–30m PB',   'split_10_30', '{:.3f}s', True),
        ('30–60m PB',   'split_30_60', '{:.3f}s', True),
        ('Top Speed',   'top_speed',   '{:.1f} mph', False),
        ('Runs Logged', None,          '{}',      True),
    ]

    for label, col, fmt, lower_is_better in metrics:
        if col is None:
            val_a, val_b = len(da), len(db_)
            winner_a, winner_b = val_a > val_b, val_b > val_a
        elif lower_is_better:
            val_a, val_b = da[col].min(), db_[col].min()
            winner_a, winner_b = val_a < val_b, val_b < val_a
        else:
            val_a, val_b = da[col].max(), db_[col].max()
            winner_a, winner_b = val_a > val_b, val_b > val_a

        color_a = '#FFD700' if winner_a else '#555566'
        color_b = '#FFD700' if winner_b else '#555566'
        trophy_a = '<span style="margin-left:8px;font-size:0.85rem;">🏆</span>' if winner_a else ''
        trophy_b = '<span style="margin-right:8px;font-size:0.85rem;">🏆</span>' if winner_b else ''

        l, mid, r = st.columns([2, 1, 2])
        l.markdown(f"""
        <div style="text-align:right;padding:10px 16px;background:#12121A;
                    border:1px solid {'#FFD700' if winner_a else '#1E1E2E'};
                    border-radius:10px;margin-bottom:6px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:1.3rem;
                         color:{color_a};">{fmt.format(val_a)}</span>{trophy_a}
        </div>""", unsafe_allow_html=True)
        mid.markdown(f"""
        <div style="text-align:center;padding:14px 0;">
            <div style="font-family:'DM Sans',sans-serif;font-size:0.62rem;letter-spacing:0.12em;
                        text-transform:uppercase;color:#2A2A3E;">{label}</div>
        </div>""", unsafe_allow_html=True)
        r.markdown(f"""
        <div style="text-align:left;padding:10px 16px;background:#12121A;
                    border:1px solid {'#FFD700' if winner_b else '#1E1E2E'};
                    border-radius:10px;margin-bottom:6px;">
            {trophy_b}<span style="font-family:'JetBrains Mono',monospace;font-size:1.3rem;
                         color:{color_b};">{fmt.format(val_b)}</span>
        </div>""", unsafe_allow_html=True)

    section_header("TOTAL TIME — SEASON OVERLAP", accent='blue')
    fig = go.Figure()
    for df_x, name, color in [(da, athlete_a, '#89C4E1'), (db_, athlete_b, '#FF3D8A')]:
        df_s = df_x[::-1].reset_index(drop=True)
        df_s['run_num'] = range(1, len(df_s)+1)
        fig.add_trace(go.Scatter(
            x=df_s['run_num'], y=df_s['total'],
            mode='lines+markers', name=name,
            line=dict(color=color, width=2),
            marker=dict(size=5),
        ))
    style_chart(fig, height=320)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT PROFILE OVERLAY", accent='pink')
    categories = ['0–10m', '10–30m', '30–60m']
    fig2 = go.Figure()
    for df_x, name, color, fill_color in [
        (da,  athlete_a, '#89C4E1', 'rgba(137,196,225,0.1)'),
        (db_, athlete_b, '#FF3D8A', 'rgba(255,61,138,0.1)'),
    ]:
        vals = [df_x['split_0_10'].mean(),
                df_x['split_10_30'].mean(),
                df_x['split_30_60'].mean()]
        fig2.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=categories + [categories[0]],
            fill='toself', name=name,
            line=dict(color=color, width=2),
            fillcolor=fill_color,
        ))
    fig2.update_layout(
        polar=dict(
            bgcolor='#12121A',
            radialaxis=dict(showticklabels=False, gridcolor='#1E1E2E'),
            angularaxis=dict(gridcolor='#1E1E2E',
                             tickfont=dict(color='#8A8A9A', family='DM Sans')),
        ),
        paper_bgcolor='#12121A', height=320,
        legend=dict(bgcolor='#0A0A0F', bordercolor='#1E1E2E', borderwidth=1,
                    font=dict(color='#8A8A9A', family='DM Sans')),
        margin=dict(l=40, r=40, t=40, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROGRESS TRACKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "PROGRESS TRACKER":
    view_header("PROGRESS TRACKER", "personal improvement over the season")

    all_athletes = get_all_athletes()
    if not all_athletes:
        empty_state("NO ATHLETES YET", "Add athletes in Settings first.")
        render_footer()
        st.stop()

    selected = st.selectbox("Select athlete", all_athletes,
                             label_visibility="collapsed", key="progress_select")
    df_p = load_athlete_runs(selected)[::-1].reset_index(drop=True)
    df_p['run_num'] = range(1, len(df_p)+1)

    if len(df_p) >= 5:
        first5 = df_p.head(5)['total'].mean()
        last5  = df_p.tail(5)['total'].mean()
        delta  = first5 - last5
        pct    = (delta / first5) * 100
        st.markdown(f"""
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin:16px 0 24px;">
            <div style="background:#12121A;border:1px solid #1DDB8B44;
                        border-left:3px solid #1DDB8B;border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;
                            color:#1DDB8B;">-{delta:.3f}s</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;
                            letter-spacing:0.1em;text-transform:uppercase;
                            color:#555566;margin-top:4px;">Time improved (first 5 vs last 5)</div>
            </div>
            <div style="background:#12121A;border:1px solid #89C4E144;
                        border-left:3px solid #89C4E1;border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;
                            color:#89C4E1;">{pct:.1f}%</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;
                            letter-spacing:0.1em;text-transform:uppercase;
                            color:#555566;margin-top:4px;">Percentage faster</div>
            </div>
            <div style="background:#12121A;border:1px solid #FF3D8A44;
                        border-left:3px solid #FF3D8A;border-radius:10px;padding:14px 20px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.6rem;
                            color:#FF3D8A;">{df_p['top_speed'].max():.1f} mph</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;
                            letter-spacing:0.1em;text-transform:uppercase;
                            color:#555566;margin-top:4px;">Peak top speed</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    section_header("ROLLING AVERAGE (5-RUN WINDOW)", accent='blue')
    df_p['rolling_avg'] = df_p['total'].rolling(5, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_p['run_num'], y=df_p['total'],
        mode='markers', name='Individual runs',
        marker=dict(color='#1E1E2E', size=6, line=dict(color='#89C4E1', width=1.5)),
    ))
    fig.add_trace(go.Scatter(
        x=df_p['run_num'], y=df_p['rolling_avg'],
        mode='lines', name='5-run average',
        line=dict(color='#89C4E1', width=2.5),
    ))
    fig.add_trace(go.Scatter(
        x=df_p['run_num'], y=df_p['total'].expanding().min(),
        mode='lines', name='Personal best',
        line=dict(color='#FF3D8A', width=1.5, dash='dot'),
    ))
    style_chart(fig, height=320)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CFG)

    section_header("SPLIT TRENDS", accent='pink')
    fig2 = go.Figure()
    for col, label, color in [
        ('split_0_10',  '0–10m',  '#89C4E1'),
        ('split_10_30', '10–30m', '#B39DDB'),
        ('split_30_60', '30–60m', '#FF3D8A'),
    ]:
        fig2.add_trace(go.Scatter(
            x=df_p['run_num'], y=df_p[col],
            mode='lines+markers', name=label,
            line=dict(color=color, width=2),
            marker=dict(size=4),
        ))
    style_chart(fig2, height=300)
    st.plotly_chart(fig2, use_container_width=True, config=CHART_CFG)

    section_header("RECENT RUNS", accent='blue')
    recent = df_p.tail(10)[::-1]
    pb = df_p['total'].min()
    rows = ''
    for _, row in recent.iterrows():
        is_pb = row['total'] == pb
        pb_badge = '<span style="font-family:DM Sans;font-size:0.6rem;background:#FF3D8A22;color:#FF3D8A;border:1px solid #FF3D8A44;border-radius:999px;padding:2px 7px;margin-left:8px;">PB</span>' if is_pb else ''
        rows += f"""
        <tr style="border-bottom:1px solid #1A1A26;">
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
            <thead>
                <tr style="background:#0D0D14;border-bottom:2px solid #1E1E2E;">
                    <th style="{th}">#</th><th style="{th}">Date</th>
                    <th style="{th}">0–10m</th><th style="{th}">10–30m</th>
                    <th style="{th}">30–60m</th><th style="{th}">Total</th>
                    <th style="{th}">Speed</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)

    render_footer()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "SETTINGS":
    view_header("SETTINGS", "manage athletes and data")

    section_header("ADD NEW ATHLETE", accent='blue')
    with st.form("add_athlete"):
        c1, c2 = st.columns(2)
        name   = c1.text_input("Full name")
        school = c2.text_input("School / Team")
        c3, c4, c5 = st.columns(3)
        events = c3.text_input("Events")
        age    = c4.number_input("Age", min_value=10, max_value=40, value=18)
        height = c5.text_input("Height")
        submitted = st.form_submit_button("ADD ATHLETE", use_container_width=True)
        if submitted and name:
            add_athlete_to_db(name, school, events, age, height)
            st.success(f"{name} added to Drive Phase.")
            st.cache_data.clear()

    section_header("LOG A MANUAL RUN", accent='pink')
    with st.form("log_run"):
        c1, c2 = st.columns(2)
        all_athletes = get_all_athletes()
        athlete_name = c1.selectbox("Athlete", all_athletes if all_athletes else ["—"])
        run_date     = c2.date_input("Date")
        c3, c4, c5 = st.columns(3)
        s1 = c3.number_input("0–10m split (s)", min_value=0.0, value=1.85, step=0.001, format="%.3f")
        s2 = c4.number_input("10–30m split (s)", min_value=0.0, value=2.40, step=0.001, format="%.3f")
        s3 = c5.number_input("30–60m split (s)", min_value=0.0, value=3.10, step=0.001, format="%.3f")
        log_submitted = st.form_submit_button("LOG RUN", use_container_width=True)
        if log_submitted and all_athletes:
            total = s1 + s2 + s3
            top_speed = round(30 / s3 * 2.237, 2)
            log_run_to_db(athlete_name, str(run_date), s1, s2, s3, total, top_speed)
            st.success(f"Run logged for {athlete_name} — {total:.3f}s")
            st.cache_data.clear()

    section_header("MANAGE ATHLETES", accent='blue')
    athletes_df = get_all_athletes_with_stats()
    if not athletes_df.empty:
        rows = ''
        for _, row in athletes_df.iterrows():
            rows += f"""
            <tr style="border-bottom:1px solid #1A1A26;">
                <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#F0F0F0;font-size:0.85rem;">{row['name']}</td>
                <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#89C4E1;font-size:0.82rem;">{row['runs']}</td>
                <td style="padding:10px 14px;font-family:'JetBrains Mono',monospace;color:#FF3D8A;font-size:0.82rem;">{row['best']:.3f}s</td>
                <td style="padding:10px 14px;font-family:'DM Sans',sans-serif;color:#555566;font-size:0.78rem;">{str(row['last_run'])[:10]}</td>
            </tr>"""
        th = "padding:10px 14px;font-family:'DM Sans',sans-serif;font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:#2A2A3E;text-align:left;font-weight:500;"
        st.markdown(f"""
        <div style="border:1px solid #1E1E2E;border-radius:12px;overflow:hidden;">
            <table style="width:100%;border-collapse:collapse;background:#12121A;">
                <thead>
                    <tr style="background:#0D0D14;border-bottom:2px solid #1E1E2E;">
                        <th style="{th}">Athlete</th><th style="{th}">Runs</th>
                        <th style="{th}">Best Total</th><th style="{th}">Last Run</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>""", unsafe_allow_html=True)
    else:
        empty_state("NO ATHLETES YET", "Use the form above to add your first athlete.")

    render_footer()
    st.stop()
