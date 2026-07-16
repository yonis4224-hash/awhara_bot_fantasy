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
    e = discord.Embed(title=f"⚽ {team['name']}", color=discord.Color.green())
    e.add_field(name="💰 الميزانية", value=f"{team['budget']}م", inline=True)
    e.add_field(name="🟢 الخبرة", value=f"{team['xp']} نقطة", inline=True)
    e.add_field(name="📐 التشكيل", value=team["formation"], inline=True)
    e.add_field(name="🎯 الخطة", value=team["tactic"], inline=True)
    e.add_field(name="🏋️ التدريب", value=f"{team['training_invest']} نقطة", inline=True)
    e.add_field(name="👥 عدد اللاعبين", value=str(len(players)), inline=True)

    if players:
        lines = []
        for p in players:
            emo = POS_EMOJI.get(p["position"], "")
            lines.append(f"{emo} `{p['id']}` **{p['name']}** — ريت {p['rating']} | {p['price']}م")
        e.add_field(name="اللاعبون", value="\n".join(lines[:25]), inline=False)
    else:
        e.add_field(name="اللاعبون", value="لا يوجد لاعبين. اضغط 🛒 شراء.", inline=False)

    e.set_footer(text="استخدم الأزرار بالأسفل للتحكم بفريقك")
    return e


def player_detail_embed(p):
    pos = POS_ARABIC.get(p["position"], p["position"])
    status = "في فريق ⚽" if p["team_id"] else "في السوق 🛒"
    e = discord.Embed(title=f"📋 {p['name']}", color=discord.Color.blue())
    e.add_field(name="المركز", value=f"{POS_EMOJI.get(p['position'],'')} {pos}", inline=True)
    e.add_field(name="الريت", value=str(p["rating"]), inline=True)
    e.add_field(name="السعر", value=f"{p['price']}م", inline=True)
    e.add_field(name="الحالة", value=status, inline=True)
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
        e = discord.Embed(title=f"📋 {p['name']}", color=discord.Color.blue())
        pos = POS_ARABIC.get(p["position"], p["position"])
        e.add_field(name="المركز", value=pos, inline=True)
        e.add_field(name="الريت", value=str(p["rating"]), inline=True)
        e.add_field(name="السعر", value=f"{p['price']}م", inline=True)
        e.add_field(name="الحالة", value="في السوق 🛒", inline=True)
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
            "🏆 إدارة الدوريات:", view=LeagueView(self.owner_id), ephemeral=True
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
