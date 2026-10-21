"""
roulette_cog.py
نظام الروليت التفاعلي الاحترافي (واجهة مختصرة، رسائل مدمجة، وإخفاء النقاط والمشتريات).
"""

import asyncio
import time
import random
import logging
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

from roulette_gif import make_image, download_avatars_concurrently
from roulette_shop import (
    RouletteShopView, get_user_data, get_points,
    has_item, use_item, record_kick, record_win, get_leaderboard
)

log = logging.getLogger("roulette_cog")

WAITING_TIME = 27
MAX_SEATS = 50
MIN_PLAYERS = 3


def format_players_text(players):
    if not players:
        return "لا يوجد مشاركون بعد — اضغط **دخول سريع** للانضمام!"
    sorted_players = sorted(players, key=lambda x: x["number"])
    lines = []
    chunk_size = 3  # 3 أعمدة لتقليل طول الرسالة في الشات
    for i in range(0, len(sorted_players), chunk_size):
        chunk = sorted_players[i:i + chunk_size]
        col_parts = [f"`[{p['number']:02d}]` <@{p['id']}>" for p in chunk]
        lines.append("   ".join(col_parts))
    return "\n".join(lines)


class ChooseSeatModal(Modal, title="اختيار رقم المقعد 🔢"):
    def __init__(self, game):
        super().__init__(timeout=60)
        self.game = game
        self.seat_input = TextInput(
            label=f"رقم المقعد (1 - {MAX_SEATS})",
            placeholder="مثال: 7",
            min_length=1,
            max_length=2,
            required=True
        )
        self.add_item(self.seat_input)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.seat_input.value.strip()
        if not val.isdigit() or not (1 <= int(val) <= MAX_SEATS):
            return await interaction.response.send_message(f"❌ اختر رقماً صحيحاً بين 1 و {MAX_SEATS}.", ephemeral=True)
        number = int(val)

        async with self.game.lock:
            if self.game.state != "WAITING" or self.game.cancelled:
                return await interaction.response.send_message("❌ انتهى وقت التسجيل.", ephemeral=True)
            if any(p["id"] == interaction.user.id for p in self.game.players):
                return await interaction.response.send_message("❌ أنت مسجل بالفعل!", ephemeral=True)
            if any(p["number"] == number for p in self.game.players):
                return await interaction.response.send_message(f"❌ المقعد `{number:02d}` محجوز!", ephemeral=True)

            self.game.players.append({
                "number": number,
                "id": interaction.user.id,
                "username": interaction.user.display_name,
                "avatar_url": interaction.user.display_avatar.url,
                "avimg": None
            })

        await interaction.response.send_message(f"✅ حجزت المقعد `[{number:02d}]`.", ephemeral=True)
        await self.game.request_refresh()


class RouletteJoinView(View):
    def __init__(self, game):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="دخول سريع", emoji="🎲", style=discord.ButtonStyle.success, row=0)
    async def join_quick(self, interaction: discord.Interaction, button: Button):
        async with self.game.lock:
            if self.game.state != "WAITING" or self.game.cancelled:
                return await interaction.response.send_message("❌ انتهى وقت التسجيل.", ephemeral=True)
            if any(p["id"] == interaction.user.id for p in self.game.players):
                return await interaction.response.send_message("❌ أنت مسجل بالفعل!", ephemeral=True)
            if len(self.game.players) >= MAX_SEATS:
                return await interaction.response.send_message("❌ المقاعد مكتملة!", ephemeral=True)

            taken = {p["number"] for p in self.game.players}
            available = [n for n in range(1, MAX_SEATS + 1) if n not in taken]
            number = random.choice(available)
            self.game.players.append({
                "number": number,
                "id": interaction.user.id,
                "username": interaction.user.display_name,
                "avatar_url": interaction.user.display_avatar.url,
                "avimg": None
            })

        await interaction.response.send_message(f"✅ انضممت في المقعد `[{number:02d}]`.", ephemeral=True)
        await self.game.request_refresh()

    @discord.ui.button(label="اختر مقعداً", emoji="🔢", style=discord.ButtonStyle.primary, row=0)
    async def choose_seat(self, interaction: discord.Interaction, button: Button):
        if self.game.state != "WAITING" or self.game.cancelled:
            return await interaction.response.send_message("❌ انتهى وقت التسجيل.", ephemeral=True)
        if any(p["id"] == interaction.user.id for p in self.game.players):
            return await interaction.response.send_message("❌ أنت مسجل بالفعل!", ephemeral=True)
        if len(self.game.players) >= MAX_SEATS:
            return await interaction.response.send_message("❌ المقاعد مكتملة!", ephemeral=True)
        await interaction.response.send_modal(ChooseSeatModal(self.game))

    @discord.ui.button(label="خروج", emoji="🚪", style=discord.ButtonStyle.danger, row=0)
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        async with self.game.lock:
            if self.game.state != "WAITING" or self.game.cancelled:
                return await interaction.response.send_message("❌ لا يمكن الخروج الآن.", ephemeral=True)
            player = next((p for p in self.game.players if p["id"] == interaction.user.id), None)
            if not player:
                return await interaction.response.send_message("❌ لست مسجلاً في اللعبة.", ephemeral=True)
            self.game.players = [p for p in self.game.players if p["id"] != interaction.user.id]

        await interaction.response.send_message("✅ خرجت من اللعبة.", ephemeral=True)
        await self.game.request_refresh()

    @discord.ui.button(label="المتجر وحقيبتي", emoji="🏪", style=discord.ButtonStyle.secondary, row=0)
    async def shop_btn(self, interaction: discord.Interaction, button: Button):
        view = RouletteShopView(interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


class DoubleKickSelect(Select):
    def __init__(self, subset_players, parent_view, row=0, placeholder="🎯 اختر لاعبين لطردهم..."):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=f"[{p['number']:02d}] {p['username']}"[:100],
                value=str(p["number"])
            )
            for p in subset_players[:25]
        ]
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=min(2, len(options)),
            options=options,
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.winner["id"]:
            return await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)

        for v in self.values:
            num = int(v)
            if num not in self.parent_view.selected_targets:
                self.parent_view.selected_targets.append(num)

        if len(self.parent_view.selected_targets) >= 2 or len(self.parent_view.others) == 1:
            self.parent_view.main_view.choice = ("double_kick", self.parent_view.selected_targets[:2])
            self.parent_view.main_view.stop()
            self.parent_view.stop()
            await interaction.response.defer()
        else:
            await interaction.response.send_message(
                f"✅ تم تحديد `[{self.parent_view.selected_targets[0]:02d}]`، اختر الهدف الثاني أو اضغط تأكيد.",
                ephemeral=True
            )


class DoubleKickSelectView(View):
    def __init__(self, winner, others, main_view):
        super().__init__(timeout=30)
        self.winner = winner
        self.others = others
        self.main_view = main_view
        self.selected_targets = []

        self.add_item(DoubleKickSelect(others[:25], self, row=0, placeholder="🎯 اختر الهدفين (1-25)..."))
        if len(others) > 25:
            self.add_item(DoubleKickSelect(others[25:50], self, row=1, placeholder="🎯 اختر الهدفين (26-50)..."))

    @discord.ui.button(label="تأكيد", emoji="⚡", style=discord.ButtonStyle.success, row=2)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)
        if not self.selected_targets:
            return await interaction.response.send_message("❌ اختر لاعباً أولاً!", ephemeral=True)
        self.main_view.choice = ("double_kick", self.selected_targets[:2])
        self.main_view.stop()
        self.stop()
        await interaction.response.defer()


class KickView(View):
    def __init__(self, game, winner, players):
        super().__init__(timeout=30)
        self.game = game
        self.winner = winner
        self.choice = None
        self.others = [p for p in players if p["id"] != winner["id"]]

        if len(self.others) <= 15:
            for i, p in enumerate(self.others):
                row = min(i // 5, 2)
                btn = Button(
                    label=f"[{p['number']:02d}] {p['username']}"[:80],
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"kick_{p['number']}",
                    row=row
                )
                btn.callback = self._make_kick_callback(p["number"])
                self.add_item(btn)
        else:
            s1 = Select(
                placeholder="🎯 اختر لاعباً لطرده (1-25)...",
                options=[
                    discord.SelectOption(label=f"[{p['number']:02d}] {p['username']}"[:100], value=str(p["number"]))
                    for p in self.others[:25]
                ],
                row=0
            )
            s1.callback = self._select_callback
            self.add_item(s1)

            if len(self.others) > 25:
                s2 = Select(
                    placeholder="🎯 اختر لاعباً لطرده (26-50)...",
                    options=[
                        discord.SelectOption(label=f"[{p['number']:02d}] {p['username']}"[:100], value=str(p["number"]))
                        for p in self.others[25:50]
                    ],
                    row=1
                )
                s2.callback = self._select_callback
                self.add_item(s2)

        rand_btn = Button(label="طرد عشوائي", emoji="🎲", style=discord.ButtonStyle.primary, row=3)
        rand_btn.callback = self._random_kick_callback
        self.add_item(rand_btn)

        with_btn = Button(label="انسحاب", emoji="🏳️", style=discord.ButtonStyle.danger, row=3)
        with_btn.callback = self._withdraw_callback
        self.add_item(with_btn)

        if has_item(winner["id"], "double_kick"):
            dk_btn = Button(label="طرد ثنائي", emoji="⚡", style=discord.ButtonStyle.success, row=3)
            dk_btn.callback = self._double_kick_callback
            self.add_item(dk_btn)

        my_pts_btn = Button(label="رصيدي ومخزوني", emoji="🎒", style=discord.ButtonStyle.secondary, row=3)
        my_pts_btn.callback = self._check_my_points
        self.add_item(my_pts_btn)

    def _make_kick_callback(self, number):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.winner["id"]:
                return await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)
            self.choice = ("kick", number, interaction)
            self.stop()
            await interaction.response.defer()
        return callback

    async def _select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)
        number = int(interaction.data["values"][0])
        self.choice = ("kick", number, interaction)
        self.stop()
        await interaction.response.defer()

    async def _random_kick_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)
        self.choice = ("random_kick", None, interaction)
        self.stop()
        await interaction.response.defer()

    async def _withdraw_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)
        self.choice = ("withdraw", None, interaction)
        self.stop()
        await interaction.response.defer()

    async def _double_kick_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)
        sub_view = DoubleKickSelectView(self.winner, self.others, self)
        await interaction.response.send_message("⚡ **اختر لاعبين لطردهم:**", view=sub_view, ephemeral=True)

    async def _check_my_points(self, interaction: discord.Interaction):
        u = get_user_data(interaction.user.id)
        inv = u.get("inventory", {})
        msg = (
            f"💰 **نقاطك الحالية:** `{u.get('points', 0)}`\n"
            f"🛡️ درع: `{inv.get('shield', 0)}` | 🔄 عكسي: `{inv.get('reverse_kick', 0)}` | ⚡ ثنائي: `{inv.get('double_kick', 0)}`"
        )
        await interaction.response.send_message(msg, ephemeral=True)


class RouletteGame:
    def __init__(self, cog, channel, starter):
        self.cog = cog
        self.channel = channel
        self.guild = channel.guild
        self.starter = starter
        self.channel_id = channel.id
        self.created_at = time.time()
        self.start_timestamp = int(self.created_at + WAITING_TIME)
        self.players = []
        self.state = "WAITING"
        self.cancelled = False
        self.lock = asyncio.Lock()
        self.main_message = None
        self.join_view = None
        self.current_view = None
        self.task = None
        self._last_refresh_time = 0.0
        self._refresh_scheduled = False

    def build_join_embed(self):
        embed = discord.Embed(
            title=f"🎡 روليت الحظ ({len(self.players)}/{MAX_SEATS})",
            description=f"{format_players_text(self.players)}\n\n⏳ يبدأ اللعب: **<t:{self.start_timestamp}:R>**",
            color=0xF1C40F
        )
        return embed

    async def request_refresh(self):
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        now = time.time()
        delay = max(0.0, 0.7 - (now - self._last_refresh_time))
        if delay > 0:
            await asyncio.sleep(delay)
        self._refresh_scheduled = False
        self._last_refresh_time = time.time()
        if self.main_message and self.state == "WAITING" and not self.cancelled:
            try:
                await self.main_message.edit(embed=self.build_join_embed(), view=self.join_view)
            except Exception:
                pass


class RouletteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    def is_game_active(self, channel_id):
        return channel_id in self.active_games

    async def stop_game(self, channel_id, author=None):
        game = self.active_games.pop(channel_id, None)
        if not game:
            return False
        game.cancelled = True
        if game.current_view:
            game.current_view.stop()
        if game.join_view:
            game.join_view.stop()
        if game.task and not game.task.done():
            game.task.cancel()
        return True

    @commands.command(name="روليت", aliases=["roulette"])
    async def roulette_cmd(self, ctx):
        if not self._can_manage_events(ctx):
            return await ctx.send("❌ للمشرفين فقط.", delete_after=5)

        cid = ctx.channel.id
        if self.is_game_active(cid):
            old = self.active_games.get(cid)
            if old and (time.time() - old.created_at) > 600:
                await self.stop_game(cid)
            else:
                return await ctx.send("❌ توجد لعبة نشطة بالفعل!", delete_after=5)

        try:
            from bot import has_active_game, get_active_game, register_game
            if has_active_game(cid):
                return await ctx.send(f"❌ توجد لعبة **{get_active_game(cid)}** نشطة في الروم!", delete_after=5)
        except Exception:
            pass

        game = RouletteGame(self, ctx.channel, ctx.author)
        self.active_games[cid] = game
        try:
            from bot import register_game
            register_game(cid, "roulette")
        except Exception:
            pass

        game.task = asyncio.create_task(self._run_game_lifecycle(ctx, game))

    @commands.command(name="متجر", aliases=["shop", "المتجر", "نقاطي", "points", "رصيدي"])
    async def shop_cmd(self, ctx):
        """فتح زر المتجر والنقاط بشكل خاص لكل لاعب دون إزعاج الشات"""
        view = View(timeout=60)
        btn = Button(label="فتح المتجر ورصيدي الشخصي", emoji="🏪", style=discord.ButtonStyle.primary)

        async def _open_ephemeral(interaction: discord.Interaction):
            shop_view = RouletteShopView(interaction.user)
            await interaction.response.send_message(embed=shop_view.build_embed(), view=shop_view, ephemeral=True)

        btn.callback = _open_ephemeral
        view.add_item(btn)
        await ctx.send("👇 **اضغط هنا لعرض نقاطك ومشترياتك بشكل خاص:**", view=view, delete_after=60)

    @commands.command(name="توب_الروليت", aliases=["توب_روليت", "roulette_top", "top_roulette"])
    async def leaderboard_cmd(self, ctx):
        top_list = get_leaderboard(limit=10)
        if not top_list:
            return await ctx.send("📋 لا توجد بيانات بعد.")

        medals = ["🥇", "🥈", "🥉"]
        lines = [
            f"{medals[i] if i < 3 else f'`{i+1:02d}.`'} <@{u['id']}> — 🏆 `{u['wins']}` فوز | 🎯 `{u['kicks']}` طرد"
            for i, u in enumerate(top_list)
        ]
        embed = discord.Embed(title="🏆 متصدرو الروليت", description="\n".join(lines), color=0xF1C40F)
        await ctx.send(embed=embed)

    async def _run_game_lifecycle(self, ctx, game):
        cid = ctx.channel.id
        try:
            game.join_view = RouletteJoinView(game)
            game.current_view = game.join_view
            game.main_message = await ctx.send(embed=game.build_join_embed(), view=game.join_view)

            await asyncio.sleep(WAITING_TIME)
            if game.cancelled:
                return

            game.state = "IN_PROGRESS"
            for b in game.join_view.children:
                b.disabled = True
            try:
                await game.main_message.edit(view=game.join_view)
            except Exception:
                pass

            if len(game.players) < MIN_PLAYERS:
                return await ctx.send(f"🚫 ألغيت اللعبة لعدم اكتمال `{MIN_PLAYERS}` لاعبين.")

            await download_avatars_concurrently(game.players)

            round_number = 1
            while len(game.players) > 2 and not game.cancelled:
                await self._run_single_round(ctx, game, round_number)
                round_number += 1
                if len(game.players) > 2 and not game.cancelled:
                    await asyncio.sleep(1.5)

            if not game.cancelled and len(game.players) >= 1:
                await self._crown_champion(ctx, game)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.exception("Roulette lifecycle error: %s", e)
        finally:
            self.active_games.pop(cid, None)
            try:
                from bot import unregister_game
                unregister_game(cid)
            except Exception:
                pass

    async def _run_single_round(self, ctx, game, round_number):
        players = list(game.players)
        random.shuffle(players)
        winner = players[-1]
        highlight_idx = len(players) - 1

        img_buf = await make_image(
            [{"number": p["number"], "img": p.get("avimg")} for p in players],
            highlight=highlight_idx
        )

        kick_view = KickView(game, winner, players)
        game.current_view = kick_view

        # رسالة واحدة مدمجة فيها الصورة والأزرار معاً لتقليل الرسائل في الشات
        content = f"🎡 **الجولة {round_number}** (`{len(players)}` متبقي) — الدور على **[{winner['number']:02d}]** <@{winner['id']}>"
        turn_msg = await ctx.send(
            content=content,
            file=discord.File(img_buf, filename="roulette.png"),
            view=kick_view
        )

        await kick_view.wait()

        for item in kick_view.children:
            item.disabled = True
        try:
            await turn_msg.edit(view=None)  # إزالة الأزرار بعد انتهاء الدور ليبقى الشات نظيفاً
        except Exception:
            pass

        if game.cancelled:
            return

        choice = kick_view.choice
        others = [p for p in players if p["id"] != winner["id"]]

        if not choice:
            await ctx.send(f"⏰ استُبعد <@{winner['id']}> لعدم التفاعل.")
            game.players = [p for p in game.players if p["id"] != winner["id"]]
            return

        c_type = choice[0]
        c_val = choice[1]
        inter = choice[2] if len(choice) > 2 else None

        if c_type == "withdraw":
            await ctx.send(f"🏳️ انسحب <@{winner['id']}> من اللعبة.")
            game.players = [p for p in game.players if p["id"] != winner["id"]]
            return

        if c_type in ("kick", "random_kick"):
            is_random = (c_type == "random_kick")
            victim = random.choice(others) if is_random else next((p for p in players if p["number"] == c_val), None)

            if not victim:
                return

            icon = "🎲" if is_random else "💣"
            rand_tag = " عشوائياً" if is_random else ""

            if use_item(victim["id"], "reverse_kick"):
                new_pts = record_kick(victim["id"])
                await ctx.send(f"🔄 **طرد عكسي!** انعكست ضربة <@{winner['id']}> وطُرد هو بدلاً من <@{victim['id']}>!")
                return

            if use_item(victim["id"], "shield"):
                await ctx.send(f"🛡️ تحطم درع <@{victim['id']}> وحماه من طرد <@{winner['id']}>!")
                return

            new_pts = record_kick(winner["id"])
            game.players = [p for p in game.players if p["id"] != victim["id"]]
            await ctx.send(f"{icon} طرد <@{winner['id']}> اللاعب <@{victim['id']}>{rand_tag}!")
            if inter:
                try:
                    await inter.followup.send(f"🎯 كسبت **+1 نقطة**! (رصيدك: `{new_pts}`)", ephemeral=True)
                except Exception:
                    pass
            return

        if c_type == "double_kick":
            if use_item(winner["id"], "double_kick"):
                target_nums = c_val if c_val else []
                targets = [p for p in players if p["number"] in target_nums]
                if not targets:
                    targets = random.sample(others, min(2, len(others))) if others else []

                events = []
                for v in targets:
                    if use_item(v["id"], "reverse_kick"):
                        record_kick(v["id"])
                        game.players = [p for p in game.players if p["id"] != winner["id"]]
                        await ctx.send(f"🔄 **طرد عكسي!** ردّ <@{v['id']}> الضربة الثنائية وطرد <@{winner['id']}>!")
                        return
                    elif use_item(v["id"], "shield"):
                        events.append(f"🛡️ نجا <@{v['id']}> بالدرع")
                    else:
                        game.players = [p for p in game.players if p["id"] != v["id"]]
                        record_kick(winner["id"])
                        events.append(f"💣 طُرد <@{v['id']}>")

                await ctx.send(f"⚡ **طرد ثنائي من <@{winner['id']}>:** " + " ، ".join(events))

    async def _crown_champion(self, ctx, game):
        if len(game.players) == 2:
            players = list(game.players)
            random.shuffle(players)
            champion = players[-1]
            img_buf = await make_image(
                [{"number": p["number"], "img": p.get("avimg")} for p in players],
                highlight=len(players) - 1
            )
            await ctx.send(
                content=f"👑 **الجولة النهائية!** الفائز باللقب هو <@{champion['id']}>!",
                file=discord.File(img_buf, filename="roulette.png")
            )
        elif len(game.players) == 1:
            champion = game.players[0]
            await ctx.send(f"👑 **انتهت اللعبة!** الفائز باللقب هو <@{champion['id']}>!")
        else:
            return

        record_win(champion["id"])

    def _can_manage_events(self, ctx):
        if not ctx.guild:
            return True
        p = ctx.author.guild_permissions
        return p.administrator or p.manage_guild or p.manage_events or p.manage_messages or ctx.author.id == ctx.guild.owner_id