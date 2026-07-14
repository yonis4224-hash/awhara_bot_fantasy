import os
import asyncio
import traceback
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import discord
from discord.ext import commands
from discord import app_commands

import db
import engine
import game_data


# ---------------------------------------------------------------------------
# Health server (for Render free‑tier)
# ---------------------------------------------------------------------------
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ohara bot is running")

    def log_message(self, *args):
        pass


def _start_web_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    server.serve_forever()


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,  # we use our own help
    activity=discord.Game(name="!مساعدة"),
)

TOKEN = os.getenv("DISCORD_TOKEN")

POS_ARABIC = {"GK": "حارس", "DEF": "دفاع", "MID": "وسط", "ATT": "هجوم"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_state(user):
    coach = db.get_coach(str(user.id))
    if not coach or not coach["team_id"]:
        return None, None
    team = db.get_team(coach["team_id"])
    players = db.team_players(team["id"])
    return team, players


def team_embed(team, players):
    e = discord.Embed(
        title=f"⚽ {team['name']}",
        color=discord.Color.green(),
    )
    e.add_field(name="💰 الميزانية", value=f"{team['budget']}م", inline=True)
    e.add_field(name="🟢 الخبرة", value=f"{team['xp']} نقطة", inline=True)
    e.add_field(name="📐 التشكيل", value=team["formation"], inline=True)
    e.add_field(name="🎯 الخطة", value=team["tactic"], inline=True)
    e.add_field(
        name="🏋️ التدريب",
        value=f"{team['training_invest']} نقطة",
        inline=True,
    )

    if players:
        lines = []
        for p in players:
            pos = POS_ARABIC.get(p["position"], p["position"])
            lines.append(f"`{p['id']}` **{p['name']}** — {pos} | ريت {p['rating']} | {p['price']}م")
        e.add_field(name="اللاعبون", value="\n".join(lines), inline=False)
    else:
        e.add_field(name="اللاعبون", value="لا توجد لاعبين بعد.", inline=False)

    return e


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
@bot.event
async def on_ready():
    db.init_db()
    print(f"✅ أوهارا المدرب الأفضل جاهز: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏱️ تهدأ شوي!",
            description=f"انتظر {error.retry_after:.0f} ثانية قبل ما تستخدم الأمر مرة ثانية.",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ ناقص معلومة!",
            description=f"استخدام الأمر: `!{ctx.command.name} {ctx.command.signature}`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ خطأ في الإدخال!",
            description="تأكد من صحة الأرقام والقيم المدخلة.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        embed = discord.Embed(
            title="❌ خطأ غير متوقع",
            description=str(error)[:1000],
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        traceback.print_exception(type(error), error, error.__traceback__)


# ---------------------------------------------------------------------------
# TEAM commands
# ---------------------------------------------------------------------------
@bot.command(name="انشاء", description="إنشاء فريق جديد")
@commands.cooldown(1, 10, commands.BucketType.user)
async def create_team(ctx, *, name):
    if db.get_coach(str(ctx.author.id)):
        embed = discord.Embed(
            title="❌ لديك فريق بالفعل!",
            description="استخدم `!فريقي` لعرض فريقك.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    tid = db.create_team(name, str(ctx.author.id))
    db.create_coach(str(ctx.author.id), str(ctx.author), tid)

    embed = discord.Embed(
        title="✅ تم إنشاء الفريق!",
        description=f"مرحباً بك في **{name}**!",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="💰 الميزانية",
        value=f"{game_data.CONFIG['START_BUDGET']}م",
        inline=True,
    )
    embed.add_field(
        name="🟢 الخبرة",
        value=f"{game_data.CONFIG['START_XP']} نقطة",
        inline=True,
    )
    embed.set_footer(text="اكتب !سوق لرؤية اللاعبين المتاحين")
    await ctx.send(embed=embed)


@bot.command(name="فريقي", description="عرض فريقك")
@commands.cooldown(1, 5, commands.BucketType.user)
async def my_team(ctx):
    team, players = get_state(ctx.author)
    if not team:
        embed = discord.Embed(
            title="❌ لا تملك فريقاً!",
            description="أنشئ فريقاً بـ `!انشاء <اسم الفريق>`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return
    await ctx.send(embed=team_embed(team, players))


# ---------------------------------------------------------------------------
# MARKET commands
# ---------------------------------------------------------------------------
@bot.command(name="سوق", description="عرض اللاعبين المتاحين للشراء")
@commands.cooldown(1, 5, commands.BucketType.user)
async def market(ctx):
    players = db.market_players()
    if not players:
        embed = discord.Embed(
            title="🛒 السوق فارغ!",
            description="لا يوجد لاعبين متاحين حالياً.",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🛒 سوق اللاعبين 2026",
        color=discord.Color.blue(),
    )

    lines = []
    for p in players[:20]:
        pos = POS_ARABIC.get(p["position"], p["position"])
        lines.append(f"`{p['id']}` **{p['name']}** — {pos} | ريت {p['rating']} | {p['price']}م")

    embed.description = "\n".join(lines)
    embed.set_footer(text="للشراء: !اشتري <رقم> | للتفاصيل: !لاعب <رقم>")
    await ctx.send(embed=embed)


@bot.command(name="اشتري", description="شراء لاعب من السوق")
@commands.cooldown(1, 5, commands.BucketType.user)
async def buy(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(
            title="❌ أنشئ فريقاً أولاً!",
            description="استخدم `!انشاء <اسم الفريق>`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    p = db.get_player(pid)
    if not p or p["team_id"] is not None:
        embed = discord.Embed(
            title="❌ اللاعب غير متاح!",
            description="هذا اللاعب ليس في السوق.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    if team["budget"] < p["price"]:
        embed = discord.Embed(
            title="❌ ميزانية غير كافية!",
            description=f"ميزانيتك: **{team['budget']}م** | سعر اللاعب: **{p['price']}م**",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.buy_player(pid, team["id"], p["price"])

    embed = discord.Embed(
        title="✅ تم الشراء!",
        description=f"اشتريت **{p['name']}** مقابل **{p['price']}م**",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="💰 الميزانية المتبقية",
        value=f"{team['budget'] - p['price']}م",
        inline=True,
    )
    await ctx.send(embed=embed)


@bot.command(name="بيع", description="بيع لاعب من فريقك")
@commands.cooldown(1, 5, commands.BucketType.user)
async def sell(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(
            title="❌ أنشئ فريقاً أولاً!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    p = db.get_player(pid)
    if not p or p["team_id"] != team["id"]:
        embed = discord.Embed(
            title="❌ هذا اللاعب ليس في فريقك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.sell_player(pid, p["price"])

    embed = discord.Embed(
        title="✅ تم البيع!",
        description=f"بعت **{p['name']}** مقابل **{p['price']}م**",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="💰 الميزانية الجديدة",
        value=f"{team['budget'] + p['price']}م",
        inline=True,
    )
    await ctx.send(embed=embed)


@bot.command(name="لاعب", description="عرض تفاصيل لاعب")
@commands.cooldown(1, 3, commands.BucketType.user)
async def player_info(ctx, pid: int):
    p = db.get_player(pid)
    if not p:
        embed = discord.Embed(
            title="❌ اللاعب غير موجود!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    pos = POS_ARABIC.get(p["position"], p["position"])
    status = "في فريق" if p["team_id"] else "في السوق"

    embed = discord.Embed(
        title=f"📋 {p['name']}",
        color=discord.Color.blue(),
    )
    embed.add_field(name="المركز", value=pos, inline=True)
    embed.add_field(name="الريت", value=str(p["rating"]), inline=True)
    embed.add_field(name="السعر", value=f"{p['price']}م", inline=True)
    embed.add_field(name="الحالة", value=status, inline=True)
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# DEVELOPMENT commands
# ---------------------------------------------------------------------------
@bot.command(name="لاعب_تطوير", description="عرض مستويات تطوير لاعب")
@commands.cooldown(1, 3, commands.BucketType.user)
async def dev_view(ctx, pid: int):
    p = db.get_player(pid)
    if not p:
        embed = discord.Embed(title="❌ اللاعب غير موجود!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    team, _ = get_state(ctx.author)
    owned = team and p["team_id"] == team["id"]

    embed = discord.Embed(
        title=f"🔧 تطوير {p['name']} (ريت {p['rating']})",
        color=discord.Color.purple(),
    )

    lines = []
    for d in game_data.DEV_LEVELS:
        own = "" if owned else " ❌ ليس بفريقك"
        lines.append(
            f"**المستوى {d['level']}**: +{d['gain']} ريت | {d['xp']} خبرة | {d['money']}م{own}"
        )

    embed.description = "\n".join(lines)
    embed.set_footer(text="للتطوير: !طور <رقم> <المستوى>")
    await ctx.send(embed=embed)


@bot.command(name="طور", description="تطوير لاعب")
@commands.cooldown(1, 5, commands.BucketType.user)
async def develop(ctx, pid: int, level: int):
    team, _ = get_state(ctx.author)
    p = db.get_player(pid)

    if not team or not p or p["team_id"] != team["id"]:
        embed = discord.Embed(
            title="❌ اللاعب ليس في فريقك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    d = next((x for x in game_data.DEV_LEVELS if x["level"] == level), None)
    if not d:
        embed = discord.Embed(
            title="❌ مستوى غير صحيح!",
            description="اختر مستوى من 1 إلى 4.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    if team["xp"] < d["xp"] or team["budget"] < d["money"]:
        embed = discord.Embed(
            title="❌ موارد غير كافية!",
            description=f"تحتاج: {d['xp']} خبرة + {d['money']}م\nلديك: {team['xp']} خبرة + {team['budget']}م",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    new_rating = min(99, p["rating"] + d["gain"])
    new_price = p["price"] + d["gain"] * game_data.CONFIG["PRICE_PER_RATING"]
    db.develop_player(pid, new_rating, new_price)
    db.update_team(team["id"], xp=team["xp"] - d["xp"], budget=team["budget"] - d["money"])

    embed = discord.Embed(
        title="✅ تم التطوير!",
        description=f"**{p['name']}** تطور من ريت {p['rating']} إلى **{new_rating}** (+{d['gain']})",
        color=discord.Color.green(),
    )
    embed.add_field(name="السعر الجديد", value=f"{new_price}م", inline=True)
    await ctx.send(embed=embed)


@bot.command(name="تدريب", description="تخصيص خبرة للتدريب قبل المباراة")
@commands.cooldown(1, 5, commands.BucketType.user)
async def train(ctx, amount: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    amount = max(0, min(amount, game_data.CONFIG["TRAIN_MAX_XP"]))
    if team["xp"] < amount:
        embed = discord.Embed(
            title="❌ خبرة غير كافية!",
            description=f"لديك: **{team['xp']}** نقطة | طلبت: **{amount}**",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.update_team(team["id"], training_invest=amount, xp=team["xp"] - amount)

    embed = discord.Embed(
        title="🏋️ تم التدريب!",
        description=f"خصصت **{amount}** نقطة خبرة للتدريب قبل المباراة القادمة.",
        color=discord.Color.green(),
    )
    embed.set_footer(text="⚠️ التدريب يظهر للخصم في !مباراتي")
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# TACTICS commands
# ---------------------------------------------------------------------------
@bot.command(name="تشكيل", description="ضبط التشكيل (مخفي حتى المباراة)")
@commands.cooldown(1, 5, commands.BucketType.user)
async def set_formation(ctx, formation):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if formation not in game_data.FORMATIONS:
        embed = discord.Embed(
            title="❌ تشكيل غير صحيح!",
            description="التشكيلات المتاحة: " + " | ".join(game_data.FORMATIONS.keys()),
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.update_team(team["id"], formation=formation)

    embed = discord.Embed(
        title="📐 تم ضبط التشكيل!",
        description=f"التشكيل الجديد: **{formation}**\n🔒 مخفي حتى المباراة.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="خطة", description="ضبط الخطة التكتيكية (مخفي حتى المباراة)")
@commands.cooldown(1, 5, commands.BucketType.user)
async def set_tactic(ctx, tactic):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if tactic not in game_data.TACTICS:
        embed = discord.Embed(
            title="❌ خطة غير صحيحة!",
            description="الخطط المتاحة: هجومي | متوازن | دفاعي",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.update_team(team["id"], tactic=tactic)

    mod = game_data.TACTICS[tactic]
    embed = discord.Embed(
        title="🎯 تم ضبط الخطة!",
        description=f"الخطة: **{tactic}**\n💡 {mod['key']}\n🔒 مخفي حتى المباراة.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="خطتي", description="عرض خطتك السرية")
@commands.cooldown(1, 3, commands.BucketType.user)
async def my_plan(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🔒 خطتك السرية",
        color=discord.Color.gold(),
    )
    embed.add_field(name="📐 التشكيل", value=team["formation"], inline=True)
    embed.add_field(name="🎯 الخطة", value=team["tactic"], inline=True)
    embed.add_field(
        name="🏋️ التدريب",
        value=f"{team['training_invest']} نقطة",
        inline=True,
    )
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# LEAGUE commands
# ---------------------------------------------------------------------------
@bot.command(name="دوري_جديد", description="إنشاء دوري جديد")
@commands.cooldown(1, 10, commands.BucketType.user)
async def new_league(ctx, *, name):
    lid = db.create_league(name, str(ctx.author.id))
    team = db.get_team_by_owner(str(ctx.author.id))
    if team:
        db.update_team(team["id"], league_id=lid)

    embed = discord.Embed(
        title="🏆 تم إنشاء الدوري!",
        description=f"**{name}** (رقم {lid})\nشارك الآخرون بـ `!انضمام {lid}`",
        color=discord.Color.gold(),
    )
    await ctx.send(embed=embed)


@bot.command(name="انضمام", description="الانضمام إلى دوري")
@commands.cooldown(1, 10, commands.BucketType.user)
async def join_l(ctx, lid: int):
    if not db.join_league(lid, str(ctx.author.id)):
        embed = discord.Embed(
            title="❌ الدوري غير موجود!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    team = db.get_team_by_owner(str(ctx.author.id))
    if team:
        db.update_team(team["id"], league_id=lid)

    embed = discord.Embed(
        title="✅ تم الانضمام!",
        description=f"انضممت إلى الدوري رقم **{lid}**",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="دوريات", description="عرض جميع الدوريات")
@commands.cooldown(1, 5, commands.BucketType.user)
async def list_leagues(ctx):
    leagues = db.get_leagues()
    if not leagues:
        embed = discord.Embed(
            title="🏆 لا توجد دوريات!",
            description="أنشئ دوري بـ `!دوري_جديد <اسم>`",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title="🏆 الدوريات", color=discord.Color.gold())
    for l in leagues:
        m = len(__import__("json").loads(l["members"]))
        embed.add_field(
            name=f"#{l['id']} - {l['name']}",
            value=f"الأعضاء: {m}",
            inline=True,
        )
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# MATCH commands
# ---------------------------------------------------------------------------
@bot.command(name="تحدي", description="تحدي لاعب آخر لمباراة")
@commands.cooldown(1, 30, commands.BucketType.user)
async def challenge_cmd(ctx, opponent: discord.Member):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    opp_team = db.get_team_by_owner(str(opponent.id))
    if not opp_team:
        embed = discord.Embed(
            title="❌ الخصم لا يملك فريقاً!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    if opponent.id == ctx.author.id:
        embed = discord.Embed(
            title="❌ لا يمكنك تحدي نفسك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    pid = db.challenge(str(ctx.author.id), str(opponent.id))

    embed = discord.Embed(
        title="⚔️ تم التحدي!",
        description=f"تحديت **{opponent.display_name}**!\nمباراة رقم: **{pid}**",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="الخطوات",
        value=(
            f"1. كلاهما يضبط خطته بـ `!خطة` و `!تشكيل`\n"
            f"2. كلاهما يكتب `!جاهز {pid}`\n"
            f"3. المباراة تبدأ تلقائياً!"
        ),
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(name="مباراتي", description="عرض مبارياتك المعلقة")
@commands.cooldown(1, 5, commands.BucketType.user)
async def my_matches(ctx):
    pendings = db.get_pending_for(str(ctx.author.id))
    if not pendings:
        embed = discord.Embed(
            title="⚔️ لا توجد مباريات معلقة!",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title="⚔️ مبارياتك المعلقة", color=discord.Color.red())
    for pm in pendings:
        opp_id = pm["opponent_id"] if pm["challenger_id"] == str(ctx.author.id) else pm["challenger_id"]
        opp = db.get_team_by_owner(opp_id)
        opp_name = opp["name"] if opp else "؟"
        opp_train = opp["training_invest"] if opp else 0

        my_ready = (
            (pm["challenger_id"] == str(ctx.author.id) and pm["challenger_ready"])
            or (pm["opponent_id"] == str(ctx.author.id) and pm["opponent_ready"])
        )
        status = "✅ جاهز" if my_ready else "❌ غير جاهز"

        embed.add_field(
            name=f"#{pm['id']} ضد {opp_name}",
            value=f"تدريب الخصم: {opp_train} نقطة\nحالة جاهزيتك: {status}",
            inline=False,
        )
    embed.set_footer(text="اكتب !جاهز <رقم> للتأكيد")
    await ctx.send(embed=embed)


@bot.command(name="جاهز", description="تأكيد الجاهزية للمباراة")
@commands.cooldown(1, 5, commands.BucketType.user)
async def ready(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    pm = db.get_pending(pid)
    if not pm or (pm["challenger_id"] != str(ctx.author.id) and pm["opponent_id"] != str(ctx.author.id)):
        embed = discord.Embed(
            title="❌ هذه المباراة غير مخصصة لك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.set_ready(pid, str(ctx.author.id))
    pm = db.get_pending(pid)

    if pm["challenger_ready"] and pm["opponent_ready"]:
        await run_match(ctx, pm)
    else:
        embed = discord.Embed(
            title="✅ تم التأكيد!",
            description=f"أنت جاهز للمباراة **#{pid}**.\nبانتظار الخصم...",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)


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
        db.update_team(c_team["id"], xp=c_team["xp"] + cfg["WIN_XP"], budget=c_team["budget"] + cfg["WIN_MONEY"], training_invest=0)
        db.update_team(o_team["id"], xp=o_team["xp"] + cfg["LOSS_XP"], budget=o_team["budget"] + cfg["LOSS_MONEY"], training_invest=0)
        winner = c_team["name"]
    elif result == "خسارة":
        db.update_team(o_team["id"], xp=o_team["xp"] + cfg["WIN_XP"], budget=o_team["budget"] + cfg["WIN_MONEY"], training_invest=0)
        db.update_team(c_team["id"], xp=c_team["xp"] + cfg["LOSS_XP"], budget=c_team["budget"] + cfg["LOSS_MONEY"], training_invest=0)
        winner = o_team["name"]
    else:
        db.update_team(c_team["id"], xp=c_team["xp"] + cfg["DRAW_XP"], budget=c_team["budget"] + cfg["DRAW_MONEY"], training_invest=0)
        db.update_team(o_team["id"], xp=o_team["xp"] + cfg["DRAW_XP"], budget=o_team["budget"] + cfg["DRAW_MONEY"], training_invest=0)
        winner = None

    embed = discord.Embed(
        title=f"⚽ نتيجة المباراة #{pm['id']}",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="النتيجة",
        value=f"**{c_team['name']}** {ga} - {gb} **{o_team['name']}**",
        inline=False,
    )

    if winner:
        embed.add_field(name="🏆 الفائز", value=f"**{winner}**", inline=False)
    else:
        embed.add_field(name="🤝 النتيجة", value="**تعادل!**", inline=False)

    plans = (
        f"• **{c_team['name']}**: {c_team['formation']} / {c_team['tactic']} / تدريب {c_team['training_invest']}\n"
        f"• **{o_team['name']}**: {o_team['formation']} / {o_team['tactic']} / تدريب {o_team['training_invest']}"
    )
    embed.add_field(name="📋 الخطط المكشوفة", value=plans, inline=False)

    if notes:
        embed.add_field(name="📝 ملاحظات", value="\n".join(notes), inline=False)

    db.delete_pending(pm["id"])
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# TIPS & HELP
# ---------------------------------------------------------------------------
@bot.command(name="نصائح", description="نصائح للعب بشكل أفضل")
@commands.cooldown(1, 10, commands.BucketType.user)
async def tips(ctx):
    embed = discord.Embed(
        title="💡 نصائح أوهارا",
        color=discord.Color.blue(),
    )
    tips_list = [
        "🎯 طابق خطتك لهوية فريقك: فريق هجومي → خطة هجومية، وإلا تُعاقب.",
        "👀 راجع تدريب الخصم في `!مباراتي` قبل `!جاهز`.",
        "⚔️ الهجوم يكسر الدفاعي، الدفاع يكسر المتوازن، المتوازن يكسر الهجومي.",
        "🌟 فريق متوسط بخطط صحيحة وتدريب مكثف قد يفوز على فريق نجوم!",
        "🔧 طور لاعبيك بـ `!طور` لرفع الريت والسعر.",
    ]
    embed.description = "\n".join(tips_list)
    await ctx.send(embed=embed)


@bot.command(name="مساعدة", description="عرض جميع الأوامر")
@commands.cooldown(1, 5, commands.BucketType.user)
async def help_cmd(ctx):
    embed = discord.Embed(
        title="📘 أوامر أوهارا المدرب الأفضل",
        description="نظام كرة قدم افتراضي كامل — أنشئ فريقك، تعاقد مع نجوم، وتقدم في الدوريات!",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="⚽ إنشاء الفريق",
        value=(
            "`!انشاء <اسم>` — إنشاء فريق جديد\n"
            "`!فريقي` — عرض فريقك وتفاصيله"
        ),
        inline=False,
    )

    embed.add_field(
        name="🛒 سوق الانتقالات",
        value=(
            "`!سوق` — عرض اللاعبين المتاحين\n"
            "`!لاعب <رقم>` — تفاصيل لاعب\n"
            "`!اشتري <رقم>` — شراء لاعب\n"
            "`!بيع <رقم>` — بيع لاعب"
        ),
        inline=False,
    )

    embed.add_field(
        name="🔧 تطوير اللاعبين",
        value=(
            "`!لاعب_تطوير <رقم>` — مستويات التطوير\n"
            "`!طور <رقم> <مستوى>` — تطوير لاعب (1-4)\n"
            "`!تدريب <نقاط>` — تدريب قبل المباراة"
        ),
        inline=False,
    )

    embed.add_field(
        name="🎯 التكتيكات",
        value=(
            "`!تشكيل <4-3-3>` — ضبط التشكيل\n"
            "`!خطة <هجومي/متوازن/دفاعي>` — ضبط الخطة\n"
            "`!خطتي` — عرض خطتك السرية"
        ),
        inline=False,
    )

    embed.add_field(
        name="🏆 الدوريات",
        value=(
            "`!دوري_جديد <اسم>` — إنشاء دوري\n"
            "`!انضمام <رقم>` — الانضمام لدوري\n"
            "`!دوريات` — قائمة الدوريات"
        ),
        inline=False,
    )

    embed.add_field(
        name="⚔️ المباريات",
        value=(
            "`!تحدي @خصم` — تحدي لاعب\n"
            "`!مباراتي` — مبارياتك المعلقة\n"
            "`!جاهز <رقم>` — تأكيد الجاهزية"
        ),
        inline=False,
    )

    embed.add_field(
        name="💡 أخرى",
        value=(
            "`!نصائح` — نصائح للعب\n"
            "`!مساعدة` — عرض هذه القائمة"
        ),
        inline=False,
    )

    embed.set_footer(text="أوامر الدوريات والمباريات قادمة قريباً!")
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
threading.Thread(target=_start_web_server, daemon=True).start()
bot.run(TOKEN)
