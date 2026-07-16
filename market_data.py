import random
import game_data

LEAGUES = [
    {"id": 1, "name": "دوري أبطال أوروبا", "flag": "🏆", "emoji": "🏆"},
    {"id": 2, "name": "الدوري الإنجليزي", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"id": 3, "name": "الدوري الإسباني", "flag": "🇪🇸", "emoji": "🇪🇸"},
    {"id": 4, "name": "الدوري الإيطالي", "flag": "🇮🇹", "emoji": "🇮🇹"},
    {"id": 5, "name": "الدوري الألماني", "flag": "🇩🇪", "emoji": "🇩🇪"},
]

CLUBS = [
    {"id": 1, "name": "ريال مدريد", "league_id": 1},
    {"id": 2, "name": "برشلونة", "league_id": 1},
    {"id": 3, "name": "بايرن ميونخ", "league_id": 1},
    {"id": 4, "name": "باريس سان جيرمان", "league_id": 1},
    {"id": 5, "name": "يوفنتوس", "league_id": 1},
    {"id": 6, "name": "مانشستر سيتي", "league_id": 1},
    {"id": 7, "name": "ليفربول", "league_id": 1},
    {"id": 8, "name": "أياكس", "league_id": 1},
    {"id": 9, "name": "بورتو", "league_id": 1},
    {"id": 10, "name": "بنفيكا", "league_id": 1},
    {"id": 11, "name": "إنتر ميلان", "league_id": 1},
    {"id": 12, "name": "تشيلسي", "league_id": 1},
    {"id": 13, "name": "أتلتيكو مدريد", "league_id": 1},
    {"id": 14, "name": "دورتموند", "league_id": 1},
    {"id": 15, "name": "ميلان", "league_id": 1},
    {"id": 16, "name": "سبورتينغ", "league_id": 1},
    {"id": 17, "name": "شاختار", "league_id": 1},
    {"id": 18, "name": "لاتسيو", "league_id": 1},
    {"id": 19, "name": "سالزبورغ", "league_id": 1},
    {"id": 20, "name": "كلوب بروج", "league_id": 1},
    {"id": 21, "name": "مانشستر يونايتد", "league_id": 2},
    {"id": 22, "name": "أرسنال", "league_id": 2},
    {"id": 23, "name": "توتنهام", "league_id": 2},
    {"id": 24, "name": "نيوكاسل", "league_id": 2},
    {"id": 25, "name": "أستون فيلا", "league_id": 2},
    {"id": 26, "name": "برايتون", "league_id": 2},
    {"id": 27, "name": "وست هام", "league_id": 2},
    {"id": 28, "name": "وولفرهامبتون", "league_id": 2},
    {"id": 29, "name": "كريستال بالاس", "league_id": 2},
    {"id": 30, "name": "فولهام", "league_id": 2},
    {"id": 31, "name": "برينتفورد", "league_id": 2},
    {"id": 32, "name": "إيفرتون", "league_id": 2},
    {"id": 33, "name": "نوتنغهام فورست", "league_id": 2},
    {"id": 34, "name": "بورنموث", "league_id": 2},
    {"id": 35, "name": "ليستر سيتي", "league_id": 2},
    {"id": 36, "name": "ساوثهامبتون", "league_id": 2},
    {"id": 37, "name": "نورويتش", "league_id": 2},
    {"id": 38, "name": "ليدز يونايتد", "league_id": 2},
    {"id": 39, "name": "بيرنلي", "league_id": 2},
    {"id": 40, "name": "واتفورد", "league_id": 2},
    {"id": 41, "name": "ريال سوسيداد", "league_id": 3},
    {"id": 42, "name": "فياريال", "league_id": 3},
    {"id": 43, "name": "ريال بيتيس", "league_id": 3},
    {"id": 44, "name": "أتلتيك بيلباو", "league_id": 3},
    {"id": 45, "name": "إشبيلية", "league_id": 3},
    {"id": 46, "name": "فالنسيا", "league_id": 3},
    {"id": 47, "name": "خيتافي", "league_id": 3},
    {"id": 48, "name": "أوساسونا", "league_id": 3},
    {"id": 49, "name": "جيرونا", "league_id": 3},
    {"id": 50, "name": "سيلتا فيغو", "league_id": 3},
    {"id": 51, "name": "رايو فاييكانو", "league_id": 3},
    {"id": 52, "name": "مايوركا", "league_id": 3},
    {"id": 53, "name": "لاس بالماس", "league_id": 3},
    {"id": 54, "name": "ألافيس", "league_id": 3},
    {"id": 55, "name": "إسبانيول", "league_id": 3},
    {"id": 56, "name": "ليغانيس", "league_id": 3},
    {"id": 57, "name": "ريال فايادوليد", "league_id": 3},
    {"id": 58, "name": "ليفانتي", "league_id": 3},
    {"id": 59, "name": "غرناطة", "league_id": 3},
    {"id": 60, "name": "قادش", "league_id": 3},
    {"id": 61, "name": "نابولي", "league_id": 4},
    {"id": 62, "name": "روما", "league_id": 4},
    {"id": 63, "name": "أتالانتا", "league_id": 4},
    {"id": 64, "name": "فيورنتينا", "league_id": 4},
    {"id": 65, "name": "بولونيا", "league_id": 4},
    {"id": 66, "name": "تورينو", "league_id": 4},
    {"id": 67, "name": "أودينيزي", "league_id": 4},
    {"id": 68, "name": "جنوى", "league_id": 4},
    {"id": 69, "name": "مونزا", "league_id": 4},
    {"id": 70, "name": "ليتشي", "league_id": 4},
    {"id": 71, "name": "فيرونا", "league_id": 4},
    {"id": 72, "name": "كالياري", "league_id": 4},
    {"id": 73, "name": "إمبولي", "league_id": 4},
    {"id": 74, "name": "بارما", "league_id": 4},
    {"id": 75, "name": "كومو", "league_id": 4},
    {"id": 76, "name": "فينيزيا", "league_id": 4},
    {"id": 77, "name": "ساسولو", "league_id": 4},
    {"id": 78, "name": "كروتوني", "league_id": 4},
    {"id": 79, "name": "بيزا", "league_id": 4},
    {"id": 80, "name": "باري", "league_id": 4},
    {"id": 81, "name": "باير ليفركوزن", "league_id": 5},
    {"id": 82, "name": "لايبزيغ", "league_id": 5},
    {"id": 83, "name": "آينتراخت فرانكفورت", "league_id": 5},
    {"id": 84, "name": "شتوتغارت", "league_id": 5},
    {"id": 85, "name": "فولفسبورغ", "league_id": 5},
    {"id": 86, "name": "ماينتس", "league_id": 5},
    {"id": 87, "name": "مونشنغلادباخ", "league_id": 5},
    {"id": 88, "name": "يونيون برلين", "league_id": 5},
    {"id": 89, "name": "فيردر بريمن", "league_id": 5},
    {"id": 90, "name": "أوغسبورغ", "league_id": 5},
    {"id": 91, "name": "هوفنهايم", "league_id": 5},
    {"id": 92, "name": "هايدنهايم", "league_id": 5},
    {"id": 93, "name": "سانت باولي", "league_id": 5},
    {"id": 94, "name": "بوخوم", "league_id": 5},
    {"id": 95, "name": "فريبرغ", "league_id": 5},
    {"id": 96, "name": "هانوفر", "league_id": 5},
    {"id": 97, "name": "هامبورغ", "league_id": 5},
    {"id": 98, "name": "كولن", "league_id": 5},
    {"id": 99, "name": "دوسلدورف", "league_id": 5},
    {"id": 100, "name": "نورنبرغ", "league_id": 5},
]

FIRST_NAMES = [
    "أحمد", "محمد", "علي", "عمر", "حسن", "حسين", "خالد", "سامي", "كريم", "يوسف",
    "عبدالله", "سعيد", "محمود", "نبيل", "ماجد", "طارق", "هاني", "ناصر", "عادل", "شريف",
    "إبراهيم", "إسماعيل", "أنس", "جمال", "فريد", "باسم", "توفيق", "جاسم", "حاتم", "خليل",
    "Alexander", "Marco", "Luis", "Carlos", "Diego", "Andres", "Jorge", "Pablo", "Sergio", "Rafael",
    "James", "Jack", "Oliver", "Harry", "William", "Thomas", "George", "David", "Daniel", "Samuel",
    "Luca", "Francesco", "Alessandro", "Lorenzo", "Matteo", "Antonio", "Giovanni", "Riccardo", "Federico", "Paolo",
    "Hans", "Klaus", "Karl", "Franz", "Otto", "Heinrich", "Ludwig", "Friedrich", "Ernst", "Wilhelm",
]
LAST_NAMES = [
    "العبدلي", "الشهري", "الغامدي", "المالكي", "القرني", "الحارثي", "الزهراني", "السلمي", "الحربي", "العتيبي",
    "المطيري", "الدوسري", "السهلي", "الشمراني", "العنزي", "القحطاني", "الهذلي", "الناصر", "الجابر", "الصالح",
    "Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres", "Flores",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Wilson", "Taylor", "Davies", "Roberts", "Walker",
    "Rossi", "Russo", "Ferrari", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco", "Bruno",
    "Mueller", "Schmidt", "Schneider", "Fischer", "Weber", "Wagner", "Becker", "Hoffmann", "Zimmermann", "Braun",
]

POS_WEIGHTS = game_data.POS_WEIGHTS


def compute_ovr(pos, attrs):
    w = POS_WEIGHTS[pos]
    total = 0.0
    for k, weight in w.items():
        total += attrs[k] * weight
    return max(40, min(99, round(total)))


def generate_player(name, pos, base, club_id, league_id, age=None):
    if pos == "GK":
        base_low, base_high = 74, 91
    elif pos == "DEF":
        base_low, base_high = 76, 91
    elif pos == "MID":
        base_low, base_high = 78, 93
    else:
        base_low, base_high = 78, 95
    core = base if base else random.randint(base_low, base_high)

    attrs = {}
    for k in game_data.ATTR_KEYS:
        # القدرات الأساسية تتمركز حول النواة، وترتبط بالمركز
        spread = random.randint(-6, 6)
        val = core + spread
        # مركزية الخصائص: حراس أقوى دفاعاً، مهاجمون أقوى تسديداً...
        if pos == "GK":
            if k == "def":
                val = core + random.randint(0, 8)
            if k in ("sho", "pas"):
                val = max(45, core - random.randint(10, 25))
        elif pos == "DEF" and k == "def":
            val = core + random.randint(0, 6)
        elif pos == "ATT" and k == "sho":
            val = core + random.randint(0, 6)
        elif pos == "MID" and k == "pas":
            val = core + random.randint(0, 6)
        attrs[k] = max(40, min(99, val))

    ovr = compute_ovr(pos, attrs)
    age = age if age else random.randint(18, 34)
    # العمر يؤثر على السعر: الشباب أغلى
    age_mod = 1.15 if age <= 23 else (1.0 if age <= 29 else 0.85)
    price = int(ovr * game_data.CONFIG["PRICE_PER_RATING"] * age_mod) + random.randint(-20, 30)
    price = max(30, price)

    return {
        "name": name,
        "position": pos,
        "pac": attrs["pac"], "sho": attrs["sho"], "pas": attrs["pas"],
        "dri": attrs["dri"], "def": attrs["def"], "phy": attrs["phy"],
        "ovr": ovr,
        "rating": ovr,
        "price": price,
        "age": age,
        "condition": 100,
        "morale": random.randint(70, 100),
        "foot": random.choice(game_data.FOOT),
        "work_rate": random.choice(game_data.WORK_RATES),
        "special": random.choice([""] + game_data.SPECIAL_ABILITIES) if random.random() < 0.3 else "",
        "club_id": club_id,
        "league_id": league_id,
    }


def generate_players_data():
    players = []
    pid = 1
    # تشكيلة واقعية: 3 حراس، 8 دفاع، 8 وسط، 5 هجوم = 24 لاعب
    squad_template = ["GK"] * 3 + ["DEF"] * 8 + ["MID"] * 8 + ["ATT"] * 5
    for club in CLUBS:
        used = set()
        for pos in squad_template:
            attempts = 0
            while attempts < 50:
                attempts += 1
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                name = f"{first} {last}"
                if name not in used:
                    used.add(name)
                    break
            p = generate_player(name, pos, None, club["id"], club["league_id"])
            p["id"] = pid
            players.append(p)
            pid += 1
    return players


PLAYERS = generate_players_data()
