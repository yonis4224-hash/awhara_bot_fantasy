import random
import game_data


def player_condition_factor(p):
    cond = p["condition"] if "condition" in p.keys() else 100
    mor = p["morale"] if "morale" in p.keys() else 90
    return (0.6 + 0.4 * cond / 100) * (0.93 + 0.07 * mor / 100)


def team_strength(players, formation, tactic, training_invest, t_full=None):
    f = game_data.FORMATIONS[formation]
    groups = {"GK": [], "DEF": [], "MID": [], "ATT": []}
    for p in players:
        groups[p["position"]].append(p)
    for k in groups:
        groups[k].sort(key=lambda x: x["ovr"], reverse=True)

    starters = []
    for pos in ["GK", "DEF", "MID", "ATT"]:
        starters += groups[pos][:f[pos]]
    avg_cond = sum(p["condition"] for p in starters) / len(starters) if starters else 100
    avg_mor = sum(p["morale"] for p in starters) / len(starters) if starters else 90
    cond_factor = (0.6 + 0.4 * avg_cond / 100) * (0.93 + 0.07 * avg_mor / 100)

    att = 0.0
    for p in groups["ATT"][:f["ATT"]]:
        att += p["sho"] * 0.40 + p["dri"] * 0.30 + p["pac"] * 0.30 + p["phy"] * 0.10
    for p in groups["MID"][:f["MID"]]:
        att += (p["pas"] * 0.40 + p["dri"] * 0.30 + p["sho"] * 0.15 + p["phy"] * 0.15) * 0.5

    deff = 0.0
    for p in groups["DEF"][:f["DEF"]]:
        deff += p["def"] * 0.55 + p["phy"] * 0.30 + p["pac"] * 0.15
    for p in groups["GK"][:f["GK"]]:
        deff += (p["def"] * 0.60 + p["phy"] * 0.40) * 1.2
    for p in groups["MID"][:f["MID"]]:
        deff += (p["def"] * 0.40 + p["phy"] * 0.20) * 0.3

    att *= cond_factor
    deff *= cond_factor

    ment = game_data.MENTALITY[tactic]
    att *= ment["attack"]
    deff *= ment["defense"]

    if t_full:
        pf = game_data.PASSING_FOCUS.get(t_full["passing"], game_data.PASSING_FOCUS["مختلط"])
        pr = game_data.PRESSING.get(t_full["pressing"], game_data.PRESSING["متوسط"])
        mk = game_data.MARKING.get(t_full["marking"], game_data.MARKING["منطقة"])
        tp = game_data.TEMPO.get(t_full["tempo"], game_data.TEMPO["عادي"])
        att *= pf["attack"] * pr["attack"] * mk["attack"] * tp["attack"]
        deff *= pf["defense"] * pr["defense"] * mk["defense"] * tp["defense"]
        if t_full["counter"] == "نعم":
            att *= 1.04
        if t_full["offside"] == "نعم":
            deff *= 1.03

    train = min(training_invest, game_data.CONFIG["TRAIN_MAX_XP"])
    tb = train / game_data.CONFIG["TRAIN_MAX_XP"]
    att *= (1 + tb * 0.35)
    deff *= (1 + tb * 0.25)

    return att, deff


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
    ca, cd = team_strength(
        challenger["players"], challenger["formation"], challenger["tactic"], challenger["training"],
        challenger.get("tactics"),
    )
    oa, od = team_strength(
        opponent["players"], opponent["formation"], opponent["tactic"], opponent["training"],
        opponent.get("tactics"),
    )

    cb = counter_bonus(challenger["tactic"], opponent["tactic"])
    ca *= (1 + cb["A"])
    oa *= (1 + cb["B"])

    ci = squad_identity(ca, cd)
    oi = squad_identity(oa, od)

    notes = []
    if ci == "هجومي" and challenger["tactic"] == "دفاعي":
        pen = 0.16 if opponent["tactic"] in ("هجومي", "متوازن") else 0.05
        cd *= (1 - pen)
        ca *= (1 - pen)
        notes.append(f"⚠️ فريقك هجومي لكنك دافعت → عوقبتَ ({int(pen*100)}%)")
    elif ci == "دفاعي" and challenger["tactic"] == "هجومي":
        pen = 0.16 if opponent["tactic"] in ("دفاعي", "متوازن") else 0.05
        cd *= (1 - pen)
        ca *= (1 - pen)
        notes.append(f"⚠️ فريقك دفاعي لكنك هاجمت → عوقبتَ ({int(pen*100)}%)")

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
