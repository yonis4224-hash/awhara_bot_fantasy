import random

LEAGUES = [
    {"id": 1, "name": "دوري أبطال أوروبا", "flag": "🏆"},
    {"id": 2, "name": "الدوري الإنجليزي", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"id": 3, "name": "الدوري الإسباني", "flag": "🇪🇸"},
    {"id": 4, "name": "الدوري الإيطالي", "flag": "🇮🇹"},
    {"id": 5, "name": "الدوري الألماني", "flag": "🇩🇪"},
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

def generate_players_data():
    players = []
    pid = 1
    for club in CLUBS:
        used = set()
        for _ in range(8):
            while True:
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                name = f"{first} {last}"
                if name not in used:
                    used.add(name)
                    break
            pos = random.choice(["GK", "DEF", "DEF", "MID", "MID", "ATT", "ATT", "ATT"])
            rating = random.randint(75, 92)
            if pos == "GK":
                rating = random.randint(75, 90)
            elif pos == "DEF":
                rating = random.randint(76, 91)
            elif pos == "MID":
                rating = random.randint(78, 93)
            else:
                rating = random.randint(78, 95)
            price = rating * 2 + random.randint(-10, 15)
            if price < 30:
                price = 30
            players.append({
                "id": pid,
                "name": name,
                "position": pos,
                "rating": rating,
                "price": price,
                "club_id": club["id"],
                "league_id": club["league_id"],
            })
            pid += 1
    return players

PLAYERS = generate_players_data()
