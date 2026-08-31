"""
Profile & Engagement Discord Cog (profile_cog.py)
Handles automatic message counting, rank card rendering, and leaderboard commands.
"""
import discord
from discord.ext import commands

from activity_logic import (
    record_message,
    get_user_rank_and_title,
    get_server_leaderboard
)
from profile_gfx import (
    render_profile_card,
    download_avatar_async
)

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """تسجيل نشاط الأعضاء وزيادة عداد الرسائل ونقاط التفاعل تلقائياً"""
        if message.author.bot or not message.guild:
            return

        # تسجيل الرسالة وحساب التفاعل
        record_message(
            user_id=message.author.id,
            username=message.author.name,
            display_name=message.author.display_name,
            char_count=len(message.content or "")
        )

    def is_user_admin(self, member: discord.Member) -> bool:
        """التحقق مما إذا كان العضو يملك رتبة إدارية أو إشرافية في السيرفر"""
        if not isinstance(member, discord.Member):
            return False
        p = member.guild_permissions
        return (
            p.administrator
            or p.manage_guild
            or p.manage_events
            or p.manage_messages
            or (member.guild and member.id == member.guild.owner_id)
        )

    @commands.command(name="بروفايل", aliases=["بطاقتي", "رتبتي", "id", "profile", "rank", "هويتي"])
    async def cmd_profile(self, ctx, member: discord.Member = None):
        """عرض البطاقة التعريفية الحديثة ونقاط التفاعل واللقب"""
        target = member or ctx.author
        
        # إشعار سريع أثناء توليد الصورة
        async with ctx.typing():
            # 1. جلب بيانات التفاعل والترتيب واللقب
            user_data = get_user_rank_and_title(
                user_id=target.id,
                username=target.name,
                display_name=target.display_name
            )

            # 2. تحديد ما إذا كان العضو إدارياً
            is_admin = self.is_user_admin(target)

            # 3. تحميل صورة الأفاتار
            avatar_url = target.display_avatar.url if target.display_avatar else None
            avatar_img = await download_avatar_async(avatar_url)

            # 4. توليد بطاقة البروفايل بالثيم المناسب
            card_buf = render_profile_card(avatar_img, user_data, is_admin=is_admin)
            file = discord.File(fp=card_buf, filename="profile_card.png")

            # 5. إرسال البطاقة
            await ctx.send(file=file)

    @commands.command(name="توب", aliases=["المتصدرين", "متصدرين", "top", "leaderboard", "توب_التفاعل"])
    async def cmd_top(self, ctx):
        """عرض قائمة توب 10 المتفاعلين في السيرفر مع ألقابهم"""
        leaders = get_server_leaderboard(sort_by="total", limit=10)
        
        embed = discord.Embed(
            title="🏆 قائمة توب 10 المتصدرين في السيرفر",
            description="ترتيب الأعضاء الأكثر تفاعلاً وإرسالاً للرسائل في السيرفر:",
            color=0xF1C40F
        )

        if not leaders:
            embed.description = "لا توجد بيانات تفاعل مسجلة حتى الآن!"
            return await ctx.send(embed=embed)

        rows = []
        for idx, u in enumerate(leaders):
            rank = idx + 1
            if rank == 1:
                icon = "👑 **#1**"
                title_tag = "`[ملك التفاعل]`"
            elif rank == 2:
                icon = "🥈 **#2**"
                title_tag = "`[متفاعل دائم]`"
            elif 3 <= rank <= 10:
                icon = f"✨ **#{rank}**"
                title_tag = "`[متفاعل]`"
            else:
                icon = f"**#{rank}**"
                title_tag = ""

            name = u.get("display_name", u.get("username", "Member"))
            total = u.get("total_messages", 0)
            weekly = u.get("weekly_messages", 0)
            xp = u.get("xp", 0)
            lvl = u.get("level", 1)

            rows.append(
                f"{icon} <@{u['user_id']}> {title_tag}\n"
                f"└ 💬 الرسائل: **{total:,}** | 📅 الأسبوع: **{weekly:,}** | ⚡ المستوى: **{lvl}** ({xp:,} XP)\n"
            )

        embed.add_field(name="المتصدرون:", value="\n".join(rows), inline=False)
        embed.set_footer(text="استخدم أمر .بروفايل لعرض بطاقتك التعريفية المصممة بالكامل!")
        await ctx.send(embed=embed)

    @commands.command(name="توب_الاسبوع", aliases=["توب_أسبوع", "weekly", "weekly_top", "متصدري_الاسبوع"])
    async def cmd_top_weekly(self, ctx):
        """عرض قائمة أنشط الأعضاء خلال هذا الأسبوع"""
        leaders = get_server_leaderboard(sort_by="weekly", limit=10)

        embed = discord.Embed(
            title="📅 قائمة متصدري التفاعل لهذا الأسبوع",
            description="ترتيب الأعضاء الأكثر نشاطاً وإرسالاً للرسائل خلال الأسبوع الحالي:",
            color=0x9B59B6
        )

        if not leaders or all(u.get("weekly_messages", 0) == 0 for u in leaders):
            embed.description = "لم يتم تسجيل رسائل هذا الأسبوع بعد، كن أول المتفاعلين!"
            return await ctx.send(embed=embed)

        rows = []
        for idx, u in enumerate(leaders):
            weekly = u.get("weekly_messages", 0)
            if weekly <= 0:
                continue
            rank = idx + 1
            icon = "👑" if rank == 1 else ("🥈" if rank == 2 else "✨")
            name = u.get("display_name", u.get("username", "Member"))
            rows.append(f"{icon} **#{rank}** <@{u['user_id']}> ➔ **{weekly:,}** رسالة هذا الأسبوع")

        embed.add_field(name="أنشط الأعضاء أسبوعياً:", value="\n".join(rows) if rows else "لا توجد رسائل مسجلة", inline=False)
        embed.set_footer(text="يتم تجديد عداد الأسبوع تلقائياً كل 7 أيام مع حفظ إجمالي الرسائل!")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
