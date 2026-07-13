import random
import game_data

def team_strength(players, formation, tactic, training_invest):
    f = game_data.FORMATIONS[formation]
    groups = {"GK": [], "DEF": [], "MID": [], "ATT": []}
    for p in players:
        groups[p["position"]].append(p["rating"])
    for k in groups:
        groups[k].sort(reverse=True)

    gk = groups["GK"][0] if groups["GK"] else 50
    def_sum = sum(groups["DEF"][:f["DEF"]]) or 50
    mid_sum = sum(groups["MID"][:f["MID"]]) or 50
    att_sum = sum(groups["ATT"][:f["ATT"]]) or 50

    attack = att_sum + mid_sum * 0.4
    defense = def_sum + gk * 0.4 + mid_sum * 0.3

    mod = game_data.TACTICS[tactic]
    attack *= mod["attack"]
    defense *= mod["defense"]

    train = min(training_invest, game_data.CONFIG["TRAIN_MAX_XP"])
    tb = train / game_data.CONFIG["TRAIN_MAX_XP"]
    attack *= (1 + tb * 0.35)
    defense *= (1 + tb * 0.25)

    return attack, defense, att_sum, def_sum, mid_sum


def squad_identity(att_sum, def_sum):
    if att_sum > def_sum * 1.08:
        return "هجومي"
    if def_sum > att_sum * 1.08:
        return "دفاعي"
    return "متوازن"


def counter_bonus(tactic_a, tactic_b):
    beats = game_data.TACTIC_BEATS
    out = {"A": 0.0, "B": 0.0}
    if beats[tactic_a] == tactic_b:
        out["A"] += 0.18
    if beats[tactic_b] == tactic_a:
        out["B"] += 0.18
    return out


def simulate(challenger, opponent):
    ca, cd, ca_att, ca_def, _ = team_strength(
        challenger["players"], challenger["formation"], challenger["tactic"], challenger["training"])
    oa, od, oa_att, oa_def, _ = team_strength(
        opponent["players"], opponent["formation"], opponent["tactic"], opponent["training"])

    cb = counter_bonus(challenger["tactic"], opponent["tactic"])
    ca *= (1 + cb["A"])
    oa *= (1 + cb["B"])

    ci = squad_identity(ca_att, ca_def)
    oi = squad_identity(oa_att, oa_def)

    notes = []
    if ci == "هجومي" and challenger["tactic"] == "دفاعي":
        pen = 0.16 if opponent["tactic"] in ("هجومي", "متوازن") else 0.05
        cd *= (1 - pen)
        ca *= (1 - pen)
        notes.append(f"⚠️ فريقك هجومي لكنك دافعت → عوقبتَ ({int(pen*100)}%) لأن الخصم استغل ضعف دفاعك")
    elif ci == "دفاعي" and challenger["tactic"] == "هجومي":
        pen = 0.16 if opponent["tactic"] in ("دفاعي", "متوازن") else 0.05
        cd *= (1 - pen)
        ca *= (1 - pen)
        notes.append(f"⚠️ فريقك دفاعي لكنك هاجمت → عوقبتَ ({int(pen*100)}%) لأن الخصم استغل ضعف هجومك")

    if oi == "هجومي" and opponent["tactic"] == "دفاعي":
        pen = 0.16 if challenger["tactic"] in ("هجومي", "متوازن") else 0.05
        od *= (1 - pen)
        oa *= (1 - pen)
        notes.append(f"⚠️ خصمك هجومي لكنه دافع → عوقب الخصم ({int(pen*100)}%)")
    elif oi == "دفاعي" and opponent["tactic"] == "هجومي":
        pen = 0.16 if challenger["tactic"] in ("دفاعي", "متوازن") else 0.05
        od *= (1 - pen)
        oa *= (1 - pen)
        notes.append(f"⚠️ خصمك دفاعي لكنه هاجم → عوقب الخصم ({int(pen*100)}%)")

    exp_a = 1.4 * (ca / (ca + od))
    exp_b = 1.4 * (oa / (oa + cd))

    goals_a = max(0, round(exp_a * random.uniform(0.6, 1.4)))
    goals_b = max(0, round(exp_b * random.uniform(0.6, 1.4)))

    if goals_a > goals_b:
        result = "فوز"
    elif goals_b > goals_a:
        result = "خسارة"
    else:
        result = "تعادل"

    return goals_a, goals_b, result, notes
