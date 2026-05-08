import sqlite3
import hashlib
import os
from datetime import date, datetime, timedelta

DB_PATH = "accountability.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            difficulty INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Migration: add user_id column to goals if it doesn't exist
    try:
        c.execute("ALTER TABLE goals ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    except Exception:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL,
            plan_date TEXT NOT NULL,
            plan_text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES goals(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS check_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL DEFAULT 0,
            check_in_date TEXT NOT NULL,
            completed INTEGER NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES goals(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Migration: add user_id to check_ins if missing, and backfill from goal owner
    try:
        c.execute("ALTER TABLE check_ins ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    c.execute("""
        UPDATE check_ins
        SET user_id = (SELECT user_id FROM goals WHERE goals.id = check_ins.goal_id)
        WHERE user_id = 0
    """)
    conn.commit()

    # Goal sharing: invitee gets access once status='accepted'
    c.execute("""
        CREATE TABLE IF NOT EXISTS goal_partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL,
            inviter_id INTEGER NOT NULL,
            invitee_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(goal_id, invitee_id),
            FOREIGN KEY (goal_id) REFERENCES goals(id),
            FOREIGN KEY (inviter_id) REFERENCES users(id),
            FOREIGN KEY (invitee_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# --- Auth ---

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + key.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return key.hex() == key_hex
    except Exception:
        return False


def create_user(username: str, password: str):
    """Returns user dict on success, raises ValueError on duplicate username."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username.strip().lower(), _hash_password(password)),
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"id": user_id, "username": username.strip().lower()}
    except sqlite3.IntegrityError:
        raise ValueError("Username already taken. Choose a different one.")
    finally:
        conn.close()


def login_user(username: str, password: str):
    """Returns user dict on success, None on failure."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username.strip().lower(),)
    ).fetchone()
    conn.close()
    if row and _verify_password(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"]}
    return None


def find_user_by_username(username: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username FROM users WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user(user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Goal operations ---

def create_goal(title, description, category, user_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO goals (title, description, category, user_id) VALUES (?, ?, ?, ?)",
        (title, description, category, user_id),
    )
    conn.commit()
    goal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return goal_id


def get_active_goals(user_id):
    """Returns own goals plus goals shared with this user (status='accepted').
    Each goal dict has 'is_owner' (bool) and 'owner_username' for context."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT g.*, u.username AS owner_username,
               CASE WHEN g.user_id = ? THEN 1 ELSE 0 END AS is_owner
        FROM goals g
        JOIN users u ON u.id = g.user_id
        WHERE g.active = 1 AND (
            g.user_id = ?
            OR g.id IN (
                SELECT goal_id FROM goal_partners
                WHERE invitee_id = ? AND status = 'accepted'
            )
        )
        ORDER BY is_owner DESC, g.created_at DESC
        """,
        (user_id, user_id, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_goal(goal_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def user_can_access_goal(goal_id, user_id) -> bool:
    """True if user owns the goal or is an accepted partner."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT 1 FROM goals WHERE id = ? AND user_id = ?
        UNION
        SELECT 1 FROM goal_partners
        WHERE goal_id = ? AND invitee_id = ? AND status = 'accepted'
        """,
        (goal_id, user_id, goal_id, user_id),
    ).fetchone()
    conn.close()
    return row is not None


def deactivate_goal(goal_id):
    conn = get_connection()
    conn.execute("UPDATE goals SET active = 0 WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()


def update_difficulty(goal_id, difficulty):
    conn = get_connection()
    conn.execute(
        "UPDATE goals SET difficulty = ? WHERE id = ?", (difficulty, goal_id)
    )
    conn.commit()
    conn.close()


# --- Sharing / partners ---

def invite_partner(goal_id, inviter_id, invitee_username):
    """Returns dict with status. Raises ValueError on validation problems."""
    invitee = find_user_by_username(invitee_username)
    if not invitee:
        raise ValueError(f"No user named '{invitee_username}'.")
    if invitee["id"] == inviter_id:
        raise ValueError("You can't invite yourself.")

    goal = get_goal(goal_id)
    if not goal or goal["user_id"] != inviter_id:
        raise ValueError("Only the goal owner can invite partners.")

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO goal_partners (goal_id, inviter_id, invitee_id, status) VALUES (?, ?, ?, 'pending')",
            (goal_id, inviter_id, invitee["id"]),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"{invitee['username']} has already been invited to this goal.")
    finally:
        conn.close()
    return {"invitee": invitee["username"]}


def get_pending_invites(user_id):
    """Invites awaiting this user's response."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT gp.id AS invite_id, gp.goal_id, gp.created_at,
               g.title, g.description, g.category,
               u.username AS inviter_username
        FROM goal_partners gp
        JOIN goals g ON g.id = gp.goal_id
        JOIN users u ON u.id = gp.inviter_id
        WHERE gp.invitee_id = ? AND gp.status = 'pending'
        ORDER BY gp.created_at DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def respond_to_invite(invite_id, user_id, accept: bool):
    new_status = "accepted" if accept else "declined"
    conn = get_connection()
    conn.execute(
        "UPDATE goal_partners SET status = ? WHERE id = ? AND invitee_id = ?",
        (new_status, invite_id, user_id),
    )
    conn.commit()
    conn.close()


def get_goal_members(goal_id):
    """Returns owner + accepted partners as list of {id, username, role}."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT u.id, u.username, 'owner' AS role
        FROM goals g JOIN users u ON u.id = g.user_id
        WHERE g.id = ?
        UNION
        SELECT u.id, u.username, 'partner' AS role
        FROM goal_partners gp JOIN users u ON u.id = gp.invitee_id
        WHERE gp.goal_id = ? AND gp.status = 'accepted'
        """,
        (goal_id, goal_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_invitees(goal_id):
    """Pending invitees for a given goal (visible to the owner)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT u.username
        FROM goal_partners gp JOIN users u ON u.id = gp.invitee_id
        WHERE gp.goal_id = ? AND gp.status = 'pending'
        """,
        (goal_id,),
    ).fetchall()
    conn.close()
    return [r["username"] for r in rows]


# --- Daily plan operations ---

def save_plan(goal_id, plan_text, plan_date=None):
    if plan_date is None:
        plan_date = str(date.today())
    conn = get_connection()
    conn.execute(
        "INSERT INTO daily_plans (goal_id, plan_date, plan_text) VALUES (?, ?, ?)",
        (goal_id, plan_date, plan_text),
    )
    conn.commit()
    conn.close()


def get_plan_for_date(goal_id, plan_date=None):
    if plan_date is None:
        plan_date = str(date.today())
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM daily_plans WHERE goal_id = ? AND plan_date = ? ORDER BY id DESC LIMIT 1",
        (goal_id, plan_date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Check-in operations (now per user_id) ---

def save_check_in(goal_id, user_id, completed, notes=""):
    today = str(date.today())
    conn = get_connection()
    conn.execute(
        "DELETE FROM check_ins WHERE goal_id = ? AND user_id = ? AND check_in_date = ?",
        (goal_id, user_id, today),
    )
    conn.execute(
        "INSERT INTO check_ins (goal_id, user_id, check_in_date, completed, notes) VALUES (?, ?, ?, ?, ?)",
        (goal_id, user_id, today, int(completed), notes),
    )
    conn.commit()
    conn.close()


def get_check_in_for_date(goal_id, user_id, check_date=None):
    if check_date is None:
        check_date = str(date.today())
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM check_ins WHERE goal_id = ? AND user_id = ? AND check_in_date = ?",
        (goal_id, user_id, check_date),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_check_ins(goal_id, user_id, days=30):
    since = str(date.today() - timedelta(days=days))
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM check_ins WHERE goal_id = ? AND user_id = ? AND check_in_date >= ? ORDER BY check_in_date DESC",
        (goal_id, user_id, since),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Stats ---

def compute_stats(goal_id, user_id):
    check_ins = get_check_ins(goal_id, user_id, days=90)

    if not check_ins:
        return {"streak": 0, "completion_rate": 0.0, "consistency_score": 0.0, "missed_days": 0, "total_days": 0}

    history = {ci["check_in_date"]: bool(ci["completed"]) for ci in check_ins}

    streak = 0
    check_date = date.today()
    while True:
        key = str(check_date)
        if key in history and history[key]:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    total = len(check_ins)
    completed = sum(1 for ci in check_ins if ci["completed"])
    missed = total - completed
    completion_rate = round(completed / total * 100, 1) if total > 0 else 0.0
    consistency_score = round(min(100.0, streak * 5 + completion_rate * 0.5), 1)

    return {
        "streak": streak,
        "completion_rate": completion_rate,
        "consistency_score": consistency_score,
        "missed_days": missed,
        "total_days": total,
    }


def maybe_adapt_difficulty(goal_id, user_id):
    goal = get_goal(goal_id)
    if not goal:
        return None

    recent = get_check_ins(goal_id, user_id, days=7)
    if len(recent) < 5:
        return None

    rate = sum(1 for ci in recent if ci["completed"]) / len(recent) * 100
    current = goal["difficulty"]

    if rate >= 80 and current < 5:
        new_diff = current + 1
        update_difficulty(goal_id, new_diff)
        return new_diff
    elif rate <= 40 and current > 1:
        new_diff = current - 1
        update_difficulty(goal_id, new_diff)
        return new_diff

    return None
