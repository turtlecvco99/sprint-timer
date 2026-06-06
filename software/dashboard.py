import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import datetime
import random
import os

st.set_page_config(page_title="Sprint Lab", page_icon="⚡", layout="wide")

# Works locally (../data/) and on Streamlit Cloud (same directory as script)
_here = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_here, '..', 'data', 'sprint_data.db')
os.makedirs(os.path.dirname(DB), exist_ok=True)

# ── Auto-seed on first boot ────────────────────────────────────────────────────
def _bootstrap():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, athlete TEXT,
        split_0_10 REAL, split_10_30 REAL,
        split_30_60 REAL, total REAL, top_speed REAL
    )''')
    conn.commit()
    count = conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
    if count == 0:
        athletes = [
            ("Franklin",  1.92, 2.48, 3.20), ("Marcus",   1.88, 2.42, 3.12),
            ("Jordan",    1.95, 2.55, 3.30), ("Darius",   1.90, 2.46, 3.18),
            ("Tyler",     1.97, 2.58, 3.35), ("Zion",     1.86, 2.39, 3.08),
            ("Cameron",   1.93, 2.50, 3.22), ("Elijah",   1.89, 2.44, 3.15),
        ]
        base = datetime.datetime.now() - datetime.timedelta(days=30)
        for name, b1, b2, b3 in athletes:
            for i in range(20):
                imp = i * 0.003
                fat = random.uniform(-0.02, 0.04)
                s1, s2, s3 = round(b1-imp+fat,3), round(b2-imp+fat,3), round(b3-imp+fat,3)
                total = round(s1+s2+s3, 3)
                conn.execute(
                    'INSERT INTO runs (date,athlete,split_0_10,split_10_30,split_30_60,total,top_speed) VALUES (?,?,?,?,?,?,?)',
                    ((base + datetime.timedelta(days=i*1.5)).isoformat(), name, s1, s2, s3, total, round(30/s3*2.237,2))
                )
        conn.commit()
    conn.close()

_bootstrap()

COLORS = {
    'bg':           '#0A0A0F',
    'surface':      '#12121A',
    'surface2':     '#1A1A26',
    'border':       '#1E1E2E',
    'border_light': '#2A2A3E',
    'blue':         '#89C4E1',
    'blue_dim':     '#5A9AB8',
    'pink':         '#FF3D8A',
    'pink_dim':     '#CC2E6E',
    'lavender':     '#B39DDB',
    'white':        '#F0F0F0',
    'gray':         '#8A8A9A',
    'gray_dim':     '#555566',
    'green':        '#1DDB8B',
    'red':          '#FF4D6A',
}

SPLIT_COLORS = [COLORS['blue'], COLORS['lavender'], COLORS['pink']]
SCALE = [[0, COLORS['blue']], [0.5, COLORS['lavender']], [1.0, COLORS['pink']]]

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

* { box-sizing: border-box; }

[data-testid="stAppViewContainer"],
[data-testid="stApp"],
.main { background-color: #0A0A0F !important; }

[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {
    background-color: #0A0A0F !important;
    padding-top: 1.5rem !important;
    max-width: 1400px !important;
}

[data-testid="stSidebar"] {
    background-color: #0D0D14 !important;
    border-right: 1px solid #1E1E2E !important;
}
[data-testid="stSidebar"] * {
    font-family: 'DM Sans', sans-serif !important;
    color: #8A8A9A !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2 {
    font-family: 'Bebas Neue', sans-serif !important;
    color: #F0F0F0 !important;
    letter-spacing: 0.08em !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    margin-bottom: 4px !important;
    display: block !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #8A8A9A !important;
    transition: all 0.2s ease !important;
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
    outline: none !important;
}
[data-testid="stTextInput"] label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #555566 !important;
}

[data-testid="metric-container"] {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    border-top: 3px solid #89C4E1 !important;
    border-radius: 12px !important;
    padding: 20px 18px !important;
    box-shadow: 0 0 24px rgba(137,196,225,0.06) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 32px rgba(137,196,225,0.14) !important;
}
[data-testid="metric-container"]:nth-child(even) {
    border-top-color: #FF3D8A !important;
    box-shadow: 0 0 24px rgba(255,61,138,0.06) !important;
}
[data-testid="metric-container"]:nth-child(even):hover {
    box-shadow: 0 0 32px rgba(255,61,138,0.14) !important;
}

[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 2.2rem !important;
    font-weight: 500 !important;
    color: #F0F0F0 !important;
    line-height: 1.1 !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: #555566 !important;
}
[data-testid="stMetricDelta"] svg { display: none !important; }
[data-testid="stMetricDelta"] > div {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
}
[data-testid="stMetricDelta"][data-direction="positive"] > div { color: #1DDB8B !important; }
[data-testid="stMetricDelta"][data-direction="negative"] > div { color: #FF4D6A !important; }

h1 {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 3.4rem !important;
    letter-spacing: 0.06em !important;
    background: linear-gradient(135deg, #89C4E1 0%, #B39DDB 50%, #FF3D8A 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    line-height: 1.05 !important;
    margin-bottom: 0.2rem !important;
}
h2 {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.7rem !important;
    letter-spacing: 0.07em !important;
    color: #89C4E1 !important;
    margin-top: 1.6rem !important;
    margin-bottom: 0.6rem !important;
}
h3 {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.2rem !important;
    letter-spacing: 0.07em !important;
    color: #8A8A9A !important;
    margin-bottom: 0.4rem !important;
}

p, li, span, div {
    font-family: 'DM Sans', sans-serif !important;
    color: #8A8A9A !important;
}

[data-testid="stCaptionContainer"] p {
    font-style: italic !important;
    color: #555566 !important;
    font-size: 0.78rem !important;
    border-left: 2px solid #89C4E1 !important;
    padding-left: 10px !important;
    margin-top: 8px !important;
}

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, #89C4E1 30%, #FF3D8A 70%, transparent 100%) !important;
    margin: 28px 0 !important;
    opacity: 0.6 !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #1E1E2E !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
iframe { background: #12121A !important; }

[data-testid="stDownloadButton"] button {
    background: transparent !important;
    border: 1px solid #89C4E1 !important;
    color: #89C4E1 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: #89C4E1 !important;
    color: #0A0A0F !important;
}

[data-testid="stButton"] button {
    background: linear-gradient(135deg, #89C4E1, #FF3D8A) !important;
    border: none !important;
    color: #0A0A0F !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    transition: opacity 0.2s ease !important;
}
[data-testid="stButton"] button:hover { opacity: 0.85 !important; }

[data-testid="stAlert"] {
    background: #12121A !important;
    border: 1px solid #1E1E2E !important;
    border-left: 3px solid #89C4E1 !important;
    border-radius: 8px !important;
    color: #8A8A9A !important;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0F; }
::-webkit-scrollbar-thumb { background: #1E1E2E; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #89C4E1; }

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

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
</style>""", unsafe_allow_html=True)


# ── style_chart ────────────────────────────────────────────────────────────────
def style_chart(fig, height=380):
    fig.update_layout(
        paper_bgcolor='#12121A',
        plot_bgcolor='#12121A',
        font=dict(family='DM Sans', color='#8A8A9A', size=12),
        height=height,
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='#1A1A26',
            bordercolor='#2A2A3E',
            font=dict(family='DM Sans', color='#F0F0F0', size=12),
        ),
        xaxis=dict(
            gridcolor='#1E1E2E', linecolor='#1E1E2E',
            tickcolor='#555566',
            tickfont=dict(family='JetBrains Mono', size=11, color='#555566'),
            showgrid=True, zeroline=False,
        ),
        yaxis=dict(
            gridcolor='#1E1E2E', linecolor='#1E1E2E',
            tickcolor='#555566',
            tickfont=dict(family='JetBrains Mono', size=11, color='#555566'),
            showgrid=True, zeroline=False,
        ),
        legend=dict(
            bgcolor='#0A0A0F', bordercolor='#1E1E2E', borderwidth=1,
            font=dict(family='DM Sans', size=11, color='#8A8A9A'),
        ),
        margin=dict(l=16, r=16, t=36, b=16),
    )
    fig.update_traces(marker=dict(line=dict(width=0)))
    return fig


# ── UI components ──────────────────────────────────────────────────────────────
def view_header(title, subtitle=None):
    sub = (f'<p style="font-family:DM Sans,sans-serif;font-size:0.78rem;color:#555566;'
           f'letter-spacing:0.12em;text-transform:uppercase;margin:4px 0 0;">{subtitle}</p>'
           ) if subtitle else ''
    st.markdown(f"""
    <div style="border-top:3px solid transparent;
                border-image:linear-gradient(90deg,#89C4E1,#FF3D8A) 1;
                padding:16px 0 12px;margin-bottom:24px;
                display:flex;align-items:flex-end;justify-content:space-between;">
        <div>
            <h1 style="margin:0;padding:0;">{title}</h1>
            {sub}
        </div>
        <span style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#555566;">
            {datetime.datetime.now().strftime('%a %b %d · %H:%M')}
        </span>
    </div>""", unsafe_allow_html=True)


def section_header(label, accent='blue'):
    color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin:28px 0 14px;">
        <div style="width:3px;height:20px;background:{color};border-radius:2px;flex-shrink:0;"></div>
        <span style="font-family:Bebas Neue,sans-serif;font-size:1.3rem;
                     letter-spacing:0.08em;color:{color};">{label}</span>
    </div>""", unsafe_allow_html=True)


def gradient_divider():
    st.markdown("<hr>", unsafe_allow_html=True)


def info_card(text, accent='blue'):
    color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    st.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;
                border-left:3px solid {color};border-radius:0 8px 8px 0;
                padding:12px 16px;margin:12px 0;">
        <p style="font-family:DM Sans,sans-serif;font-size:0.82rem;
                  color:#8A8A9A;margin:0;font-style:italic;">{text}</p>
    </div>""", unsafe_allow_html=True)


def metric_card(col, icon, label, value, delta=None, accent='blue'):
    border_color = '#89C4E1' if accent == 'blue' else '#FF3D8A'
    glow = 'rgba(137,196,225,0.08)' if accent == 'blue' else 'rgba(255,61,138,0.08)'
    delta_html = ''
    if delta is not None:
        d_color = '#1DDB8B' if delta <= 0 else '#FF4D6A'
        d_sign  = '+' if delta > 0 else ''
        delta_html = (f'<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;'
                      f'color:{d_color};margin-top:4px;">{d_sign}{delta:.2f}s</div>')
    col.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;
                border-top:3px solid {border_color};border-radius:12px;
                padding:18px 16px;box-shadow:0 0 24px {glow};">
        <div style="font-family:DM Sans,sans-serif;font-size:0.65rem;letter-spacing:0.14em;
                    text-transform:uppercase;color:#555566;margin-bottom:8px;">
            {icon}&nbsp; {label}
        </div>
        <div style="font-family:JetBrains Mono,monospace;font-size:2rem;
                    color:#F0F0F0;line-height:1.1;">{value}</div>
        {delta_html}
    </div>""", unsafe_allow_html=True)


# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_athlete(name):
    conn = sqlite3.connect(DB)
    df = pd.read_sql('SELECT * FROM runs WHERE athlete=? ORDER BY date DESC',
                     conn, params=(name,))
    conn.close()
    if df.empty:
        return df
    df['date']       = pd.to_datetime(df['date'])
    df['run_number'] = range(len(df), 0, -1)
    return df


@st.cache_data(ttl=5)
def load_leaderboard():
    conn = sqlite3.connect(DB)
    df = pd.read_sql('''
        SELECT
            athlete,
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
    df['rank']     = range(1, len(df) + 1)
    df['last_run'] = pd.to_datetime(df['last_run']).dt.strftime('%b %d, %Y')
    return df


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 20px;">
        <div style="font-family:Bebas Neue,sans-serif;font-size:2rem;
                    letter-spacing:0.1em;color:#F0F0F0;">⚡ SPRINT LAB</div>
        <div style="font-family:DM Sans,sans-serif;font-size:0.65rem;
                    letter-spacing:0.18em;text-transform:uppercase;
                    color:#555566;margin-top:2px;">track · analyze · dominate</div>
    </div>
    <hr style="border:none;height:1px;background:linear-gradient(90deg,#89C4E1,#FF3D8A);
               margin:0 0 20px;opacity:0.4;">
    """, unsafe_allow_html=True)

    athlete = st.text_input("Athlete", value="Franklin",
                             label_visibility="collapsed",
                             placeholder="Athlete name")

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    view_raw = st.radio("", [
        "🏅  LEADERBOARD",
        "⚡  SEASON ARC",
        "🔥  SESSION BREAKDOWN",
        "🏆  HALL OF RECORDS",
        "📈  SPEED PROFILE",
        "🗄️  DATA VAULT",
    ], label_visibility="collapsed")

    view = view_raw.split("  ")[1]

    st.markdown('<div style="height:32px"></div>', unsafe_allow_html=True)
    sidebar_stats = st.empty()

    if st.button("↺  REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── LEADERBOARD ────────────────────────────────────────────────────────────────
if view == "LEADERBOARD":
    lb = load_leaderboard()
    view_header("LEADERBOARD", f"{len(lb)} athletes ranked · auto-updates every 5s")

    if lb.empty:
        st.markdown("""
        <div style="text-align:center;padding:80px 40px;">
            <div style="font-family:Bebas Neue,sans-serif;font-size:4rem;
                        letter-spacing:0.06em;color:#1E1E2E;line-height:1;">
                NO RUNS LOGGED YET
            </div>
            <div style="font-family:DM Sans,sans-serif;font-size:0.9rem;
                        color:#555566;margin-top:16px;letter-spacing:0.08em;
                        text-transform:uppercase;">
                Get on the track and break some beams.
            </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    MEDALS       = {1: "🥇", 2: "🥈", 3: "🥉"}
    PODIUM_COLS  = {1: COLORS['pink'], 2: COLORS['blue'], 3: COLORS['lavender']}

    section_header("PODIUM", accent='pink')
    cols = st.columns(3)
    for i, col in enumerate(cols):
        if i < len(lb):
            row   = lb.iloc[i]
            medal = MEDALS.get(i + 1, "")
            color = PODIUM_COLS.get(i + 1, COLORS['gray'])
            col.markdown(f"""
            <div style="background:{color}12;border:1px solid {color}40;
                        border-top:3px solid {color};border-radius:14px;
                        padding:24px 16px;text-align:center;">
                <div style="font-size:2.4rem;line-height:1;margin-bottom:12px;">{medal}</div>
                <div style="font-family:Bebas Neue,sans-serif;font-size:1.6rem;
                            letter-spacing:0.06em;color:{color};">{row['athlete'].upper()}</div>
                <div style="font-family:JetBrains Mono,monospace;font-size:2.4rem;
                            color:#F0F0F0;font-weight:500;line-height:1.2;margin:8px 0;">
                    {row['best_total']:.2f}s
                </div>
                <div style="font-family:DM Sans,sans-serif;font-size:0.75rem;
                            color:#555566;letter-spacing:0.06em;">
                    {row['runs']} runs &nbsp;·&nbsp; {row['top_speed']:.1f} mph top speed
                </div>
            </div>""", unsafe_allow_html=True)

    gradient_divider()
    section_header("FULL RANKINGS", accent='blue')

    display = lb.copy()
    display['medal'] = display['rank'].map(lambda r: MEDALS.get(r, f"#{r}"))
    display = display[['medal', 'athlete', 'best_total', 'best_0_10',
                        'best_10_30', 'best_30_60', 'top_speed', 'runs', 'last_run']]
    display.columns = ['Rank', 'Athlete', 'Best Total', '0–10m',
                       '10–30m', '30–60m', 'Top Speed (mph)', 'Runs', 'Last Run']
    for c in ['Best Total', '0–10m', '10–30m', '30–60m']:
        display[c] = display[c].apply(lambda x: f"{x:.3f}s")
    display['Top Speed (mph)'] = display['Top Speed (mph)'].apply(lambda x: f"{x:.1f}")
    st.dataframe(display, use_container_width=True, hide_index=True)

    gradient_divider()
    section_header("BEST TOTAL TIME", accent='pink')

    lb_sorted = lb.sort_values('best_total')
    fig = go.Figure(go.Bar(
        x=lb_sorted['athlete'],
        y=lb_sorted['best_total'],
        marker=dict(color=lb_sorted['best_total'], colorscale=SCALE, showscale=False),
        text=lb_sorted['best_total'].apply(lambda x: f"{x:.2f}s"),
        textposition='outside',
        textfont=dict(family='JetBrains Mono', color=COLORS['white'], size=11),
    ))
    style_chart(fig, height=340)
    fig.update_layout(yaxis_title="Time (s)", bargap=0.35)
    st.plotly_chart(fig, use_container_width=True)

    section_header("SPLIT BREAKDOWN", accent='blue')
    lb_melted = lb.melt(id_vars='athlete',
                        value_vars=['best_0_10', 'best_10_30', 'best_30_60'],
                        var_name='split', value_name='time')
    lb_melted['split'] = lb_melted['split'].map({
        'best_0_10': '0–10m', 'best_10_30': '10–30m', 'best_30_60': '30–60m'
    })
    fig2 = px.bar(lb_melted, x='athlete', y='time', color='split', barmode='stack',
                  color_discrete_map={
                      '0–10m':  COLORS['blue'],
                      '10–30m': COLORS['lavender'],
                      '30–60m': COLORS['pink'],
                  },
                  labels={'time': 'Time (s)', 'athlete': 'Athlete', 'split': 'Split'})
    style_chart(fig2, height=340)
    fig2.update_layout(bargap=0.35)
    st.plotly_chart(fig2, use_container_width=True)
    st.stop()


# ── Load athlete data ──────────────────────────────────────────────────────────
df = load_athlete(athlete)

if not df.empty:
    days = (df['date'].max() - df['date'].min()).days
    sidebar_stats.markdown(f"""
    <div style="background:#12121A;border:1px solid #1E1E2E;
                border-radius:10px;padding:16px;">
        <div style="font-family:DM Sans,sans-serif;font-size:0.65rem;letter-spacing:0.12em;
                    text-transform:uppercase;color:#555566;margin-bottom:12px;">
            Session Stats
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:DM Sans,sans-serif;font-size:0.75rem;color:#555566;">Total runs</span>
                <span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#89C4E1;">{len(df)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:DM Sans,sans-serif;font-size:0.75rem;color:#555566;">Days training</span>
                <span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#89C4E1;">{days}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:DM Sans,sans-serif;font-size:0.75rem;color:#555566;">Best total</span>
                <span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#FF3D8A;">{df['total'].min():.2f}s</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:DM Sans,sans-serif;font-size:0.75rem;color:#555566;">Top speed</span>
                <span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#FF3D8A;">{df['top_speed'].max():.1f} mph</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

if df.empty:
    st.markdown("""
    <div style="text-align:center;padding:80px 40px;">
        <div style="font-family:Bebas Neue,sans-serif;font-size:4rem;
                    letter-spacing:0.06em;color:#1E1E2E;line-height:1;">
            NO RUNS LOGGED YET
        </div>
        <div style="font-family:DM Sans,sans-serif;font-size:0.9rem;
                    color:#555566;margin-top:16px;letter-spacing:0.08em;
                    text-transform:uppercase;">
            Get on the track and break some beams.
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

best   = df.loc[df['total'].idxmin()]
latest = df.iloc[0]

# ── Page header + metrics ──────────────────────────────────────────────────────
view_header("SPRINT LAB",
            f"{len(df)} runs logged · season {df['date'].dt.year.iloc[0]}")

c1, c2, c3, c4, c5, c6 = st.columns(6)
metric_card(c1, '📊', 'Total Runs',    str(len(df)),                          accent='blue')
metric_card(c2, '⏱',  'Latest Total',  f"{latest['total']:.2f}s",             accent='pink')
metric_card(c3, '🏆', 'Personal Best', f"{best['total']:.2f}s",
            delta=latest['total'] - best['total'],                             accent='blue')
metric_card(c4, '🚀', 'Best 0–10m',   f"{df['split_0_10'].min():.2f}s",      accent='pink')
metric_card(c5, '⚡', 'Best 10–30m',  f"{df['split_10_30'].min():.2f}s",     accent='blue')
metric_card(c6, '💨', 'Top Speed',    f"{df['top_speed'].max():.1f} mph",     accent='pink')

gradient_divider()

# ── SEASON ARC ─────────────────────────────────────────────────────────────────
if view == "SEASON ARC":
    section_header("SPLIT TRENDS — FULL SEASON", accent='blue')
    df_asc = df[::-1]
    fig = go.Figure()
    for col, label, color in zip(
        ['split_0_10', 'split_10_30', 'split_30_60'],
        ['0–10m', '10–30m', '30–60m'],
        SPLIT_COLORS
    ):
        fig.add_trace(go.Scatter(
            x=df_asc['run_number'], y=df_asc[col],
            name=label, mode='lines+markers',
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
        ))
    style_chart(fig, height=380)
    fig.update_layout(xaxis_title="Run number", yaxis_title="Split time (s)")
    st.plotly_chart(fig, use_container_width=True)

    section_header("WEEKLY AVERAGE TOTAL TIME", accent='pink')
    df['week'] = df['date'].dt.to_period('W').astype(str)
    weekly = df.groupby('week')['total'].mean().reset_index()
    fig2 = px.bar(weekly, x='week', y='total',
                  color='total', color_continuous_scale=SCALE,
                  labels={'total': 'Avg total (s)', 'week': 'Week'})
    style_chart(fig2, height=300)
    fig2.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

# ── SESSION BREAKDOWN ─────────────────────────────────────────────────────────
elif view == "SESSION BREAKDOWN":
    section_header("LAST SESSION — FATIGUE INDEX", accent='pink')
    today = df[df['date'].dt.date == df['date'].dt.date.iloc[0]]

    if len(today) < 2:
        info_card("Only one run in this session. Run multiple reps to see the fatigue chart.", accent='blue')
    else:
        today_asc = today[::-1].reset_index(drop=True)
        today_asc['rep'] = [f"Rep {i+1}" for i in range(len(today_asc))]
        fig = go.Figure()
        for col, label, color in zip(
            ['split_0_10', 'split_10_30', 'split_30_60'],
            ['0–10m', '10–30m', '30–60m'],
            SPLIT_COLORS
        ):
            fig.add_trace(go.Bar(x=today_asc['rep'], y=today_asc[col],
                                 name=label, marker_color=color))
        style_chart(fig, height=360)
        fig.update_layout(barmode='stack', yaxis_title='Time (s)')
        st.plotly_chart(fig, use_container_width=True)
        info_card("Rising 30–60m bars signal speed endurance fatigue. If rep 3+ climbs more than 0.15s above rep 1 — rack up. Session's done.", accent='pink')

# ── HALL OF RECORDS ───────────────────────────────────────────────────────────
elif view == "HALL OF RECORDS":
    section_header("PERSONAL BEST PROGRESSION", accent='blue')
    df_asc = df[::-1].copy()
    df_asc['pb_total'] = df_asc['total'].cummin()
    df_asc['pb_0_10']  = df_asc['split_0_10'].cummin()
    df_asc['pb_10_30'] = df_asc['split_10_30'].cummin()

    fig = go.Figure()
    for col, label, color in [
        ('pb_total', 'Total PB',  COLORS['pink']),
        ('pb_0_10',  '0–10m PB',  COLORS['blue']),
        ('pb_10_30', '10–30m PB', COLORS['lavender']),
    ]:
        fig.add_trace(go.Scatter(
            x=df_asc['run_number'], y=df_asc[col],
            name=label, mode='lines',
            line=dict(width=2.5, color=color),
        ))
    style_chart(fig, height=380)
    fig.update_layout(xaxis_title='Run number', yaxis_title='Time (s)')
    st.plotly_chart(fig, use_container_width=True)

    section_header("CURRENT PERSONAL BESTS", accent='pink')
    pb_data = {
        "Split":  ["0–10m", "10–30m", "30–60m", "Total", "Top speed"],
        "Best":   [
            f"{df['split_0_10'].min():.3f}s",
            f"{df['split_10_30'].min():.3f}s",
            f"{df['split_30_60'].min():.3f}s",
            f"{df['total'].min():.3f}s",
            f"{df['top_speed'].max():.1f} mph",
        ],
        "Run #":  [
            int(df.loc[df['split_0_10'].idxmin(), 'run_number']),
            int(df.loc[df['split_10_30'].idxmin(), 'run_number']),
            int(df.loc[df['split_30_60'].idxmin(), 'run_number']),
            int(df.loc[df['total'].idxmin(), 'run_number']),
            int(df.loc[df['top_speed'].idxmax(), 'run_number']),
        ],
    }
    st.dataframe(pd.DataFrame(pb_data), use_container_width=True, hide_index=True)

# ── SPEED PROFILE ─────────────────────────────────────────────────────────────
elif view == "SPEED PROFILE":
    section_header("VELOCITY CURVE — LATEST VS PERSONAL BEST", accent='blue')

    def velocity_points(row):
        splits = [row['split_0_10'], row['split_10_30'], row['split_30_60']]
        velocities = [0] + [d / s * 2.237 for d, s in zip([10, 20, 30], splits)]
        return [0, 10, 30, 60], velocities

    fig = go.Figure()
    for row, label, color, dash, width in [
        (latest, 'Latest run',    COLORS['blue'],  'solid', 2.5),
        (best,   'Personal best', COLORS['white'], 'dot',   1.5),
    ]:
        x, y = velocity_points(row)
        fig.add_trace(go.Scatter(
            x=x, y=y, name=label, mode='lines+markers',
            line=dict(color=color, width=width, dash=dash),
            marker=dict(size=7, color=color),
        ))
    style_chart(fig, height=380)
    fig.update_layout(xaxis_title='Distance (m)', yaxis_title='Speed (mph)')
    st.plotly_chart(fig, use_container_width=True)
    info_card("Elite sprinters peak around 60–70m. If your curve flattens early, your acceleration phase is your ceiling. If it's still climbing at 60m, build your top-end engine.", accent='blue')

# ── DATA VAULT ────────────────────────────────────────────────────────────────
elif view == "DATA VAULT":
    section_header("ALL RUNS", accent='blue')
    display = df[['run_number', 'date', 'split_0_10',
                  'split_10_30', 'split_30_60', 'total', 'top_speed']].copy()
    display.columns = ['Run', 'Date', '0–10m', '10–30m', '30–60m', 'Total', 'Top Speed (mph)']
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("↓  EXPORT CSV", display.to_csv(index=False),
                       "sprint_data.csv", "text/csv")
