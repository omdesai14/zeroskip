import streamlit as st
import base64
from PIL import Image
from database import (
    init_db,
    create_user,
    login_user,
    create_goal,
    get_active_goals,
    get_goal,
    deactivate_goal,
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
    layout="centered",
)

init_db()

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

[data-testid="stSidebar"] {
    background: #0f0f0f;
    border-right: 1px solid #222;
}
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

.stat-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 20px 16px;
    text-align: center;
    margin-bottom: 8px;
}
.stat-label {
    font-size: 12px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}
.stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
}
.stat-value.green  { color: #4ade80; }
.stat-value.yellow { color: #facc15; }
.stat-value.red    { color: #f87171; }
.stat-value.blue   { color: #60a5fa; }

.goal-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.goal-title { font-size: 17px; font-weight: 600; color: #fff; margin-bottom: 4px; }
.goal-meta  { font-size: 12px; color: #888; }

.plan-box {
    background: #111827;
    border-left: 3px solid #6366f1;
    border-radius: 0 10px 10px 0;
    padding: 18px 20px;
    color: #d1d5db;
    font-size: 14px;
    line-height: 1.7;
    margin: 12px 0;
}

.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
}
.badge-green  { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.badge-red    { background: #2d0a0a; color: #f87171; border: 1px solid #7f1d1d; }
.badge-yellow { background: #1c1a00; color: #facc15; border: 1px solid #713f12; }

.feedback-box {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 22px;
    color: #c9d1d9;
    font-size: 15px;
    line-height: 1.75;
    margin-top: 16px;
}

.page-title {
    font-size: 26px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
}
.page-sub {
    font-size: 14px;
    color: #666;
    margin-bottom: 24px;
}

.divider { border-top: 1px solid #222; margin: 20px 0; }

.auth-box {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 16px;
    padding: 36px 32px;
    max-width: 420px;
    margin: 60px auto 0 auto;
}
.auth-title {
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
    text-align: center;
}
.auth-sub {
    font-size: 13px;
    color: #666;
    text-align: center;
    margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)

CATEGORIES = ["Health & Fitness", "Learning", "Career", "Mindfulness", "Finance", "Other"]
DIFF_COLOR = {1: "#4ade80", 2: "#86efac", 3: "#facc15", 4: "#fb923c", 5: "#f87171"}


# ── Auth gate ─────────────────────────────────────────────────
def show_auth():
    try:
        with open("logo.png", "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{img_b64}" width="110" style="border-radius:22px">'
    except Exception:
        logo_html = '<div style="font-size:48px">🎯</div>'

    st.markdown(f"""
    <div style='width:100%;text-align:center;margin-top:48px;margin-bottom:32px'>
        <div style='margin:0 auto;display:inline-block'>{logo_html}</div>
        <div style='font-size:32px;font-weight:800;color:#fff;letter-spacing:-0.5px;margin-top:16px'>ZeroSkip</div>
        <div style='font-size:14px;color:#555;margin-top:6px'>Your personal AI coach. Build habits that stick.</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Log In", "Create Account"])

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
                    st.success("Account created! Welcome.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


# Check auth
if "user" not in st.session_state:
    show_auth()
    st.stop()

user = st.session_state["user"]
user_id = user["id"]

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    try:
        with open("logo.png", "rb") as f:
            sb_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<img src="data:image/png;base64,{sb_b64}" width="40" style="border-radius:10px;margin-bottom:4px">', unsafe_allow_html=True)
    except Exception:
        pass
    st.markdown("## ZeroSkip")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    page = st.radio("", ["Goals", "Today", "Progress", "AI Feedback"], label_visibility="collapsed")
    st.markdown("---")
    goals = get_active_goals(user_id)
    st.markdown(f"<div style='font-size:12px;color:#555;'>Active goals: <b style='color:#888'>{len(goals)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:12px;color:#555;margin-top:4px'>Logged in as <b style='color:#888'>{user['username']}</b></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("Log Out", use_container_width=True):
        del st.session_state["user"]
        st.rerun()


# ── Helper ────────────────────────────────────────────────────
def goal_selector(goals):
    if not goals:
        st.info("No active goals. Go to Goals to create one.")
        return None, None
    options = {g["title"]: g["id"] for g in goals}
    title = st.selectbox("Select goal", list(options.keys()), label_visibility="collapsed")
    return title, options[title]


# ============================================================
# PAGE: Goals
# ============================================================
def page_goals():
    st.markdown('<div class="page-title">Your Goals</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Track what matters most to you.</div>', unsafe_allow_html=True)

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
                st.success(f'Goal "{title}" created!')
                st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    goals = get_active_goals(user_id)
    if not goals:
        st.markdown("<div style='color:#555;text-align:center;padding:40px 0'>No goals yet. Create one above.</div>", unsafe_allow_html=True)
        return

    for goal in goals:
        diff = goal["difficulty"]
        diff_label = DIFFICULTY_LABELS.get(diff, "?")
        color = DIFF_COLOR.get(diff, "#888")

        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(f"""
            <div class="goal-card">
                <div class="goal-title">{goal['title']}</div>
                <div class="goal-meta">
                    {goal.get('category','')} &nbsp;·&nbsp;
                    <span style="color:{color}">● {diff_label}</span>
                </div>
                {"<div style='margin-top:8px;font-size:13px;color:#666'>"+goal['description']+"</div>" if goal.get('description') else ""}
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("Archive", key=f"arch_{goal['id']}"):
                deactivate_goal(goal["id"])
                st.rerun()


# ============================================================
# PAGE: Today
# ============================================================
def page_today():
    st.markdown('<div class="page-title">Today\'s Check-In</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Generate your plan and log your progress.</div>', unsafe_allow_html=True)

    goals = get_active_goals(user_id)
    selected_title, goal_id = goal_selector(goals)
    if not goal_id:
        return

    goal = get_goal(goal_id)
    stats = compute_stats(goal_id)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-card"><div class="stat-label">Streak</div><div class="stat-value blue">{stats["streak"]}d</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card"><div class="stat-label">Completion</div><div class="stat-value {"green" if stats["completion_rate"]>=70 else "yellow" if stats["completion_rate"]>=40 else "red"}">{stats["completion_rate"]}%</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card"><div class="stat-label">Consistency</div><div class="stat-value">{stats["consistency_score"]}</div></div>', unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    st.markdown("#### Today's Plan")
    existing_plan = get_plan_for_date(goal_id)

    if existing_plan:
        st.markdown(f'<div class="plan-box">{existing_plan["plan_text"].replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#555;font-size:13px;margin-bottom:12px'>No plan generated yet for today.</div>", unsafe_allow_html=True)
        if st.button("Generate Plan with AI", type="primary"):
            with st.spinner("Building your plan..."):
                try:
                    plan_text = generate_daily_plan(goal, stats)
                    save_plan(goal_id, plan_text)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    st.markdown("#### Check In")
    existing_ci = get_check_in_for_date(goal_id)

    if existing_ci and not st.session_state.get("editing_ci"):
        status_text = "Completed" if existing_ci["completed"] else "Missed"
        badge_cls = "badge-green" if existing_ci["completed"] else "badge-red"
        st.markdown(f'<div style="margin:8px 0"><span class="badge {badge_cls}">{status_text}</span></div>', unsafe_allow_html=True)
        if existing_ci.get("notes"):
            st.markdown(f'<div style="font-size:13px;color:#666;margin-top:6px">"{existing_ci["notes"]}"</div>', unsafe_allow_html=True)
        if st.button("Edit check-in"):
            st.session_state["editing_ci"] = True
            st.rerun()
    else:
        with st.form("check_in_form"):
            completed = st.radio(
                "Did you complete today's task?",
                ["Yes, I did it!", "No, I missed it"],
                horizontal=True,
            )
            notes = st.text_input("Add a note (optional)", placeholder="What happened today?")
            submitted = st.form_submit_button("Save Check-In", type="primary")

        if submitted:
            is_done = completed.startswith("Yes")
            save_check_in(goal_id, is_done, notes)
            st.session_state.pop("editing_ci", None)

            new_diff = maybe_adapt_difficulty(goal_id)
            if new_diff:
                direction = "up" if new_diff > goal["difficulty"] else "down"
                st.success(f"Saved! Difficulty adjusted {direction} to **{DIFFICULTY_LABELS[new_diff]}**.")
            elif is_done:
                st.success("Logged. Keep the streak alive!")
            else:
                st.warning("Logged. Tomorrow is a new chance — don't quit.")
            st.rerun()


# ============================================================
# PAGE: Progress
# ============================================================
def page_progress():
    st.markdown('<div class="page-title">Progress</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Your stats over the last 30 days.</div>', unsafe_allow_html=True)

    goals = get_active_goals(user_id)
    selected_title, goal_id = goal_selector(goals)
    if not goal_id:
        return

    stats = compute_stats(goal_id)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="stat-card"><div class="stat-label">Streak</div><div class="stat-value blue">{stats["streak"]}</div><div style="font-size:11px;color:#555;margin-top:4px">days</div></div>', unsafe_allow_html=True)
    rate = stats["completion_rate"]
    rate_color = "green" if rate >= 70 else "yellow" if rate >= 40 else "red"
    c2.markdown(f'<div class="stat-card"><div class="stat-label">Completion</div><div class="stat-value {rate_color}">{rate}%</div></div>', unsafe_allow_html=True)
    score = stats["consistency_score"]
    score_color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
    c3.markdown(f'<div class="stat-card"><div class="stat-label">Consistency</div><div class="stat-value {score_color}">{score}</div><div style="font-size:11px;color:#555;margin-top:4px">/ 100</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-card"><div class="stat-label">Missed</div><div class="stat-value red">{stats["missed_days"]}</div><div style="font-size:11px;color:#555;margin-top:4px">days</div></div>', unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown(f"**Completion rate**")
    st.progress(int(stats["completion_rate"]))
    st.markdown(f"**Consistency score**")
    st.progress(int(stats["consistency_score"]))

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("#### Check-In History")
    check_ins = get_check_ins(goal_id, days=30)
    if not check_ins:
        st.markdown("<div style='color:#555;font-size:13px'>No check-ins yet.</div>", unsafe_allow_html=True)
        return

    for ci in check_ins:
        badge_cls = "badge-green" if ci["completed"] else "badge-red"
        label = "Done" if ci["completed"] else "Missed"
        note_html = f"<span style='color:#555;font-size:12px;margin-left:10px'>{ci['notes']}</span>" if ci.get("notes") else ""
        st.markdown(
            f'<div style="padding:8px 0;border-bottom:1px solid #1a1a1a;display:flex;align-items:center;gap:12px">'
            f'<span style="color:#555;font-size:13px;width:100px">{ci["check_in_date"]}</span>'
            f'<span class="badge {badge_cls}">{label}</span>'
            f'{note_html}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("#### Completion Chart")
    import pandas as pd
    chart_data = {ci["check_in_date"]: int(ci["completed"]) for ci in reversed(check_ins)}
    df = pd.DataFrame({"Date": list(chart_data.keys()), "Completed": list(chart_data.values())}).set_index("Date")
    st.bar_chart(df, color="#6366f1")


# ============================================================
# PAGE: AI Feedback
# ============================================================
def page_ai_feedback():
    st.markdown('<div class="page-title">AI Feedback</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Honest, data-driven coaching based on your real history.</div>', unsafe_allow_html=True)

    goals = get_active_goals(user_id)
    selected_title, goal_id = goal_selector(goals)
    if not goal_id:
        return

    goal = get_goal(goal_id)
    stats = compute_stats(goal_id)
    check_ins = get_check_ins(goal_id, days=14)

    diff = goal["difficulty"]
    diff_label = DIFFICULTY_LABELS.get(diff, "?")
    diff_color = DIFF_COLOR.get(diff, "#888")

    c1, c2, c3, c4 = st.columns(4)
    rate = stats["completion_rate"]
    rate_color = "green" if rate >= 70 else "yellow" if rate >= 40 else "red"
    score = stats["consistency_score"]
    score_color = "green" if score >= 70 else "yellow" if score >= 40 else "red"

    c1.markdown(f'<div class="stat-card"><div class="stat-label">Streak</div><div class="stat-value blue">{stats["streak"]}d</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card"><div class="stat-label">Completion</div><div class="stat-value {rate_color}">{rate}%</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card"><div class="stat-label">Consistency</div><div class="stat-value {score_color}">{score}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-card"><div class="stat-label">Difficulty</div><div class="stat-value" style="color:{diff_color};font-size:16px">{diff_label}</div></div>', unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    if not check_ins:
        st.markdown('<div style="color:#555;font-size:14px">Complete at least one check-in to get feedback.</div>', unsafe_allow_html=True)
        return

    if st.button("Get AI Feedback", type="primary"):
        with st.spinner("Analyzing your behavior patterns..."):
            try:
                feedback = generate_feedback(goal, stats, check_ins)
                st.markdown(f'<div class="feedback-box">{feedback.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            except ValueError as e:
                st.error(str(e))


# ── Router ────────────────────────────────────────────────────
if page == "Goals":
    page_goals()
elif page == "Today":
    page_today()
elif page == "Progress":
    page_progress()
elif page == "AI Feedback":
    page_ai_feedback()
