"""
roulette_cog.py
نظام الروليت التفاعلي المتقدم لبوت أوهارا (يدعم حتى 50 لاعباً).
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
    RouletteShopView, get_user_data, add_points, get_points,
    buy_item, has_item, use_item, ITEMS, record_kick, record_win,
    get_leaderboard
)

log = logging.getLogger("roulette_cog")

WAITING_TIME = 27
MAX_SEATS = 50
MIN_PLAYERS = 3

HOWTO_TEXT = (
    f"**1-** انضم في اللعبة عبر الدخول السريع أو اختر مقعدك المفضل (1-{MAX_SEATS}).\n"
    "**2-** في كل جولة تدور العجلة وتختار لاعباً عشوائياً.\n"
    "**3-** اللاعب المختار يملك 30 ثانية لاختيار لاعب لطرده من اللعبة.\n"
    "**4-** يستمر الطرد حتى يتبقى لاعبان، ثم تدور العجلة لتتويج الفائز باللقب و 3 نقاط! 👑"
)

ITEMS_INFO = (
    "🛡️ **درع ضد الطرد (18 نقطة):** يحميك تلقائياً من أول محاولة طرد موجهة إليك.\n"
    "🔄 **طرد عكسي (22 نقطة):** يعكس الضربة ليطرد اللاعب المعتدي بدلاً منك ويمنحك +1 نقطة!\n"
    "⚡ **طرد ثنائي (25 نقطة):** يتيح لك طرد لاعبين اثنين في نفس دورك باللعبة."
)


def format_players_text(players):
    if not players:
        return "لا يوجد لاعبين مشاركين حالياً.\nاضغط على الأزرار بالأسفل للانضمام!"
    sorted_players = sorted(players, key=lambda x: x["number"])
    lines = []
    chunk_size = 2
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
            label=f"رقم المقعد المطلوب (من 1 إلى {MAX_SEATS})",
            placeholder="مثال: 7 أو 45",
            min_length=1,
            max_length=2,
            required=True
        )
        self.add_item(self.seat_input)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.seat_input.value.strip()
        if not val.isdigit():
            return await interaction.response.send_message("❌ الرجاء إدخال رقم صحيح فقط!", ephemeral=True)
        number = int(val)
        if number < 1 or number > MAX_SEATS:
            return await interaction.response.send_message(f"❌ الرجاء اختيار رقم بين 1 و {MAX_SEATS}!", ephemeral=True)

        async with self.game.lock:
            if self.game.state != "WAITING" or self.game.cancelled:
                return await interaction.response.send_message("❌ انتهت فترة التسجيل لهذه الجولة.", ephemeral=True)
            if any(p["id"] == interaction.user.id for p in self.game.players):
                return await interaction.response.send_message("❌ أنت مشارك بالفعل في الروليت!", ephemeral=True)
            if any(p["number"] == number for p in self.game.players):
                return await interaction.response.send_message(f"❌ المقعد رقم **{number}** محجوز بالفعل! اختر مقعداً آخر أو استخدم الدخول السريع.", ephemeral=True)

            self.game.players.append({
                "number": number,
                "id": interaction.user.id,
                "username": interaction.user.display_name,
                "avatar_url": interaction.user.display_avatar.url,
                "avimg": None
            })

        await interaction.response.send_message(f"✅ تم حجز المقعد رقم **[{number:02d}]** بنجاح!", ephemeral=True)
        await self.game.request_refresh()


class RouletteJoinView(View):
    def __init__(self, game):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="دخول سريع 🎲", style=discord.ButtonStyle.success, row=0)
    async def join_quick(self, interaction: discord.Interaction, button: Button):
        async with self.game.lock:
            if self.game.state != "WAITING" or self.game.cancelled:
                return await interaction.response.send_message("❌ انتهت فترة التسجيل لهذه الجولة.", ephemeral=True)
            if any(p["id"] == interaction.user.id for p in self.game.players):
                return await interaction.response.send_message("❌ أنت مشارك بالفعل! للخروج اضغط على زر 'خروج'.", ephemeral=True)
            if len(self.game.players) >= MAX_SEATS:
                return await interaction.response.send_message(f"❌ عدد المقاعد مكتمل ({MAX_SEATS}/{MAX_SEATS})!", ephemeral=True)

            taken = {p["number"] for p in self.game.players}
            available = [n for n in range(1, MAX_SEATS + 1) if n not in taken]
            if not available:
                return await interaction.response.send_message("❌ عدد المقاعد مكتمل!", ephemeral=True)

            number = random.choice(available)
            self.game.players.append({
                "number": number,
                "id": interaction.user.id,
                "username": interaction.user.display_name,
                "avatar_url": interaction.user.display_avatar.url,
                "avimg": None
            })

        await interaction.response.send_message(f"✅ تم تسجيلك بنجاح في المقعد رقم **[{number:02d}]**!", ephemeral=True)
        await self.game.request_refresh()

    @discord.ui.button(label="اختيار مقعد 🔢", style=discord.ButtonStyle.primary, row=0)
    async def choose_seat(self, interaction: discord.Interaction, button: Button):
        if self.game.state != "WAITING" or self.game.cancelled:
            return await interaction.response.send_message("❌ انتهت فترة التسجيل لهذه الجولة.", ephemeral=True)
        if any(p["id"] == interaction.user.id for p in self.game.players):
            return await interaction.response.send_message("❌ أنت مشارك بالفعل في الروليت!", ephemeral=True)
        if len(self.game.players) >= MAX_SEATS:
            return await interaction.response.send_message("❌ عدد المقاعد مكتمل!", ephemeral=True)

        await interaction.response.send_modal(ChooseSeatModal(self.game))

    @discord.ui.button(label="خروج 🚪", style=discord.ButtonStyle.danger, row=0)
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        async with self.game.lock:
            if self.game.state != "WAITING" or self.game.cancelled:
                return await interaction.response.send_message("❌ لا يمكنك الخروج بعد بدء اللعبة.", ephemeral=True)
            player = next((p for p in self.game.players if p["id"] == interaction.user.id), None)
            if not player:
                return await interaction.response.send_message("❌ أنت غير مشارك في اللعبة بالفعل.", ephemeral=True)

            self.game.players = [p for p in self.game.players if p["id"] != interaction.user.id]

        await interaction.response.send_message(f"✅ تم خروجك من اللعبة وإخلاء المقعد رقم **[{player['number']:02d}]**.", ephemeral=True)
        await self.game.request_refresh()

    @discord.ui.button(label="المتجر 🏪", style=discord.ButtonStyle.secondary, row=0)
    async def shop_btn(self, interaction: discord.Interaction, button: Button):
        view = RouletteShopView(interaction.user)
        embed = view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="الخواص 📜", style=discord.ButtonStyle.secondary, row=0)
    async def items_guide_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="📜 دليل خواص الروليت التكتيكية",
            description=ITEMS_INFO,
            color=0x3498DB
        )
        embed.set_footer(text="يمكنك شراء الخواص عبر زر المتجر 🏪 واستخدامها تلقائياً باللعبة!")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DoubleKickSelect(Select):
    def __init__(self, subset_players, parent_view, row=0, placeholder="🎯 اختر لاعبين لطردهم..."):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=f"[{p['number']:02d}] {p['username']}"[:100],
                value=str(p["number"]),
                description=f"طرد اللاعب رقم {p['number']}"
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
            return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)

        selected_nums = [int(v) for v in self.values]
        for num in selected_nums:
            if num not in self.parent_view.selected_targets:
                self.parent_view.selected_targets.append(num)

        # إذا اختار لاعبين اثنين أو لم يتبق سواهم، ننفذ الطرد الثنائي فوراً
        if len(self.parent_view.selected_targets) >= 2 or len(self.parent_view.others) == 1:
            final_targets = self.parent_view.selected_targets[:2]
            self.parent_view.main_view.choice = ("double_kick", final_targets)
            self.parent_view.main_view.stop()
            self.parent_view.stop()
            await interaction.response.defer()
        else:
            await interaction.response.send_message(
                f"✅ تم تحديد المقعد `[{selected_nums[0]:02d}]` كهدف أول! اختر الهدف الثاني أو اضغط زر **تأكيد الطرد**.",
                ephemeral=True
            )


class DoubleKickSelectView(View):
    def __init__(self, winner, others, main_view):
        super().__init__(timeout=30)
        self.winner = winner
        self.others = others
        self.main_view = main_view
        self.selected_targets = []

        self.add_item(DoubleKickSelect(
            others[:25], self, row=0,
            placeholder="🎯 اختر لاعباً أو لاعبين (القائمة 1-25)..."
        ))
        if len(others) > 25:
            self.add_item(DoubleKickSelect(
                others[25:50], self, row=1,
                placeholder="🎯 اختر لاعباً أو لاعبين (القائمة 26-50)..."
            ))

    @discord.ui.button(label="تأكيد الطرد ⚡", style=discord.ButtonStyle.success, row=2)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)
        if not self.selected_targets:
            return await interaction.response.send_message("❌ الرجاء اختيار لاعب واحد على الأقل من القائمة أولاً!", ephemeral=True)
        self.main_view.choice = ("double_kick", self.selected_targets[:2])
        self.main_view.stop()
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="إلغاء ↩️", style=discord.ButtonStyle.secondary, row=2)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)
        self.stop()
        await interaction.response.send_message("↩️ تم إلغاء الطرد الثنائي، يمكنك الاختيار العادي.", ephemeral=True)


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
            select1_options = [
                discord.SelectOption(
                    label=f"[{p['number']:02d}] {p['username']}"[:100],
                    value=str(p["number"]),
                    description=f"المقعد رقم {p['number']}"
                )
                for p in self.others[:25]
            ]
            s1 = Select(
                placeholder="🎯 اختر اللاعب المراد طرده (1-25)...",
                options=select1_options,
                row=0
            )
            s1.callback = self._select_callback
            self.add_item(s1)

            if len(self.others) > 25:
                select2_options = [
                    discord.SelectOption(
                        label=f"[{p['number']:02d}] {p['username']}"[:100],
                        value=str(p["number"]),
                        description=f"المقعد رقم {p['number']}"
                    )
                    for p in self.others[25:50]
                ]
                s2 = Select(
                    placeholder="🎯 تابع قائمة اللاعبين (26-50)...",
                    options=select2_options,
                    row=1
                )
                s2.callback = self._select_callback
                self.add_item(s2)

        rand_btn = Button(label="🎲 طرد عشوائي", style=discord.ButtonStyle.primary, row=3)
        rand_btn.callback = self._random_kick_callback
        self.add_item(rand_btn)

        with_btn = Button(label="🏳️ انسحاب", style=discord.ButtonStyle.danger, row=3)
        with_btn.callback = self._withdraw_callback
        self.add_item(with_btn)

        if has_item(winner["id"], "double_kick"):
            dk_btn = Button(label="⚡ طرد ثنائي", style=discord.ButtonStyle.success, row=3)
            dk_btn.callback = self._double_kick_callback
            self.add_item(dk_btn)

    def _make_kick_callback(self, number):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.winner["id"]:
                return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)
            self.choice = ("kick", number)
            self.stop()
            await interaction.response.defer()
        return callback

    async def _select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)
        number = int(interaction.data["values"][0])
        self.choice = ("kick", number)
        self.stop()
        await interaction.response.defer()

    async def _random_kick_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)
        self.choice = ("random_kick", None)
        self.stop()
        await interaction.response.defer()

    async def _withdraw_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)
        self.choice = ("withdraw", None)
        self.stop()
        await interaction.response.defer()

    async def _double_kick_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.winner["id"]:
            return await interaction.response.send_message("❌ فقط صاحب الدور يمكنه الاختيار!", ephemeral=True)
        sub_view = DoubleKickSelectView(self.winner, self.others, self)
        await interaction.response.send_message(
            "⚡ **خاصية الطرد الثنائي:** اختر لاعبين اثنين من القائمة أدناه لطردهم في نفس الدور:",
            view=sub_view,
            ephemeral=True
        )


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
            title="🎡 لعبة روليت الحظ | Roulette",
            color=0xF1C40F
        )
        embed.description = f"__**قائمة المشاركين:**__\n{format_players_text(self.players)}"
        embed.add_field(name="📜 طريقة اللعب:", value=HOWTO_TEXT, inline=False)
        embed.add_field(
            name="⏳ وقت التسجيل المتبقي:",
            value=f"**<t:{self.start_timestamp}:R>**\n👥 المشاركين: `{len(self.players)} / {MAX_SEATS}`",
            inline=False
        )
        embed.set_footer(text="انضم الآن عبر الدخول السريع أو اختر مقعدك المفضل!")
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
        """بدء لعبة روليت الحظ في هذا الروم"""
        if not self._can_manage_events(ctx):
            return await ctx.send("❌ | فقط المشرفين (Manage Events / Admin) يمكنهم بدء لعبة الروليت.")

        cid = ctx.channel.id
        if self.is_game_active(cid):
            old = self.active_games.get(cid)
            if old and (time.time() - old.created_at) > 600:
                await self.stop_game(cid)
            else:
                return await ctx.send("❌ يوجد لعبة روليت نشطة بالفعل في هذا الروم!")

        try:
            from bot import has_active_game, get_active_game, register_game
            if has_active_game(cid):
                return await ctx.send(f"❌ يوجد لعبة **{get_active_game(cid)}** تعمل في هذا الروم بالفعل!")
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

    @commands.command(name="متجر", aliases=["shop", "المتجر"])
    async def shop_cmd(self, ctx):
        """فتح متجر خواص الروليت التكتيكية"""
        view = RouletteShopView(ctx.author)
        embed = view.build_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="نقاطي", aliases=["points", "النقاط", "رصيد", "سجلي"])
    async def points_cmd(self, ctx):
        """عرض رصيد نقاطك وسجلك ومخزون الخواص"""
        u = get_user_data(ctx.author.id)
        pts = u.get("points", 0)
        total_pts = u.get("total_points_earned", pts)
        wins = u.get("total_wins", 0)
        kicks = u.get("total_kicks", 0)
        inv = u.get("inventory", {})

        embed = discord.Embed(
            title="📊 بطاقة سجل ورصيد اللاعب",
            color=0x2ECC71
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="💰 الرصيد الحالي", value=f"`{pts}` نقطة", inline=True)
        embed.add_field(name="📜 إجمالي النقاط", value=f"`{total_pts}` نقطة", inline=True)
        embed.add_field(name="🏆 الانتصارات", value=f"`{wins}` فوز", inline=True)
        embed.add_field(name="🎯 الطرد الناجح", value=f"`{kicks}` حالة", inline=True)

        inv_text = (
            f"• 🛡️ درع ضد الطرد: `{inv.get('shield', 0)}`\n"
            f"• 🔄 طرد عكسي: `{inv.get('reverse_kick', 0)}`\n"
            f"• ⚡ طرد ثنائي: `{inv.get('double_kick', 0)}`"
        )
        embed.add_field(name="🎒 مخزون الخواص", value=inv_text, inline=False)
        embed.set_footer(text="استخدم .متجر لشراء المزيد من الخواص!")
        await ctx.send(embed=embed)

    @commands.command(name="توب_الروليت", aliases=["توب_روليت", "roulette_top", "top_roulette"])
    async def leaderboard_cmd(self, ctx):
        """عرض قائمة متصدري لعبة الروليت بالسيرفر"""
        top_list = get_leaderboard(limit=10)
        if not top_list:
            return await ctx.send("📋 لا توجد بيانات مسجلة في ترتيب الروليت بعد!")

        embed = discord.Embed(
            title="🏆 لوحة شرف متصدري روليت الحظ",
            description="ترتيب أفضل اللاعبين بناءً على النقاط والانتصارات الكلية:\n",
            color=0xF1C40F
        )

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for idx, u in enumerate(top_list):
            prefix = medals[idx] if idx < len(medals) else f"`{idx + 1:02d}.`"
            lines.append(
                f"{prefix} <@{u['id']}> — **{u['points']}** نقطة "
                f"(🏆 `{u['wins']}` فوز | 🎯 `{u['kicks']}` طرد)"
            )

        embed.description += "\n".join(lines)
        embed.set_footer(text="العب الروليت واطرد خصومك لترتفع في لوحة الشرف!")
        await ctx.send(embed=embed)

    async def _run_game_lifecycle(self, ctx, game):
        cid = ctx.channel.id
        try:
            game.join_view = RouletteJoinView(game)
            game.current_view = game.join_view
            embed = game.build_join_embed()
            game.main_message = await ctx.send(embed=embed, view=game.join_view)

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
                await ctx.send(f"🚫 تم إلغاء اللعبة لعدم وجود **{MIN_PLAYERS}** لاعبين على الأقل.")
                return

            await ctx.send(f"✅ اكتمل تسجيل اللاعبين ({len(game.players)} لاعبين)! جاري تجهيز العجلة وبدء الجولة الأولى...")

            await download_avatars_concurrently(game.players)

            round_number = 1
            while len(game.players) > 2 and not game.cancelled:
                await self._run_single_round(ctx, game, round_number)
                round_number += 1
                if len(game.players) > 2 and not game.cancelled:
                    await asyncio.sleep(2)

            if not game.cancelled and len(game.players) >= 1:
                await self._crown_champion(ctx, game)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.exception("Error during roulette game lifecycle: %s", e)
            try:
                await ctx.send("⚠️ حدث خطأ غير متوقع أثناء تشغيل الروليت وتم إيقاف اللعبة.")
            except Exception:
                pass
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

        content = (
            f"🎯 **الجولة {round_number}** | المتبقي: `{len(players)}` لاعبين\n"
            f"المختار بالقرعة: **[{winner['number']:02d}]** — <@{winner['id']}>"
        )
        img_file = discord.File(img_buf, filename="roulette.png")
        await ctx.send(content=content, file=img_file)

        if game.cancelled:
            return

        kick_view = KickView(game, winner, players)
        game.current_view = kick_view
        prompt_msg = await ctx.send(
            f"👉 <@{winner['id']}> لديك **30 ثانية** لاختيار لاعب لطرده من اللعبة!",
            view=kick_view
        )

        await kick_view.wait()

        for item in kick_view.children:
            item.disabled = True
        try:
            await prompt_msg.edit(view=kick_view)
        except Exception:
            pass

        if game.cancelled:
            return

        choice = kick_view.choice
        others = [p for p in players if p["id"] != winner["id"]]

        if not choice:
            await ctx.send(f"💣 تم طرد <@{winner['id']}> من اللعبة لعدم التفاعل خلال 30 ثانية!")
            game.players = [p for p in game.players if p["id"] != winner["id"]]
            return

        c_type, c_val = choice

        if c_type == "withdraw":
            await ctx.send(f"🏳️ قرر <@{winner['id']}> الانسحاب من اللعبة!")
            game.players = [p for p in game.players if p["id"] != winner["id"]]
            return

        if c_type in ("kick", "random_kick"):
            is_random = (c_type == "random_kick")
            if is_random:
                victim = random.choice(others) if others else None
            else:
                victim = next((p for p in players if p["number"] == c_val), None)

            if not victim:
                await ctx.send(f"💣 تم استبعاد <@{winner['id']}> من اللعبة لعدم توفر هدف صالح.")
                game.players = [p for p in game.players if p["id"] != winner["id"]]
                return

            kick_str = " (عشوائياً)" if is_random else ""

            if use_item(victim["id"], "reverse_kick"):
                v_pts = record_kick(victim["id"])
                await ctx.send(
                    f"🔄 **طرد عكسي!** حاول <@{winner['id']}> طرد <@{victim['id']}>{kick_str}، "
                    f"لكن <@{victim['id']}> استخدم **الطرد العكسي 🔄**!\n"
                    f"انعكست الضربة وطُرد المهاجم <@{winner['id']}> بدلاً منه! "
                    f"وحصل <@{victim['id']}> على **+1 نقطة** 🎯 (نقاطه: `{v_pts}`)."
                )
                game.players = [p for p in game.players if p["id"] != winner["id"]]
                return

            if use_item(victim["id"], "shield"):
                await ctx.send(
                    f"🛡️ **درع ضد الطرد!** حاول <@{winner['id']}> طرد <@{victim['id']}>{kick_str}، "
                    f"لكن **الدرع 🛡️** حماه وتصدى للهجمة وتم استهلاكه!\n"
                    f"نجا <@{victim['id']}> وتستمر المنافسة دون أي طرد هذه الجولة."
                )
                return

            w_pts = record_kick(winner["id"])
            await ctx.send(
                f"💣 تم طرد <@{victim['id']}> من اللعبة{kick_str}! "
                f"وحصل <@{winner['id']}> على **+1 نقطة** 🎯 (نقاطه: `{w_pts}`)."
            )
            game.players = [p for p in game.players if p["id"] != victim["id"]]
            return

        if c_type == "double_kick":
            if use_item(winner["id"], "double_kick"):
                target_nums = c_val if c_val else []
                targets = [p for p in players if p["number"] in target_nums]
                if not targets:
                    targets = random.sample(others, min(2, len(others))) if others else []

                report = []
                pts_earned = 0
                for v in targets:
                    if use_item(v["id"], "reverse_kick"):
                        v_pts = record_kick(v["id"])
                        report.append(f"🔄 رد <@{v['id']}> الضربة بطرد عكسي!")
                        game.players = [p for p in game.players if p["id"] != winner["id"]]
                        await ctx.send(
                            f"⚡ **طرد ثنائي:** حاول <@{winner['id']}> استهداف <@{v['id']}>، "
                            f"لكن <@{v['id']}> استخدم **الطرد العكسي 🔄** فطرد المهاجم فوراً! وحصل على **+1 نقطة** (نقاطه: `{v_pts}`)."
                        )
                        return
                    elif use_item(v["id"], "shield"):
                        report.append(f"🛡️ نجا <@{v['id']}> بالدرع!")
                    else:
                        game.players = [p for p in game.players if p["id"] != v["id"]]
                        report.append(f"💣 طرد <@{v['id']}>")
                        record_kick(winner["id"])
                        pts_earned += 1

                total_pts = get_points(winner["id"])
                res_str = " | ".join(report) if report else "لم يصب أحداً"
                await ctx.send(
                    f"⚡ **نتائج الطرد الثنائي لـ <@{winner['id']}>:**\n"
                    f"{res_str}\n"
                    f"حصل على **+{pts_earned}** نقاط 🎯 (إجمالي نقاطه: `{total_pts}`)."
                )

    async def _crown_champion(self, ctx, game):
        if len(game.players) == 2:
            players = list(game.players)
            random.shuffle(players)
            champion = players[-1]
            highlight_idx = len(players) - 1

            img_buf = await make_image(
                [{"number": p["number"], "img": p.get("avimg")} for p in players],
                highlight=highlight_idx
            )
            content = (
                "👑 **الجولة الحاسمة والنهائية!**\n"
                f"اللاعب المختار هو بطل الروليت: **[{champion['number']:02d}]** — <@{champion['id']}>"
            )
            await ctx.send(content=content, file=discord.File(img_buf, filename="roulette.png"))
        elif len(game.players) == 1:
            champion = game.players[0]
        else:
            await ctx.send("🏁 انتهت اللعبة دون بقاء أي فائز.")
            return

        c_pts = record_win(champion["id"])
        embed = discord.Embed(
            title="🎉 مبروك! فوز بطل الروليت 👑",
            description=f"استطاع **<@{champion['id']}>** الصمود والفوز باللعبة!\n\n"
                        f"🏅 **الجائزة:** `+3` نقاط تضاف إلى رصيده!\n"
                        f"💰 **إجمالي رصيده الحالي:** `{c_pts}` نقطة",
            color=0xF1C40F
        )
        embed.set_thumbnail(url=champion.get("avatar_url", ""))
        embed.set_footer(text="شكراً لجميع المشاركين على الروح الرياضية! 🎲")
        await ctx.send(embed=embed)

    def _can_manage_events(self, ctx):
        if not ctx.guild:
            return True
        p = ctx.author.guild_permissions
        return (
            p.administrator
            or p.manage_guild
            or p.manage_events
            or p.manage_messages
            or ctx.author.id == ctx.guild.owner_id
        )