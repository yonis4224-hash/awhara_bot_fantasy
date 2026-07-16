import sqlite3
import json
import random
import os
import game_data
import market_data

DB_PATH = os.getenv("DB_PATH", "ohara.db")
CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
CONN.row_factory = sqlite3.Row


def _add_col(table, col, ctype, default=None):
    c = CONN.cursor()
    try:
        if default is None:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}")
        else:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ctype} DEFAULT {default}")
        CONN.commit()
    except sqlite3.OperationalError:
        pass


def init_db():
    c = CONN.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS coaches (
        discord_id TEXT PRIMARY KEY,
        username TEXT,
        team_id INTEGER
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        owner_id TEXT,
        budget INTEGER,
        xp INTEGER,
        formation TEXT DEFAULT '4-3-3',
        tactic TEXT DEFAULT 'متوازن',
        training_invest INTEGER DEFAULT 0,
        league_id INTEGER DEFAULT 0,
        tokens INTEGER DEFAULT 50,
        level INTEGER DEFAULT 1,
        reputation INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        titles INTEGER DEFAULT 0,
        passing TEXT DEFAULT 'مختلط',
        pressing TEXT DEFAULT 'متوسط',
        marking TEXT DEFAULT 'منطقة',
        tempo TEXT DEFAULT 'عادي',
        counter TEXT DEFAULT 'لا',
        offside TEXT DEFAULT 'لا',
        captain_pid INTEGER DEFAULT 0,
        setpiece_pid INTEGER DEFAULT 0
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        position TEXT,
        rating INTEGER,
        price INTEGER,
        team_id INTEGER,
        club_id INTEGER DEFAULT 0,
        league_id INTEGER DEFAULT 0,
        pac INTEGER DEFAULT 70,
        sho INTEGER DEFAULT 70,
        pas INTEGER DEFAULT 70,
        dri INTEGER DEFAULT 70,
        def INTEGER DEFAULT 70,
        phy INTEGER DEFAULT 70,
        ovr INTEGER DEFAULT 70,
        age INTEGER DEFAULT 25,
        condition INTEGER DEFAULT 100,
        morale INTEGER DEFAULT 90,
        foot TEXT DEFAULT 'يمين',
        work_rate TEXT DEFAULT 'متوسط/متوسط',
        special TEXT DEFAULT ''
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS leagues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        owner_id TEXT,
        members TEXT DEFAULT '[]',
        status TEXT DEFAULT 'open'
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS pending_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenger_id TEXT,
        opponent_id TEXT,
        league_id INTEGER DEFAULT 0,
        challenger_ready INTEGER DEFAULT 0,
        opponent_ready INTEGER DEFAULT 0
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS player_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        event TEXT,
        amount INTEGER DEFAULT 0,
        from_id TEXT DEFAULT '',
        to_id TEXT DEFAULT '',
        time TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        buyer_id TEXT,
        amount INTEGER,
        status TEXT DEFAULT 'pending',
        time TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        team_id INTEGER PRIMARY KEY,
        stadium INTEGER DEFAULT 1,
        training INTEGER DEFAULT 1,
        medical INTEGER DEFAULT 1,
        youth INTEGER DEFAULT 1
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        league_id INTEGER,
        round INTEGER DEFAULT 0,
        total_rounds INTEGER DEFAULT 0,
        fixtures TEXT DEFAULT '[]',
        standings TEXT DEFAULT '{}',
        status TEXT DEFAULT 'active'
    )""")

    # ترحيل الأعمدة إن وُجدت قاعدة قديمة
    _add_col("teams", "tokens", "INTEGER", 50)
    _add_col("teams", "level", "INTEGER", 1)
    _add_col("teams", "reputation", "INTEGER", 0)
    _add_col("teams", "wins", "INTEGER", 0)
    _add_col("teams", "losses", "INTEGER", 0)
    _add_col("teams", "draws", "INTEGER", 0)
    _add_col("teams", "titles", "INTEGER", 0)
    _add_col("teams", "passing", "TEXT", "'مختلط'")
    _add_col("teams", "pressing", "TEXT", "'متوسط'")
    _add_col("teams", "marking", "TEXT", "'منطقة'")
    _add_col("teams", "tempo", "TEXT", "'عادي'")
    _add_col("teams", "counter", "TEXT", "'لا'")
    _add_col("teams", "offside", "TEXT", "'لا'")
    _add_col("teams", "captain_pid", "INTEGER", 0)
    _add_col("teams", "setpiece_pid", "INTEGER", 0)
    for col in ["pac", "sho", "pas", "dri", "def", "phy", "ovr", "age", "condition", "morale", "foot", "work_rate", "special"]:
        _add_col("players", col, "INTEGER" if col in ("pac","sho","pas","dri","def","phy","ovr","age","condition","morale") else "TEXT", "''" if col in ("foot","work_rate","special") else 70 if col != "condition" else 100)

    c.execute("SELECT COUNT(*) FROM players")
    if c.fetchone()[0] == 0:
        for p in market_data.PLAYERS:
            c.execute(
                "INSERT INTO players (id, name, position, rating, price, team_id, club_id, league_id, "
                "pac, sho, pas, dri, def, phy, ovr, age, condition, morale, foot, work_rate, special) "
                "VALUES (?,?,?,?,?,NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (p["id"], p["name"], p["position"], p["rating"], p["price"], p["club_id"], p["league_id"],
                 p["pac"], p["sho"], p["pas"], p["dri"], p["def"], p["phy"], p["ovr"], p["age"],
                 p["condition"], p["morale"], p["foot"], p["work_rate"], p["special"]),
            )
    CONN.commit()


# ---------------------------------------------------------------------------
# السجل التاريخي
# ---------------------------------------------------------------------------
def add_history(player_id, event, amount=0, from_id="", to_id=""):
    c = CONN.cursor()
    c.execute("INSERT INTO player_history (player_id, event, amount, from_id, to_id) VALUES (?,?,?,?,?)",
              (player_id, event, amount, from_id, to_id))
    CONN.commit()


def get_history(player_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM player_history WHERE player_id=? ORDER BY time DESC LIMIT 20", (player_id,))
    return c.fetchall()


# ---------------------------------------------------------------------------
# الدوريات والأنشية (بيانات ثابتة)
# ---------------------------------------------------------------------------
def get_leagues_list():
    return market_data.LEAGUES


def get_clubs_by_league(league_id):
    return [c for c in market_data.CLUBS if c["league_id"] == league_id]


def get_club(club_id):
    for c in market_data.CLUBS:
        if c["id"] == club_id:
            return c
    return None


def get_league(league_id):
    for l in market_data.LEAGUES:
        if l["id"] == league_id:
            return l
    return None


# ---------------------------------------------------------------------------
# السوق
# ---------------------------------------------------------------------------
def get_market_players_by_club(club_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE club_id=? AND team_id IS NULL ORDER BY ovr DESC", (club_id,))
    return c.fetchall()


def get_market_players_by_league(league_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE league_id=? AND team_id IS NULL ORDER BY ovr DESC", (league_id,))
    return c.fetchall()


def market_players():
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE team_id IS NULL ORDER BY ovr DESC")
    return c.fetchall()


def get_free_agents():
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE team_id IS NULL AND club_id=0 ORDER BY ovr DESC LIMIT 25")
    return c.fetchall()


# ---------------------------------------------------------------------------
# المدربون والفرق
# ---------------------------------------------------------------------------
def get_coach(discord_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM coaches WHERE discord_id=?", (discord_id,))
    return c.fetchone()


def create_coach(discord_id, username, team_id):
    c = CONN.cursor()
    c.execute("INSERT OR REPLACE INTO coaches (discord_id, username, team_id) VALUES (?,?,?)",
              (discord_id, username, team_id))
    CONN.commit()


def create_team(name, owner_id):
    c = CONN.cursor()
    c.execute(
        "INSERT INTO teams (name, owner_id, budget, xp, tokens) VALUES (?,?,?,?,?)",
        (name, owner_id, game_data.CONFIG["START_BUDGET"], game_data.CONFIG["START_XP"], game_data.CONFIG["START_TOKENS"]),
    )
    CONN.commit()
    tid = c.lastrowid
    c.execute("INSERT OR IGNORE INTO facilities (team_id) VALUES (?)", (tid,))
    CONN.commit()
    available = c.execute("SELECT id FROM players WHERE team_id IS NULL ORDER BY RANDOM() LIMIT 11").fetchall()
    for row in available:
        c.execute("UPDATE players SET team_id=? WHERE id=?", (tid, row["id"]))
        add_history(row["id"], "تعاقد", 0, owner_id, str(tid))
    CONN.commit()
    return tid


def get_team(team_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM teams WHERE id=?", (team_id,))
    return c.fetchone()


def get_team_by_owner(owner_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM teams WHERE owner_id=?", (owner_id,))
    return c.fetchone()


def update_team(team_id, **fields):
    c = CONN.cursor()
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values())
    vals.append(team_id)
    c.execute(f"UPDATE teams SET {sets} WHERE id=?", vals)
    CONN.commit()


def get_player(pid):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE id=?", (pid,))
    return c.fetchone()


def team_players(team_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE team_id=? ORDER BY ovr DESC", (team_id,))
    return c.fetchall()


def team_starters(team_id, formation):
    f = game_data.FORMATIONS[formation]
    c = CONN.cursor()
    players = c.execute("SELECT * FROM players WHERE team_id=? ORDER BY ovr DESC", (team_id,)).fetchall()
    groups = {"GK": [], "DEF": [], "MID": [], "ATT": []}
    for p in players:
        groups[p["position"]].append(p)
    chosen = []
    for pos in ["GK", "DEF", "MID", "ATT"]:
        chosen += groups[pos][:f[pos]]
    return chosen


def buy_player(pid, team_id, price, buyer_id=""):
    c = CONN.cursor()
    p = c.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone()
    c.execute("UPDATE players SET team_id=? WHERE id=?", (team_id, pid))
    c.execute("UPDATE teams SET budget=budget-? WHERE id=?", (price, team_id))
    add_history(pid, "شراء", price, buyer_id, str(team_id))
    CONN.commit()


def sell_player(pid, price, seller_id=""):
    c = CONN.cursor()
    c.execute("UPDATE players SET team_id=NULL WHERE id=?", (pid,))
    c.execute("UPDATE teams SET budget=budget+? WHERE id=(SELECT team_id FROM players WHERE id=?)",
              (price, pid))
    add_history(pid, "بيع", price, seller_id, "")
    CONN.commit()


def release_player(pid):
    c = CONN.cursor()
    c.execute("UPDATE players SET team_id=NULL WHERE id=?", (pid,))
    add_history(pid, "طرد")
    CONN.commit()


def develop_player(pid, new_rating, new_price):
    c = CONN.cursor()
    c.execute("UPDATE players SET rating=?, price=? WHERE id=?", (new_rating, new_price, pid))
    CONN.commit()


def update_player(pid, **fields):
    c = CONN.cursor()
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values())
    vals.append(pid)
    c.execute(f"UPDATE players SET {sets} WHERE id=?", vals)
    CONN.commit()


def resign(discord_id):
    c = CONN.cursor()
    c.execute("SELECT team_id FROM coaches WHERE discord_id=?", (discord_id,))
    row = c.fetchone()
    if not row or not row["team_id"]:
        return False
    team_id = row["team_id"]
    c.execute("UPDATE players SET team_id=NULL WHERE team_id=?", (team_id,))
    c.execute("DELETE FROM pending_matches WHERE challenger_id=? OR opponent_id=?",
              (discord_id, discord_id))
    c.execute("DELETE FROM facilities WHERE team_id=?", (team_id,))
    c.execute("DELETE FROM seasons WHERE league_id IN (SELECT id FROM leagues WHERE owner_id=?)", (discord_id,))
    c.execute("DELETE FROM teams WHERE id=?", (team_id,))
    c.execute("DELETE FROM coaches WHERE discord_id=?", (discord_id,))
    CONN.commit()
    return True


# ---------------------------------------------------------------------------
# الرموز والسمعة والمستوى
# ---------------------------------------------------------------------------
def add_tokens(team_id, amount):
    c = CONN.cursor()
    c.execute("UPDATE teams SET tokens=tokens+? WHERE id=?", (amount, team_id))
    CONN.commit()


def spend_tokens(team_id, amount):
    c = CONN.cursor()
    row = c.execute("SELECT tokens FROM teams WHERE id=?", (team_id,)).fetchone()
    if not row or row["tokens"] < amount:
        return False
    c.execute("UPDATE teams SET tokens=tokens-? WHERE id=?", (amount, team_id))
    CONN.commit()
    return True


def add_reputation(team_id, amount):
    c = CONN.cursor()
    c.execute("UPDATE teams SET reputation=reputation+? WHERE id=?", (amount, team_id))
    CONN.commit()


def record_result(team_id, result):
    c = CONN.cursor()
    t = c.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()
    xp = game_data.CONFIG["WIN_XP" if result == "فوز" else ("DRAW_XP" if result == "تعادل" else "LOSS_XP")]
    money = game_data.CONFIG["WIN_MONEY" if result == "فوز" else ("DRAW_MONEY" if result == "تعادل" else "LOSS_MONEY")]
    tokens = game_data.CONFIG["WIN_TOKENS" if result == "فوز" else ("DRAW_TOKENS" if result == "تعادل" else "LOSS_TOKENS")]
    col = {"فوز": "wins", "تعادل": "draws", "خسارة": "losses"}[result]
    new_xp = t["xp"] + xp
    new_level = t["level"]
    level_up = False
    while new_xp >= new_level * 1000:
        new_xp -= new_level * 1000
        new_level += 1
        level_up = True
    c.execute(
        f"UPDATE teams SET {col}={col}+1, xp=?, budget=budget+?, tokens=tokens+?, level=?, reputation=reputation+? WHERE id=?",
        (new_xp, money, tokens, new_level, (10 if result == "فوز" else 3), team_id),
    )
    CONN.commit()
    return level_up, new_level


# ---------------------------------------------------------------------------
# التدريب والراحة
# ---------------------------------------------------------------------------
def train_drill(team_id, drill_key, level, investment):
    c = CONN.cursor()
    players = c.execute("SELECT * FROM players WHERE team_id=?", (team_id,)).fetchall()
    fac = get_facilities(team_id)
    training_bonus = game_data.FACILITIES["training"]["levels"][fac["training"] - 1]["bonus"]
    attrs = game_data.DRILLS[drill_key]["attrs"]
    for p in players:
        new_attrs = {k: p[k] for k in game_data.ATTR_KEYS}
        for a in attrs:
            gain = random.randint(1, 2) + training_bonus + (1 if p["age"] <= 24 else 0)
            new_attrs[a] = min(99, new_attrs[a] + gain)
        new_ovr = market_data.compute_ovr(p["position"], new_attrs)
        # فقدان الجاهزية والروح بسبب التدريب
        cond = max(40, p["condition"] - random.randint(6, 12))
        mor = max(50, p["morale"] - random.randint(0, 5))
        c.execute(
            "UPDATE players SET pac=?,sho=?,pas=?,dri=?,def=?,phy=?,ovr=?,rating=?,condition=?,morale=? WHERE id=?",
            (new_attrs["pac"], new_attrs["sho"], new_attrs["pas"], new_attrs["dri"],
             new_attrs["def"], new_attrs["phy"], new_ovr, new_ovr, cond, mor, p["id"]),
        )
    # خصم الاستثمار
    c.execute("UPDATE teams SET xp=xp-? WHERE id=?", (investment, team_id))
    CONN.commit()


def reduce_condition(team_id, amount):
    c = CONN.cursor()
    players = c.execute("SELECT * FROM players WHERE team_id=?", (team_id,)).fetchall()
    for p in players:
        cond = max(30, p["condition"] - amount)
        c.execute("UPDATE players SET condition=? WHERE id=?", (cond, p["id"]))
    CONN.commit()


def rest_team(team_id):
    c = CONN.cursor()
    fac = get_facilities(team_id)
    recover = game_data.FACILITIES["medical"]["levels"][fac["medical"] - 1]["recover"]
    players = c.execute("SELECT * FROM players WHERE team_id=?", (team_id,)).fetchall()
    for p in players:
        cond = min(100, p["condition"] + recover + random.randint(0, 8))
        mor = min(100, p["morale"] + random.randint(2, 8))
        c.execute("UPDATE players SET condition=?, morale=? WHERE id=?", (cond, mor, p["id"]))
    CONN.commit()
    return recover


# ---------------------------------------------------------------------------
# المنشآت
# ---------------------------------------------------------------------------
def get_facilities(team_id):
    c = CONN.cursor()
    row = c.execute("SELECT * FROM facilities WHERE team_id=?", (team_id,)).fetchone()
    if not row:
        c.execute("INSERT OR IGNORE INTO facilities (team_id) VALUES (?)", (team_id,))
        CONN.commit()
        row = c.execute("SELECT * FROM facilities WHERE team_id=?", (team_id,)).fetchone()
    return row


def upgrade_facility(team_id, key):
    fac = get_facilities(team_id)
    cur = fac[key]
    spec = game_data.FACILITIES[key]
    if cur >= len(spec["levels"]):
        return False, "وصلت لأعلى مستوى"
    next_lvl = spec["levels"][cur]
    cost = next_lvl["cost"]
    team = get_team(team_id)
    if team["budget"] < cost:
        return False, f"ميزانيتك ({team['budget']}م) لا تكفي (تحتاج {cost}م)"
    c = CONN.cursor()
    c.execute(f"UPDATE facilities SET {key}=? WHERE team_id=?", (cur + 1, team_id))
    c.execute("UPDATE teams SET budget=budget-? WHERE id=?", (cost, team_id))
    CONN.commit()
    return True, cost


# ---------------------------------------------------------------------------
# الكشافة (استقدام لاعبين أحرار)
# ---------------------------------------------------------------------------
def scout_player(team_id):
    fac = get_facilities(team_id)
    youth_bonus = game_data.FACILITIES["youth"]["levels"][fac["youth"] - 1]["quality"]
    c = CONN.cursor()
    pid = c.execute("SELECT MAX(id) FROM players").fetchone()[0] or 0
    pid += 1
    name = f"{random.choice(market_data.FIRST_NAMES)} {random.choice(market_data.LAST_NAMES)}"
    roll = random.random()
    pos = "GK" if roll < 0.12 else ("DEF" if roll < 0.45 else ("MID" if roll < 0.8 else "ATT"))
    base = random.randint(78, 88) + youth_bonus
    p = market_data.generate_player(name, pos, base, 0, 0, age=random.randint(17, 22))
    p["id"] = pid
    p["condition"] = 100
    p["morale"] = 100
    c.execute(
        "INSERT INTO players (id, name, position, rating, price, team_id, club_id, league_id, "
        "pac, sho, pas, dri, def, phy, ovr, age, condition, morale, foot, work_rate, special) "
        "VALUES (?,?,?,?,?,NULL,0,0,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (pid, p["name"], p["position"], p["rating"], p["price"], p["pac"], p["sho"], p["pas"],
         p["dri"], p["def"], p["phy"], p["ovr"], p["age"], p["condition"], p["morale"],
         p["foot"], p["work_rate"], p["special"]),
    )
    CONN.commit()
    return p


# ---------------------------------------------------------------------------
# الدوريات
# ---------------------------------------------------------------------------
def get_leagues():
    c = CONN.cursor()
    c.execute("SELECT * FROM leagues")
    return c.fetchall()


def create_league(name, owner_id):
    c = CONN.cursor()
    c.execute("INSERT INTO leagues (name, owner_id, members) VALUES (?,?,?)",
              (name, owner_id, json.dumps([owner_id])))
    CONN.commit()
    return c.lastrowid


def join_league(league_id, discord_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM leagues WHERE id=?", (league_id,))
    row = c.fetchone()
    if not row:
        return False
    members = json.loads(row["members"])
    if discord_id not in members:
        members.append(discord_id)
        c.execute("UPDATE leagues SET members=? WHERE id=?", (json.dumps(members), league_id))
        CONN.commit()
    return True


def get_league(league_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM leagues WHERE id=?", (league_id,))
    return c.fetchone()


def get_league_teams(league_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM teams WHERE league_id=?", (league_id,))
    return c.fetchall()


# ---------------------------------------------------------------------------
# مواسم الدوري (جدول مباريات + ترتيب)
# ---------------------------------------------------------------------------
def create_season(league_id):
    teams = get_league_teams(league_id)
    if len(teams) < 2:
        return None
    ids = [t["id"] for t in teams]
    random.shuffle(ids)
    n = len(ids)
    # جدولة round-robin (مباريات ذهاب فقط لتقصير الموسم)
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a = ids[i]
            b = ids[n - 1 - i]
            pairs.append((a, b))
        ids.insert(1, ids.pop())
        rounds.append(pairs)
    standings = {str(tid): {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0} for tid in ids}
    c = CONN.cursor()
    c.execute("DELETE FROM seasons WHERE league_id=?", (league_id,))
    c.execute("INSERT INTO seasons (league_id, round, total_rounds, fixtures, standings, status) VALUES (?,?,?,?,?,?)",
              (league_id, 0, len(rounds), json.dumps(rounds), json.dumps(standings), "active"))
    CONN.commit()
    return len(rounds)


def get_season(league_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM seasons WHERE league_id=? ORDER BY id DESC LIMIT 1", (league_id,))
    return c.fetchone()


def advance_season(league_id):
    season = get_season(league_id)
    if not season or season["status"] != "active":
        return None
    fixtures = json.loads(season["fixtures"])
    standings = json.loads(season["standings"])
    r = season["round"]
    if r >= len(fixtures):
        return "انتهى"
    results = []
    for a, b in fixtures[r]:
        ga, gb, _, _ = engine_sim(a, b)
        results.append((a, b, ga, gb))
        _apply_standings(standings, a, b, ga, gb)
        reduce_condition(a, game_data.CONFIG["MATCH_CONDITION_COST"])
        reduce_condition(b, game_data.CONFIG["MATCH_CONDITION_COST"])
        if ga > gb:
            record_result(a, "فوز"); record_result(b, "خسارة")
        elif gb > ga:
            record_result(b, "فوز"); record_result(a, "خسارة")
        else:
            record_result(a, "تعادل"); record_result(b, "تعادل")
    new_round = r + 1
    status = "active"
    if new_round >= len(fixtures):
        status = "finished"
        # تحديد البطل
        champ = max(standings.items(), key=lambda kv: (kv[1]["Pts"], kv[1]["GF"] - kv[1]["GA"]))
        c = CONN.cursor()
        c.execute("UPDATE teams SET titles=titles+1 WHERE id=?", (int(champ[0]),))
        CONN.commit()
    c = CONN.cursor()
    c.execute("UPDATE seasons SET round=?, standings=?, status=? WHERE id=?",
              (new_round, json.dumps(standings), status, season["id"]))
    CONN.commit()
    return results


def _apply_standings(standings, a, b, ga, gb):
    sa, sb = standings[str(a)], standings[str(b)]
    sa["P"] += 1
    sb["P"] += 1
    sa["GF"] += ga
    sa["GA"] += gb
    sb["GF"] += gb
    sb["GA"] += ga
    if ga > gb:
        sa["W"] += 1; sa["Pts"] += 3; sb["L"] += 1
    elif gb > ga:
        sb["W"] += 1; sb["Pts"] += 3; sa["L"] += 1
    else:
        sa["D"] += 1; sb["D"] += 1; sa["Pts"] += 1; sb["Pts"] += 1


def engine_sim(team_a_id, team_b_id):
    import engine
    a = db_team_for_sim(team_a_id)
    b = db_team_for_sim(team_b_id)
    return engine.simulate(a, b)


def db_team_for_sim(team_id):
    team = get_team(team_id)
    players = team_starters(team_id, team["formation"])
    return {
        "players": players,
        "formation": team["formation"],
        "tactic": team["tactic"],
        "training": team["training_invest"],
        "tactics": team,
    }


def challenge(challenger_id, opponent_id, league_id=0):
    c = CONN.cursor()
    c.execute("INSERT INTO pending_matches (challenger_id, opponent_id, league_id) VALUES (?,?,?)",
              (challenger_id, opponent_id, league_id))
    CONN.commit()
    return c.lastrowid


def get_pending_for(user_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM pending_matches WHERE challenger_id=? OR opponent_id=?", (user_id, user_id))
    return c.fetchall()


def get_pending(pid):
    c = CONN.cursor()
    c.execute("SELECT * FROM pending_matches WHERE id=?", (pid,))
    return c.fetchone()


def set_ready(pid, user_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM pending_matches WHERE id=?", (pid,))
    row = c.fetchone()
    if not row:
        return
    if row["challenger_id"] == user_id:
        c.execute("UPDATE pending_matches SET challenger_ready=1 WHERE id=?", (pid,))
    else:
        c.execute("UPDATE pending_matches SET opponent_ready=1 WHERE id=?", (pid,))
    CONN.commit()


def delete_pending(pid):
    c = CONN.cursor()
    c.execute("DELETE FROM pending_matches WHERE id=?", (pid,))
    CONN.commit()


def commit():
    CONN.commit()
