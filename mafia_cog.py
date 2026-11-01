import asyncio
import os
import random
from collections import Counter
from dataclasses import dataclass, field

import discord
from discord.ext import commands

MIN_PLAYERS = int(os.getenv("MAFIA_MIN_PLAYERS", "5"))
MAX_PLAYERS = 20
NIGHT_TIME = 60      # أقصى مدة لليل (ثانية)
MIN_NIGHT = 20       # أقل مدة لليل حتى لا يُكشف من مات دوره من سرعة الانتهاء
DISCUSS_TIME = 90    # نقاش النهار
VOTE_TIME = 60       # التصويت على الاتهام
DEFENSE_TIME = 25    # دفاع المتهم
VERDICT_TIME = 25    # التصويت مذنب/بريء

ROLES = {
    "godfather": ("👑", "العرّاب", "mafia",
                  "زعيم المافيا. يظهر «بريئاً» أمام المحقق، وصوته يحسم قرار القتل."),
    "mafia": ("🔪", "مافيا", "mafia",
              "تقتلون شخصاً كل ليلة بالاتفاق. تظهر «مشبوهاً» أمام المحقق."),
    "detective": ("🕵️", "المحقق", "town",
                  "كل ليلة تحقق مع لاعب وتعرف إن كان «مشبوهاً» أو «بريئاً». (العرّاب يظهر بريئاً!)"),
    "doctor": ("🩺", "الطبيب", "town",
               "كل ليلة تحمي لاعباً من القتل. لا يمكنك حماية نفس الشخص ليلتين متتاليتين، ونفسك مرة واحدة فقط."),
    "bodyguard": ("🛡️", "الحارس", "town",
                  "تحرس لاعباً: إذا هاجمته المافيا تموت بدلاً منه ويموت معك صاحب قرار القتل."),
    "jester": ("🃏", "المهرّج", "neutral",
               "تفوز وحدك إذا أقنعتهم بإعدامك بالتصويت! اجعلهم يشكّون بك."),
    "citizen": ("🙂", "مواطن", "town",
                 "لا قدرة لك سوى عقلك وصوتك. حلّل، أقنع، وصوّت بحكمة."),
}

active_mafia_games = {}


async def safe(coro):
    try:
        return await coro
    except discord.HTTPException:
        return None
    except Exception:
        return None


def build_roles(n: int) -> list[str]:
    mafia_count = max(1, (n - 1) // 3)
    roles = ["godfather"] + ["mafia"] * (mafia_count - 1)
    roles += ["detective", "doctor"]
    if n >= 7:
        roles.append("bodyguard")
    if n >= 8:
        roles.append("jester")
    roles += ["citizen"] * (n - len(roles))
    random.shuffle(roles)
    return roles


@dataclass
class Player:
    member: discord.Member
    role: str = "citizen"
    alive: bool = True
    notes: list = field(default_factory=list)
    last_saved: int | None = None
    self_heal_used: bool = False

    @property
    def id(self):
        return self.member.id

    @property
    def name(self):
        return self.member.display_name

    @property
    def team(self):
        return ROLES[self.role][2]

    @property
    def label(self):
        e, n, *_ = ROLES[self.role]
        return f"{e} {n}"


class MafiaGame:
    def __init__(self, channel: discord.TextChannel, host: discord.Member):
        self.channel = channel
        self.guild = channel.guild
        self.host = host
        self.players: dict[int, Player] = {}
        self.phase = "lobby"
        self.round = 0
        self.night_actions: dict[int, tuple] = {}
        self.night_done = asyncio.Event()
        self.votes: dict[int, int] = {}
        self.needed = 2
        self.vote_event = asyncio.Event()
        self.accused_id: int | None = None
        self.verdicts: dict[int, bool] = {}
        self.verdict_event = asyncio.Event()
        self.mafia_channel = None
        self.winner: str | None = None
        self.task: asyncio.Task | None = None
        self.state = "RUNNING"

    def alive(self):
        return [p for p in self.players.values() if p.alive]

    def lobby_embed(self):
        names = "\n".join(f"• {p.member.mention}" for p in self.players.values())
        e = discord.Embed(
            title="🎭 لعبة مافيا (Mafia)",
            description=f"المضيف: {self.host.mention}\n\n**اللاعبون ({len(self.players)}/{MAX_PLAYERS}):**\n{names}",
            color=0x8B0000
        )
        e.set_footer(text=f"الحد الأدنى {MIN_PLAYERS} لاعبين • المضيف يضغط «ابدأ»")
        return e

    async def set_talk(self, allow: bool):
        await safe(self.channel.set_permissions(
            self.guild.default_role, send_messages=(None if allow else False)))

    async def kill(self, p: Player):
        p.alive = False
        await safe(self.channel.set_permissions(p.member, send_messages=False))

    async def run(self):
        try:
            await self.setup()
            while self.state != "GAME_OVER":
                self.round += 1
                await self.night()
                if self.check_win():
                    break
                await self.day()
                if self.check_win():
                    break
            if self.winner:
                await self.announce_winner()
        except asyncio.CancelledError:
            await safe(self.channel.send("🛑 تم إلغاء لعبة المافيا."))
        except Exception as ex:
            await safe(self.channel.send(f"⚠️ حدث خطأ في لعبة المافيا: `{ex}`"))
        finally:
            self.state = "GAME_OVER"
            await self.cleanup()

    async def setup(self):
        self.phase = "setup"
        roles = build_roles(len(self.players))
        for p, r in zip(self.players.values(), roles):
            p.role = r

        mafia = [p for p in self.players.values() if p.team == "mafia"]
        ow = {
            self.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        for p in mafia:
            ow[p.member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        self.mafia_channel = await safe(self.guild.create_text_channel(
            "مافيا-سري", overwrites=ow, category=self.channel.category))
        if self.mafia_channel:
            await safe(self.mafia_channel.send(
                "🔪 " + " ".join(p.member.mention for p in mafia) +
                "\nهذا مقركم السري. تناقشوا هنا في هوية الضحية ثم صوّتوا من زر «قدرة الليل» في القناة العامة."))

        counts = Counter(p.role for p in self.players.values())
        lines = [f"{ROLES[r][0]} {ROLES[r][1]} × {c}" for r, c in counts.items()]
        e = discord.Embed(title="🎬 بدأت لعبة المافيا!", color=0x2F3136,
                          description="تم توزيع الأدوار. اضغط **«🎭 دوري»** لتعرف دورك سراً.\n\n**الأدوار الموجودة:**\n" + "\n".join(lines))
        await self.channel.send(embed=e, view=GamePanel(self))
        await asyncio.sleep(10)

    async def cleanup(self):
        await safe(self.channel.set_permissions(self.guild.default_role, send_messages=None))
        for p in self.players.values():
            await safe(self.channel.set_permissions(p.member, overwrite=None))
        if self.mafia_channel:
            await safe(self.mafia_channel.delete())
        active_mafia_games.pop(self.channel.id, None)
        try:
            from bot import unregister_game
            unregister_game(self.channel.id)
        except Exception:
            pass

    def night_options(self, p: Player):
        alive = self.alive()
        if p.role in ("mafia", "godfather"):
            return "kill", [x for x in alive if x.team != "mafia"], "اختر الضحية"
        if p.role == "doctor":
            opts = [x for x in alive
                    if x.id != p.last_saved and not (x.id == p.id and p.self_heal_used)]
            return "save", opts, "من تحمي هذه الليلة؟"
        if p.role == "detective":
            return "check", [x for x in alive if x.id != p.id], "مع من تحقق؟"
        if p.role == "bodyguard":
            return "guard", [x for x in alive if x.id != p.id], "من تحرس؟"
        return None

    def check_night_done(self):
        required = []
        for p in self.alive():
            o = self.night_options(p)
            if o and o[1]:
                required.append(p.id)
        if all(r in self.night_actions for r in required):
            self.night_done.set()

    async def night(self):
        self.phase = "night"
        self.night_actions = {}
        self.night_done = asyncio.Event()
        await self.set_talk(False)
        e = discord.Embed(title=f"🌙 الليلة {self.round}",
                          description=f"حلّ الظلام... القناة مغلقة.\nأصحاب القدرات: اضغطوا **«🌙 قدرة الليل»** (لديكم {NIGHT_TIME} ثانية).\nالمافيا: تناقشوا في قناتكم السرية ثم صوّتوا.",
                          color=0x0B1D51)
        await self.channel.send(embed=e, view=GamePanel(self))
        self.check_night_done()

        loop = asyncio.get_running_loop()
        start = loop.time()
        try:
            await asyncio.wait_for(self.night_done.wait(), NIGHT_TIME)
        except asyncio.TimeoutError:
            pass
        rest = MIN_NIGHT - (loop.time() - start)
        if rest > 0:
            await asyncio.sleep(rest)

        self.phase = "dawn"
        await self.resolve_night()

    async def resolve_night(self):
        acts = self.night_actions
        alive = self.alive()
        by_role = lambda *roles: next((p for p in alive if p.role in roles), None)

        mafia_votes = {uid: a[1] for uid, a in acts.items() if a[0] == "kill"}
        target_id, decider = None, None
        gf = by_role("godfather")
        if gf and gf.id in mafia_votes:
            target_id, decider = mafia_votes[gf.id], gf
        elif mafia_votes:
            top = Counter(mafia_votes.values()).most_common()
            if len(top) == 1 or top[0][1] > top[1][1]:
                target_id = top[0][0]
                decider = self.players[next(u for u, t in mafia_votes.items() if t == target_id)]

        doctor = by_role("doctor")
        doc_target = acts[doctor.id][1] if doctor and doctor.id in acts else None
        if doctor:
            doctor.last_saved = doc_target
            if doc_target == doctor.id:
                doctor.self_heal_used = True
        bg = by_role("bodyguard")
        guard_target = acts[bg.id][1] if bg and bg.id in acts else None

        deaths: list[tuple[Player, str]] = []
        if target_id:
            victim = self.players[target_id]
            if bg and guard_target == target_id:
                if bg.id != doc_target:
                    deaths.append((bg, "ضحّى بنفسه ليحمي شخصاً من المافيا ⚔️"))
                if decider:
                    deaths.append((decider, "سقط في اشتباك مع الحارس ⚔️"))
                victim.notes.append(f"🛡️ ليلة {self.round}: حارسك أنقذك من هجوم المافيا!")
            elif doc_target == target_id:
                victim.notes.append(f"🩺 ليلة {self.round}: تعرّضت لهجوم لكن الطبيب أنقذك!")
                doctor.notes.append(f"✅ ليلة {self.round}: أنقذتَ **{victim.name}** من هجوم المافيا!")
            else:
                deaths.append((victim, "قُتل على يد المافيا 🔪"))

        for p in alive:
            if p.role == "detective" and p.id in acts:
                t = self.players[acts[p.id][1]]
                suspicious = t.team == "mafia" and t.role != "godfather"
                res = "🔴 **مشبوه**" if suspicious else "🟢 **بريء**"
                p.notes.append(f"🔎 ليلة {self.round}: {t.name} ← {res}")

        e = discord.Embed(title=f"🌅 فجر اليوم {self.round}", color=0xF5A623)
        if not deaths:
            e.description = "مرّت الليلة بسلام... لم يمت أحد! 😮‍💨"
        else:
            seen, lines = set(), []
            for p, why in deaths:
                if p.id in seen:
                    continue
                seen.add(p.id)
                await self.kill(p)
                lines.append(f"💀 **{p.name}** — كان {p.label}\n└ {why}")
            e.description = "\n\n".join(lines)
        e.set_footer(text="📜 أصحاب القدرات: راجعوا «معلوماتي» لرؤية ما حصل لكم ليلاً.")
        await self.channel.send(embed=e)

    async def day(self):
        self.phase = "day"
        await self.set_talk(True)
        alive = self.alive()
        e = discord.Embed(
            title=f"☀️ النهار {self.round}",
            description=f"النقاش مفتوح لمدة **{DISCUSS_TIME}** ثانية.\nالأحياء ({len(alive)}): " +
                        "، ".join(p.name for p in alive) +
                        "\n\n💡 اطرحوا الأسئلة، قارنوا الأقوال، وتتبّعوا التناقضات!",
            color=0xFFD166)
        await self.channel.send(embed=e, view=GamePanel(self))
        await asyncio.sleep(DISCUSS_TIME)

        if self.state == "GAME_OVER":
            return

        self.phase = "vote"
        self.votes = {}
        self.needed = max(2, (len(alive) + 1) // 2)
        self.accused_id = None
        self.vote_event = asyncio.Event()
        view = VoteView(self)
        msg = await self.channel.send(embed=self.vote_embed(), view=view)
        try:
            await asyncio.wait_for(self.vote_event.wait(), VOTE_TIME)
        except asyncio.TimeoutError:
            pass
        await safe(msg.edit(view=None))

        if self.state == "GAME_OVER":
            return

        if self.accused_id is None:
            self.phase = "none"
            await self.channel.send(embed=discord.Embed(
                description="⚖️ لم يصل أي لاعب إلى الأغلبية المطلوبة... لا إعدام اليوم. المافيا تبتسم 😈",
                color=0x555555))
            return
        await self.trial(self.players[self.accused_id])

    def vote_embed(self):
        c = Counter(self.votes.values())
        lines = []
        for tid, n in c.most_common():
            voters = "، ".join(self.players[u].name for u, t in self.votes.items() if t == tid)
            lines.append(f"**{self.players[tid].name}** — {n}/{self.needed}\n└ {voters}")
        e = discord.Embed(
            title="🗳️ من تتهمون؟",
            description=("\n".join(lines) or "لا أصوات بعد.") +
                        f"\n\nالأغلبية المطلوبة: **{self.needed}** أصوات • الأصوات علنية!",
            color=0xE63946)
        return e

    async def trial(self, accused: Player):
        self.phase = "trial"
        await self.set_talk(False)
        await safe(self.channel.set_permissions(accused.member, send_messages=True))
        await self.channel.send(embed=discord.Embed(
            title="⚖️ المحاكمة",
            description=f"{accused.member.mention} وصلت إليك أغلبية الأصوات!\nلديك **{DEFENSE_TIME}** ثانية للدفاع عن نفسك. الجميع صامتون.",
            color=0xB5179E))
        await asyncio.sleep(DEFENSE_TIME)
        await safe(self.channel.set_permissions(accused.member, overwrite=None))

        if self.state == "GAME_OVER":
            return

        self.phase = "verdict"
        self.verdicts = {}
        self.verdict_event = asyncio.Event()
        msg = await self.channel.send(embed=discord.Embed(
            title="🔨 الحكم",
            description=f"هل **{accused.name}** مذنب؟ صوّتوا خلال {VERDICT_TIME} ثانية.",
            color=0xB5179E), view=VerdictView(self, accused))
        try:
            await asyncio.wait_for(self.verdict_event.wait(), VERDICT_TIME)
        except asyncio.TimeoutError:
            pass
        await safe(msg.edit(view=None))

        guilty = [self.players[u].name for u, v in self.verdicts.items() if v]
        innocent = [self.players[u].name for u, v in self.verdicts.items() if not v]
        details = f"👎 مذنب ({len(guilty)}): {'، '.join(guilty) or '—'}\n👍 بريء ({len(innocent)}): {'، '.join(innocent) or '—'}"
        if len(guilty) > len(innocent):
            await self.kill(accused)
            await self.channel.send(embed=discord.Embed(
                title="🪢 تم الإعدام",
                description=f"{details}\n\n**{accused.name}** أُعدم... وكان {accused.label}!",
                color=0x000000))
            if accused.role == "jester":
                self.winner = "jester"
        else:
            await self.channel.send(embed=discord.Embed(
                title="🕊️ تمت التبرئة",
                description=f"{details}\n\n**{accused.name}** نجا من الإعدام.",
                color=0x2A9D8F))

    def check_win(self):
        if self.winner:
            return True
        alive = self.alive()
        mafia = [p for p in alive if p.team == "mafia"]
        others = len(alive) - len(mafia)
        if not mafia:
            self.winner = "town"
        elif len(mafia) >= others:
            self.winner = "mafia"
        return bool(self.winner)

    async def announce_winner(self):
        title = {"town": "🏆 فازت المدينة!", "mafia": "🏆 فازت المافيا!",
                 "jester": "🃏 فاز المهرّج! لقد خدعكم جميعاً!"}.get(self.winner, "انتهت اللعبة!")
        roles = "\n".join(f"{'🟢' if p.alive else '💀'} {p.member.mention} — {p.label}"
                          for p in self.players.values())
        await self.channel.send(embed=discord.Embed(
            title=title, description=f"**الأدوار الحقيقية:**\n{roles}", color=0xFFD700))


class GamePanel(discord.ui.View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    def _player(self, interaction):
        return self.game.players.get(interaction.user.id)

    @discord.ui.button(label="دوري", emoji="🎭", style=discord.ButtonStyle.primary)
    async def my_role(self, interaction: discord.Interaction, button):
        p = self._player(interaction)
        if not p or p.role is None:
            return await interaction.response.send_message("أنت لست في اللعبة.", ephemeral=True)
        e, n, _, desc = ROLES[p.role]
        text = f"{e} **{n}**\n{desc}"
        if p.team == "mafia":
            mates = "، ".join(f"{x.name} ({x.label})" for x in self.game.players.values()
                              if x.team == "mafia" and x.id != p.id)
            text += f"\n\n**فريقك:** {mates or 'أنت وحدك'}"
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="معلوماتي", emoji="📜", style=discord.ButtonStyle.secondary)
    async def my_notes(self, interaction: discord.Interaction, button):
        p = self._player(interaction)
        if not p:
            return await interaction.response.send_message("أنت لست في اللعبة.", ephemeral=True)
        text = "\n".join(p.notes) or "لا توجد معلومات سرية حتى الآن."
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="قدرة الليل", emoji="🌙", style=discord.ButtonStyle.danger)
    async def night_ability(self, interaction: discord.Interaction, button):
        g = self.game
        p = self._player(interaction)
        if not p or not p.alive:
            return await interaction.response.send_message("لا يمكنك استخدام هذا الزر.", ephemeral=True)
        if g.phase != "night":
            return await interaction.response.send_message("ليس وقت الليل الآن.", ephemeral=True)
        opt = g.night_options(p)
        if not opt or not opt[1]:
            return await interaction.response.send_message("😴 لا قدرة ليلية لديك. نم بهدوء.", ephemeral=True)
        kind, targets, prompt = opt
        view = discord.ui.View(timeout=NIGHT_TIME)
        view.add_item(TargetSelect(g, p, kind, targets, prompt))
        await interaction.response.send_message(f"{ROLES[p.role][0]} **{prompt}**", view=view, ephemeral=True)


class TargetSelect(discord.ui.Select):
    def __init__(self, game: MafiaGame, player: Player, kind: str, targets: list[Player], prompt: str):
        super().__init__(placeholder=prompt,
                         options=[discord.SelectOption(label=t.name[:100], value=str(t.id)) for t in targets])
        self.game, self.player, self.kind = game, player, kind

    async def callback(self, interaction: discord.Interaction):
        g = self.game
        if g.phase != "night":
            return await interaction.response.edit_message(content="⏰ انتهى الليل.", view=None)
        tid = int(self.values[0])
        g.night_actions[self.player.id] = (self.kind, tid)
        await interaction.response.edit_message(
            content=f"✅ اخترت **{g.players[tid].name}**. (يمكنك التغيير قبل نهاية الليل)", view=self.view)
        g.check_night_done()


class VoteSelect(discord.ui.Select):
    def __init__(self, game: MafiaGame):
        super().__init__(placeholder="اختر من تتهمه...",
                         options=[discord.SelectOption(label=p.name[:100], value=str(p.id))
                                   for p in game.alive()])
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        g = self.game
        p = g.players.get(interaction.user.id)
        if g.phase != "vote" or not p or not p.alive:
            return await interaction.response.send_message("لا يمكنك التصويت الآن.", ephemeral=True)
        tid = int(self.values[0])
        if tid == p.id:
            return await interaction.response.send_message("لا يمكنك التصويت على نفسك 😅", ephemeral=True)
        g.votes[p.id] = tid
        await interaction.response.edit_message(embed=g.vote_embed())
        if Counter(g.votes.values())[tid] >= g.needed:
            g.accused_id = tid
            g.phase = "vote_done"
            g.vote_event.set()


class VoteView(discord.ui.View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game
        self.add_item(VoteSelect(game))

    @discord.ui.button(label="سحب صوتي", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def withdraw(self, interaction: discord.Interaction, button):
        g = self.game
        if g.phase != "vote" or interaction.user.id not in g.votes:
            return await interaction.response.send_message("ليس لديك صوت لسحبه.", ephemeral=True)
        g.votes.pop(interaction.user.id)
        await interaction.response.edit_message(embed=g.vote_embed())


class VerdictView(discord.ui.View):
    def __init__(self, game: MafiaGame, accused: Player):
        super().__init__(timeout=None)
        self.game, self.accused = game, accused

    async def cast(self, interaction: discord.Interaction, guilty: bool):
        g = self.game
        p = g.players.get(interaction.user.id)
        if g.phase != "verdict" or not p or not p.alive or p.id == self.accused.id:
            return await interaction.response.send_message("لا يمكنك التصويت الآن.", ephemeral=True)
        g.verdicts[p.id] = guilty
        await interaction.response.send_message("✅ سُجّل حكمك (يمكنك تغييره).", ephemeral=True)
        eligible = len([x for x in g.alive() if x.id != self.accused.id])
        if len(g.verdicts) >= eligible:
            g.verdict_event.set()

    @discord.ui.button(label="مذنب", emoji="👎", style=discord.ButtonStyle.danger)
    async def guilty(self, interaction, button):
        await self.cast(interaction, True)

    @discord.ui.button(label="بريء", emoji="👍", style=discord.ButtonStyle.success)
    async def innocent(self, interaction, button):
        await self.cast(interaction, False)


class MafiaLobbyView(discord.ui.View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=900)
        self.game = game

    async def on_timeout(self):
        if self.game.phase == "lobby":
            active_mafia_games.pop(self.game.channel.id, None)
            try:
                from bot import unregister_game
                unregister_game(self.game.channel.id)
            except Exception:
                pass

    @discord.ui.button(label="انضمام", emoji="✅", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button):
        g = self.game
        if interaction.user.id in g.players:
            return await interaction.response.send_message("أنت منضم بالفعل.", ephemeral=True)
        if len(g.players) >= MAX_PLAYERS:
            return await interaction.response.send_message("اللوبي ممتلئ.", ephemeral=True)
        g.players[interaction.user.id] = Player(interaction.user)
        await interaction.response.edit_message(embed=g.lobby_embed())

    @discord.ui.button(label="مغادرة", emoji="🚪", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button):
        g = self.game
        if interaction.user.id == g.host.id:
            return await interaction.response.send_message("المضيف لا يغادر. يمكن استخدام `.انهاء` للإلغاء.", ephemeral=True)
        if g.players.pop(interaction.user.id, None) is None:
            return await interaction.response.send_message("أنت لست في اللوبي.", ephemeral=True)
        await interaction.response.edit_message(embed=g.lobby_embed())

    @discord.ui.button(label="ابدأ", emoji="▶️", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button):
        g = self.game
        if interaction.user.id != g.host.id:
            return await interaction.response.send_message("المضيف فقط يستطيع البدء.", ephemeral=True)
        if len(g.players) < MIN_PLAYERS:
            return await interaction.response.send_message(f"نحتاج {MIN_PLAYERS} لاعبين على الأقل للبدء.", ephemeral=True)
        g.phase = "setup"
        await interaction.response.edit_message(embed=g.lobby_embed(), view=None)
        self.stop()
        g.task = asyncio.create_task(g.run())


class MafiaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="مافيا", aliases=["mafia", "المافيا"])
    async def cmd_mafia(self, ctx):
        """بدء لعبة مافيا جديدة في الروم"""
        cid = ctx.channel.id
        if cid in active_mafia_games:
            return await ctx.send("❌ توجد لعبة مافيا قائمة بالفعل في هذه القناة!")

        from bot import has_active_game, get_active_game, register_game
        if has_active_game(cid):
            return await ctx.send(f"❌ يوجد لعبة **{get_active_game(cid)}** تعمل في هذا الروم بالفعل!\nيمكنك إنهاؤها أولاً بأمر: `.انهاء`")

        game = MafiaGame(ctx.channel, ctx.author)
        game.players[ctx.author.id] = Player(ctx.author)
        active_mafia_games[cid] = game
        register_game(cid, "mafia")

        await ctx.send(embed=game.lobby_embed(), view=MafiaLobbyView(game))

    @commands.command(name="_انهاء_المافيا", aliases=["stop_mafia", "انهاء_المافيا"])
    async def cmd_stop_mafia(self, ctx):
        """إلغاء لعبة المافيا الحالية (للمضيف أو المشرفين)"""
        cid = ctx.channel.id
        game = active_mafia_games.get(cid)
        if not game:
            return await ctx.send("❌ لا توجد لعبة مافيا نشطة في هذه القناة.")

        from bot import is_admin_or_mod
        if ctx.author.id != game.host.id and not is_admin_or_mod(ctx):
            return await ctx.send("❌ فقط المضيف أو المشرفين يمكنهم إلغاء اللعبة.")

        await ctx.send("🛑 جارٍ إلغاء لعبة المافيا...")
        game.state = "GAME_OVER"
        if game.task and not game.task.done():
            game.task.cancel()
        else:
            await game.cleanup()


async def setup(bot: commands.Bot):
    await bot.add_cog(MafiaCog(bot))
