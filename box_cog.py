"""
نظام لعبة صندوق الحظ السريع (Box Game)
مستوحى من بنك الحظ السريع مع توليد رقعة الصناديق ديناميكياً بـ Pillow
الأمر: _صندوق
"""
import asyncio
import io
import random
import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont

GAME_SECONDS = 30

active_box_games = {}


# ---------------- الجوائز ----------------
def make_prizes():
    prizes = [
        ("coin", 50), ("coin", 50), ("coin", 100), ("coin", 100),
        ("coin", 200), ("diamond", 500), ("bomb", -150), ("bomb", -150),
        ("coin", 75),
    ]
    random.shuffle(prizes)
    return prizes


# ---------------- الرسم بـ Pillow ----------------
CELL, GAP, MARGIN = 150, 16, 24
SIZE = MARGIN * 2 + CELL * 3 + GAP * 2


def get_font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial.ttf", "segoeui.ttf", "tahoma.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def center_text(d, xy, text, font, fill):
    x, y = xy
    box = d.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text((x - w / 2 - box[0], y - h / 2 - box[1]), text, font=font, fill=fill)


def draw_icon(d, kind, cx, cy):
    if kind == "coin":
        d.ellipse((cx - 38, cy - 38, cx + 38, cy + 38), fill=(255, 200, 40), outline=(190, 130, 10), width=5)
        d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), outline=(220, 150, 20), width=4)
    elif kind == "diamond":
        pts = [(cx - 42, cy - 10), (cx - 22, cy - 38), (cx + 22, cy - 38), (cx + 42, cy - 10), (cx, cy + 42)]
        d.polygon(pts, fill=(80, 220, 255), outline=(20, 140, 190))
        d.line([(cx - 42, cy - 10), (cx + 42, cy - 10)], fill=(20, 140, 190), width=3)
        d.line([(cx - 22, cy - 38), (cx, cy - 10), (cx + 22, cy - 38)], fill=(20, 140, 190), width=3)
        d.line([(cx - 14, cy - 10), (cx, cy + 42), (cx + 14, cy - 10)], fill=(20, 140, 190), width=3)
    else:  # bomb
        d.ellipse((cx - 34, cy - 24, cx + 34, cy + 44), fill=(35, 35, 40), outline=(0, 0, 0), width=3)
        d.ellipse((cx - 20, cy - 10, cx - 6, cy + 4), fill=(110, 110, 120))
        d.line([(cx + 14, cy - 22), (cx + 30, cy - 42)], fill=(160, 120, 60), width=6)
        d.ellipse((cx + 24, cy - 52, cx + 40, cy - 36), fill=(255, 90, 30))


def render_board(prizes, opened, reveal_all=False):
    img = Image.new("RGB", (SIZE, SIZE), (24, 26, 38))
    d = ImageDraw.Draw(img)
    num_font, val_font = get_font(60), get_font(30)

    for i in range(9):
        r, c = divmod(i, 3)
        x0 = MARGIN + c * (CELL + GAP)
        y0 = MARGIN + r * (CELL + GAP)
        x1, y1 = x0 + CELL, y0 + CELL
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        kind, val = prizes[i]

        if i in opened or reveal_all:
            if kind == "bomb":
                bg, edge = (120, 35, 40), (220, 70, 70)
            elif kind == "diamond":
                bg, edge = (25, 80, 110), (90, 210, 255)
            else:
                bg, edge = (90, 70, 20), (255, 200, 40)
            if i not in opened:  # مكشوف في النهاية فقط ولم يفتحه أحد
                bg = tuple(int(v * 0.55) for v in bg)
                edge = tuple(int(v * 0.55) for v in edge)
            d.rounded_rectangle((x0, y0, x1, y1), 22, fill=bg, outline=edge, width=5)
            draw_icon(d, kind, cx, cy - 14)
            sign = "+" if val > 0 else ""
            center_text(d, (cx, y1 - 24), f"{sign}{val}", val_font, (255, 255, 255))
        else:
            d.rounded_rectangle((x0, y0, x1, y1), 22, fill=(60, 90, 200), outline=(130, 160, 255), width=5)
            d.rounded_rectangle((x0 + 12, y0 + 12, x1 - 12, y1 - 12), 16, outline=(100, 130, 230), width=3)
            center_text(d, (cx, cy), str(i + 1), num_font, (255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


# ---------------- واجهة اللعبة ----------------
class BoxGame(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.prizes = make_prizes()
        self.opened = {}          # index -> user_id
        self.scores = {}          # user_id -> points
        self.finished = False
        self.message = None
        self.lock = asyncio.Lock()
        self.counter = 0
        self.timer_task = None
        self.buttons = []
        for i in range(9):
            b = discord.ui.Button(label=str(i + 1), style=discord.ButtonStyle.primary, row=i // 3)
            b.callback = self.make_callback(i)
            self.buttons.append(b)
            self.add_item(b)

    def board_file(self, reveal_all=False):
        self.counter += 1
        return discord.File(render_board(self.prizes, self.opened, reveal_all), filename=f"box_board_{self.counter}.png")

    def standings(self):
        if not self.scores:
            return "▫️ *لا أحد لعب بعد*"
        rank = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        medals = ["🥇", "🥈", "🥉"]
        return "\n".join(
            f"{medals[n] if n < 3 else '▫️'} <@{uid}> — **{pts}** نقطة" for n, (uid, pts) in enumerate(rank)
        )

    def make_callback(self, i):
        async def callback(interaction: discord.Interaction):
            async with self.lock:
                if self.finished or i in self.opened:
                    return await interaction.response.send_message("❌ هذا الصندوق تم فتحه بالفعل!", ephemeral=True)
                
                self.opened[i] = interaction.user.id
                kind, val = self.prizes[i]
                self.scores[interaction.user.id] = self.scores.get(interaction.user.id, 0) + val
                self.buttons[i].disabled = True
                self.buttons[i].style = (
                    discord.ButtonStyle.danger if kind == "bomb" else discord.ButtonStyle.success
                )

                sign = "+" if val > 0 else ""
                icon = "💣" if kind == "bomb" else ("💎" if kind == "diamond" else "🪙")
                last = f"{icon} {interaction.user.mention} فتح الصندوق **{i + 1}** ({sign}{val} نقطة)"

                if len(self.opened) == 9:
                    return await self.finish(interaction, last)

                kwargs = dict(
                    content=f"🎁 **صندوق الحظ السريع** — متبقي {len(self.prizes) - len(self.opened)} صناديق!\n{last}\n\n📊 **الترتيب الحالي:**\n{self.standings()}",
                    attachments=[self.board_file()],
                    view=self,
                )
                await interaction.response.edit_message(**kwargs)
        return callback

    async def finish(self, interaction=None, last=""):
        if self.finished:
            return
        self.finished = True
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        for b in self.buttons:
            b.disabled = True

        text = f"🏁 **انتهت لعبة صندوق الحظ!**\n{last}\n\n📊 **النتائج النهائية:**\n{self.standings()}"
        if self.scores:
            winner = max(self.scores, key=self.scores.get)
            top_score = self.scores[winner]
            if top_score > 0:
                text += f"\n\n🏆 **الفائز بالمركز الأول:** <@{winner}> بمجموع **{top_score}** نقطة! 🎉"
            else:
                text += f"\n\n💥 انتهت اللعبة دون رصيد إيجابي!"

        kwargs = dict(content=text, attachments=[self.board_file(reveal_all=True)], view=self)
        try:
            if interaction and not interaction.response.is_done():
                await interaction.response.edit_message(**kwargs)
            elif self.message:
                await self.message.edit(**kwargs)
        except Exception:
            pass

        # تنظيف حالة اللعبة في الروم
        active_box_games.pop(self.channel_id, None)
        try:
            from bot import unregister_game
            unregister_game(self.channel_id)
        except Exception:
            pass

    async def timer(self):
        try:
            await asyncio.sleep(GAME_SECONDS)
            async with self.lock:
                if not self.finished:
                    await self.finish(None, "⏰ **انتهى الوقت (30 ثانية)!**")
        except asyncio.CancelledError:
            pass


# ---------------- الـ Cog الأساسي ----------------
class BoxCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="صندوق", aliases=["_صندوق", "صناديق", "_صناديق", "box", "_box", "boxes", "_boxes", "صندوق_الحظ"])
    async def box_command(self, ctx):
        """بدء لعبة صندوق الحظ السريعة (30 ثانية)"""
        cid = ctx.channel.id
        from bot import has_active_game, get_active_game, register_game

        if has_active_game(cid):
            gname = get_active_game(cid) or "أخرى"
            return await ctx.send(f"❌ توجد لعبة **{gname}** نشطة بالفعل في هذا الروم! انتظر انتهاءها أو اطلب من الأدمن إنهاءها بأمر `.انهاء`", delete_after=6)

        game = BoxGame(cid)
        active_box_games[cid] = game
        register_game(cid, "box")

        file = game.board_file()
        content = (
            f"🎁 **صندوق الحظ السريع** — لديكم **{GAME_SECONDS}** ثانية!\n"
            f"👇 اضغطوا على أزرار الصناديق لفتحها وحصد النقاط.\n"
            f"🪙 عملات ذهبية (+50 إلى +200) • 💎 ألماس (+500) • 💣 احذروا القنابل (-150)!"
        )
        msg = await ctx.send(content=content, file=file, view=game)
        game.message = msg
        game.timer_task = asyncio.create_task(game.timer())

    @app_commands.command(name="صندوق", description="ابدأ لعبة صندوق الحظ السريعة (30 ثانية)")
    async def box_slash(self, interaction: discord.Interaction):
        """أمر سلاش لبدء لعبة صندوق الحظ"""
        cid = interaction.channel_id
        from bot import has_active_game, get_active_game, register_game

        if has_active_game(cid):
            gname = get_active_game(cid) or "أخرى"
            return await interaction.response.send_message(f"❌ توجد لعبة **{gname}** نشطة بالفعل في هذا الروم!", ephemeral=True)

        game = BoxGame(cid)
        active_box_games[cid] = game
        register_game(cid, "box")

        file = game.board_file()
        content = (
            f"🎁 **صندوق الحظ السريع** — لديكم **{GAME_SECONDS}** ثانية!\n"
            f"👇 اضغطوا على أزرار الصناديق لفتحها وحصد النقاط.\n"
            f"🪙 عملات ذهبية (+50 إلى +200) • 💎 ألماس (+500) • 💣 احذروا القنابل (-150)!"
        )
        await interaction.response.send_message(content=content, file=file, view=game)
        game.message = await interaction.original_response()
        game.timer_task = asyncio.create_task(game.timer())


async def setup(bot):
    await bot.add_cog(BoxCog(bot))
