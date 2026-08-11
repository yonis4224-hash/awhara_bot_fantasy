"""
Tarneeb Discord Cog & Interactive UI (tarneeb_cog.py)
Handles Discord UI interactions, lobby views, ephemeral hand views, select menus, and commands.
"""
import io
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Select

from tarneeb_logic import TarneebGame, Card, SUIT_NAMES_AR, RANK_NAMES_AR
from tarneeb_gfx import render_player_hand, render_table

import os

active_games = {}
TARNEEB_CHANNEL_ID = int(os.getenv("TARNEEB_CHANNEL_ID", "1528566822935330989"))

class CardSelectMenu(Select):
    def __init__(self, player, legal_cards, game, cog):
        self.player = player
        self.legal_cards = legal_cards
        self.game = game
        self.cog = cog

        options = []
        for idx, card in enumerate(legal_cards):
            s_name = SUIT_NAMES_AR.get(card.suit, card.suit)
            r_name = RANK_NAMES_AR.get(card.rank, str(card.rank))
            options.append(discord.SelectOption(
                label=f"{r_name} - {s_name}",
                value=card.code,
                description=f"رمي بطاقة {r_name} {s_name}",
                emoji="🎴"
            ))

        super().__init__(placeholder="اختر البطاقة التي تريد لعبها...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.player.user_id:
            return await interaction.response.send_message("❌ هذه ليست أوراقك!", ephemeral=True)

        if self.game.turn_index != self.player.seat:
            return await interaction.response.send_message("❌ ليس دورك الآن للعب!", ephemeral=True)

        card_code = self.values[0]
        suit, rank = card_code.split('-')
        chosen_card = Card(suit, int(rank))

        success, msg = self.game.play_card(self.player.seat, chosen_card)
        if not success:
            return await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

        await interaction.response.send_message(f"✅ لعبت بطاقة: `{chosen_card}`", ephemeral=True)
        await self.cog.update_game_table(interaction.channel, self.game)


class ShowHandView(View):
    def __init__(self, player, legal_cards, game, cog):
        super().__init__(timeout=120)
        self.add_item(CardSelectMenu(player, legal_cards, game, cog))


class TarneebGameMainView(View):
    def __init__(self, game, cog):
        super().__init__(timeout=None)
        self.game = game
        self.cog = cog

    @discord.ui.button(label="🎴 عرض أوراقي", style=discord.ButtonStyle.primary, custom_id="tarneeb_show_hand")
    async def show_hand_btn(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        player = next((p for p in self.game.players if p.user_id == user_id), None)
        if not player:
            return await interaction.response.send_message("❌ أنت لست لاعباً في هذه الطاولة!", ephemeral=True)

        hand_img_buf = render_player_hand(player.hand)
        file = discord.File(fp=hand_img_buf, filename="hand.png")

        legal_cards = self.game.get_legal_cards(player.seat) if (self.game.state == 'PLAYING' and self.game.turn_index == player.seat) else player.hand

        if self.game.state == 'PLAYING' and self.game.turn_index == player.seat:
            view = ShowHandView(player, legal_cards, self.game, self.cog)
            await interaction.response.send_message("👇 **أوراقك الحالية. يمكنك اختيار بطاقة للعبها عند مجيء دورك:**", file=file, view=view, ephemeral=True)
        else:
            await interaction.response.send_message("👇 **أوراقك الحالية في الطرنيب:**", file=file, ephemeral=True)

    @discord.ui.button(label="🔄 تحديث الطاولة", style=discord.ButtonStyle.secondary, custom_id="tarneeb_refresh_table")
    async def refresh_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.cog.update_game_table(interaction.channel, self.game)

    @discord.ui.button(label="🚪 مغادرة", style=discord.ButtonStyle.danger, custom_id="tarneeb_leave")
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        success, msg = self.game.remove_player(interaction.user.id)
        if not success:
            return await interaction.response.send_message(msg, ephemeral=True)

        button.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog.update_game_table(interaction.channel, self.game)
        await interaction.followup.send(f"✅ {msg}", ephemeral=True)


class TarneebBiddingView(View):
    def __init__(self, game, cog):
        super().__init__(timeout=120)
        self.game = game
        self.cog = cog

        current = game.current_bid
        for bid_val in range(max(7, current + 1), 14):
            btn = Button(label=str(bid_val), style=discord.ButtonStyle.danger if bid_val >= 12 else discord.ButtonStyle.primary, custom_id=f"bid_{bid_val}")
            btn.callback = self.make_bid_callback(bid_val)
            self.add_item(btn)

        pass_btn = Button(label="تمرير (بس) 🚫", style=discord.ButtonStyle.secondary, custom_id="bid_pass")
        pass_btn.callback = self.make_bid_callback(0)
        self.add_item(pass_btn)

    def make_bid_callback(self, bid_val):
        async def callback(interaction: discord.Interaction):
            curr_player = self.game.players[self.game.turn_index]
            if str(interaction.user.id) != curr_player.user_id:
                return await interaction.response.send_message("❌ ليس دورك في المزايدة!", ephemeral=True)

            success, msg = self.game.process_bid(curr_player.seat, bid_val)
            if not success:
                return await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

            await interaction.response.send_message(f"✅ {msg}")
            await self.cog.update_game_table(interaction.channel, self.game)
        return callback

    @discord.ui.button(label="🚪 مغادرة", style=discord.ButtonStyle.danger, custom_id="tarneeb_leave")
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        success, msg = self.game.remove_player(interaction.user.id)
        if not success:
            return await interaction.response.send_message(msg, ephemeral=True)

        button.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog.update_game_table(interaction.channel, self.game)
        await interaction.followup.send(f"✅ {msg}", ephemeral=True)


class TarneebTrumpSelectView(View):
    def __init__(self, game, cog):
        super().__init__(timeout=120)
        self.game = game
        self.cog = cog

    @discord.ui.button(label="كوبا ♥", style=discord.ButtonStyle.danger)
    async def hearts_btn(self, interaction: discord.Interaction, button: Button):
        await self.select_trump(interaction, 'H')

    @discord.ui.button(label="سبيد ♠", style=discord.ButtonStyle.primary)
    async def spades_btn(self, interaction: discord.Interaction, button: Button):
        await self.select_trump(interaction, 'S')

    @discord.ui.button(label="ديناري ♦", style=discord.ButtonStyle.danger)
    async def diamonds_btn(self, interaction: discord.Interaction, button: Button):
        await self.select_trump(interaction, 'D')

    @discord.ui.button(label="شيريا ♣", style=discord.ButtonStyle.primary)
    async def clubs_btn(self, interaction: discord.Interaction, button: Button):
        await self.select_trump(interaction, 'C')

    async def select_trump(self, interaction: discord.Interaction, suit):
        curr_player = self.game.players[self.game.highest_bidder]
        if str(interaction.user.id) != curr_player.user_id:
            return await interaction.response.send_message("❌ فقط الفائز بالطلب يمكنه اختيار الطرنيب!", ephemeral=True)

        success, msg = self.game.set_tarneeb_suit(suit)
        if not success:
            return await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

        await interaction.response.send_message(f"✅ {msg}")
        await self.cog.update_game_table(interaction.channel, self.game)

    @discord.ui.button(label="🚪 مغادرة", style=discord.ButtonStyle.danger, custom_id="tarneeb_leave")
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        success, msg = self.game.remove_player(interaction.user.id)
        if not success:
            return await interaction.response.send_message(msg, ephemeral=True)

        button.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog.update_game_table(interaction.channel, self.game)
        await interaction.followup.send(f"✅ {msg}", ephemeral=True)


class TarneebLobbyView(View):
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
            return await interaction.response.send_message("❌ فقط منشئ الطاولة يمكنه بدء اللعبة!", ephemeral=True)

        self.game.start_game()
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(content="🎮 **تم بدء اللعبة! جاري إعداد طاولة الطرنيب...**", view=self)

        await self.cog.update_game_table(interaction.channel, self.game)

    @discord.ui.button(label="مغادرة 🚪", style=discord.ButtonStyle.secondary)
    async def leave_btn(self, interaction: discord.Interaction, button: Button):
        success, msg = self.game.remove_player(interaction.user.id)
        if not success:
            return await interaction.response.send_message(msg, ephemeral=True)

        embed = self.cog.build_lobby_embed(self.game)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="إلغاء ❌", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != str(self.host_user.id):
            return await interaction.response.send_message("❌ فقط منشئ الطاولة يمكنه إلغاؤها!", ephemeral=True)

        if interaction.channel.id in active_games:
            del active_games[interaction.channel.id]
        from bot import unregister_game
        unregister_game(interaction.channel.id)
        await interaction.response.edit_message(content="❌ **تم إلغاء طاولة الطرنيب.**", embed=None, view=None)


class TarneebCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_lobby_embed(self, game):
        embed = discord.Embed(
            title="🃏 طاولة طرنيب جديدة",
            description="انضم للطاولة للعب طرنيب 4 لاعبين (فريقين)!",
            color=discord.Color.gold()
        )
        p_list = ""
        for i in range(4):
            if i < len(game.players):
                p = game.players[i]
                p_list += f"**المقعد {i+1}**: {p.name} (فريق {p.team})\n"
            else:
                p_list += f"**المقعد {i+1}**: *(شاجر/فارغ)*\n"
        embed.add_field(name="اللاعبون الان:", value=p_list, inline=False)
        embed.set_footer(text="الفريق 1: مقعد 1 + 3 | الفريق 2: مقعد 2 + 4")
        return embed

    async def update_game_table(self, channel, game):
        # إذا لم تعد اللعبة مسجلة (انتهت/أُلغيت) تجاهل التحديث لمنع إحياء طاولة قديمة
        if channel.id not in active_games or active_games.get(channel.id) is not game:
            return

        # 1. Process AI turns if active player is AI
        await self.check_and_process_ai(channel, game)

        # 2. Render PIL table graphic
        players_info = [{'name': p.name, 'team': p.team} for p in game.players]
        bidder_info = None
        if game.highest_bidder is not None:
            bidder_info = {
                'name': game.players[game.highest_bidder].name,
                'bid': game.current_bid
            }

        table_buf = render_table(
            current_trick=game.current_trick,
            tarneeb_suit=game.tarneeb_suit,
            bidder_info=bidder_info,
            score_t1=game.score_t1,
            score_t2=game.score_t2,
            round_tricks_t1=game.round_tricks_t1,
            round_tricks_t2=game.round_tricks_t2,
            players_info=players_info,
            turn_index=game.turn_index
        )
        file = discord.File(fp=table_buf, filename="tarneeb_table.png")

        # 3. Determine view based on game state
        curr_p = game.players[game.turn_index]
        turn_mention = f"<@{curr_p.user_id}>" if not curr_p.is_ai else f"🤖 **{curr_p.name}**"

        if game.state == 'BIDDING':
            desc = f"📢 **مرحلة المزايدة (الطلب)**\nالدور الآن على: {turn_mention}\nأعلى طلب حالي: **{game.current_bid or 'لا يوجد'}**"
            view = TarneebBiddingView(game, self) if not curr_p.is_ai else TarneebGameMainView(game, self)
        elif game.state == 'SELECT_TRUMP':
            bidder_name = game.players[game.highest_bidder].name
            desc = f"🔥 **اختيار الطرنيب (الحكم)**\nالفائز بالطلب: **{bidder_name}** ({game.current_bid})\nاختر نوع الطرنيب للجولة!"
            view = TarneebTrumpSelectView(game, self) if not game.players[game.highest_bidder].is_ai else TarneebGameMainView(game, self)
        elif game.state == 'PLAYING':
            desc = f"🎴 **مرحلة اللعب**\nالدور الآن على: {turn_mention}\nاضغط على **'عرض أوراقي'** لرؤية أوراقك واختيار بطاقة!"
            view = TarneebGameMainView(game, self)
        elif game.state == 'ROUND_END':
            desc = f"🏁 **انتهت الجولة!**\n{game.last_round_msg}\n\nجاري بدء الجولة التالية خلال ثوانٍ..."
            view = TarneebGameMainView(game, self)
            await channel.send(content=desc, file=file, view=view)
            await asyncio.sleep(4)
            game.start_new_round()
            return await self.update_game_table(channel, game)
        elif game.state == 'GAME_OVER':
            desc = f"👑 **انتهت اللعبة بالكامل!**\n{game.last_round_msg}"
            view = None
            if channel.id in active_games:
                del active_games[channel.id]
            from bot import unregister_game
            unregister_game(channel.id)
            return await channel.send(content=desc, file=file)
        else:
            desc = "طاولة الطرنيب"
            view = TarneebGameMainView(game, self)

        await channel.send(content=desc, file=file, view=view)

    async def check_and_process_ai(self, channel, game):
        """Processes AI turns sequentially if current turn is AI."""
        while True:
            if game.state not in ['BIDDING', 'SELECT_TRUMP', 'PLAYING']:
                break

            if game.state == 'BIDDING':
                curr_p = game.players[game.turn_index]
                if not curr_p.is_ai:
                    break
                await asyncio.sleep(1.5)
                ai_bid = game.ai_make_bid(curr_p.seat)
                game.process_bid(curr_p.seat, ai_bid)

            elif game.state == 'SELECT_TRUMP':
                bidder_p = game.players[game.highest_bidder]
                if not bidder_p.is_ai:
                    break
                await asyncio.sleep(1.5)
                ai_suit = game.ai_choose_trump(bidder_p.seat)
                game.set_tarneeb_suit(ai_suit)

            elif game.state == 'PLAYING':
                curr_p = game.players[game.turn_index]
                if not curr_p.is_ai:
                    break
                await asyncio.sleep(1.5)
                ai_card = game.ai_play_card(curr_p.seat)
                game.play_card(curr_p.seat, ai_card)

    @commands.command(name="طرنيب", aliases=["tarneeb", "الطرنيب"])
    async def cmd_tarneeb(self, ctx):
        """بدء لعبة طرنيب جديدة"""
        if TARNEEB_CHANNEL_ID and ctx.channel.id != TARNEEB_CHANNEL_ID:
            return await ctx.send(f"❌ عفواً! يمكنك استخدام لعبة الطرنيب فقط في الروم المخصص: <#{TARNEEB_CHANNEL_ID}>")

        if ctx.channel.id in active_games:
            return await ctx.send("❌ يوجد بالفعل طاولة طرنيب نشطة في هذا الروم!")
        # التحقق من عدم وجود لعبة أخرى من نوع مختلف
        from bot import has_active_game, get_active_game, register_game
        if has_active_game(ctx.channel.id):
            return await ctx.send(f"❌ يوجد لعبة **{get_active_game(ctx.channel.id)}** تعمل في هذا الروم بالفعل!")

        game = TarneebGame(ctx.channel.id)
        active_games[ctx.channel.id] = game
        register_game(ctx.channel.id, "tarneeb")

        # Add host as Player 1
        game.add_player(ctx.author.id, ctx.author.display_name)

        embed = self.build_lobby_embed(game)
        view = TarneebLobbyView(ctx.author, game, self)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="_انهاء", aliases=["انهاء_الطرنيب", "stop_tarneeb"])
    async def cmd_end_tarneeb(self, ctx):
        """إنهاء لعبة الطرنيب الحالية بواسطة الأدمن"""
        if not ctx.author.guild_permissions.manage_events and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ فقط المسؤولين يمكنهم إلغاء أو إنهاء اللعبة!")

        if ctx.channel.id in active_games:
            del active_games[ctx.channel.id]
            from bot import unregister_game
            unregister_game(ctx.channel.id)
            await ctx.send("⏹️ **تم إنهاء لعبة الطرنيب في هذا الروم بنجاح بواسطة الأدمن.**")
        else:
            await ctx.send("❌ لا توجد لعبة طرنيب نشطة حالياً في هذا الروم!")


async def setup(bot):
    await bot.add_cog(TarneebCog(bot))
