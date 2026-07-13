import os
import discord
from discord.ext import commands
import db
import engine
import game_data

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("DISCORD_TOKEN")

def get_state(user):
    coach = db.get_coach(str(user.id))
    if not coach or not coach["team_id"]:
        return None, None
    team = db.get_team(coach["team_id"])
    players = db.team_players(team["id"])
    return team, players

@bot.event
async def on_ready():
    db.init_db()
    print(f"أوهارا المدرب الأفضل جاهز: {bot.user}")

@bot.command(name="انشاء")
async def create_team(ctx, *, name):
    if db.get_coach(str(ctx.author.id)):
        await ctx.send("❌ لديك فريق بالفعل. استخدم `!فريقي` لعرضه.")
        return
    tid = db.create_team(name, str(ctx.author.id))
    db.create_coach(str(ctx.author.id), str(ctx.author), tid)
    await ctx.send(f"✅ تم إنشاء فريق **{name}**! ميزانيتك: {game_data.CONFIG['START_BUDGET']}م ، خبرتك: {game_data.CONFIG['START_XP']} نقطة.\nاكتب `!سوق` لرؤية اللاعبين.")

@bot.command(name="سوق")
async def market(ctx):
    players = db.market_players()
    if not players:
        await ctx.send("السوق فارغ حالياً.")
        return
    lines = ["**🛒 سوق اللاعبين 2026**", "```"]
    lines.append(f"{'#':<4}{'الاسم':<18}{'المركز':<6}{'الريت':<5}{'السعر':<6}")
    for p in players[:30]:
        pos = {"GK":"حارس","DEF":"دفاع","MID":"وسط","ATT":"هجوم"}[p["position"]]
        lines.append(f"{p['id']:<4}{p['name'][:16]:<18}{pos:<6}{p['rating']:<5}{p['price']}م".rstrip())
    lines.append("```")
    lines.append("للشراء: `!اشتري <رقم>`")
    await ctx.send("\n".join(lines))

@bot.command(name="اشتري")
async def buy(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً بـ `!انشاء <اسم الفريق>`")
        return
    p = db.get_player(pid)
    if not p or p["team_id"] is not None:
        await ctx.send("❌ اللاعب غير متاح.")
        return
    if team["budget"] < p["price"]:
        await ctx.send(f"❌ ميزانيتك ({team['budget']}م) لا تكفي لسعر {p['price']}م.")
        return
    db.buy_player(pid, team["id"], p["price"])
    await ctx.send(f"✅ اشتريت **{p['name']}** مقابل {p['price']}م.")

@bot.command(name="بيع")
async def sell(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    p = db.get_player(pid)
    if not p or p["team_id"] != team["id"]:
        await ctx.send("❌ هذا اللاعب ليس في فريقك.")
        return
    db.sell_player(pid, p["price"])
    await ctx.send(f"✅ بعت **{p['name']}** مقابل {p['price']}م.")

@bot.command(name="فريقي")
async def my_team(ctx):
    team, players = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    lines = [f"**⚽ {team['name']}**", f"💰 الميزانية: {team['budget']}م | 🟢 الخبرة: {team['xp']} نقطة",
             f"📐 التشكيل: {team['formation']} | 🎯 الخطة: {team['tactic']}",
             f"🏋️ تدريب قبل المباراة: {team['training_invest']} نقطة", "```"]
    for p in players:
        pos = {"GK":"حارس","DEF":"دفاع","MID":"وسط","ATT":"هجوم"}[p["position"]]
        lines.append(f"{p['id']:<4}{p['name'][:16]:<18}{pos:<6}{p['rating']:<5}{p['price']}م".rstrip())
    lines.append("```")
    await ctx.send("\n".join(lines))

@bot.command(name="لاعب_تطوير")
async def dev_view(ctx, pid: int):
    p = db.get_player(pid)
    if not p:
        await ctx.send("❌ اللاعب غير موجود.")
        return
    team, _ = get_state(ctx.author)
    owned = team and p["team_id"] == team["id"]
    lines = [f"**🔧 تطوير {p['name']}** (الريت الحالي: {p['rating']})", "```"]
    lines.append(f"{'المستوى':<8}{'الزيادة':<8}{'الخبرة':<8}{'المال':<8}")
    for d in game_data.DEV_LEVELS:
        own = "" if owned else " (ليس بفريقك)"
        lines.append(f"{d['level']:<8}+{d['gain']:<8}{d['xp']:<8}{d['money']}م{own}".rstrip())
    lines.append("```")
    lines.append("للتطوير: `!طور <رقم> <المستوى>`")
    await ctx.send("\n".join(lines))

@bot.command(name="طور")
async def develop(ctx, pid: int, level: int):
    team, _ = get_state(ctx.author)
    p = db.get_player(pid)
    if not team or not p or p["team_id"] != team["id"]:
        await ctx.send("❌ اللاعب ليس في فريقك.")
        return
    d = next((x for x in game_data.DEV_LEVELS if x["level"] == level), None)
    if not d:
        await ctx.send("❌ مستوى تطوير غير صحيح (1-4).")
        return
    if team["xp"] < d["xp"] or team["budget"] < d["money"]:
        await ctx.send("❌ لا تملك الخبرة أو المال الكافي.")
        return
    new_rating = min(99, p["rating"] + d["gain"])
    new_price = p["price"] + d["gain"] * game_data.CONFIG["PRICE_PER_RATING"]
    db.develop_player(pid, new_rating, new_price)
    db.update_team(team["id"], xp=team["xp"]-d["xp"], budget=team["budget"]-d["money"])
    await ctx.send(f"✅ تطور **{p['name']}** إلى ريت {new_rating} (+{d['gain']})، وسعره أصبح {new_price}م.")

@bot.command(name="تدريب")
async def train(ctx, amount: int):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    amount = max(0, min(amount, game_data.CONFIG["TRAIN_MAX_XP"]))
    if team["xp"] < amount:
        await ctx.send("❌ خبرتك غير كافية لهذا التدريب.")
        return
    db.update_team(team["id"], training_invest=amount, xp=team["xp"]-amount)
    await ctx.send(f"🏋️ خصصت {amount} نقطة خبرة للتدريب قبل المباراة القادمة (يظهرها الخصم!).")

@bot.command(name="تشكيل")
async def set_formation(ctx, formation):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    if formation not in game_data.FORMATIONS:
        await ctx.send("❌ تشكيل غير صحيح. الخيارات: " + ", ".join(game_data.FORMATIONS.keys()))
        return
    db.update_team(team["id"], formation=formation)
    await ctx.send(f"📐 تم ضبط التشكيل إلى {formation} (مخفي حتى المباراة).")

@bot.command(name="خطة")
async def set_tactic(ctx, tactic):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    if tactic not in game_data.TACTICS:
        await ctx.send("❌ خطة غير صحيحة. الخيارات: هجومي / متوازن / دفاعي")
        return
    db.update_team(team["id"], tactic=tactic)
    await ctx.send(f"🎯 تم ضبط الخطة إلى {tactic}. المفتاح: {game_data.TACTICS[tactic]['key']} (مخفي حتى المباراة).")

@bot.command(name="خطتي")
async def my_plan(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    await ctx.send(f"🔒 خطتك السرية:\nالتشكيل: {team['formation']}\nالخطة: {team['tactic']}\nالتدريب: {team['training_invest']} نقطة")

@bot.command(name="دوري_جديد")
async def new_league(ctx, *, name):
    lid = db.create_league(name, str(ctx.author.id))
    db.update_team(db.get_team_by_owner(str(ctx.author.id))["id"], league_id=lid)
    await ctx.send(f"🏆 تم إنشاء دوري **{name}** (رقم {lid}). شارك الآخرون بـ `!انضمام {lid}`")

@bot.command(name="انضمام")
async def join_l(ctx, lid: int):
    if not db.join_league(lid, str(ctx.author.id)):
        await ctx.send("❌ الدوري غير موجود.")
        return
    team = db.get_team_by_owner(str(ctx.author.id))
    if team:
        db.update_team(team["id"], league_id=lid)
    await ctx.send(f"✅ انضممت إلى الدوري {lid}.")

@bot.command(name="دوريات")
async def list_leagues(ctx):
    leagues = db.get_leagues()
    if not leagues:
        await ctx.send("لا توجد دوريات بعد.")
        return
    lines = ["**🏆 الدوريات**"]
    for l in leagues:
        m = len(__import__("json").loads(l["members"]))
        lines.append(f"#{l['id']} - {l['name']} (الأعضاء: {m})")
    await ctx.send("\n".join(lines))

@bot.command(name="تحدي")
async def challenge_cmd(ctx, opponent: discord.Member):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    opp_team = db.get_team_by_owner(str(opponent.id))
    if not opp_team:
        await ctx.send("❌ الخصم لا يملك فريقاً.")
        return
    if opponent.id == ctx.author.id:
        await ctx.send("❌ لا يمكنك تحدي نفسك.")
        return
    pid = db.challenge(str(ctx.author.id), str(opponent.id))
    await ctx.send(f"⚔️ تحديت **{opponent.display_name}**! (مباراة #{pid})\nكلاهما يضبط خطته ثم يكتب `!جاهز {pid}`.")

@bot.command(name="مباراتي")
async def my_matches(ctx):
    pendings = db.get_pending_for(str(ctx.author.id))
    if not pendings:
        await ctx.send("لا توجد مباريات معلقة.")
        return
    lines = ["**⚔️ مبارياتك المعلقة**"]
    for pm in pendings:
        opp_id = pm["opponent_id"] if pm["challenger_id"] == str(ctx.author.id) else pm["challenger_id"]
        opp = db.get_team_by_owner(opp_id)
        opp_train = opp["training_invest"] if opp else 0
        lines.append(f"#{pm['id']} ضد {opp['name'] if opp else '؟'} | تدريب الخصم المكشوف: {opp_train} نقطة")
        lines.append(f"   جاهزيتك: {'✅' if (pm['challenger_id']==str(ctx.author.id) and pm['challenger_ready']) or (pm['opponent_id']==str(ctx.author.id) and pm['opponent_ready']) else '❌'}")
    await ctx.send("\n".join(lines))

@bot.command(name="جاهز")
async def ready(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        await ctx.send("❌ أنشئ فريقاً أولاً.")
        return
    pm = db.get_pending(pid)
    if not pm or (pm["challenger_id"] != str(ctx.author.id) and pm["opponent_id"] != str(ctx.author.id)):
        await ctx.send("❌ هذه المباراة غير مخصصة لك.")
        return
    db.set_ready(pid, str(ctx.author.id))
    pm = db.get_pending(pid)
    if pm["challenger_ready"] and pm["opponent_ready"]:
        await run_match(ctx, pm)
    else:
        await ctx.send(f"✅ أنت جاهز للمباراة #{pid}. بانتظار الخصم `!جاهز {pid}`.")

async def run_match(ctx, pm):
    c_team = db.get_team_by_owner(pm["challenger_id"])
    o_team = db.get_team_by_owner(pm["opponent_id"])
    challenger = {
        "players": db.team_players(c_team["id"]),
        "formation": c_team["formation"],
        "tactic": c_team["tactic"],
        "training": c_team["training_invest"],
    }
    opponent = {
        "players": db.team_players(o_team["id"]),
        "formation": o_team["formation"],
        "tactic": o_team["tactic"],
        "training": o_team["training_invest"],
    }
    ga, gb, result, notes = engine.simulate(challenger, opponent)

    cfg = game_data.CONFIG
    if result == "فوز":
        db.update_team(c_team["id"], xp=c_team["xp"]+cfg["WIN_XP"], budget=c_team["budget"]+cfg["WIN_MONEY"],
                       training_invest=0)
        db.update_team(o_team["id"], xp=o_team["xp"]+cfg["LOSS_XP"], budget=o_team["budget"]+cfg["LOSS_MONEY"],
                       training_invest=0)
        reward = f"🏆 فاز **{c_team['name']}**! (+{cfg['WIN_XP']} خبرة، +{cfg['WIN_MONEY']}م)"
    elif result == "خسارة":
        db.update_team(o_team["id"], xp=o_team["xp"]+cfg["WIN_XP"], budget=o_team["budget"]+cfg["WIN_MONEY"],
                       training_invest=0)
        db.update_team(c_team["id"], xp=c_team["xp"]+cfg["LOSS_XP"], budget=c_team["budget"]+cfg["LOSS_MONEY"],
                       training_invest=0)
        reward = f"🏆 فاز **{o_team['name']}**! (+{cfg['WIN_XP']} خبرة، +{cfg['WIN_MONEY']}م)"
    else:
        db.update_team(c_team["id"], xp=c_team["xp"]+cfg["DRAW_XP"], budget=c_team["budget"]+cfg["DRAW_MONEY"],
                       training_invest=0)
        db.update_team(o_team["id"], xp=o_team["xp"]+cfg["DRAW_XP"], budget=o_team["budget"]+cfg["DRAW_MONEY"],
                       training_invest=0)
        reward = f"🤝 تعادل! (كل فريق +{cfg['DRAW_XP']} خبرة، +{cfg['DRAW_MONEY']}م)"

    report = [f"**⚽ نتيجة المباراة #{pm['id']}**",
              f"{c_team['name']} {ga} - {gb} {o_team['name']}",
              "",
              f"🔓 الخطط المكشوفة:",
              f"• {c_team['name']}: {c_team['formation']} / {c_team['tactic']} / تدريب {c_team['training_invest']}",
              f"• {o_team['name']}: {o_team['formation']} / {o_team['tactic']} / تدريب {o_team['training_invest']}"]
    if notes:
        report.append("")
        report.extend(notes)
    report.append("")
    report.append(reward)
    db.delete_pending(pm["id"])
    await ctx.send("\n".join(report))

@bot.command(name="نصائح")
async def tips(ctx):
    await ctx.send(
        "**💡 نصائح أوهارا:**\n"
        "• طابق خطتك لهوية فريقك: فريق هجومي → خطة هجومية، وإلا تُعاقب.\n"
        "• راجع تدريب الخصم في `!مباراتي` قبل `!جاهز`؛ إن درب بكثافة زد تدريبك أو غير خطتك.\n"
        "• الهجوم يكسر الدفاعي، الدفاع يكسر المتوازن، المتوازن يكسر الهجومي.\n"
        "• فريق متوسط بخطط صحيحة وتدريب مكثف قد يفوز على فريق نجوم!\n"
        "• طور لاعبيك بـ `!لاعب_تطوير` لرفع الريت والسعر.")

@bot.command(name="مساعدة")
async def help_cmd(ctx):
    await ctx.send(
        "**📘 أوامر أوهارا المدرب الأفضل:**\n"
        "`!انشاء <اسم>` - إنشاء فريق\n"
        "`!سوق` - عرض اللاعبين | `!اشتري <رقم>` | `!بيع <رقم>`\n"
        "`!فريقي` - قائمة فريقك\n"
        "`!لاعب_تطوير <رقم>` - مستويات التطوير | `!طور <رقم> <مستوى>`\n"
        "`!تدريب <نقاط>` - تدريب قبل المباراة\n"
        "`!تشكيل <4-3-3...>` | `!خطة <هجومي/متوازن/دفاعي>` | `!خطتي`\n"
        "`!دوري_جديد <اسم>` | `!انضمام <رقم>` | `!دوريات`\n"
        "`!تحدي @خصم` | `!مباراتي` | `!جاهز <رقم>`\n"
        "`!نصائح` - نصائح اللعب")

bot.run(TOKEN)
