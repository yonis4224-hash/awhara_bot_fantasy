import io
import random
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Select

from basra_logic import BasraGame, BasraCard, SUIT_NAMES_AR, RANK_NAMES_AR
from basra_gfx import render_basra_table, draw_single_card
from tarneeb_gfx import render_player_hand

active_basra_games = {}

class BasraCardSelectMenu(Select):
    def __init__(self, player, game, cog):
        self.player = player
        self.game = game
        self.cog = cog

        options = []
        for idx, card in enumerate(player.hand):
            s_name = SUIT_NAMES_AR.get(card.suit, card.suit)
            r_name = RANK_NAMES_AR.get(card.rank, str(card.rank))
            options.append(discord.SelectOption(
                label=f"{r_name} - {s_name}",
                value=card.code,
                description=f"لعب بطاقة {r_name} {s_name}",
                emoji="🃏"
            ))

        super().__init__(placeholder="اختر بطاقة للعبها على الأرض...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.player.user_id:
            return await interaction.response.send_message("❌ هذه ليست أوراقك!", ephemeral=True)

        curr_p = self.game.get_current_player()
        if curr_p.user_id != self.player.user_id:
            return await interaction.response.send_message("❌ ليس دورك الآن للعب!", ephemeral=True)

        card_code = self.values[0]
        suit, rank = card_code.split('-')
        chosen_card = BasraCard(suit, int(rank))

        # إلغاء مؤقت المهلة فور قيام اللاعب بحركته
        self.cog.cancel_turn_timer(self.game)

        success, msg = self.game.play_card(self.player.seat_idx, chosen_card)
        if not success:
            return await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

        await interaction.response.send_message(f"✅ لعبت بطاقة: `{chosen_card}`", ephemeral=True)
        await self.cog.update_table(interaction.channel, self.game)


class BasraShowHandView(View):
    def __init__(self, player, game, cog):
        super().__init__(timeout=120)
        self.add_item(BasraCardSelectMenu(player, game, cog))


class BasraGameMainView(View):
    def __init__(self, game, cog):
        super().__init__(timeout=None)
        self.game = game
        self.cog = cog

    @discord.ui.button(label="🎴 عرض أوراقي", style=discord.ButtonStyle.primary, custom_id="basra_show_hand")
    async def show_hand_btn(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        player = next((p for p in self.game.players if p.user_id == user_id), None)
        if not player:
            return await interaction.response.send_message("❌ أنت لست لاعباً في هذه الطاولة!", ephemeral=True)

        hand_img_buf = render_player_hand(player.hand)
        file = discord.File(fp=hand_img_buf, filename="basra_hand.png")

        curr_p = self.game.get_current_player()
        if curr_p.user_id == user_id:
            view = BasraShowHandView(player, self.game, self.cog)
            await interaction.response.send_message("👇 **أوراقك الحالية. اختر بطاقة للعبها:**", file=file, view=view, ephemeral=True)
        else:
            await interaction.response.send_message("👇 **أوراقك الحالية في الشكوبا:**", file=file, ephemeral=True)

    @discord.ui.button(label="🔄 تحديث الطاولة", style=discord.ButtonStyle.secondary, custom_id="basra_refresh_table")
    async def refresh_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.cog.update_table(interaction.channel, self.game)

    @discord.ui.button(label="📊 النقاط", style=discord.ButtonStyle.primary, custom_id="basra_scores")
    async def scores_btn(self, interaction: discord.Interaction, button: Button):
        msg = f"📊 **النقاط الحالية:**\n"
        for p in self.game.players:
            msg += f"• **{p.name}**: {p.score} نقطة | كروت مجمعة: {len(p.captured)} | شكوبات: {p.basra_count}\n"
        msg += f"🎯 الهدف: {self.game.target_score} نقطة"
        if self.game.tie_bonus > 0:
            msg += f"\n⚡ مكافأة التعادل المعلقة: {self.game.tie_bonus} نقطة"
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="🚪 مغادرة", style=discord.ButtonStyle.danger, custom_id="basra_leave")
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        success, msg = self.game.replace_with_ai(interaction.user.id)
        if not success:
            return await interaction.response.send_message(msg, ephemeral=True)

        button.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog.update_table(interaction.channel, self.game)
        await interaction.followup.send(f"✅ {msg}", ephemeral=True)


class BasraLobbyView(View):
    def __init__(self, host_user, game, cog):
        super().__init__(timeout=180)
        self.host_user = host_user
        self.game = game
        self.cog = cog

    @discord.ui.button(label="انضمام 🎮", style=discord.ButtonStyle.success)
    async def join_btn(self, interaction: discord.Interaction, button: Button):
        success, msg = self.game.add_player(interaction.user.id, interaction.user.display_name)
        if not success:
            return await interaction.response.send_message(msg, ephemeral=True)

        embed = self.cog.build_lobby_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="إضافة بوت AI 🤖", style=discord.ButtonStyle.secondary)
    async def ai_btn(self, interaction: discord.Interaction, button: Button):
        if len(self.game.players) >= 4:
            return await interaction.response.send_message("❌ الطاولة مكتملة (4 لاعبين)!", ephemeral=True)

        self.game.fill_with_ai()
        embed = self.cog.build_lobby_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="بدء اللعبة 🚀", style=discord.ButtonStyle.primary)
    async def start_btn(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != str(self.host_user.id):
            return await interaction.response.send_message("❌ فقط منشئ الطاولة يمكنه بدء اللعبة!", ephemeral=True)

        self.game.start_game()
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(content="🃏 **تم بدء اللعبة! جاري إعداد طاولة الشكوبا...**", view=self)

        await self.cog.update_table(interaction.channel, self.game)

    @discord.ui.button(label="إلغاء ❌", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != str(self.host_user.id):
            return await interaction.response.send_message("❌ فقط منشئ الطاولة يمكنه إلغاؤها!", ephemeral=True)

        self.cog.cancel_turn_timer(self.game)
        if interaction.channel.id in active_basra_games:
            del active_basra_games[interaction.channel.id]
        from bot import unregister_game
        unregister_game(interaction.channel.id)
        await interaction.response.edit_message(content="❌ **تم إلغاء طاولة البصرة.**", embed=None, view=None)


class BasraCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cancel_turn_timer(self, game):
        """إلغاء أي مؤقت دور قيد التشغيل للعبة"""
        if hasattr(game, "turn_timer_task") and game.turn_timer_task:
            if not game.turn_timer_task.done():
                game.turn_timer_task.cancel()
            game.turn_timer_task = None

    async def start_turn_timer(self, channel, game):
        """بدء مهلة 20 ثانية لدور اللاعب الحالي إذا كان لاعباً حقيقياً"""
        self.cancel_turn_timer(game)
        if game.state == 'PLAYING':
            curr_p = game.get_current_player()
            if not curr_p.is_ai:
                game.turn_timer_task = asyncio.create_task(self._turn_timeout_task(channel, game, game.turn_index))

    async def _turn_timeout_task(self, channel, game, seat):
        """ينتظر 20 ثانية ثم يلعب بطاقة تلقائياً إذا لم يلعب اللاعب"""
        try:
            await asyncio.sleep(20)
            if channel.id not in active_basra_games or active_basra_games.get(channel.id) is not game:
                return
            if game.state != 'PLAYING' or game.turn_index != seat:
                return
            player = game.players[seat]
            if player.is_ai or not player.hand:
                return
            auto_card = random.choice(player.hand)
            game.play_card(seat, auto_card)
            await channel.send(f"⌛ **انتهت مهلة الـ 20 ثانية لـ <@{player.user_id}>!** تم لعب بطاقة تلقائياً: `{auto_card}`")
            await self.update_table(channel, game)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in Basra turn timer: {e}")

    def build_lobby_embed(self, game):
        embed = discord.Embed(
            title="🃏 طاولة بصرة / شكوبا جديدة",
            description="انضم للعب بصرة تفاعلية (4 لاعبين)!\n⏱️ **مهلة كل دور:** 20 ثانية (لعب تلقائي عند التأخر)",
            color=discord.Color.green()
        )
        p_list = ""
        for i in range(4):
            if i < len(game.players):
                p = game.players[i]
                p_list += f"**المقعد {i+1}**: {p.name}\n"
            else:
                p_list += f"**المقعد {i+1}**: *(فارغ)*\n"
        embed.add_field(name="اللاعبون الحاليون:", value=p_list, inline=False)
        embed.set_footer(text="الشكوبا / البصرة 4 لاعبين (يمكن إكمال المقاعد بـ AI)")
        return embed

    async def update_table(self, channel, game):
        # إذا لم تعد اللعبة مسجلة (انتهت/أُلغيت) تجاهل التحديث لمنع إحياء طاولة قديمة
        if channel.id not in active_basra_games or active_basra_games.get(channel.id) is not game:
            self.cancel_turn_timer(game)
            return

        # 1. إلغاء المؤقت أثناء معالجة أدوار الـ AI
        self.cancel_turn_timer(game)
        await self.check_and_process_ai(channel, game)

        # 2. Render PIL table graphic
        players_info = []
        for p in game.players:
            players_info.append({'name': p.name, 'score': p.score, 'captured_count': len(p.captured)})

        table_buf = render_basra_table(
            ground_cards=game.ground,
            players_info=players_info,
            current_turn_idx=game.turn_index,
            log_msg=game.log_msg
        )
        file = discord.File(fp=table_buf, filename="basra_table.png")

        # 3. Handle Game Over or Playing state
        if game.state == 'GAME_OVER':
            self.cancel_turn_timer(game)
            view = None
            content = game.log_msg
            if channel.id in active_basra_games:
                del active_basra_games[channel.id]
            from bot import unregister_game
            unregister_game(channel.id)
            return await channel.send(content=content, file=file)

        curr_p = game.get_current_player()
        mention = f"<@{curr_p.user_id}>" if not curr_p.is_ai else f"🤖 **{curr_p.name}**"
        content = f"🃏 **لعبة البصرة** | الدور الآن على: {mention} ⏱️ (لديك 20 ثانية)\n📢 {game.log_msg}"
        view = BasraGameMainView(game, self)

        await channel.send(content=content, file=file, view=view)

        # 4. بدء مهلة الـ 20 ثانية للاعب البشري بعد إرسال واجهة الدور
        if game.state == 'PLAYING' and not curr_p.is_ai:
            await self.start_turn_timer(channel, game)

    async def check_and_process_ai(self, channel, game):
        """Processes AI turns sequentially if current turn is AI."""
        while game.state == 'PLAYING':
            curr_p = game.get_current_player()
            if not curr_p.is_ai:
                break
            await asyncio.sleep(2.0)
            game.ai_play_turn()

    @commands.command(name="بصرة", aliases=["basra", "البصرة", "بصره", "شكوبا", "scopa"])
    async def cmd_basra(self, ctx):
        """بدء لعبة بصرة / شكوبا جديدة"""
        if ctx.channel.id in active_basra_games:
            return await ctx.send("❌ يوجد بالفعل طاولة بصرة نشطة في هذا الروم!")
        # التحقق من عدم وجود لعبة أخرى من نوع مختلف
        from bot import has_active_game, get_active_game, register_game
        if has_active_game(ctx.channel.id):
            return await ctx.send(f"❌ يوجد لعبة **{get_active_game(ctx.channel.id)}** تعمل في هذا الروم بالفعل!\nيمكنك إنهاؤها أولاً بأمر: `.انهاء`")

        game = BasraGame(ctx.channel.id, target_score=121)
        active_basra_games[ctx.channel.id] = game
        register_game(ctx.channel.id, "basra")

        # Add host as Player 1
        game.add_player(ctx.author.id, ctx.author.display_name)

        embed = self.build_lobby_embed(game)
        view = BasraLobbyView(ctx.author, game, self)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="_انهاء_البصرة", aliases=["انهاء_البصرة", "stop_basra", "_انهاء_الشكوبا"])
    async def cmd_end_basra(self, ctx):
        """إنهاء لعبة البصرة الحالية بواسطة الأدمن"""
        from bot import is_admin_or_mod
        if not is_admin_or_mod(ctx):
            return await ctx.send("❌ فقط المسؤولين يمكنهم إلغاء أو إنهاء اللعبة!")

        if ctx.channel.id in active_basra_games:
            game = active_basra_games.get(ctx.channel.id)
            if game:
                self.cancel_turn_timer(game)
            del active_basra_games[ctx.channel.id]
            from bot import unregister_game
            unregister_game(ctx.channel.id)
            await ctx.send("⏹️ **تم إنهاء لعبة البصرة في هذا الروم بنجاح بواسطة الأدمن.**")
        else:
            await ctx.send("❌ لا توجد لعبة بصرة نشطة حالياً في هذا الروم!")


async def setup(bot):
    await bot.add_cog(BasraCog(bot))
