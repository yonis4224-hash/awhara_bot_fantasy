import sqlite3
import json
import os
import game_data
import market_data

DB_PATH = os.getenv("DB_PATH", "ohara.db")
CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
CONN.row_factory = sqlite3.Row

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
        league_id INTEGER DEFAULT 0
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
        league_id INTEGER DEFAULT 0
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
    c.execute("SELECT COUNT(*) FROM players")
    if c.fetchone()[0] == 0:
        for p in market_data.PLAYERS:
            c.execute("INSERT INTO players (id, name, position, rating, price, team_id, club_id, league_id) "
                      "VALUES (?,?,?,?,?,NULL,?,?)",
                      (p["id"], p["name"], p["position"], p["rating"], p["price"], p["club_id"], p["league_id"]))
    CONN.commit()

def add_history(player_id, event, amount=0, from_id="", to_id=""):
    c = CONN.cursor()
    c.execute("INSERT INTO player_history (player_id, event, amount, from_id, to_id) VALUES (?,?,?,?,?)",
              (player_id, event, amount, from_id, to_id))
    CONN.commit()

def get_history(player_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM player_history WHERE player_id=? ORDER BY time DESC LIMIT 20", (player_id,))
    return c.fetchall()

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

def get_market_players_by_club(club_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE club_id=? AND team_id IS NULL ORDER BY rating DESC", (club_id,))
    return c.fetchall()

def get_market_players_by_league(league_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE league_id=? AND team_id IS NULL ORDER BY rating DESC", (league_id,))
    return c.fetchall()

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
    c.execute("INSERT INTO teams (name, owner_id, budget, xp) VALUES (?,?,?,?)",
              (name, owner_id, game_data.CONFIG["START_BUDGET"], game_data.CONFIG["START_XP"]))
    CONN.commit()
    tid = c.lastrowid
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

def market_players():
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE team_id IS NULL ORDER BY rating DESC")
    return c.fetchall()

def get_player(pid):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE id=?", (pid,))
    return c.fetchone()

def team_players(team_id):
    c = CONN.cursor()
    c.execute("SELECT * FROM players WHERE team_id=? ORDER BY rating DESC", (team_id,))
    return c.fetchall()

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
    c.execute("DELETE FROM teams WHERE id=?", (team_id,))
    c.execute("DELETE FROM coaches WHERE discord_id=?", (discord_id,))
    CONN.commit()
    return True

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
