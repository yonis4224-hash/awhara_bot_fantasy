"""
Activity and Profile Logic Engine (activity_logic.py)
Tracks total messages, weekly messages (with auto 7-day reset), activity points (XP),
calculates server ranks, assigns titles (drawn on image), and selects card themes.
"""
import os
import json
import time

DATA_PATH = os.path.join("src", "data", "activity_data.json")
if not os.path.exists(os.path.dirname(DATA_PATH)):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

# In-memory cooldown tracker to prevent message spam from awarding XP excessively (10s cooldown)
_user_msg_cooldown = {}

def _get_current_week_number():
    """Returns an integer representing the current year-week (e.g. 202635)"""
    gm = time.gmtime()
    # (year * 100) + week_number
    return (gm.tm_year * 100) + int(time.strftime("%U", gm))

def load_activity_data():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_activity_data(data):
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving activity data: {e}")

def get_user_profile(user_id, username="", display_name=""):
    uid = str(user_id)
    data = load_activity_data()
    current_week = _get_current_week_number()

    if uid not in data:
        data[uid] = {
            "user_id": uid,
            "username": username or uid,
            "display_name": display_name or username or uid,
            "total_messages": 0,
            "weekly_messages": 0,
            "current_week": current_week,
            "xp": 0,
            "level": 1,
            "first_seen": int(time.time()),
            "last_active": int(time.time())
        }
        save_activity_data(data)

    u = data[uid]
    # Update username / display_name if provided
    if username:
        u["username"] = username
    if display_name:
        u["display_name"] = display_name

    # Check if week has rolled over, reset weekly count
    if u.get("current_week", 0) != current_week:
        u["weekly_messages"] = 0
        u["current_week"] = current_week
        save_activity_data(data)

    return u

def record_message(user_id, username="", display_name="", char_count=0):
    """
    Records a sent message for a user.
    Increments total_messages and weekly_messages.
    Awards XP points with anti-spam cooldown.
    """
    uid = str(user_id)
    data = load_activity_data()
    current_week = _get_current_week_number()

    u = data.setdefault(uid, {
        "user_id": uid,
        "username": username or uid,
        "display_name": display_name or username or uid,
        "total_messages": 0,
        "weekly_messages": 0,
        "current_week": current_week,
        "xp": 0,
        "level": 1,
        "first_seen": int(time.time()),
        "last_active": int(time.time())
    })

    if username:
        u["username"] = username
    if display_name:
        u["display_name"] = display_name

    # Reset weekly count if week rolled over
    if u.get("current_week", 0) != current_week:
        u["weekly_messages"] = 0
        u["current_week"] = current_week

    u["total_messages"] = u.get("total_messages", 0) + 1
    u["weekly_messages"] = u.get("weekly_messages", 0) + 1
    u["last_active"] = int(time.time())

    # Award XP (with 7 seconds cooldown per user)
    now = time.time()
    last_xp_time = _user_msg_cooldown.get(uid, 0)
    if (now - last_xp_time) >= 7:
        _user_msg_cooldown[uid] = now
        xp_gain = 5 if char_count > 10 else 3
        u["xp"] = u.get("xp", 0) + xp_gain
        # Level formula: level = floor(sqrt(xp / 30)) + 1
        u["level"] = int((u["xp"] / 30) ** 0.5) + 1

    save_activity_data(data)
    return u

def get_server_leaderboard(sort_by="total", limit=10):
    """
    Returns sorted list of all active users.
    sort_by: 'total' for total messages, 'weekly' for weekly messages, 'xp' for activity points.
    """
    data = load_activity_data()
    current_week = _get_current_week_number()

    users_list = []
    for uid, u in data.items():
        # Check weekly reset on readout
        weekly = u.get("weekly_messages", 0) if u.get("current_week", 0) == current_week else 0
        users_list.append({
            "user_id": uid,
            "username": u.get("username", uid),
            "display_name": u.get("display_name", u.get("username", uid)),
            "total_messages": u.get("total_messages", 0),
            "weekly_messages": weekly,
            "xp": u.get("xp", 0),
            "level": u.get("level", 1)
        })

    if sort_by == "weekly":
        users_list.sort(key=lambda x: (x["weekly_messages"], x["total_messages"], x["xp"]), reverse=True)
    elif sort_by == "xp":
        users_list.sort(key=lambda x: (x["xp"], x["total_messages"]), reverse=True)
    else:  # total
        users_list.sort(key=lambda x: (x["total_messages"], x["xp"]), reverse=True)

    # Assign rank index (1-based)
    for idx, item in enumerate(users_list):
        item["rank"] = idx + 1

    return users_list[:limit] if limit else users_list

def get_user_rank_and_title(user_id, username="", display_name=""):
    """
    Calculates exact rank in server, derives custom image title & card theme.
    Returns dictionary with:
    - rank: integer (e.g. 1, 2, 5, 23)
    - title: text (e.g. '👑 ملك التفاعل', '🥈 متفاعل دائم', '✨ متفاعل', 'عضو نشيط')
    - theme: 'gold' | 'purple' | 'dark'
    - total_messages, weekly_messages, xp, level
    """
    all_sorted = get_server_leaderboard(sort_by="total", limit=0)
    uid = str(user_id)

    user_entry = None
    for item in all_sorted:
        if item["user_id"] == uid:
            user_entry = item
            break

    if not user_entry:
        u = get_user_profile(user_id, username, display_name)
        user_entry = {
            "user_id": uid,
            "username": u["username"],
            "display_name": u["display_name"],
            "total_messages": u["total_messages"],
            "weekly_messages": u["weekly_messages"],
            "xp": u["xp"],
            "level": u["level"],
            "rank": len(all_sorted) + 1
        }

    rank = user_entry.get("rank", 999)
    level = user_entry.get("level", 1)

    # Determine Title and Theme according to specifications
    if rank == 1:
        title = "👑 ملك التفاعل"
        theme = "gold"
    elif rank == 2:
        title = "🥈 متفاعل دائم"
        theme = "purple"
    elif 3 <= rank <= 10:
        title = "✨ متفاعل"
        theme = "purple"
    else:
        # For rank > 10
        if level >= 15:
            title = "⭐ عضو أسطوري"
        elif level >= 10:
            title = "💎 عضو متميز"
        elif level >= 5:
            title = "🔥 عضو متفاعل"
        else:
            title = "🌱 عضو نشيط"
        theme = "dark"

    user_entry["title"] = title
    user_entry["theme"] = theme
    return user_entry
