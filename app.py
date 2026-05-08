import streamlit as st
import base64
from PIL import Image
from database import (
    init_db,
    create_user,
    login_user,
    get_user,
    create_goal,
    get_active_goals,
    get_goal,
    deactivate_goal,
    user_can_access_goal,
    invite_partner,
    get_pending_invites,
    respond_to_invite,
    get_goal_members,
    get_pending_invitees,
    save_plan,
    get_plan_for_date,
    save_check_in,
    get_check_in_for_date,
    get_check_ins,
    compute_stats,
    maybe_adapt_difficulty,
)
from ai_engine import generate_daily_plan, generate_feedback, DIFFICULTY_LABELS

try:
    _icon = Image.open("logo.png")
except Exception:
    _icon = "🎯"

st.set_page_config(
    page_title="ZeroSkip",
    page_icon=_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ──────────────────────────────────────────────────────────────
# THEME — dark editorial, matches the LinkedIn deck aesthetic
# ──────────────────────────────────────────────────────────────
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:ital,wght@1,400;1,600&family=JetBrains+Mono:wght@400&display=swap');

:root {
    --bg:        #0A0A0C;
    --surface:   #121216;
    --surface-2: #16171C;
    --border:    #2A2C31;
    --border-soft:#1F2126;
    --ink:       #FFFFFF;
    --ink-dim:   #AEB0B6;
    --ink-faint: #686B73;
    --rose:      #FF6F91;
    --violet:    #B29CFF;
    --amber:     #F5A623;
    --teal:      #4FD1C5;
    --pink:      #FF8AB8;
    --blue:      #6FB1FF;
    --emerald:   #4ADE80;
    --serif:     'Source Serif 4', Georgia, serif;
    --sans:      'Inter', -apple-system, 'Helvetica Neue', sans-serif;
}

html, body, .stApp, [class*="css"] {
    background: var(--bg) !important;
    color: var(--ink) !important;
    font-family: var(--sans);
}
.stApp { background: var(--bg) !important; }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1080px; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #08080A !important;
    border-right: 1px solid var(--border-soft);
}
[data-testid="stSidebar"] * { color: var(--ink-dim); }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--ink) !important; }

/* sidebar nav radio: clean stacked links */
[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 2px;
}
[data-testid="stSidebar"] [role="radiogroup"] > label {
    background: transparent;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 0;
    transition: background 0.12s;
    cursor: pointer;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(255,255,255,0.04);
}
[data-testid="stSidebar"] [role="radiogroup"] > label[data-checked="true"],
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stSidebar"] [role="radiogroup"] > label p {
    color: var(--ink-dim) !important;
    font-size: 14px !important;
    font-weight: 500;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {
    color: var(--ink) !important;
}

/* ── Typography ──────────────────────────────────────────── */
.eyebrow {
    font-size: 11px;
    font-weight: 600;
    color: var(--ink-faint);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 18px;
}
.headline {
    font-size: 44px;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.05;
    margin: 0;
    letter-spacing: -0.02em;
}
.headline-italic {
    font-family: var(--serif);
    font-style: italic;
    font-weight: 400;
    font-size: 44px;
    color: var(--ink);
    line-height: 1.0;
    margin: 0 0 8px 0;
    letter-spacing: -0.01em;
}
.subhead {
    font-size: 15px;
    color: var(--ink-dim);
    line-height: 1.55;
    max-width: 720px;
    margin: 14px 0 28px 0;
}
.section-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--ink-faint);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin: 32px 0 14px 0;
    border-bottom: 1px solid var(--border-soft);
    padding-bottom: 10px;
}

/* ── Cards ───────────────────────────────────────────────── */
.card {
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 12px;
}
.card-glow {
    background:
        radial-gradient(120% 80% at 0% 0%, rgba(178,156,255,0.18), transparent 55%),
        var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 12px;
}
.card-row { display: flex; align-items: center; gap: 14px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot.rose    { background: var(--rose); }
.dot.violet  { background: var(--violet); }
.dot.amber   { background: var(--amber); }
.dot.teal    { background: var(--teal); }
.dot.pink    { background: var(--pink); }
.dot.blue    { background: var(--blue); }
.dot.emerald { background: var(--emerald); }
.dot.faint   { background: var(--ink-faint); }

.goal-title { font-size: 20px; font-weight: 700; color: var(--ink); letter-spacing:-0.01em; }
.goal-meta  { font-size: 12px; color: var(--ink-faint); letter-spacing: 0.06em; text-transform: uppercase; margin-top:4px;}
.goal-desc  { font-size: 14px; color: var(--ink-dim); line-height: 1.55; margin-top: 10px; }

.fn-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--ink-faint);
    font-style: italic;
}

/* ── Stat tiles ──────────────────────────────────────────── */
.stat {
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    padding: 18px 18px;
}
.stat .label {
    font-size: 10px;
    color: var(--ink-faint);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.stat .value {
    font-size: 32px;
    font-weight: 700;
    color: var(--ink);
    letter-spacing: -0.02em;
    line-height: 1;
}
.stat .unit { font-size: 12px; color: var(--ink-faint); margin-left: 4px; }
.stat .value.green   { color: var(--emerald); }
.stat .value.amber   { color: var(--amber); }
.stat .value.rose    { color: var(--rose); }
.stat .value.violet  { color: var(--violet); }
.stat .value.teal    { color: var(--teal); }

/* ── Badges ──────────────────────────────────────────────── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border: 1px solid var(--border);
}
.badge.done    { color: var(--emerald); border-color: rgba(74,222,128,0.35); background: rgba(74,222,128,0.08); }
.badge.missed  { color: var(--rose);    border-color: rgba(255,111,145,0.35); background: rgba(255,111,145,0.08); }
.badge.pending { color: var(--amber);   border-color: rgba(245,166,35,0.35);  background: rgba(245,166,35,0.08); }
.badge.shared  { color: var(--violet);  border-color: rgba(178,156,255,0.35); background: rgba(178,156,255,0.08); }
.badge.owner   { color: var(--ink-dim); border-color: var(--border); background: transparent; }

/* ── Plan / Feedback boxes ───────────────────────────────── */
.panel {
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-left: 3px solid var(--violet);
    border-radius: 12px;
    padding: 20px 22px;
    color: var(--ink-dim);
    font-size: 14.5px;
    line-height: 1.7;
}
.panel.amber  { border-left-color: var(--amber); }
.panel.rose   { border-left-color: var(--rose); }
.panel.teal   { border-left-color: var(--teal); }

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button, .stFormSubmitButton > button {
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.12s;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: #1d1e23;
    border-color: #3a3c42;
    color: var(--ink);
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stButton > button[kind="primaryFormSubmit"],
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"] {
    background: var(--ink) !important;
    color: var(--bg) !important;
    border: 1px solid var(--ink) !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
.stButton > button[kind="primaryFormSubmit"]:hover,
[data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: #e8e8eb !important;
    color: var(--bg) !important;
}

/* ── Inputs ──────────────────────────────────────────────── */
input, textarea, select,
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background: var(--surface) !important;
    color: var(--ink) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--violet) !important;
    box-shadow: 0 0 0 1px var(--violet) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label {
    color: var(--ink-dim) !important;
    font-size: 12px !important;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
[data-baseweb="popover"] { background: var(--surface) !important; }

/* ── Tabs ────────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
    border-bottom: 1px solid var(--border-soft) !important;
    background: transparent !important;
    gap: 24px;
}
[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--ink-faint) !important;
    border: none !important;
    padding: 10px 0 14px 0 !important;
    font-size: 13px !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 600;
}
[aria-selected="true"][data-baseweb="tab"] { color: var(--ink) !important; }
[data-baseweb="tab-highlight"] { background: var(--ink) !important; height: 2px !important; }

/* ── Progress bars ───────────────────────────────────────── */
.stProgress > div > div > div { background: var(--ink) !important; }
.stProgress > div > div { background: var(--border-soft) !important; height: 4px !important; }

/* ── Expander ────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-radius: 12px;
}
[data-testid="stExpander"] summary { color: var(--ink) !important; }

/* ── Misc ────────────────────────────────────────────────── */
hr, .divider { border: none; border-top: 1px solid var(--border-soft); margin: 28px 0; }
a { color: var(--ink); text-decoration: underline; text-underline-offset: 3px; }
.muted { color: var(--ink-faint); font-size: 12px; }

/* ── Auth screen ─────────────────────────────────────────── */
.auth-wrap {
    max-width: 440px; margin: 60px auto 0 auto; text-align: center;
}
.auth-brand {
    font-size: 36px; font-weight: 800; color: var(--ink);
    letter-spacing: -0.02em; margin-top: 22px;
}
.auth-brand .ital {
    font-family: var(--serif); font-style: italic; font-weight: 400; color: var(--ink-dim);
}
.auth-tag { font-size: 13px; color: var(--ink-faint); margin-top: 6px; letter-spacing: 0.04em; }

/* ── Buddy row ───────────────────────────────────────────── */
.buddy-row {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 18px;
    border: 1px solid var(--border-soft);
    border-radius: 12px;
    background: var(--surface);
    margin-bottom: 8px;
}
.avatar {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; color: var(--ink);
    background: linear-gradient(135deg, var(--violet), var(--rose));
    flex-shrink: 0;
}
.avatar.teal   { background: linear-gradient(135deg, var(--teal), var(--blue)); }
.avatar.amber  { background: linear-gradient(135deg, var(--amber), var(--rose)); }
.avatar.emerald{ background: linear-gradient(135deg, var(--emerald), var(--teal)); }
.buddy-name { font-size: 14px; font-weight: 600; color: var(--ink); }
.buddy-meta { font-size: 11px; color: var(--ink-faint); letter-spacing: 0.06em; text-transform: uppercase; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


CATEGORIES = ["Health & Fitness", "Learning", "Career", "Mindfulness", "Finance", "Other"]
DIFF_DOT = {1: "emerald", 2: "teal", 3: "amber", 4: "rose", 5: "violet"}
AVATAR_TONES = ["", "teal", "amber", "emerald"]


def avatar_class_for(username: str) -> str:
    return AVATAR_TONES[sum(ord(c) for c in username) % len(AVATAR_TONES)]


def initials(username: str) -> str:
    return (username[:1] + username[-1:]).upper() if username else "?"


def page_intro(eyebrow: str, headline: str, italic: str, subhead: str):
    st.markdown(
        f'<div class="eyebrow">{eyebrow}</div>'
        f'<div class="headline">{headline}</div>'
        f'<div class="headline-italic">{italic}</div>'
        f'<div class="subhead">{subhead}</div>',
        unsafe_allow_html=True,
    )


def section(label: str):
    st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────
def show_auth():
    try:
        with open("logo.png", "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{img_b64}" width="92" style="border-radius:20px">'
    except Exception:
        logo_html = '<div style="font-size:48px">🎯</div>'

    st.markdown(
        f'<div class="auth-wrap">'
        f'<div>{logo_html}</div>'
        f'<div class="auth-brand">ZeroSkip<span class="ital">.</span></div>'
        f'<div class="auth-tag">DON\'T BREAK THE STREAK</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        tab1, tab2 = st.tabs(["LOG IN", "CREATE ACCOUNT"])
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Please fill in both fields.")
                else:
                    user = login_user(username, password)
                    if user:
                        st.session_state["user"] = user
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Choose a username")
                new_password = st.text_input("Choose a password", type="password")
                confirm = st.text_input("Confirm password", type="password")
                submitted2 = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            if submitted2:
                if not new_username or not new_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm:
                    st.error("Passwords don't match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        user = create_user(new_username, new_password)
                        st.session_state["user"] = user
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))


if "user" not in st.session_state:
    show_auth()
    st.stop()

user = st.session_state["user"]
user_id = user["id"]


# ──────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    try:
        with open("logo.png", "rb") as f:
            sb_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin-top:6px;margin-bottom:18px">'
            f'<img src="data:image/png;base64,{sb_b64}" width="32" style="border-radius:8px">'
            f'<div style="font-size:18px;font-weight:800;color:#fff;letter-spacing:-0.01em">ZeroSkip</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        st.markdown("## ZeroSkip")

    pending = get_pending_invites(user_id)
    inbox_label = f"Inbox ({len(pending)})" if pending else "Inbox"

    st.markdown('<div style="font-size:10px;color:#686B73;letter-spacing:0.18em;margin:14px 0 10px 4px;font-weight:600">NAVIGATE</div>', unsafe_allow_html=True)
    page = st.radio(
        "nav",
        ["Goals", "Today", "Progress", "AI Feedback", inbox_label],
        label_visibility="collapsed",
    )

    st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
    st.markdown('<div style="border-top:1px solid #1F2126;margin: 0 -8px 14px -8px"></div>', unsafe_allow_html=True)

    goals = get_active_goals(user_id)
    own_count = sum(1 for g in goals if g["is_owner"])
    shared_count = len(goals) - own_count
    st.markdown(
        f'<div style="font-size:11px;color:#686B73;letter-spacing:0.06em;line-height:1.8">'
        f'<div>OWNED &nbsp;<span style="color:#AEB0B6">·</span>&nbsp; <b style="color:#fff">{own_count}</b></div>'
        f'<div>SHARED WITH YOU &nbsp;<span style="color:#AEB0B6">·</span>&nbsp; <b style="color:#fff">{shared_count}</b></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
    av_class = avatar_class_for(user["username"])
    st.markdown(
        f'<div class="buddy-row" style="background:transparent;border:1px solid #1F2126;padding:10px 12px">'
        f'<div class="avatar {av_class}" style="width:30px;height:30px;font-size:11px">{initials(user["username"])}</div>'
        f'<div><div class="buddy-name" style="font-size:13px">{user["username"]}</div>'
        f'<div class="buddy-meta">SIGNED IN</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("Log Out", use_container_width=True, key="logout_btn"):
        del st.session_state["user"]
        st.rerun()


# Normalize page label (strip the count from Inbox)
page_key = "Inbox" if page.startswith("Inbox") else page


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def goal_selector(goals, key="goal_select"):
    if not goals:
        st.markdown(
            '<div class="card" style="text-align:center;color:#686B73;padding:34px">'
            'No active goals yet. Head to <b style="color:#fff">Goals</b> to create one.'
            '</div>',
            unsafe_allow_html=True,
        )
        return None
    options = {}
    for g in goals:
        suffix = "" if g["is_owner"] else f"  ·  shared by @{g['owner_username']}"
        options[f"{g['title']}{suffix}"] = g["id"]
    label = st.selectbox("Select goal", list(options.keys()), key=key, label_visibility="collapsed")
    return options[label]


def stat_tile(label, value, unit="", color=""):
    return (
        f'<div class="stat">'
        f'<div class="label">{label}</div>'
        f'<div class="value {color}">{value}<span class="unit">{unit}</span></div>'
        f'</div>'
    )


def status_badge(completed_today, has_check_in):
    if not has_check_in:
        return '<span class="badge pending">Pending</span>'
    return '<span class="badge done">Completed</span>' if completed_today else '<span class="badge missed">Missed</span>'


# ──────────────────────────────────────────────────────────────
# PAGE: Goals
# ──────────────────────────────────────────────────────────────
def page_goals():
    page_intro(
        "01  /  YOUR GOALS",
        "What you're",
        "building toward.",
        "Create a goal, share it with a buddy, and let ZeroSkip handle the daily structure.",
    )

    with st.expander("＋  Create a new goal"):
        with st.form("create_goal_form"):
            title = st.text_input("Goal title", placeholder="e.g. Run 3x per week")
            description = st.text_area("Why does this matter?", placeholder="Optional — describe what success looks like.")
            category = st.selectbox("Category", CATEGORIES)
            submitted = st.form_submit_button("Create Goal", type="primary")
        if submitted:
            if not title.strip():
                st.error("Please enter a goal title.")
            else:
                create_goal(title.strip(), description.strip(), category, user_id)
                st.rerun()

    section("ACTIVE GOALS")

    goals = get_active_goals(user_id)
    if not goals:
        st.markdown(
            '<div class="card" style="text-align:center;color:#686B73;padding:40px">'
            'No goals yet. Create one above.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    for goal in goals:
        diff = goal["difficulty"]
        diff_label = DIFFICULTY_LABELS.get(diff, "?")
        dot_color = DIFF_DOT.get(diff, "faint")
        is_owner = bool(goal["is_owner"])
        members = get_goal_members(goal["id"])
        partner_count = len(members) - 1
        share_badge = (
            f'<span class="badge shared">Shared · {partner_count + 1} member{"s" if partner_count > 0 else ""}</span>'
            if partner_count > 0 else ""
        )
        owner_badge = (
            '<span class="badge owner">Owner</span>' if is_owner
            else f'<span class="badge owner">Shared by @{goal["owner_username"]}</span>'
        )

        col1, col2 = st.columns([6, 1.2])
        with col1:
            desc_html = (
                f'<div class="goal-desc">{goal["description"]}</div>'
                if goal.get("description") else ""
            )
            st.markdown(
                f'<div class="card-glow">'
                f'<div class="card-row" style="justify-content:space-between">'
                f'  <div class="card-row">'
                f'    <span class="dot {dot_color}"></span>'
                f'    <span class="goal-title">{goal["title"]}</span>'
                f'  </div>'
                f'  <div style="display:flex;gap:8px">{owner_badge}{share_badge}</div>'
                f'</div>'
                f'<div class="goal-meta">{goal.get("category","")} &nbsp;·&nbsp; {diff_label.upper()} LEVEL</div>'
                f'{desc_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
            if is_owner:
                if st.button("Manage", key=f"mng_{goal['id']}", use_container_width=True):
                    st.session_state["managing_goal"] = goal["id"]
                    st.rerun()

        # Manage panel (sharing + archive) only for owner of the goal
        if is_owner and st.session_state.get("managing_goal") == goal["id"]:
            with st.container():
                st.markdown('<div class="card" style="margin-top:-4px">', unsafe_allow_html=True)

                st.markdown('<div class="section-label" style="margin-top:0">PARTNERS</div>', unsafe_allow_html=True)
                for m in members:
                    av = avatar_class_for(m["username"])
                    you = " (you)" if m["id"] == user_id else ""
                    role_label = "OWNER" if m["role"] == "owner" else "PARTNER"
                    st.markdown(
                        f'<div class="buddy-row">'
                        f'<div class="avatar {av}">{initials(m["username"])}</div>'
                        f'<div><div class="buddy-name">@{m["username"]}{you}</div>'
                        f'<div class="buddy-meta">{role_label}</div></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                pending_invitees = get_pending_invitees(goal["id"])
                for un in pending_invitees:
                    av = avatar_class_for(un)
                    st.markdown(
                        f'<div class="buddy-row" style="opacity:0.6">'
                        f'<div class="avatar {av}">{initials(un)}</div>'
                        f'<div><div class="buddy-name">@{un}</div>'
                        f'<div class="buddy-meta">INVITED · AWAITING REPLY</div></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown('<div class="section-label" style="margin-top:18px">INVITE A PARTNER</div>', unsafe_allow_html=True)
                with st.form(f"invite_form_{goal['id']}"):
                    invitee = st.text_input("Username", placeholder="e.g. alex", key=f"inv_{goal['id']}")
                    sent = st.form_submit_button("Send invite", type="primary")
                if sent:
                    if not invitee.strip():
                        st.error("Enter a username.")
                    else:
                        try:
                            invite_partner(goal["id"], user_id, invitee.strip())
                            st.success(f"Invited @{invitee.strip().lower()}.")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

                cA, cB, cC = st.columns([1, 1, 4])
                if cA.button("Done", key=f"done_{goal['id']}"):
                    st.session_state.pop("managing_goal", None)
                    st.rerun()
                if cB.button("Archive goal", key=f"arch_{goal['id']}"):
                    deactivate_goal(goal["id"])
                    st.session_state.pop("managing_goal", None)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# PAGE: Today
# ──────────────────────────────────────────────────────────────
def page_today():
    page_intro(
        "02  /  TODAY",
        "Show up.",
        "Mark it. Move on.",
        "Generate today's plan, log your check-in, and see how your buddies are doing.",
    )

    goals = get_active_goals(user_id)
    goal_id = goal_selector(goals, key="today_goal")
    if not goal_id:
        return

    goal = get_goal(goal_id)
    stats = compute_stats(goal_id, user_id)
    members = get_goal_members(goal_id)
    is_shared = len(members) > 1

    section("YOUR STATS")
    c1, c2, c3 = st.columns(3)
    c1.markdown(stat_tile("Streak", stats["streak"], "d", "violet"), unsafe_allow_html=True)
    rate = stats["completion_rate"]
    c2.markdown(stat_tile("Completion", rate, "%",
                           "green" if rate >= 70 else "amber" if rate >= 40 else "rose"), unsafe_allow_html=True)
    c3.markdown(stat_tile("Consistency", stats["consistency_score"], "/100"), unsafe_allow_html=True)

    section("TODAY'S PLAN")
    existing_plan = get_plan_for_date(goal_id)
    if existing_plan:
        plan_html = existing_plan["plan_text"].replace("\n", "<br>")
        st.markdown(f'<div class="panel">{plan_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="muted" style="margin-bottom:12px">No plan generated yet for today.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Generate Plan with AI", type="primary"):
            with st.spinner("Building your plan..."):
                try:
                    plan_text = generate_daily_plan(goal, stats)
                    save_plan(goal_id, plan_text)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    section("YOUR CHECK-IN")
    existing_ci = get_check_in_for_date(goal_id, user_id)
    if existing_ci and not st.session_state.get(f"editing_ci_{goal_id}"):
        badge = '<span class="badge done">Completed</span>' if existing_ci["completed"] else '<span class="badge missed">Missed</span>'
        note = f'<div style="font-size:13px;color:#AEB0B6;margin-top:8px">"{existing_ci["notes"]}"</div>' if existing_ci.get("notes") else ""
        st.markdown(f'<div class="card">{badge}{note}</div>', unsafe_allow_html=True)
        if st.button("Edit check-in", key=f"edit_{goal_id}"):
            st.session_state[f"editing_ci_{goal_id}"] = True
            st.rerun()
    else:
        with st.form(f"check_in_form_{goal_id}"):
            completed = st.radio(
                "Did you complete today's task?",
                ["Yes, I did it!", "No, I missed it"],
                horizontal=True,
            )
            notes = st.text_input("Add a note (optional)", placeholder="What happened today?")
            submitted = st.form_submit_button("Save Check-In", type="primary")
        if submitted:
            is_done = completed.startswith("Yes")
            save_check_in(goal_id, user_id, is_done, notes)
            st.session_state.pop(f"editing_ci_{goal_id}", None)
            new_diff = maybe_adapt_difficulty(goal_id, user_id)
            if new_diff:
                direction = "up" if new_diff > goal["difficulty"] else "down"
                st.success(f"Saved. Difficulty adjusted {direction} to {DIFFICULTY_LABELS[new_diff]}.")
            st.rerun()

    if is_shared:
        section("BUDDY STATUS · TODAY")
        for m in members:
            if m["id"] == user_id:
                continue
            their_ci = get_check_in_for_date(goal_id, m["id"])
            their_stats = compute_stats(goal_id, m["id"])
            badge_html = (
                '<span class="badge done">Completed</span>' if their_ci and their_ci["completed"]
                else '<span class="badge missed">Missed</span>' if their_ci
                else '<span class="badge pending">Pending</span>'
            )
            av = avatar_class_for(m["username"])
            st.markdown(
                f'<div class="buddy-row" style="justify-content:space-between">'
                f'<div style="display:flex;align-items:center;gap:12px">'
                f'<div class="avatar {av}">{initials(m["username"])}</div>'
                f'<div><div class="buddy-name">@{m["username"]}</div>'
                f'<div class="buddy-meta">STREAK · {their_stats["streak"]}D &nbsp;·&nbsp; {their_stats["completion_rate"]}% RATE</div></div>'
                f'</div>'
                f'<div>{badge_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────────
# PAGE: Progress
# ──────────────────────────────────────────────────────────────
def page_progress():
    page_intro(
        "03  /  PROGRESS",
        "The numbers",
        "don't lie.",
        "Last 30 days. Your streak, completion rate, and consistency — versus your buddies.",
    )

    goals = get_active_goals(user_id)
    goal_id = goal_selector(goals, key="prog_goal")
    if not goal_id:
        return

    members = get_goal_members(goal_id)
    is_shared = len(members) > 1

    section("YOUR STATS")
    stats = compute_stats(goal_id, user_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(stat_tile("Streak", stats["streak"], "d", "violet"), unsafe_allow_html=True)
    rate = stats["completion_rate"]
    rc = "green" if rate >= 70 else "amber" if rate >= 40 else "rose"
    c2.markdown(stat_tile("Completion", rate, "%", rc), unsafe_allow_html=True)
    score = stats["consistency_score"]
    sc = "green" if score >= 70 else "amber" if score >= 40 else "rose"
    c3.markdown(stat_tile("Consistency", score, "/100", sc), unsafe_allow_html=True)
    c4.markdown(stat_tile("Missed", stats["missed_days"], "d", "rose"), unsafe_allow_html=True)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="muted" style="margin-bottom:6px">COMPLETION</div>', unsafe_allow_html=True)
    st.progress(min(100, int(stats["completion_rate"])))
    st.markdown('<div class="muted" style="margin-bottom:6px;margin-top:14px">CONSISTENCY</div>', unsafe_allow_html=True)
    st.progress(min(100, int(stats["consistency_score"])))

    if is_shared:
        section("HEAD TO HEAD")
        cols = st.columns(len(members))
        for i, m in enumerate(members):
            their_stats = compute_stats(goal_id, m["id"])
            av = avatar_class_for(m["username"])
            you_tag = ' <span class="muted" style="margin-left:6px">YOU</span>' if m["id"] == user_id else ""
            cols[i].markdown(
                f'<div class="card">'
                f'<div class="buddy-row" style="margin-bottom:10px">'
                f'<div class="avatar {av}" style="width:32px;height:32px;font-size:11px">{initials(m["username"])}</div>'
                f'<div class="buddy-name">@{m["username"]}{you_tag}</div></div>'
                f'<div class="muted">STREAK</div>'
                f'<div style="font-size:24px;font-weight:700;margin-bottom:8px">{their_stats["streak"]}<span class="unit" style="font-size:12px;color:#686B73"> days</span></div>'
                f'<div class="muted">COMPLETION</div>'
                f'<div style="font-size:18px;font-weight:600">{their_stats["completion_rate"]}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    section("CHECK-IN HISTORY")
    check_ins = get_check_ins(goal_id, user_id, days=30)
    if not check_ins:
        st.markdown('<div class="muted">No check-ins yet.</div>', unsafe_allow_html=True)
        return

    for ci in check_ins:
        cls = "done" if ci["completed"] else "missed"
        label = "Completed" if ci["completed"] else "Missed"
        note_html = f'<span style="color:#686B73;font-size:12px;margin-left:12px">{ci["notes"]}</span>' if ci.get("notes") else ""
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid #1F2126">'
            f'<span style="color:#686B73;font-size:12px;width:90px;letter-spacing:0.04em">{ci["check_in_date"]}</span>'
            f'<span class="badge {cls}">{label}</span>'
            f'{note_html}</div>',
            unsafe_allow_html=True,
        )

    section("DAILY CHART")
    import pandas as pd
    chart_data = {ci["check_in_date"]: int(ci["completed"]) for ci in reversed(check_ins)}
    df = pd.DataFrame({"Date": list(chart_data.keys()), "Completed": list(chart_data.values())}).set_index("Date")
    st.bar_chart(df, color="#B29CFF", height=220)


# ──────────────────────────────────────────────────────────────
# PAGE: AI Feedback
# ──────────────────────────────────────────────────────────────
def page_ai_feedback():
    page_intro(
        "04  /  AI FEEDBACK",
        "Honest coaching.",
        "Built on your real data.",
        "Claude reads your last 14 days and tells you exactly where you're slipping — and what to fix.",
    )

    goals = get_active_goals(user_id)
    goal_id = goal_selector(goals, key="fb_goal")
    if not goal_id:
        return

    goal = get_goal(goal_id)
    stats = compute_stats(goal_id, user_id)
    check_ins = get_check_ins(goal_id, user_id, days=14)

    diff = goal["difficulty"]
    diff_label = DIFFICULTY_LABELS.get(diff, "?")

    section("AT A GLANCE")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(stat_tile("Streak", stats["streak"], "d", "violet"), unsafe_allow_html=True)
    rate = stats["completion_rate"]
    rc = "green" if rate >= 70 else "amber" if rate >= 40 else "rose"
    c2.markdown(stat_tile("Completion", rate, "%", rc), unsafe_allow_html=True)
    score = stats["consistency_score"]
    sc = "green" if score >= 70 else "amber" if score >= 40 else "rose"
    c3.markdown(stat_tile("Consistency", score, "/100", sc), unsafe_allow_html=True)
    c4.markdown(
        f'<div class="stat"><div class="label">Difficulty</div>'
        f'<div class="value" style="font-size:20px;color:var(--{DIFF_DOT.get(diff,"violet")})">{diff_label}</div></div>',
        unsafe_allow_html=True,
    )

    if not check_ins:
        st.markdown(
            '<div class="card" style="margin-top:18px;color:#686B73">'
            'Complete at least one check-in to unlock AI feedback.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    if st.button("Get AI Feedback", type="primary"):
        with st.spinner("Analyzing your behavior patterns..."):
            try:
                feedback = generate_feedback(goal, stats, check_ins)
                fb_html = feedback.replace("\n", "<br>")
                st.markdown(f'<div class="panel teal" style="margin-top:18px">{fb_html}</div>', unsafe_allow_html=True)
            except ValueError as e:
                st.error(str(e))


# ──────────────────────────────────────────────────────────────
# PAGE: Inbox
# ──────────────────────────────────────────────────────────────
def page_inbox():
    page_intro(
        "05  /  INBOX",
        "Goal invitations,",
        "from your people.",
        "Accept to share a goal — both of you can check in independently and see each other's progress.",
    )

    invites = get_pending_invites(user_id)
    if not invites:
        st.markdown(
            '<div class="card" style="text-align:center;color:#686B73;padding:42px">'
            'No pending invites. To get one, ask a friend to share a goal with @<b style="color:#fff">' + user["username"] + '</b>.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    for inv in invites:
        av = avatar_class_for(inv["inviter_username"])
        desc = f'<div class="goal-desc">{inv["description"]}</div>' if inv.get("description") else ""
        st.markdown(
            f'<div class="card-glow">'
            f'<div class="card-row" style="justify-content:space-between">'
            f'<div class="card-row">'
            f'<div class="avatar {av}">{initials(inv["inviter_username"])}</div>'
            f'<div><div class="buddy-meta">@{inv["inviter_username"]} INVITED YOU</div>'
            f'<div class="goal-title">{inv["title"]}</div></div>'
            f'</div>'
            f'<span class="badge shared">Pending</span>'
            f'</div>'
            f'<div class="goal-meta" style="margin-top:8px">{inv.get("category", "")}</div>'
            f'{desc}'
            f'</div>',
            unsafe_allow_html=True,
        )
        a, b, _ = st.columns([1, 1, 4])
        if a.button("Accept", key=f"acc_{inv['invite_id']}", type="primary"):
            respond_to_invite(inv["invite_id"], user_id, accept=True)
            st.rerun()
        if b.button("Decline", key=f"dec_{inv['invite_id']}"):
            respond_to_invite(inv["invite_id"], user_id, accept=False)
            st.rerun()


# ──────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────
if page_key == "Goals":
    page_goals()
elif page_key == "Today":
    page_today()
elif page_key == "Progress":
    page_progress()
elif page_key == "AI Feedback":
    page_ai_feedback()
elif page_key == "Inbox":
    page_inbox()
