import discord
import db
import engine
import market_data
import game_data

POS_ARABIC = {"GK": "حارس", "DEF": "دفاع", "MID": "وسط", "ATT": "هجوم"}
POS_EMOJI = {"GK": "🧤", "DEF": "🛡️", "MID": "🎽", "ATT": "⚽"}


# ---------------------------------------------------------------------------
# Embed builders
# ---------------------------------------------------------------------------
def team_embed(team, players):
    g = lambda k, d=0: team[k] if k in team.keys() else d
    e = discord.Embed(title=f"⚽ {team['name']}", color=discord.Color.green())
    e.add_field(name="💰 الميزانية", value=f"{g('budget')}م", inline=True)
    e.add_field(name="🪙 الرموز", value=f"{g('tokens')}", inline=True)
    e.add_field(name="⭐ المستوى", value=f"{g('level', 1)}", inline=True)
    e.add_field(name="📊 السمعة", value=f"{g('reputation')}", inline=True)
    e.add_field(name="🏆 الألقاب", value=f"{g('titles')}", inline=True)
    e.add_field(name="📈 السجل", value=f"{g('wins')}ف/{g('draws')}ت/{g('losses')}خ", inline=True)
    e.add_field(name="📐 التشكيل", value=g("formation", "4-3-3"), inline=True)
    e.add_field(name="🎯 الخطة", value=g("tactic", "متوازن"), inline=True)
    e.add_field(name="🏋️ التدريب", value=f"{g('training_invest')} نقطة", inline=True)

    avg_cond = round(sum(p["condition"] for p in players) / len(players)) if players else 0
    e.add_field(name="🔋 متوسط الجاهزية", value=f"{avg_cond}%", inline=True)
    e.add_field(name="👥 عدد اللاعبين", value=str(len(players)), inline=True)

    if players:
        lines = []
        for p in players:
            emo = POS_EMOJI.get(p["position"], "")
            lines.append(f"{emo} `{p['id']}` **{p['name']}** — OVR {p['ovr']} | 🔋{p['condition']}%")
        e.add_field(name="اللاعبون", value="\n".join(lines[:25]), inline=False)
    else:
        e.add_field(name="اللاعبون", value="لا يوجد لاعبين. اضغط 🛒 شراء.", inline=False)

    e.set_footer(text="استخدم الأزرار بالأسفل للتحكم بفريقك")
    return e


def _bar(val):
    filled = round(val / 10)
    return "█" * filled + "░" * (10 - filled)


def player_detail_embed(p):
    return player_card_embed(p)


def player_card_embed(p):
    pos = POS_ARABIC.get(p["position"], p["position"])
    status = "في فريق ⚽" if p["team_id"] else ("لاعب حر 🌟" if p["club_id"] == 0 else "في السوق 🛒")
    color = discord.Color.gold() if p["club_id"] == 0 else (discord.Color.green() if p["team_id"] else discord.Color.blue())
    e = discord.Embed(title=f"{POS_EMOJI.get(p['position'],'')} {p['name']}", color=color)
    e.add_field(name="المركز", value=f"{pos}", inline=True)
    e.add_field(name="⭐ OVR", value=f"**{p['ovr']}**", inline=True)
    e.add_field(name="💰 السعر", value=f"{p['price']}م", inline=True)
    e.add_field(name="🎂 العمر", value=f"{p['age']}", inline=True)
    e.add_field(name="🦶 القدم", value=p["foot"], inline=True)
    e.add_field(name="🔋 الجاهزية", value=f"{p['condition']}%", inline=True)
    e.add_field(name="😊 الروح", value=f"{p['morale']}%", inline=True)
    e.add_field(name="⚙️ الجهد", value=p["work_rate"], inline=True)
    if p["special"]:
        e.add_field(name="✨ مهارة خاصة", value=p["special"], inline=True)

    attr_lines = []
    for k in game_data.ATTR_KEYS:
        a = game_data.ATTR[k]
        attr_lines.append(f"{a['emoji']} {a['name']} `{p[k]}` {_bar(p[k])}")
    e.add_field(name="📊 الخصائص", value="\n".join(attr_lines), inline=False)
    e.add_field(name="الحالة", value=status, inline=False)
    return e


# ---------------------------------------------------------------------------
# Ownership guard mixin
# ---------------------------------------------------------------------------
class OwnedView(discord.ui.View):
    def __init__(self, owner_id, timeout=180):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ هذه القائمة ليست لك! اكتب `!فريقي` لفتح قائمتك.", ephemeral=True
            )
            return False
        return True


# ---------------------------------------------------------------------------
# SELL / RELEASE / VIEW / DEVELOP: pick an owned player
# ---------------------------------------------------------------------------
class OwnedPlayerSelect(discord.ui.Select):
    def __init__(self, owner_id, action):
        self.owner_id = owner_id
        self.action = action
        team = db.get_team_by_owner(str(owner_id))
        players = db.team_players(team["id"]) if team else []
        options = [
            discord.SelectOption(
                label=f"{p['name']} (ريت {p['rating']})",
                description=f"{POS_ARABIC.get(p['position'],'')} | {p['price']}م",
                value=str(p["id"]),
            )
            for p in players[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="لا يوجد لاعبين", value="none")]
        placeholders = {
            "sell": "اختر لاعباً لبيعه...",
            "release": "اختر لاعباً لطرده...",
            "view": "اختر لاعباً لعرضه...",
            "develop": "اختر لاعباً لتطويره...",
        }
        super().__init__(placeholder=placeholders.get(action, "اختر لاعباً..."), options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("لا يوجد لاعبين في فريقك.", ephemeral=True)
            return
        pid = int(self.values[0])
        p = db.get_player(pid)
        team = db.get_team_by_owner(str(self.owner_id))

        if not p or p["team_id"] != team["id"]:
            await interaction.response.send_message("❌ هذا اللاعب ليس في فريقك.", ephemeral=True)
            return

        if self.action == "sell":
            db.sell_player(pid, p["price"])
            e = discord.Embed(
                title="💰 تم البيع!",
                description=f"بعت **{p['name']}** مقابل **{p['price']}م**\n💰 الميزانية: {team['budget']+p['price']}م",
                color=discord.Color.green(),
            )
            await interaction.response.edit_message(embed=e, view=None)

        elif self.action == "release":
            db.release_player(pid)
            e = discord.Embed(
                title="❌ تم الطرد!",
                description=f"طردت **{p['name']}** من الفريق (بدون تعويض مادي).",
                color=discord.Color.orange(),
            )
            await interaction.response.edit_message(embed=e, view=None)

        elif self.action == "view":
            await interaction.response.edit_message(embed=player_detail_embed(p), view=None)

        elif self.action == "develop":
            view = OwnedView(self.owner_id)
            view.add_item(DevLevelSelect(self.owner_id, pid))
            await interaction.response.edit_message(
                content=f"🔧 اختر مستوى تطوير **{p['name']}** (ريت {p['rating']}):", view=view
            )


class DevLevelSelect(discord.ui.Select):
    def __init__(self, owner_id, pid):
        self.owner_id = owner_id
        self.pid = pid
        options = [
            discord.SelectOption(
                label=f"المستوى {d['level']} (+{d['gain']} ريت)",
                description=f"{d['xp']} خبرة + {d['money']}م",
                value=str(d["level"]),
            )
            for d in game_data.DEV_LEVELS
        ]
        super().__init__(placeholder="اختر مستوى التطوير...", options=options)

    async def callback(self, interaction: discord.Interaction):
        level = int(self.values[0])
        team = db.get_team_by_owner(str(self.owner_id))
        p = db.get_player(self.pid)
        d = next((x for x in game_data.DEV_LEVELS if x["level"] == level), None)

        if not p or p["team_id"] != team["id"]:
            await interaction.response.send_message("❌ اللاعب لم يعد في فريقك.", ephemeral=True)
            return
        if team["xp"] < d["xp"] or team["budget"] < d["money"]:
            await interaction.response.send_message(
                f"❌ موارد غير كافية. تحتاج {d['xp']} خبرة + {d['money']}م.", ephemeral=True
            )
            return

        new_rating = min(99, p["rating"] + d["gain"])
        new_price = p["price"] + d["gain"] * game_data.CONFIG["PRICE_PER_RATING"]
        db.develop_player(self.pid, new_rating, new_price)
        db.update_team(team["id"], xp=team["xp"] - d["xp"], budget=team["budget"] - d["money"])

        e = discord.Embed(
            title="✅ تم التطوير!",
            description=f"**{p['name']}**: ريت {p['rating']} ← **{new_rating}** (+{d['gain']})\nالسعر الجديد: {new_price}م",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=e, view=None)


# ---------------------------------------------------------------------------
# FORMATION / TACTIC selects
# ---------------------------------------------------------------------------
class FormationSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        options = [discord.SelectOption(label=f, value=f) for f in game_data.FORMATIONS]
        super().__init__(placeholder="اختر التشكيل...", options=options)

    async def callback(self, interaction: discord.Interaction):
        team = db.get_team_by_owner(str(self.owner_id))
        db.update_team(team["id"], formation=self.values[0])
        e = discord.Embed(
            title="📐 تم ضبط التشكيل!",
            description=f"التشكيل: **{self.values[0]}**\n🔒 مخفي حتى المباراة.",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=e, view=None)


class TacticSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(label=t, description=game_data.TACTICS[t]["key"], value=t)
            for t in game_data.TACTICS
        ]
        super().__init__(placeholder="اختر الخطة...", options=options)

    async def callback(self, interaction: discord.Interaction):
        team = db.get_team_by_owner(str(self.owner_id))
        db.update_team(team["id"], tactic=self.values[0])
        e = discord.Embed(
            title="🎯 تم ضبط الخطة!",
            description=f"الخطة: **{self.values[0]}**\n💡 {game_data.TACTICS[self.values[0]]['key']}\n🔒 مخفي حتى المباراة.",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=e, view=None)


# ---------------------------------------------------------------------------
# TRAINING modal
# ---------------------------------------------------------------------------
class TrainModal(discord.ui.Modal, title="🏋️ تدريب الفريق"):
    def __init__(self, owner_id):
        super().__init__()
        self.owner_id = owner_id
        self.amount = discord.ui.TextInput(
            label=f"نقاط الخبرة (حد أقصى {game_data.CONFIG['TRAIN_MAX_XP']})",
            placeholder="مثال: 200",
            required=True,
            max_length=5,
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(str(self.amount.value))
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقماً صحيحاً.", ephemeral=True)
            return
        team = db.get_team_by_owner(str(self.owner_id))
        amount = max(0, min(amount, game_data.CONFIG["TRAIN_MAX_XP"]))
        if team["xp"] < amount:
            await interaction.response.send_message(
                f"❌ خبرتك ({team['xp']}) غير كافية.", ephemeral=True
            )
            return
        db.update_team(team["id"], training_invest=amount, xp=team["xp"] - amount)
        e = discord.Embed(
            title="🏋️ تم التدريب!",
            description=f"خصصت **{amount}** نقطة للتدريب قبل المباراة.\n⚠️ يظهر للخصم في مبارياته.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


# ---------------------------------------------------------------------------
# CHALLENGE (user select)
# ---------------------------------------------------------------------------
class ChallengeUserSelect(discord.ui.UserSelect):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        super().__init__(placeholder="اختر خصماً للتحدي...", max_values=1)

    async def callback(self, interaction: discord.Interaction):
        opponent = self.values[0]
        if opponent.id == self.owner_id:
            await interaction.response.send_message("❌ لا يمكنك تحدي نفسك.", ephemeral=True)
            return
        opp_team = db.get_team_by_owner(str(opponent.id))
        if not opp_team:
            await interaction.response.send_message("❌ الخصم لا يملك فريقاً.", ephemeral=True)
            return
        pid = db.challenge(str(self.owner_id), str(opponent.id))
        e = discord.Embed(
            title="⚔️ تم التحدي!",
            description=(
                f"تحديت **{opponent.display_name}**! (مباراة #{pid})\n\n"
                f"1. كلاكما يضبط الخطة والتشكيل\n"
                f"2. كلاكما يكتب `!جاهز {pid}`"
            ),
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(content=None, embed=e, view=None)


# ---------------------------------------------------------------------------
# LEAGUE view
# ---------------------------------------------------------------------------
class NewLeagueModal(discord.ui.Modal, title="🏆 إنشاء دوري"):
    def __init__(self, owner_id):
        super().__init__()
        self.owner_id = owner_id
        self.lname = discord.ui.TextInput(label="اسم الدوري", required=True, max_length=40)
        self.add_item(self.lname)

    async def on_submit(self, interaction: discord.Interaction):
        name = str(self.lname.value)
        lid = db.create_league(name, str(self.owner_id))
        team = db.get_team_by_owner(str(self.owner_id))
        if team:
            db.update_team(team["id"], league_id=lid)
        e = discord.Embed(
            title="🏆 تم إنشاء الدوري!",
            description=f"**{name}** (رقم {lid})\nالآخرون ينضمون عبر قائمة الدوريات.",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


class JoinLeagueSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        import json
        leagues = db.get_leagues()
        options = [
            discord.SelectOption(
                label=f"#{l['id']} - {l['name']}",
                description=f"الأعضاء: {len(json.loads(l['members']))}",
                value=str(l["id"]),
            )
            for l in leagues[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="لا توجد دوريات", value="none")]
        super().__init__(placeholder="اختر دوري للانضمام...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("لا توجد دوريات. أنشئ واحداً!", ephemeral=True)
            return
        lid = int(self.values[0])
        db.join_league(lid, str(self.owner_id))
        team = db.get_team_by_owner(str(self.owner_id))
        if team:
            db.update_team(team["id"], league_id=lid)
        e = discord.Embed(
            title="✅ تم الانضمام!",
            description=f"انضممت إلى الدوري رقم **{lid}**.",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(content=None, embed=e, view=None)


class LeagueView(OwnedView):
    @discord.ui.button(label="إنشاء دوري", emoji="➕", style=discord.ButtonStyle.success)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NewLeagueModal(self.owner_id))

    @discord.ui.button(label="انضمام لدوري", emoji="🔗", style=discord.ButtonStyle.primary)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(JoinLeagueSelect(self.owner_id))
        await interaction.response.edit_message(content="🏆 اختر دوري:", view=view)


# ---------------------------------------------------------------------------
# RESIGN confirmation
# ---------------------------------------------------------------------------
class ResignView(OwnedView):
    @discord.ui.button(label="نعم، أستقيل", emoji="🚪", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.resign(str(self.owner_id))
        e = discord.Embed(
            title="🚪 تمت الاستقالة",
            description="تم حل فريقك وإطلاق سراح جميع لاعبيك. يمكنك البدء من جديد بـ `!انشاء`.",
            color=discord.Color.dark_red(),
        )
        await interaction.response.edit_message(content=None, embed=e, view=None)

    @discord.ui.button(label="إلغاء", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="تم الإلغاء. ✅", embed=None, view=None)


# ---------------------------------------------------------------------------
# MARKET views: League -> Club -> Players
# ---------------------------------------------------------------------------
class MarketLeagueSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(label=l["name"], emoji=l["emoji"], value=str(l["id"]))
            for l in market_data.LEAGUES
        ]
        super().__init__(placeholder="اختر الدوري...", options=options)

    async def callback(self, interaction: discord.Interaction):
        lid = int(self.values[0])
        league = db.get_league(lid)
        clubs = db.get_clubs_by_league(lid)
        options = [
            discord.SelectOption(label=c["name"], value=str(c["id"]))
            for c in clubs
        ]
        view = OwnedView(self.owner_id)
        view.add_item(MarketClubSelect(self.owner_id, lid, options))
        embed = discord.Embed(title=f"{league['flag']} {league['name']}", color=discord.Color.blue())
        embed.description = "اختر النادي لعرض لاعبيه المتاحين:"
        await interaction.response.edit_message(embed=embed, view=view)


class MarketClubSelect(discord.ui.Select):
    def __init__(self, owner_id, league_id, options, page=0):
        self.owner_id = owner_id
        self.league_id = league_id
        self.page = page
        per_page = 20
        start = page * per_page
        opts = options[start:start + per_page]
        if len(options) > start + per_page:
            opts.append(discord.SelectOption(label="⬇️ التالي", value="next"))
        if page > 0:
            opts.insert(0, discord.SelectOption(label="⬆️ السابق", value="prev"))
        opts.append(discord.SelectOption(label="🔙 رجوع", value="back"))
        super().__init__(placeholder="اختر النادي...", options=opts)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "back":
            view = OwnedView(self.owner_id)
            view.add_item(MarketLeagueSelect(self.owner_id))
            embed = discord.Embed(title="🛒 سوق الانتقالات", color=discord.Color.blue())
            embed.description = "اختر الدوري:"
            await interaction.response.edit_message(embed=embed, view=view)
            return
        if val == "next":
            clubs = db.get_clubs_by_league(self.league_id)
            opts = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in clubs]
            view = OwnedView(self.owner_id)
            view.add_item(MarketClubSelect(self.owner_id, self.league_id, opts, self.page + 1))
            await interaction.response.edit_message(view=view)
            return
        if val == "prev":
            clubs = db.get_clubs_by_league(self.league_id)
            opts = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in clubs]
            view = OwnedView(self.owner_id)
            view.add_item(MarketClubSelect(self.owner_id, self.league_id, opts, self.page - 1))
            await interaction.response.edit_message(view=view)
            return
        cid = int(val)
        club = db.get_club(cid)
        players = db.get_market_players_by_club(cid)
        view = OwnedView(self.owner_id)
        view.add_item(MarketPlayerSelect(self.owner_id, cid, self.league_id, players))
        embed = discord.Embed(
            title=f"⚽ {club['name']}",
            description=f"اللاعبون المتاحون للشراء:",
            color=discord.Color.blue(),
        )
        await interaction.response.edit_message(embed=embed, view=view)


class MarketPlayerSelect(discord.ui.Select):
    def __init__(self, owner_id, club_id, league_id, players, page=0):
        self.owner_id = owner_id
        self.club_id = club_id
        self.league_id = league_id
        self.page = page
        per_page = 20
        start = page * per_page
        slice = players[start:start + per_page]
        options = []
        for p in slice:
            pos = POS_ARABIC.get(p["position"], p["position"])
            options.append(
                discord.SelectOption(
                    label=f"{p['name']} (ريت {p['rating']})",
                    description=f"{pos} | {p['price']}م | رقم {p['id']}",
                    value=f"p_{p['id']}",
                )
            )
        if len(players) > start + per_page:
            options.append(discord.SelectOption(label="⬇️ التالي", value="next"))
        if page > 0:
            options.insert(0, discord.SelectOption(label="⬆️ السابق", value="prev"))
        options.append(discord.SelectOption(label="🔙 رجوع", value="back"))
        super().__init__(placeholder="اختر لاعباً للشراء...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "back":
            clubs = db.get_clubs_by_league(self.league_id)
            opts = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in clubs]
            view = OwnedView(self.owner_id)
            view.add_item(MarketClubSelect(self.owner_id, self.league_id, opts))
            league = db.get_league(self.league_id)
            embed = discord.Embed(title=f"{league['flag']} {league['name']}", color=discord.Color.blue())
            embed.description = "اختر النادي:"
            await interaction.response.edit_message(embed=embed, view=view)
            return
        if val == "next":
            players = db.get_market_players_by_club(self.club_id)
            view = OwnedView(self.owner_id)
            view.add_item(MarketPlayerSelect(self.owner_id, self.club_id, self.league_id, players, self.page + 1))
            await interaction.response.edit_message(view=view)
            return
        if val == "prev":
            players = db.get_market_players_by_club(self.club_id)
            view = OwnedView(self.owner_id)
            view.add_item(MarketPlayerSelect(self.owner_id, self.club_id, self.league_id, players, self.page - 1))
            await interaction.response.edit_message(view=view)
            return
        pid = int(val[2:])
        p = db.get_player(pid)
        team = db.get_team_by_owner(str(self.owner_id))
        e = player_card_embed(p)
        view = OwnedView(self.owner_id)
        club = db.get_club(p["club_id"])
        if club:
            e.add_field(name="النادي", value=club["name"], inline=True)
        view.add_item(OfferButton(self.owner_id, pid, p["price"]))
        view.add_item(BackToMarketButton(self.owner_id, self.club_id, self.league_id))
        await interaction.response.edit_message(embed=e, view=view)


class OfferButton(discord.ui.Button):
    def __init__(self, owner_id, pid, price):
        super().__init__(label=f"💰 شراء ({price}م)", style=discord.ButtonStyle.success)
        self.owner_id = owner_id
        self.pid = pid
        self.price = price

    async def callback(self, interaction: discord.Interaction):
        team = db.get_team_by_owner(str(self.owner_id))
        if not team:
            await interaction.response.send_message(
                "❌ أنشئ فريقاً أولاً بـ `!انشاء <اسم>` قبل شراء اللاعبين.", ephemeral=True
            )
            return
        if team["budget"] < self.price:
            await interaction.response.send_message(
                f"❌ ميزانيتك ({team['budget']}م) لا تكفي لسعر اللاعب ({self.price}م).", ephemeral=True
            )
            return
        p = db.get_player(self.pid)
        if not p or p["team_id"] is not None:
            await interaction.response.send_message("❌ اللاعب لم يعد متاحاً.", ephemeral=True)
            return
        db.buy_player(self.pid, team["id"], self.price, str(self.owner_id))
        new_team = db.get_team(team["id"])
        e = discord.Embed(
            title="✅ تم الشراء!",
            description=f"اشتريت **{p['name']}** مقابل **{p['price']}م**\n💰 الميزانية المتبقية: {new_team['budget']}م",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(content=None, embed=e, view=None)


class BackToMarketButton(discord.ui.Button):
    def __init__(self, owner_id, club_id, league_id):
        super().__init__(label="🔙 العودة للسوق", style=discord.ButtonStyle.secondary)
        self.owner_id = owner_id
        self.club_id = club_id
        self.league_id = league_id

    async def callback(self, interaction: discord.Interaction):
        clubs = db.get_clubs_by_league(self.league_id)
        opts = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in clubs]
        view = OwnedView(self.owner_id)
        view.add_item(MarketClubSelect(self.owner_id, self.league_id, opts))
        league = db.get_league(self.league_id)
        embed = discord.Embed(title=f"{league['flag']} {league['name']}", color=discord.Color.blue())
        embed.description = "اختر النادي:"
        await interaction.response.edit_message(embed=embed, view=view)


class MarketView(OwnedView):
    @discord.ui.button(label="افتتاح السوق", emoji="🛒", style=discord.ButtonStyle.success)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(MarketLeagueSelect(self.owner_id))
        embed = discord.Embed(title="🛒 سوق الانتقالات", color=discord.Color.blue())
        embed.description = "اختر الدوري:"
        await interaction.response.edit_message(embed=embed, view=view)


# ---------------------------------------------------------------------------
# PLAYER HISTORY
# ---------------------------------------------------------------------------
class HistoryView(OwnedView):
    def __init__(self, owner_id, pid):
        super().__init__(owner_id)
        self.pid = pid
        self.add_item(BackButton(owner_id))

    @discord.ui.button(label="🔄 تحديث", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = db.get_player(self.pid)
        history = db.get_history(self.pid)
        e = discord.Embed(title=f"📜 سجل {p['name']}", color=discord.Color.purple())
        lines = []
        for h in history:
            lines.append(f"▫️ {h['event']} | {h['amount']}م | {h['time']}")
        e.description = "\n".join(lines[:15]) if lines else "لا يوجد سجل."
        await interaction.response.edit_message(embed=e, view=self)


class BackButton(discord.ui.Button):
    def __init__(self, owner_id):
        super().__init__(label="🔙 رجوع", style=discord.ButtonStyle.secondary)
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="تم الرجوع.", embed=None, view=None)


# ---------------------------------------------------------------------------
# FULL TACTICS (Top Eleven style)
# ---------------------------------------------------------------------------
def tactics_embed(team):
    e = discord.Embed(title="🧠 التكتيك الكامل", color=discord.Color.purple())
    e.add_field(name="🅿️ تركيز التمرير", value=team["passing"], inline=True)
    e.add_field(name="⏱️ الضغط", value=team["pressing"], inline=True)
    e.add_field(name="🛡️ الرقابة", value=team["marking"], inline=True)
    e.add_field(name="⚡ الإيقاع", value=team["tempo"], inline=True)
    e.add_field(name="🔁 الهجوم المرتد", value=team["counter"], inline=True)
    e.add_field(name="🚩 فخ التسلل", value=team["offside"], inline=True)
    e.set_footer(text="🔒 كلها مخفية عن الخصم حتى صافرة البداية")
    return e


class TacticDimSelect(discord.ui.Select):
    def __init__(self, owner_id, column, options_dict, label):
        self.owner_id = owner_id
        self.column = column
        options = [discord.SelectOption(label=k, value=k) for k in options_dict]
        super().__init__(placeholder=label, options=options, custom_id=f"tac_{column}")

    async def callback(self, interaction: discord.Interaction):
        team = db.get_team_by_owner(str(self.owner_id))
        db.update_team(team["id"], **{self.column: self.values[0]})
        await interaction.response.edit_message(
            embed=tactics_embed(db.get_team_by_owner(str(self.owner_id))),
            view=FullTacticsView(self.owner_id),
        )


class FullTacticsView(OwnedView):
    def __init__(self, owner_id):
        super().__init__(owner_id)
        self.add_item(TacticDimSelect(owner_id, "passing", game_data.PASSING_FOCUS, "🅿️ تركيز التمرير..."))
        self.add_item(TacticDimSelect(owner_id, "pressing", game_data.PRESSING, "⏱️ الضغط..."))
        self.add_item(TacticDimSelect(owner_id, "marking", game_data.MARKING, "🛡️ الرقابة..."))
        self.add_item(TacticDimSelect(owner_id, "tempo", game_data.TEMPO, "⚡ الإيقاع..."))

    @discord.ui.button(label="🔁 الهجوم المرتد", style=discord.ButtonStyle.primary, row=1)
    async def counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        db.update_team(team["id"], counter="لا" if team["counter"] == "نعم" else "نعم")
        await interaction.response.edit_message(
            embed=tactics_embed(db.get_team_by_owner(str(self.owner_id))), view=self)

    @discord.ui.button(label="🚩 فخ التسلل", style=discord.ButtonStyle.primary, row=1)
    async def offside(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        db.update_team(team["id"], offside="لا" if team["offside"] == "نعم" else "نعم")
        await interaction.response.edit_message(
            embed=tactics_embed(db.get_team_by_owner(str(self.owner_id))), view=self)

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        players = db.team_players(team["id"])
        await interaction.response.edit_message(
            embed=team_embed(team, players), view=TeamPanel(self.owner_id))


# ---------------------------------------------------------------------------
# TRAINING DRILL (7 drills)
# ---------------------------------------------------------------------------
class TrainingDrillSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(label=f"{d['emoji']} {k}", description=d["desc"], value=k)
            for k, d in game_data.DRILLS.items()
        ]
        super().__init__(placeholder="اختر الحصة التدريبية...", options=options)

    async def callback(self, interaction: discord.Interaction):
        drill = self.values[0]
        await interaction.response.send_modal(TrainDrillModal(self.owner_id, drill))


class TrainDrillModal(discord.ui.Modal, title="🏋️ حصة تدريبية"):
    def __init__(self, owner_id, drill):
        super().__init__()
        self.owner_id = owner_id
        self.drill = drill
        self.amount = discord.ui.TextInput(
            label=f"نقاط الخبرة للاستثمار (حتى {game_data.CONFIG['TRAIN_MAX_XP']})",
            placeholder="مثال: 200", required=True, max_length=5)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(str(self.amount.value))
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقماً صحيحاً.", ephemeral=True)
            return
        team = db.get_team_by_owner(str(self.owner_id))
        amount = max(0, min(amount, game_data.CONFIG["TRAIN_MAX_XP"]))
        if team["xp"] < amount:
            await interaction.response.send_message(
                f"❌ خبرتك ({team['xp']}) غير كافية.", ephemeral=True)
            return
        if team["training_invest"] > 0:
            db.update_team(team["id"], training_invest=0)
        db.train_drill(team["id"], self.drill, 1, amount)
        d = game_data.DRILLS[self.drill]
        e = discord.Embed(
            title=f"{d['emoji']} تمت الحصة: {self.drill}",
            description=(
                f"استثمرت **{amount}** نقطة خبرة.\n"
                f"📈 تطورت الخصائص: {', '.join(game_data.ATTR[a]['name'] for a in d['attrs'])}\n"
                f"🔋 انخفضت جاهزية اللاعبين قليلاً. استعدها بـ `!راحة`."
            ),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


# ---------------------------------------------------------------------------
# FACILITIES
# ---------------------------------------------------------------------------
def facilities_embed(team):
    fac = db.get_facilities(team["id"])
    e = discord.Embed(title=f"🏗️ منشآت {team['name']}", color=discord.Color.teal())
    lines = []
    for key, spec in game_data.FACILITIES.items():
        cur = fac[key]
        lvl_info = spec["levels"][min(cur, len(spec["levels"]) - 1)]
        if cur >= len(spec["levels"]):
            lines.append(f"{spec['emoji']} **{spec['name']}**: ممتلئ (مستوى {cur})")
        else:
            lines.append(f"{spec['emoji']} **{spec['name']}**: مستوى {cur} → التالي {lvl_info['cost']}م")
    e.description = "\n".join(lines)
    e.add_field(name="💰 الميزانية", value=f"{team['budget']}م", inline=True)
    e.set_footer(text="كل منشأة تمنحك ميزة تنافسية دائمة")
    return e


class FacilityUpgradeButton(discord.ui.Button):
    def __init__(self, owner_id, key):
        self.owner_id = owner_id
        self.key = key
        spec = game_data.FACILITIES[key]
        team = db.get_team_by_owner(str(owner_id))
        fac = db.get_facilities(team["id"])
        cur = fac[key]
        if cur >= len(spec["levels"]):
            super().__init__(label=f"{spec['emoji']} {spec['name']} (ممتلئ)", style=discord.ButtonStyle.secondary,
                             disabled=True, custom_id=f"fac_{key}")
        else:
            cost = spec["levels"][cur]["cost"]
            super().__init__(label=f"{spec['emoji']} {spec['name']} → {cost}م",
                             style=discord.ButtonStyle.success, custom_id=f"fac_{key}")

    async def callback(self, interaction: discord.Interaction):
        ok, info = db.upgrade_facility(db.get_team_by_owner(str(self.owner_id))["id"], self.key)
        if not ok:
            await interaction.response.send_message(f"❌ {info}", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=facilities_embed(db.get_team_by_owner(str(self.owner_id))),
            view=FacilitiesView(self.owner_id))


class FacilitiesView(OwnedView):
    def __init__(self, owner_id):
        super().__init__(owner_id)
        for key in game_data.FACILITIES:
            self.add_item(FacilityUpgradeButton(owner_id, key))

    @discord.ui.button(label="🔙 رجوع", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        players = db.team_players(team["id"])
        await interaction.response.edit_message(embed=team_embed(team, players), view=TeamPanel(self.owner_id))


# ---------------------------------------------------------------------------
# SCOUT (free agents)
# ---------------------------------------------------------------------------
class ScoutView(OwnedView):
    @discord.ui.button(label="🔍 كشافة (10 رموز)", emoji="🌟", style=discord.ButtonStyle.success)
    async def scout(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        if not db.spend_tokens(team["id"], 10):
            await interaction.response.send_message(
                f"❌ رموزك ({team['tokens']}) لا تكفي (تحتاج 10).", ephemeral=True)
            return
        p = db.scout_player(team["id"])
        db.update_player(p["id"], team_id=team["id"])
        db.add_history(p["id"], "كشافة", 0, str(self.owner_id), str(team["id"]))
        e = player_card_embed(p)
        e.title = "🌟 لاعب جديد من الكشافة!"
        e.description = f"انضم **{p['name']}** مباشرة إلى فريقك!"
        await interaction.response.edit_message(content=None, embed=e, view=None)


# ---------------------------------------------------------------------------
# SEASON (league matchdays)
# ---------------------------------------------------------------------------
class SeasonView(OwnedView):
    @discord.ui.button(label="📊 الترتيب", emoji="🏆", style=discord.ButtonStyle.primary)
    async def standings(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        if not team["league_id"]:
            await interaction.response.send_message("❌ فريقك ليس في دوري. انضم عبر `!دوريات`.", ephemeral=True)
            return
        season = db.get_season(team["league_id"])
        if not season or season["status"] != "active":
            await interaction.response.send_message("❌ لا يوجد موسم نشط. ابدأ بـ `!موسم`.", ephemeral=True)
            return
        standings = json.loads(season["standings"])
        teams = {t["id"]: t for t in db.get_league_teams(team["league_id"])}
        rows = []
        for tid, s in sorted(standings.items(), key=lambda kv: (kv[1]["Pts"], kv[1]["GF"] - kv[1]["GA"]), reverse=True):
            name = teams.get(int(tid), {}).get("name", f"فريق {tid}")
            rows.append(f"`{len(rows)+1}.` **{name}** — {s['Pts']}ن | {s['W']}ف/{s['D']}ت/{s['L']}خ | {s['GF']}-{s['GA']}")
        e = discord.Embed(title=f"🏆 ترتيب الدوري (جولة {season['round']}/{season['total_rounds']})",
                          color=discord.Color.gold())
        e.description = "\n".join(rows) if rows else "لا يوجد"
        await interaction.response.edit_message(content=None, embed=e, view=self)

    @discord.ui.button(label="⚽ تقديم جولة", emoji="▶️", style=discord.ButtonStyle.success)
    async def advance(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        if not team["league_id"]:
            await interaction.response.send_message("❌ فريقك ليس في دوري.", ephemeral=True)
            return
        res = db.advance_season(team["league_id"])
        if res is None:
            await interaction.response.send_message("❌ لا يوجد موسم نشط. ابدأ بـ `!موسم`.", ephemeral=True)
            return
        if res == "انتهى":
            await interaction.response.send_message("🏁 انتهى الموسم! البطل توج باللقب.", embed=None, view=None)
            return
        lines = []
        teams = {t["id"]: t for t in db.get_league_teams(team["league_id"])}
        for a, b, ga, gb in res:
            na = teams.get(a, {}).get("name", f"فريق {a}")
            nb = teams.get(b, {}).get("name", f"فريق {b}")
            lines.append(f"⚽ {na} **{ga}** - **{gb}** {nb}")
        e = discord.Embed(title="⚽ نتائج الجولة", color=discord.Color.green())
        e.description = "\n".join(lines)
        await interaction.response.edit_message(content=None, embed=e, view=self)


# ---------------------------------------------------------------------------
# CLUB / LEAGUE SELECTION (real clubs, no typing names)
# ---------------------------------------------------------------------------
class RealLeagueSelect(discord.ui.Select):
    def __init__(self, owner_id, mode, league_id=None):
        self.owner_id = owner_id
        self.mode = mode
        self.league_id = league_id
        options = [
            discord.SelectOption(label=l["name"], emoji=l["emoji"], value=str(l["id"]))
            for l in market_data.LEAGUES
        ]
        super().__init__(placeholder="اختر الدوري الحقيقي...", options=options, custom_id=f"rls_{mode}")

    async def callback(self, interaction: discord.Interaction):
        lid = int(self.values[0])
        owner = str(self.owner_id)
        team = db.get_team_by_owner(owner)
        if self.mode == "create":
            clubs = db.available_clubs(lid)
            if not clubs:
                await interaction.response.send_message("❌ لا توجد أندية متاحة في هذا الدوري.", ephemeral=True)
                return
            view = OwnedView(self.owner_id)
            view.add_item(ClubSelect(self.owner_id, lid, "create"))
            e = discord.Embed(title=f"🏟️ اختر ناديك في {db.get_league(lid)['name']}", color=discord.Color.green())
            e.description = "هذه الأندية متاحة (لم يأخذها أحد):"
            await interaction.response.edit_message(embed=e, view=view)
        elif self.mode == "leaguecreate":
            if team and team["real_league_id"] == lid:
                rl_name = db.get_league(lid)["name"]
                l_id = db.create_league(f"دوري {rl_name}", owner, lid)
                db.update_team(team["id"], league_id=l_id)
                e = discord.Embed(title="🏆 تم إنشاء الدوري!", color=discord.Color.gold(),
                                  description=f"**دوري {rl_name}** (رقم {l_id})\nانضم زملاؤك عبر `!انضمام {l_id}`.")
                await interaction.response.edit_message(embed=e, view=None)
                return
            clubs = db.available_clubs(lid)
            if not clubs:
                await interaction.response.send_message("❌ لا توجد أندية متاحة في هذا الدوري.", ephemeral=True)
                return
            view = OwnedView(self.owner_id)
            view.add_item(ClubSelect(self.owner_id, lid, "leaguecreate"))
            e = discord.Embed(title=f"🏆 اختر ناديك في {db.get_league(lid)['name']} لإنشاء الدوري",
                              color=discord.Color.gold())
            e.description = "سيُنشأ الدوري وستنضم إليه بهذا النادي."
            await interaction.response.edit_message(embed=e, view=view)


class ClubSelect(discord.ui.Select):
    def __init__(self, owner_id, real_league_id, mode="create", league_id=None, page=0):
        self.owner_id = owner_id
        self.real_league_id = real_league_id
        self.mode = mode
        self.league_id = league_id
        self.page = page
        clubs = db.available_clubs(real_league_id)
        per_page = 20
        start = page * per_page
        slice_clubs = clubs[start:start + per_page]
        options = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in slice_clubs]
        if len(clubs) > start + per_page:
            options.append(discord.SelectOption(label="⬇️ التالي", value="next"))
        if page > 0:
            options.insert(0, discord.SelectOption(label="⬆️ السابق", value="prev"))
        options.append(discord.SelectOption(label="🔙 رجوع", value="back"))
        super().__init__(placeholder="اختر ناديك...", options=options,
                         custom_id=f"cs_{mode}_{real_league_id}_{page}")

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "back":
            view = OwnedView(self.owner_id)
            view.add_item(RealLeagueSelect(self.owner_id, self.mode, self.league_id))
            await interaction.response.edit_message(content="اختر الدوري:", view=view)
            return
        if val == "next":
            view = OwnedView(self.owner_id)
            view.add_item(ClubSelect(self.owner_id, self.real_league_id, self.mode, self.league_id, self.page + 1))
            await interaction.response.edit_message(view=view)
            return
        if val == "prev":
            view = OwnedView(self.owner_id)
            view.add_item(ClubSelect(self.owner_id, self.real_league_id, self.mode, self.league_id, self.page - 1))
            await interaction.response.edit_message(view=view)
            return
        cid = int(val)
        owner = str(self.owner_id)
        team = db.get_team_by_owner(owner)
        if self.mode == "create":
            if db.club_taken(cid):
                await interaction.response.send_message("❌ هذا النادي مأخوذ بالفعل من لاعب آخر.", ephemeral=True)
                return
            tid, budget = db.create_team_with_club(cid, owner)
            db.create_coach(owner, str(interaction.user), tid)
            club = db.get_club(cid)
            e = discord.Embed(title="✅ تم إنشاء الفريق!", color=discord.Color.green(),
                              description=(f"**{club['name']}** ({db.get_league(club['league_id'])['name']})\n"
                                           f"👥 24 لاعباً في تشكيلتك\n💰 الميزانية: {budget}م (تعويض للأندية الضعيفة)"))
            e.set_footer(text="اكتب !فريقي لفتح لوحة التحكم")
            await interaction.response.edit_message(embed=e, view=None)
        elif self.mode == "leaguecreate":
            if db.club_taken(cid):
                await interaction.response.send_message("❌ هذا النادي مأخوذ بالفعل.", ephemeral=True)
                return
            if not team:
                db.create_team_with_club(cid, owner)
                db.create_coach(owner, str(interaction.user), db.get_team_by_owner(owner)["id"])
            elif team["club_id"] != cid:
                await interaction.response.send_message(
                    "❌ لديك فريق باسم آخر. استقل بـ !فريقي ← استقالة ثم أعد المحاولة.", ephemeral=True)
                return
            rl_name = db.get_league(self.real_league_id)["name"]
            lid = db.create_league(f"دوري {rl_name}", owner, self.real_league_id)
            db.update_team(db.get_team_by_owner(owner)["id"], league_id=lid)
            e = discord.Embed(title="🏆 تم إنشاء الدوري!", color=discord.Color.gold(),
                              description=f"**دوري {rl_name}** (رقم {lid})\nانضم زملاؤك عبر `!انضمام {lid}` واختاروا أنديتهم.")
            await interaction.response.edit_message(embed=e, view=None)
        elif self.mode == "join":
            league = db.get_league(self.league_id)
            if not league:
                await interaction.response.send_message("❌ الدوري غير موجود.", ephemeral=True)
                return
            rl = league["real_league_id"]
            if db.get_club(cid)["league_id"] != rl:
                await interaction.response.send_message("❌ هذا النادي ليس في دوري هذه المسابقة.", ephemeral=True)
                return
            if db.club_taken(cid):
                await interaction.response.send_message("❌ هذا النادي مأخوذ بالفعل.", ephemeral=True)
                return
            if not team:
                db.create_team_with_club(cid, owner)
                db.create_coach(owner, str(interaction.user), db.get_team_by_owner(owner)["id"])
            elif team["club_id"] != cid:
                await interaction.response.send_message("❌ لديك فريق باسم آخر. استقل أولاً.", ephemeral=True)
                return
            db.join_league(self.league_id, owner, cid)
            e = discord.Embed(title="✅ تم الانضمام!", color=discord.Color.green(),
                              description=f"انضممت إلى الدوري رقم **{self.league_id}** بفريق **{db.get_club(cid)['name']}**.")
            await interaction.response.edit_message(embed=e, view=None)


class CreateTeamView(OwnedView):
    @discord.ui.button(label="➕ إنشاء فريق", emoji="🏟️", style=discord.ButtonStyle.success)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(RealLeagueSelect(self.owner_id, "create"))
        e = discord.Embed(title="🏟️ اختر الدوري ثم ناديك", color=discord.Color.green())
        e.description = "ستحصل على تشكيلة النادي الحقيقية (24 لاعباً). الأندية الضعيفة تحصل على ميزانية أكبر."
        await interaction.response.edit_message(embed=e, view=view)


class LeaguePickSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        leagues = db.get_leagues()
        options = [
            discord.SelectOption(label=f"#{l['id']} - {l['name']}",
                                 description=f"الأعضاء: {len(json.loads(l['members']))}", value=str(l["id"]))
            for l in leagues[:25]
        ]
        if not options:
            options = [discord.SelectOption(label="لا توجد دوريات", value="none")]
        super().__init__(placeholder="اختر دوريًا...", options=options, custom_id="lps")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("لا توجد دوريات.", ephemeral=True)
            return
        lid = int(self.values[0])
        league = db.get_league(lid)
        rl = league["real_league_id"]
        view = OwnedView(self.owner_id)
        view.add_item(ClubSelect(self.owner_id, rl, "join", league_id=lid))
        e = discord.Embed(title=f"🏟️ اختر ناديك في دوري #{lid}", color=discord.Color.green())
        e.description = "اختر نادياً متاحاً (لم يأخذه أحد):"
        await interaction.response.edit_message(embed=e, view=view)


class LeagueMenuView(OwnedView):
    @discord.ui.button(label="إنشاء دوري", emoji="➕", style=discord.ButtonStyle.success)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(RealLeagueSelect(self.owner_id, "leaguecreate"))
        e = discord.Embed(title="🏆 اختر الدوري الحقيقي للمسابقة", color=discord.Color.gold())
        e.description = "ستنشئ دوريًا تنافس فيه أنت وزملاؤك بأنديتكم الحقيقية."
        await interaction.response.edit_message(embed=e, view=view)

    @discord.ui.button(label="انضمام لدوري", emoji="🔗", style=discord.ButtonStyle.primary)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        leagues = db.get_leagues()
        if not leagues:
            await interaction.response.send_message("لا توجد دوريات. أنشئ واحداً!", ephemeral=True)
            return
        view = OwnedView(self.owner_id)
        view.add_item(LeaguePickSelect(self.owner_id))
        await interaction.response.edit_message(content="🏆 اختر دوريًا للانضمام:", view=view)


class TeamPanel(OwnedView):
    @discord.ui.button(label="سوق", emoji="🛒", style=discord.ButtonStyle.success, row=0)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MarketView(self.owner_id)
        embed = discord.Embed(title="🛒 سوق الانتقالات", color=discord.Color.blue())
        embed.description = "اختر الدوري ثم النادي لعرض اللاعبين المتاحين."
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="عرض للبيع", emoji="💰", style=discord.ButtonStyle.primary, row=0)
    async def sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(OwnedPlayerSelect(self.owner_id, "sell"))
        await interaction.response.send_message("💰 اختر لاعباً لبيعه:", view=view, ephemeral=True)

    @discord.ui.button(label="تطوير", emoji="🔧", style=discord.ButtonStyle.primary, row=0)
    async def develop(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(OwnedPlayerSelect(self.owner_id, "develop"))
        await interaction.response.send_message("🔧 اختر لاعباً لتطويره:", view=view, ephemeral=True)

    @discord.ui.button(label="عرض لاعب", emoji="📋", style=discord.ButtonStyle.secondary, row=0)
    async def view_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(OwnedPlayerSelect(self.owner_id, "view"))
        await interaction.response.send_message("📋 اختر لاعباً لعرض تفاصيله:", view=view, ephemeral=True)

    @discord.ui.button(label="طرد لاعب", emoji="❌", style=discord.ButtonStyle.danger, row=1)
    async def release(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(OwnedPlayerSelect(self.owner_id, "release"))
        await interaction.response.send_message("❌ اختر لاعباً لطرده:", view=view, ephemeral=True)

    @discord.ui.button(label="تشكيل", emoji="📐", style=discord.ButtonStyle.secondary, row=1)
    async def formation(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(FormationSelect(self.owner_id))
        await interaction.response.send_message("📐 اختر التشكيل:", view=view, ephemeral=True)

    @discord.ui.button(label="خطة", emoji="🎯", style=discord.ButtonStyle.secondary, row=1)
    async def tactic(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(TacticSelect(self.owner_id))
        await interaction.response.send_message("🎯 اختر الخطة:", view=view, ephemeral=True)

    @discord.ui.button(label="تدريب", emoji="🏋️", style=discord.ButtonStyle.secondary, row=1)
    async def train(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TrainModal(self.owner_id))

    @discord.ui.button(label="تحدي", emoji="⚔️", style=discord.ButtonStyle.danger, row=2)
    async def challenge(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(ChallengeUserSelect(self.owner_id))
        await interaction.response.send_message("⚔️ اختر خصماً:", view=view, ephemeral=True)

    @discord.ui.button(label="الدوريات", emoji="🏆", style=discord.ButtonStyle.primary, row=2)
    async def leagues(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🏆 إدارة الدوريات:", view=LeagueMenuView(self.owner_id), ephemeral=True
        )

    @discord.ui.button(label="تحديث", emoji="🔄", style=discord.ButtonStyle.secondary, row=2)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        players = db.team_players(team["id"]) if team else []
        await interaction.response.edit_message(embed=team_embed(team, players), view=self)

    @discord.ui.button(label="استقالة", emoji="🚪", style=discord.ButtonStyle.danger, row=2)
    async def resign(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "⚠️ هل أنت متأكد من حل فريقك؟ هذا الإجراء لا يمكن التراجع عنه.",
            view=ResignView(self.owner_id),
            ephemeral=True,
        )

    @discord.ui.button(label="تكتيك كامل", emoji="🧠", style=discord.ButtonStyle.secondary, row=3)
    async def full_tactics(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        await interaction.response.send_message(
            embed=tactics_embed(team), view=FullTacticsView(self.owner_id), ephemeral=True)

    @discord.ui.button(label="حصة تدريب", emoji="🏋️", style=discord.ButtonStyle.secondary, row=3)
    async def drill(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OwnedView(self.owner_id)
        view.add_item(TrainingDrillSelect(self.owner_id))
        await interaction.response.send_message("🏋️ اختر الحصة التدريبية:", view=view, ephemeral=True)

    @discord.ui.button(label="منشآت", emoji="🏗️", style=discord.ButtonStyle.secondary, row=3)
    async def facilities(self, interaction: discord.Interaction, button: discord.ui.Button):
        team = db.get_team_by_owner(str(self.owner_id))
        await interaction.response.send_message(
            embed=facilities_embed(team), view=FacilitiesView(self.owner_id), ephemeral=True)

    @discord.ui.button(label="كشافة", emoji="🔍", style=discord.ButtonStyle.primary, row=3)
    async def scout(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔍 الكشافة تجلب لك لاعباً حراً مباشرة لفريقك مقابل 10 رموز:",
            view=ScoutView(self.owner_id), ephemeral=True)

    @discord.ui.button(label="موسمي", emoji="🏆", style=discord.ButtonStyle.primary, row=3)
    async def season(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🏆 إدارة موسم دوريك:", view=SeasonView(self.owner_id), ephemeral=True)
