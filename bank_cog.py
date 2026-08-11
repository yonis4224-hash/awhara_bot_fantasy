"""
Bank Al-Haz Discord Cog & Interactive Views (bank_cog.py)
Handles Discord commands, lobby buttons, turn actions, and game board rendering updates.
"""
import io
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button

from bank_logic import BankGame, JAIL_BAIL
from bank_gfx import render_board

active_bank_games = {}

class BankLobbyView(View):
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
            return await interaction.response.send_message("❌ الطاولة مكتملة بالفعل!", ephemeral=True)

        self.game.fill_with_ai()
        embed = self.cog.build_lobby_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="بدء اللعبة 🚀", style=discord.ButtonStyle.primary)
    async def start_btn(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != str(self.host_user.id):
            return await interaction.response.send_message("❌ فقط منشئ اللعبة يمكنه البدء!", ephemeral=True)

        self.game.start_game()
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(content="🎲 **تم بدء بنك الحظ! جاري رسم وتجهيز رقعة اللعبة...**", view=self)

        await self.cog.update_board(interaction.channel, self.game)

    @discord.ui.button(label="إلغاء ❌", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != str(self.host_user.id):
            return await interaction.response.send_message("❌ فقط منشئ اللعبة يمكنه الإلغاء!", ephemeral=True)

        if interaction.channel.id in active_bank_games:
            del active_bank_games[interaction.channel.id]
        from bot import unregister_game
        unregister_game(interaction.channel.id)
        await interaction.response.edit_message(content="❌ **تم إلغاء بنك الحظ.**", embed=None, view=None)


class BankTurnView(View):
    def __init__(self, game, cog):
        super().__init__(timeout=None)
        self.game = game
        self.cog = cog

        curr_p = game.get_current_player()
        tile = game.tiles[curr_p.position]

        # Enable/Disable buttons based on state
        self.roll_btn.disabled = not game.can_roll
        self.buy_btn.disabled = not game.can_buy
        self.build_btn.disabled = not game.can_build
        self.bail_btn.disabled = not (curr_p.in_jail and curr_p.balance >= JAIL_BAIL)

    @discord.ui.button(label="🎲 رمي النرد", style=discord.ButtonStyle.primary, custom_id="bank_roll")
    async def roll_btn(self, interaction: discord.Interaction, button: Button):
        curr_p = self.game.get_current_player()
        if str(interaction.user.id) != curr_p.user_id:
            return await interaction.response.send_message("❌ ليس دورك الآن!", ephemeral=True)

        success, msg = self.game.roll_dice()
        await interaction.response.defer()
        await self.cog.update_board(interaction.channel, self.game)

    @discord.ui.button(label="🏠 شراء العقار", style=discord.ButtonStyle.success, custom_id="bank_buy")
    async def buy_btn(self, interaction: discord.Interaction, button: Button):
        curr_p = self.game.get_current_player()
        if str(interaction.user.id) != curr_p.user_id:
            return await interaction.response.send_message("❌ ليس دورك الآن!", ephemeral=True)

        success, msg = self.game.buy_current_property()
        if not success:
            return await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

        await interaction.response.defer()
        await self.cog.update_board(interaction.channel, self.game)

    @discord.ui.button(label="🏗️ تطوير/بناء", style=discord.ButtonStyle.secondary, custom_id="bank_build")
    async def build_btn(self, interaction: discord.Interaction, button: Button):
        curr_p = self.game.get_current_player()
        if str(interaction.user.id) != curr_p.user_id:
            return await interaction.response.send_message("❌ ليس دورك الآن!", ephemeral=True)

        success, msg = self.game.upgrade_current_property()
        if not success:
            return await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

        await interaction.response.defer()
        await self.cog.update_board(interaction.channel, self.game)

    @discord.ui.button(label="💵 دفع كفالة", style=discord.ButtonStyle.secondary, custom_id="bank_bail")
    async def bail_btn(self, interaction: discord.Interaction, button: Button):
        curr_p = self.game.get_current_player()
        if str(interaction.user.id) != curr_p.user_id:
            return await interaction.response.send_message("❌ ليس دورك الآن!", ephemeral=True)

        success, msg = self.game.pay_jail_bail()
        if not success:
            return await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

        await interaction.response.defer()
        await self.cog.update_board(interaction.channel, self.game)

    @discord.ui.button(label="➡️ إنهاء الدور", style=discord.ButtonStyle.danger, custom_id="bank_end_turn")
    async def end_turn_btn(self, interaction: discord.Interaction, button: Button):
        curr_p = self.game.get_current_player()
        if str(interaction.user.id) != curr_p.user_id:
            return await interaction.response.send_message("❌ ليس دورك الآن!", ephemeral=True)

        if self.game.can_roll:
            return await interaction.response.send_message("❌ يجب عليك رمي النرد أولاً قبل إنهاء دورك!", ephemeral=True)

        self.game.end_turn()
        await interaction.response.defer()
        await self.cog.update_board(interaction.channel, self.game)


class BankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_lobby_embed(self, game):
        embed = discord.Embed(
            title="🏰 طاولة بنك الحظ جديدة",
            description="انضم لجمع الثروات وشراء المدن وتطوير العقارات!",
            color=discord.Color.dark_gold()
        )
        p_list = ""
        for i in range(4):
            if i < len(game.players):
                p = game.players[i]
                p_list += f"**المقعد {i+1}**: {p.name}\n"
            else:
                p_list += f"**المقعد {i+1}**: *(فارغ)*\n"
        embed.add_field(name="اللاعبون الحاليون:", value=p_list, inline=False)
        embed.set_footer(text="تبدأ اللعبة من 2 إلى 4 لاعبين (يمكن إكمال الباقي بـ AI)")
        return embed

    async def update_board(self, channel, game):
        # 1. Process AI turns if active player is AI
        await self.check_and_process_ai(channel, game)

        # 2. Render PIL board graphic
        players_data = [{
            'name': p.name,
            'balance': p.balance,
            'position': p.position,
            'in_jail': p.in_jail,
            'bankrupt': p.bankrupt
        } for p in game.players]

        board_buf = render_board(
            tiles=game.tiles,
            players=players_data,
            current_turn_idx=game.turn_index,
            last_dice=game.last_dice,
            log_msg=game.log_msg
        )
        file = discord.File(fp=board_buf, filename="bank_board.png")

        # 3. View & State handling
        if game.state == 'GAME_OVER':
            view = None
            content = f"👑 **انتهت اللعبة!**\n{game.log_msg}"
            if channel.id in active_bank_games:
                del active_bank_games[channel.id]
            from bot import unregister_game
            unregister_game(channel.id)
            return await channel.send(content=content, file=file)

        curr_p = game.get_current_player()
        mention = f"<@{curr_p.user_id}>" if not curr_p.is_ai else f"🤖 **{curr_p.name}**"
        content = f"🏰 **بنك الحظ** | الدور الآن على: {mention}\n📢 {game.log_msg}"
        view = BankTurnView(game, self) if not curr_p.is_ai else None

        await channel.send(content=content, file=file, view=view)

    async def check_and_process_ai(self, channel, game):
        """Processes AI turns sequentially if current turn is AI."""
        while game.state == 'PLAYING':
            curr_p = game.get_current_player()
            if not curr_p.is_ai or curr_p.bankrupt:
                break
            await asyncio.sleep(2.0)
            game.ai_play_turn()

    @commands.command(name="بنك_الحظ", aliases=["بنك", "bank", "المونوبولي"])
    async def cmd_bank(self, ctx):
        """بدء لعبة بنك الحظ جديدة"""
        if ctx.channel.id in active_bank_games:
            return await ctx.send("❌ يوجد بالفعل لعبة بنك الحظ نشطة في هذا الروم!")
        # التحقق من عدم وجود لعبة أخرى من نوع مختلف
        from bot import has_active_game, get_active_game, register_game
        if has_active_game(ctx.channel.id):
            return await ctx.send(f"❌ يوجد لعبة **{get_active_game(ctx.channel.id)}** تعمل في هذا الروم بالفعل!")

        game = BankGame(ctx.channel.id)
        active_bank_games[ctx.channel.id] = game
        register_game(ctx.channel.id, "bank")

        # Add host as Player 1
        game.add_player(ctx.author.id, ctx.author.display_name)

        embed = self.build_lobby_embed(game)
        view = BankLobbyView(ctx.author, game, self)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(BankCog(bot))
