import json
import urllib.request
import urllib.parse
import urllib.error
import os
import random
import sys

# Fix terminal encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
elif hasattr(sys.stdout, 'buffer'):
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE_URL = "https://api.msmc.cc/api/fc26/team/"

# Alternative names to try for clubs that fail
CLUB_TEAM_ALT = {
    18: ["Lazio", "S.S. Lazio"],
    19: ["RB Salzburg", "Red Bull Salzburg", "FC Red Bull Salzburg", "Salzburg"],
    23: ["Tottenham", "Tottenham Hotspur", "Spurs"],
    24: ["Newcastle", "Newcastle United", "Newcastle Utd"],
    27: ["West Ham", "West Ham United"],
    34: ["Bournemouth", "AFC Bournemouth"],
    37: ["Norwich", "Norwich City"],
    42: ["Villarreal", "Villarreal CF"],
    44: ["Athletic Club", "Athletic Bilbao", "Athletic"],
    45: ["Sevilla", "Sevilla FC"],
    46: ["Valencia", "Valencia CF"],
    47: ["Getafe", "Getafe CF"],
    48: ["Osasuna", "CA Osasuna"],
    49: ["Girona", "Girona FC"],
    50: ["Celta Vigo", "RC Celta", "RC Celta de Vigo"],
    52: ["Mallorca", "RCD Mallorca"],
    53: ["Las Palmas", "UD Las Palmas"],
    54: ["Alaves", "Deportivo Alaves", "Alavés", "Deportivo Alavés"],
    55: ["Espanyol", "RCD Espanyol"],
    56: ["Leganes", "CD Leganes", "Leganés", "CD Leganés"],
    57: ["Real Valladolid", "Valladolid", "Real Valladolid CF"],
    58: ["Levante", "Levante UD"],
    59: ["Granada", "Granada CF"],
    60: ["Cadiz", "Cádiz", "Cadiz CF", "Cádiz CF"],
    78: ["Crotone", "FC Crotone"],
    79: ["Pisa", "Pisa SC", "AC Pisa"],
    80: ["Bari", "SSC Bari"],
    96: ["Hannover 96", "Hannover"],
    97: ["HSV", "Hamburger SV"],
    98: ["1. FC Köln", "FC Köln", "Köln"],
    99: ["Fortuna Düsseldorf", "Fortuna"],
    100: ["1. FC Nürnberg", "Nürnberg", "FC Nürnberg"],
}

# Mapping of our club IDs to API team names
CLUB_TEAM_MAP = {
    1: "Real Madrid",
    2: "FC Barcelona",
    3: "FC Bayern München",
    4: "Paris SG",
    5: "Juventus",
    6: "Manchester City",
    7: "Liverpool",
    8: "Ajax",
    9: "FC Porto",
    10: "SL Benfica",
    11: "Lombardia FC",
    12: "Chelsea",
    13: "Atlético de Madrid",
    14: "Borussia Dortmund",
    15: "Milano FC",
    16: "Sporting CP",
    17: "Shakhtar Donetsk",
    18: "Lazio",  # will try alt
    19: "FC Red Bull Salzburg",  # will try alt
    20: "Club Brugge",
    21: "Manchester Utd",
    22: "Arsenal",
    23: "Tottenham Hotspur",  # will try alt
    24: "Newcastle United",  # will try alt
    25: "Aston Villa",
    26: "Brighton",
    27: "West Ham United",  # will try alt
    28: "Wolves",
    29: "Crystal Palace",
    30: "Fulham",
    31: "Brentford",
    32: "Everton",
    33: "Nott'm Forest",
    34: "Bournemouth",  # will try alt
    35: "Leicester City",
    36: "Southampton",
    37: "Norwich City",  # will try alt
    38: "Leeds United",
    39: "Burnley",
    40: "Watford",
    41: "Real Sociedad",
    42: "Villarreal",  # will try alt
    43: "Real Betis",
    44: "Athletic Bilbao",  # will try alt
    45: "Sevilla",  # will try alt
    46: "Valencia",  # will try alt
    47: "Getafe",  # will try alt
    48: "Osasuna",  # will try alt
    49: "Girona",  # will try alt
    50: "Celta Vigo",  # will try alt
    51: "Rayo Vallecano",
    52: "Mallorca",  # will try alt
    53: "Las Palmas",  # will try alt
    54: "Alavés",  # will try alt
    55: "Espanyol",  # will try alt
    56: "Leganés",  # will try alt
    57: "Real Valladolid",  # will try alt
    58: "Levante",  # will try alt
    59: "Granada",  # will try alt
    60: "Cádiz",  # will try alt
    61: "Napoli",
    62: "Roma",
    63: "Atalanta",
    64: "Fiorentina",
    65: "Bologna",
    66: "Torino",
    67: "Udinese",
    68: "Genoa",
    69: "Monza",
    70: "Lecce",
    71: "Hellas Verona",
    72: "Cagliari",
    73: "Empoli",
    74: "Parma",
    75: "Como",
    76: "Venezia",
    77: "Sassuolo",
    78: "Crotone",
    79: "Pisa",
    80: "Bari",
    81: "Leverkusen",
    82: "RB Leipzig",
    83: "Eintracht Frankfurt",
    84: "VfB Stuttgart",
    85: "VfL Wolfsburg",
    86: "Mainz 05",
    87: "Borussia Mönchengladbach",
    88: "Union Berlin",
    89: "Werder Bremen",
    90: "FC Augsburg",
    91: "TSG Hoffenheim",
    92: "1. FC Heidenheim",
    93: "FC St. Pauli",
    94: "VfL Bochum",
    95: "SC Freiburg",
    96: "Hannover 96",
    97: "Hamburger SV",
    98: "1. FC Köln",
    99: "Fortuna Düsseldorf",
    100: "1. FC Nürnberg",
}

LEAGUE_MAP = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

# Map API position to our system
def map_position(pos):
    if pos == "GK": return "GK"
    if pos in ("CB", "LB", "RB", "LWB", "RWB"): return "DEF"
    return "MID" if pos in ("CDM", "CM", "CAM", "LM", "RM", "LW", "RW") else "ATT"

# Map API position to detail position
def map_position_detail(pos):
    mapping = {
        "GK": "GK",
        "CB": "DEF", "LB": "DEF", "RB": "DEF", "LWB": "DEF", "RWB": "DEF",
        "CDM": "MID", "CM": "MID", "CAM": "MID", "LM": "MID", "RM": "MID",
        "LW": "MID", "RW": "MID",
        "ST": "ATT", "CF": "ATT", "LF": "ATT", "RF": "ATT",
    }
    return mapping.get(pos, "MID")

def fetch_team(api_name):
    encoded = urllib.parse.quote(api_name, safe='')
    url = BASE_URL + encoded
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data
    except Exception as e:
        return None

def fetch_team_with_alt(club_id, api_name):
    data = fetch_team(api_name)
    if data:
        return api_name, data
    # Try alternatives
    if club_id in CLUB_TEAM_ALT:
        for alt in CLUB_TEAM_ALT[club_id]:
            data = fetch_team(alt)
            if data:
                return alt, data
    return None, None

def convert_player(p, pid, club_id, league_id):
    pac = int(p.get("PAC", 50))
    sho = int(p.get("SHO", 50))
    pas = int(p.get("PAS", 50))
    dri = int(p.get("DRI", 50))
    deff = int(p.get("DEF", 50))
    phy = int(p.get("PHY", 50))
    ovr = int(p.get("OVR", 50))
    
    pos_api = p.get("Position", "ST")
    pos = map_position_detail(pos_api)
    
    foot = p.get("Preferred foot", "Right")
    weak_foot = int(p.get("Weak foot", 3))
    skill_moves = int(p.get("Skill moves", 3))
    
    age = int(p.get("Age", 25))
    age_mod = 1.15 if age <= 23 else (1.0 if age <= 29 else 0.85)
    price = int(ovr * 150 * age_mod) + random.randint(-20, 30)
    price = max(30, price)
    
    return {
        "id": pid,
        "name": p.get("Name", "Unknown"),
        "position": pos,
        "position_detail": pos_api,
        "pac": pac,
        "sho": sho,
        "pas": pas,
        "dri": dri,
        "def": deff,
        "phy": phy,
        "ovr": ovr,
        "rating": ovr,
        "price": price,
        "age": age,
        "condition": 100,
        "morale": random.randint(70, 100),
        "foot": foot,
        "weak_foot": weak_foot,
        "skill_moves": skill_moves,
        "work_rate": random.choice(["منخفض", "متوسط", "عالي"]),
        "special": "",
        "play_styles": p.get("play style", []),
        "height": p.get("Height", ""),
        "weight": p.get("Weight", ""),
        "nation": p.get("Nation", ""),
        "gkdiving": int(p.get("GK Diving", 0)) if p.get("GK Diving") else 0,
        "gkhandling": int(p.get("GK Handling", 0)) if p.get("GK Handling") else 0,
        "gkkicking": int(p.get("GK Kicking", 0)) if p.get("GK Kicking") else 0,
        "gkpositioning": int(p.get("GK Positioning", 0)) if p.get("GK Positioning") else 0,
        "gkreflexes": int(p.get("GK Reflexes", 0)) if p.get("GK Reflexes") else 0,
        "club_id": club_id,
        "league_id": league_id,
    }

def main():
    all_players = []
    pid = 1
    found = 0
    not_found = []
    
    for club_id in sorted(CLUB_TEAM_MAP.keys()):
        api_name = CLUB_TEAM_MAP[club_id]
        league_id = 1 if club_id <= 20 else (2 if club_id <= 40 else (3 if club_id <= 60 else (4 if club_id <= 80 else 5)))
        
        used_name, team_data = fetch_team_with_alt(club_id, api_name)
        
        if team_data and len(team_data) > 0:
            for p in team_data:
                player = convert_player(p, pid, club_id, league_id)
                all_players.append(player)
                pid += 1
            found += 1
            safe = used_name.encode('ascii', 'replace').decode('ascii')
            sys.stdout.write(f"OK [{club_id}] {safe} ({len(team_data)} players)\n")
        else:
            not_found.append(club_id)
            safe = api_name.encode('ascii', 'replace').decode('ascii')
            sys.stdout.write(f"XX [{club_id}] {safe} - NOT FOUND\n")
        sys.stdout.flush()
    
    sys.stdout.write(f"\n=== RESULTS ===\n")
    sys.stdout.write(f"Teams found: {found}/100\n")
    sys.stdout.write(f"Total players: {len(all_players)}\n")
    if not_found:
        sys.stdout.write(f"Not found clubs: {not_found}\n")
    
    with open("market_data_fc26.py", "w", encoding="utf-8") as f:
        f.write("PLAYERS = ")
        json.dump(all_players, f, ensure_ascii=False, indent=2)
        f.write("\n")
    
    sys.stdout.write(f"Saved to market_data_fc26.py\n")

if __name__ == "__main__":
    main()
