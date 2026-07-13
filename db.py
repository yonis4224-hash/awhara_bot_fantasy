import sqlite3
import json
import os
import game_data

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
        team_id INTEGER
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
    c.execute("SELECT COUNT(*) FROM players")
    if c.fetchone()[0] == 0:
        for name, pos, rating, price in game_data.PLAYERS:
            c.execute("INSERT INTO players (name, position, rating, price, team_id) VALUES (?,?,?,?,NULL)",
                      (name, pos, rating, price))
    CONN.commit()

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
    return c.lastrowid

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

def buy_player(pid, team_id, price):
    c = CONN.cursor()
    c.execute("UPDATE players SET team_id=? WHERE id=?", (team_id, pid))
    c.execute("UPDATE teams SET budget=budget-? WHERE id=?", (price, team_id))
    CONN.commit()

def sell_player(pid, price):
    c = CONN.cursor()
    c.execute("UPDATE players SET team_id=NULL WHERE id=?", (pid,))
    c.execute("UPDATE teams SET budget=budget+? WHERE id=(SELECT team_id FROM players WHERE id=?)",
              (price, pid))
    CONN.commit()

def develop_player(pid, new_rating, new_price):
    c = CONN.cursor()
    c.execute("UPDATE players SET rating=?, price=? WHERE id=?", (new_rating, new_price, pid))
    CONN.commit()

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
