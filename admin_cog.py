import os
import discord

from discord.ext import commands

from discord.ui import View, Select, Modal, TextInput, UserSelect, RoleSelect, Button

import io

import asyncio

import aiohttp

import datetime



# المعرفات الثابتة المعطاة

TICKET_CHANNEL_ID = 1499527310011924540

ADMIN_ROLE_1 = 1137970284402585615

ADMIN_ROLE_2 = 1137970284402585614



ADMIN_ROLES = {ADMIN_ROLE_1, ADMIN_ROLE_2}



def is_admin_member(member: discord.Member) -> bool:

    """التحقق الحصري من صلاحية الأدمن ستريتر (Administrator) أو مالك السيرفر"""

    if not isinstance(member, discord.Member):

        return False

    return member.guild_permissions.administrator or member.id == member.guild.owner_id



def get_main_admin_embed(author: discord.Member) -> discord.Embed:

    embed = discord.Embed(

        title="🛡️ لوحة القرارات والإعلانات الإدارية",

        description=(

            "اختر من القائمة المنسدلة بالأسفل نوع الإعلان أو القرار الإداري الذي تريد نشره.\n"

            "إذا كان القرار يتطلب عضواً أو رتبة، **ستظهر لك قائمة فورية برتب وأعضاء السيرفر لاختيارهم بضغطة زر** بدون الحاجة لنسخ أي تاغ! ✨\n\n"

            "**📋 الخيارات المتاحة (16 قرار إداري رسمي وفاتورة مرتبة):**\n"

            "• `1` 🎪 إنشاء فعالية • `2` ⭐ ترقية عضو • `3` 🌟 نجم/أدمن الأسبوع\n"

            "• `4` ⚠️ تحذير إداري • `5` 🔻 سحب رتبة • `6` ⛔ حظر عضو (BAN)\n"

            "• `7` 🛑 طرد عضو (KICK) • `8` 🔇 إسكات مؤقت (MUTE) • `9` 📢 اجتماع إداري\n"

            "• `10` 📥 فتح التقديم • `11` 🔒 إغلاق التقديم • `12` 👑 تكريم متميز\n"

            "• `13` 🛠️ صيانة وتحديث • `14` 📜 تحديث قوانين • `15` 📢 تعميم عام • `16` 🔔 فاتورة جديدة"

        ),

        color=discord.Color.dark_purple()

    )

    embed.set_footer(text=f"طلب بواسطة: {author.display_name} • اختر من القائمة للمتابعة", icon_url=author.display_avatar.url)

    return embed



# ==============================================================================

# نماذج الإدخال (Modals)

# ==============================================================================



class BaseAdminModal(Modal):

    def __init__(self, title: str, formatter, panel_message: discord.Message = None, image_bytes: bytes = None, filename: str = None):

        super().__init__(title=title[:45])

        self.formatter = formatter

        self.panel_message = panel_message

        self.image_bytes = image_bytes

        self.filename = filename or "image.png"



    async def on_submit(self, interaction: discord.Interaction):

        values = [child.value.strip() for child in self.children if isinstance(child, TextInput)]

        res = self.formatter(*values)

        

        # دعم إرسال Embed مخصص أو نص عادي
        content_txt = None
        embed = None
        if isinstance(res, tuple):
            content_txt, embed = res
        elif isinstance(res, discord.Embed):
            embed = res
        else:
            content_txt = res

        # إرسال في القناة مع الصورة المرفقة وشعار المتجر إن وُجد
        files_to_send = []
        if getattr(self, "extra_files", None):
            files_to_send.extend(self.extra_files)

        if self.image_bytes:
            file = discord.File(io.BytesIO(self.image_bytes), filename=self.filename)
            files_to_send.append(file)
            if embed:
                embed.set_image(url=f"attachment://{self.filename}")

        if embed:
            if files_to_send:
                await interaction.channel.send(content=content_txt, embed=embed, files=files_to_send)
            else:
                await interaction.channel.send(content=content_txt, embed=embed)
        else:
            if files_to_send:
                await interaction.channel.send(content=content_txt, files=files_to_send)
            else:
                await interaction.channel.send(content=content_txt)

        

        # تنظيف رسالة اللوحة بعد النشر لعدم حدوث لخبطة في الشات

        if self.panel_message:

            try:

                await self.panel_message.delete()

            except Exception:

                pass

        

        # رد خاص يؤكد للإداري نجاح العملية

        await interaction.response.send_message("✅ تم تجهيز ونشر الإعلان الإداري بنجاح!", ephemeral=True)



# 1. إنشاء فعالية
class EventModal(BaseAdminModal):
    def __init__(self, panel_message=None, image_bytes: bytes = None, filename: str = None):
        super().__init__(image_bytes=image_bytes, filename=filename, title="🎪 إنشاء إعلان فعالية", formatter=self.format_msg, panel_message=panel_message)
        self.name = TextInput(label="اسم الفعالية", placeholder="مثلاً: فعالية ألعاب وتحديات", max_length=100, required=True)
        self.desc = TextInput(label="الشرح وتفاصيل الفعالية", placeholder="اكتب نبذة عن الفعالية وكيفية التنافس...", style=discord.TextStyle.paragraph, required=True)
        self.time = TextInput(label="الساعة والموعد", placeholder="مثلاً: اليوم الساعة 9:00 مساءً", max_length=100, required=True)
        self.prize = TextInput(label="الجوائز (اختياري)", placeholder="مثلاً: رتبة مميزة + نقاط روليت", max_length=100, required=False)

        self.add_item(self.name)
        self.add_item(self.desc)
        self.add_item(self.time)
        self.add_item(self.prize)

    def format_msg(self, name, desc, time_val, prize):
        embed = discord.Embed(
            title="🎪 إعلان فعالية جديدة",
            description=f"### {desc}\n\nنتمنى التوفيق والروح الرياضية لجميع المشاركين! 🔥",
            color=discord.Color.from_rgb(255, 170, 0)
        )
        embed.add_field(name="🎮 اسم الفعالية", value=f"`{name}`", inline=False)
        embed.add_field(name="⏰ الموعد والساعة", value=f"`{time_val}`", inline=False)
        embed.add_field(name="🎫 طريقة المشاركة", value=f"لتقديم تكت مشاركة توجه إلى <#{TICKET_CHANNEL_ID}>", inline=False)
        if prize:
            embed.add_field(name="🎁 الجوائز", value=f"`{prize}`", inline=False)
        return embed


# 2. ترقية عضو (ترقية إدارية حقيقية منفصلة تماماً)
class PromotionModal(BaseAdminModal):
    def __init__(self, user: discord.Member, role: discord.Role, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        self.role = role
        super().__init__(image_bytes=image_bytes, filename=filename, title="⭐ قرار إداري: ترقية عضو", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الترقية", placeholder="مثال: مجتهد ويستحق الترقية لتفاعله ونشاطه المميز", max_length=150, required=True)
        self.add_item(self.reason)

    def format_msg(self, reason):
        embed = discord.Embed(
            title="⭐ قرار إداري: ترقية عضو",
            description="بالتوفيق لك ومن الأفضل للأفضل بإذن الله، ومبارك لك! 🎉",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.add_field(name="👤 العضو المُرقى", value=self.user.mention, inline=False)
        embed.add_field(name="🎖️ الرتبة الجديدة", value=self.role.mention, inline=False)
        embed.add_field(name="📋 سبب الترقية", value=reason, inline=False)
        embed.add_field(name="⚖️ القرار الرسمي", value="ترقية ومنح رتبة إدارية جديدة في السيرفر", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 3. أدمن الأسبوع / نجم الأسبوع
class StarOfWeekModal(BaseAdminModal):
    def __init__(self, user: discord.Member, role: discord.Role, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        self.role = role
        super().__init__(image_bytes=image_bytes, filename=filename, title="🌟 اختيار نجم / أدمن الأسبوع", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الاختيار والتميز", placeholder="مثال: تفاعل استثنائي ومجهود رائع خلال هذا الأسبوع", max_length=150, required=True)
        self.add_item(self.reason)

    def format_msg(self, reason):
        embed = discord.Embed(
            title="🌟 أدمن الأسبوع / نجم الأسبوع",
            description="نبارك لك هذا التألق المستحق متمنين لك وللجميع دوام التقدم والنجاح! 👑",
            color=discord.Color.from_rgb(255, 223, 0)
        )
        embed.add_field(name="👤 النجم المختار", value=self.user.mention, inline=False)
        embed.add_field(name="🎖️ الرتبة الممنوحة", value=self.role.mention, inline=False)
        embed.add_field(name="✨ سبب الاختيار", value=reason, inline=False)
        embed.add_field(name="⚖️ القرار الرسمي", value="منح رتبة وتكريم أدمن الأسبوع", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 4. إنذار إداري
class WarningModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        super().__init__(image_bytes=image_bytes, filename=filename, title="⚠️ تسجيل تحذير إداري", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب التحذير", placeholder="سبب مخالفة القوانين بالتفصيل...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="المدة / درجة الإنذار", placeholder="مثلاً: 24 ساعة / إنذار ثاني / دائم", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, reason, duration):
        embed = discord.Embed(
            title="⚠️ إنذار إداري رسمي",
            description="نرجو الالتزام بقوانين وأنظمة السيرفر لتجنب العقوبات الإدارية الأشد.",
            color=discord.Color.from_rgb(255, 140, 0)
        )
        embed.add_field(name="👤 العضو المخالف", value=self.user.mention, inline=False)
        embed.add_field(name="📋 سبب الإنذار", value=reason, inline=False)
        embed.add_field(name="⏳ المدة / الدرجة", value=f"`{duration}`", inline=False)
        embed.add_field(name="⚖️ القرار الرسمي", value="تسجيل إنذار رسمي في السجل التأديبي", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 5. سحب رتبة / إعفاء إداري
class DemoteModal(BaseAdminModal):
    def __init__(self, user: discord.Member, role: discord.Role, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        self.role = role
        super().__init__(image_bytes=image_bytes, filename=filename, title="🔻 سحب رتبة وإعفاء إداري", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="السبب وملاحظات الإعفاء", placeholder="سبب سحب الرتبة أو طلب الإعفاء...", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.reason)

    def format_msg(self, reason):
        embed = discord.Embed(
            title="🔻 قرار إداري: سحب رتبة / إعفاء",
            description="نشكر العضو على جهوده السابقة ونتمنى له التوفيق دائماً.",
            color=discord.Color.from_rgb(220, 53, 69)
        )
        embed.add_field(name="👤 العضو المعفي", value=self.user.mention, inline=False)
        embed.add_field(name="🎖️ الرتبة المسحوبة", value=self.role.mention, inline=False)
        embed.add_field(name="📋 السبب والملاحظات", value=reason, inline=False)
        embed.add_field(name="⚖️ القرار الرسمي", value="سحب الرتبة والإعفاء من المهام الإدارية", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 6. حظر عضو (BAN)
class BanModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        super().__init__(image_bytes=image_bytes, filename=filename, title="⛔ حظر عضو (BAN)", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الحظر", placeholder="السبب المفصل للحظر...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="نوع الحظر / المدة", placeholder="مثلاً: حظر نهائي / 7 أيام", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, reason, duration):
        embed = discord.Embed(
            title="⛔ قرار إداري: حظر عضو (BAN)",
            description="تؤكد الإدارة التزامها بتطبيق القوانين لحماية سلامة وراحة المجتمع.",
            color=discord.Color.from_rgb(180, 0, 0)
        )
        embed.add_field(name="👤 العضو المحظور", value=self.user.mention, inline=False)
        embed.add_field(name="📋 سبب الحظر", value=reason, inline=False)
        embed.add_field(name="⏳ المدة / النوع", value=f"`{duration}`", inline=False)
        embed.add_field(name="⚖️ القرار الرسمي", value="حظر العضو من السيرفر لمخالفته الصريحة للأنظمة والقوانين", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 7. طرد عضو (KICK)
class KickModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        super().__init__(image_bytes=image_bytes, filename=filename, title="🛑 طرد عضو (KICK)", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الطرد", placeholder="السبب ومخالفة التعليمات...", style=discord.TextStyle.paragraph, required=True)
        self.admin = TextInput(label="الإداري المنفذ", placeholder="اسمك أو منشن الإداري المسؤول", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.admin)

    def format_msg(self, reason, admin):
        embed = discord.Embed(
            title="🛑 قرار إداري: طرد عضو (KICK)",
            description="نؤكد على أهمية احترام القوانين لضمان بقاء السيرفر بيئة آمنة ومريحة للجميع.",
            color=discord.Color.from_rgb(210, 40, 40)
        )
        embed.add_field(name="👤 العضو المطرود", value=self.user.mention, inline=False)
        embed.add_field(name="📋 سبب الطرد", value=reason, inline=False)
        embed.add_field(name="👮 الإداري المنفذ", value=admin, inline=False)
        embed.add_field(name="⚖️ القرار الرسمي", value="طرد العضو كإجراء تأديبي", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 8. إسكات مؤقت (MUTE)
class MuteModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        super().__init__(image_bytes=image_bytes, filename=filename, title="🔇 إسكات مؤقت (MUTE)", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الإسكات", placeholder="مثلاً: سبام / ألفاظ غير لائقة...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="مدة الإسكات", placeholder="مثلاً: ساعتين / 24 ساعة", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, reason, duration):
        embed = discord.Embed(
            title="🔇 قرار إداري: إسكات مؤقت (MUTE)",
            description="يرجى الالتزام بآداب الحديث والتواصل في رومات السيرفر.",
            color=discord.Color.from_rgb(108, 117, 125)
        )
        embed.add_field(name="👤 العضو المكتوم", value=self.user.mention, inline=False)
        embed.add_field(name="📋 سبب الإسكات", value=reason, inline=False)
        embed.add_field(name="⏳ مدة الإسكات", value=f"`{duration}`", inline=False)
        embed.add_field(name="⚖️ القرار الرسمي", value="كتم العضو ومنعه من الكتابة والتحدث لحين انقضاء المدة", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 9. اجتماع إداري
class MeetingModal(BaseAdminModal):
    def __init__(self, panel_message=None, image_bytes: bytes = None, filename: str = None):
        super().__init__(image_bytes=image_bytes, filename=filename, title="📢 دعوة اجتماع إداري", formatter=self.format_msg, panel_message=panel_message)
        self.title_input = TextInput(label="موضوع الاجتماع", placeholder="مثلاً: مناقشة خطة الفعاليات وتطوير السيرفر", max_length=100, required=True)
        self.time = TextInput(label="الموعد والوقت", placeholder="مثلاً: غداً الساعة 10:00 مساءً", max_length=100, required=True)
        self.roles = TextInput(label="الرتب المطلوبة للحضور", placeholder="مثلاً: جميع الإداريين / المشرفين", max_length=100, required=True)
        self.topics = TextInput(label="أهم المحاور", placeholder="اكتب المحاور أو جدول الأعمال باختصار...", style=discord.TextStyle.paragraph, required=True)

        self.add_item(self.title_input)
        self.add_item(self.time)
        self.add_item(self.roles)
        self.add_item(self.topics)

    def format_msg(self, title, time_val, roles, topics):
        embed = discord.Embed(
            title="📢 إعلان: اجتماع إداري هام",
            description="⚠️ **تنبيه:** الحضور إجباري للرتب المعنية، ومن يتعذر عليه الحضور يرجى إبلاغ الإدارة مسبقاً.",
            color=discord.Color.from_rgb(0, 123, 255)
        )
        embed.add_field(name="📌 موضوع الاجتماع", value=f"`{title}`", inline=False)
        embed.add_field(name="⏰ الموعد والوقت", value=f"`{time_val}`", inline=False)
        embed.add_field(name="👥 الرتب المطلوبة", value=f"`{roles}`", inline=False)
        embed.add_field(name="📝 أهم المحاور", value=topics, inline=False)
        return embed


# 10. فتح التقديم للإدارة
class ApplyOpenModal(BaseAdminModal):
    def __init__(self, panel_message=None, image_bytes: bytes = None, filename: str = None):
        super().__init__(image_bytes=image_bytes, filename=filename, title="🌟 فتح باب التقديم للإدارة", formatter=self.format_msg, panel_message=panel_message)
        self.roles = TextInput(label="الرتب المتاحة للتقديم", placeholder="مثلاً: مشرف شات / منظم فعاليات", max_length=100, required=True)
        self.reqs = TextInput(label="الشروط والمتطلبات", placeholder="اكتب الشروط الأساسية للتقديم...", style=discord.TextStyle.paragraph, required=True)
        self.deadline = TextInput(label="آخر موعد للتقديم", placeholder="مثلاً: يوم الجمعة القادم الساعة 12:00 منتصف الليل", max_length=100, required=True)

        self.add_item(self.roles)
        self.add_item(self.reqs)
        self.add_item(self.deadline)

    def format_msg(self, roles, reqs, deadline):
        embed = discord.Embed(
            title="🌟 فتح باب التقديم لطاقم الإدارة",
            description="يسرنا فتح باب الانضمام لطاقم العمل لكل من يمتلك الشغف والرغبة في التطوير! 💼",
            color=discord.Color.from_rgb(40, 167, 69)
        )
        embed.add_field(name="💼 الرتب المتاحة", value=f"`{roles}`", inline=False)
        embed.add_field(name="📜 أهم الشروط والمتطلبات", value=reqs, inline=False)
        embed.add_field(name="🎫 طريقة التقديم", value=f"توجه إلى روم التكت <#{TICKET_CHANNEL_ID}> لتقديم طلبك.", inline=False)
        embed.add_field(name="⏳ آخر موعد للتقديم", value=f"`{deadline}`", inline=False)
        return embed


# 11. إغلاق التقديم للإدارة
class ApplyCloseModal(BaseAdminModal):
    def __init__(self, panel_message=None, image_bytes: bytes = None, filename: str = None):
        super().__init__(image_bytes=image_bytes, filename=filename, title="🔒 إغلاق باب التقديم للإدارة", formatter=self.format_msg, panel_message=panel_message)
        self.notes = TextInput(label="ملاحظات الإدارة", placeholder="نشكر كل من تقدم وسنراجع جميع الطلبات...", style=discord.TextStyle.paragraph, required=True)
        self.date = TextInput(label="موعد إعلان المقبولين", placeholder="مثلاً: بعد غدٍ بإذن الله", max_length=100, required=True)

        self.add_item(self.notes)
        self.add_item(self.date)

    def format_msg(self, notes, date):
        embed = discord.Embed(
            title="🔒 إغلاق باب التقديم للإدارة",
            description="شاكرين لكم جميعاً مشاركتكم ونتمنى التوفيق لكل من تقدم! 🌟",
            color=discord.Color.from_rgb(108, 117, 125)
        )
        embed.add_field(name="📝 ملاحظات الإدارة", value=notes, inline=False)
        embed.add_field(name="📅 موعد إعلان النتائج", value=f"`{date}`", inline=False)
        return embed


# 12. تكريم عضو متميز
class HonorModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        super().__init__(image_bytes=image_bytes, filename=filename, title="👑 تكريم عضو متميز", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب التكريم والتميز", placeholder="تفاعله المميز وأخلاقه العالية...", style=discord.TextStyle.paragraph, required=True)
        self.reward = TextInput(label="المكافأة المقدمة", placeholder="مثلاً: رتبة خاصة + نقاط في الروليت", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.reward)

    def format_msg(self, reason, reward):
        embed = discord.Embed(
            title="👑 تكريم العضو المتميز",
            description="نشكرك على تفاعلك وأخلاقك العالية ونتمنى لك دوام التألق في مجتمعنا! 💐",
            color=discord.Color.from_rgb(255, 193, 7)
        )
        embed.add_field(name="👤 العضو المكرم", value=self.user.mention, inline=False)
        embed.add_field(name="✨ سبب التميز", value=reason, inline=False)
        embed.add_field(name="🎁 المكافأة والتقدير", value=f"`{reward}`", inline=False)
        if self.user.display_avatar:
            embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed


# 13. إعلان صيانة وتحديث
class MaintenanceModal(BaseAdminModal):
    def __init__(self, panel_message=None, image_bytes: bytes = None, filename: str = None):
        super().__init__(image_bytes=image_bytes, filename=filename, title="🛠️ إعلان صيانة وتحديث", formatter=self.format_msg, panel_message=panel_message)
        self.details = TextInput(label="تفاصيل الصيانة والتطوير", placeholder="تحديث البوتات وإعادة تنظيم الرومات...", style=discord.TextStyle.paragraph, required=True)
        self.time = TextInput(label="الموعد والمدة المتوقعة", placeholder="مثلاً: الليلة من 2:00 إلى 4:00 فجراً", max_length=100, required=True)
        self.affected = TextInput(label="الخدمات أو الرومات المتأثرة", placeholder="مثلاً: روم الألعاب وبوت الروليت", max_length=100, required=True)

        self.add_item(self.details)
        self.add_item(self.time)
        self.add_item(self.affected)

    def format_msg(self, details, time_val, affected):
        embed = discord.Embed(
            title="🛠️ إعلان صيانة وتحديث في السيرفر",
            description="نعتذر عن أي إزعاج مؤقت، ونعمل دائماً لتوفير أفضل تجربة لكم! ⚙️",
            color=discord.Color.from_rgb(23, 162, 184)
        )
        embed.add_field(name="🔧 تفاصيل الصيانة", value=details, inline=False)
        embed.add_field(name="⏰ الموعد والمدة المتوقعة", value=f"`{time_val}`", inline=False)
        embed.add_field(name="⚠️ الرومات / الخدمات المتأثرة", value=f"`{affected}`", inline=False)
        return embed


# 14. تحديث القوانين والأنظمة
class RulesModal(BaseAdminModal):
    def __init__(self, panel_message=None, image_bytes: bytes = None, filename: str = None):
        super().__init__(image_bytes=image_bytes, filename=filename, title="📜 تحديث قوانين السيرفر", formatter=self.format_msg, panel_message=panel_message)
        self.rule = TextInput(label="البند أو القانون المعدل", placeholder="مثلاً: البند رقم 4 (قوانين الإعلانات)", max_length=100, required=True)
        self.content = TextInput(label="نص التعديل الجديد", placeholder="اكتب التعديل الجديد بوضوح...", style=discord.TextStyle.paragraph, required=True)
        self.notes = TextInput(label="ملاحظات وتنبيهات", placeholder="يرجى الالتزام لتجنب العقوبات...", style=discord.TextStyle.paragraph, required=True)

        self.add_item(self.rule)
        self.add_item(self.content)
        self.add_item(self.notes)

    def format_msg(self, rule, content, notes):
        embed = discord.Embed(
            title="📜 تنويه هام: تحديث في قوانين السيرفر",
            description="⚠️ نرجو من الجميع الاطلاع والالتزام التام بالقوانين تجنباً لأي مخالفات.",
            color=discord.Color.from_rgb(111, 66, 193)
        )
        embed.add_field(name="📌 البند المعدل", value=f"`{rule}`", inline=False)
        embed.add_field(name="⚖️ نص التعديل الجديد", value=content, inline=False)
        embed.add_field(name="💡 ملاحظات الإدارة", value=notes, inline=False)
        return embed


# 15. تعميم إداري عام
class AnnouncementModal(BaseAdminModal):
    def __init__(self, panel_message=None, image_bytes: bytes = None, filename: str = None):
        super().__init__(image_bytes=image_bytes, filename=filename, title="📢 تعميم إداري عام", formatter=self.format_msg, panel_message=panel_message)
        self.title_input = TextInput(label="عنوان البيان / التعميم", placeholder="مثلاً: تنبيه بخصوص الفعاليات القادمة", max_length=100, required=True)
        self.text = TextInput(label="نص البيان والتوجيهات", placeholder="اكتب نص التعميم بالتفصيل...", style=discord.TextStyle.paragraph, required=True)
        self.note = TextInput(label="تنبيه أو توجيه خاص", placeholder="مثلاً: يرجى التفاعل والالتزام", max_length=150, required=False)

        self.add_item(self.title_input)
        self.add_item(self.text)
        self.add_item(self.note)

    def format_msg(self, title, text, note):
        embed = discord.Embed(
            title=f"📢 {title}",
            description=f"{text}\n\nشاكرين للجميع حسن التعاون والالتزام الدائم.",
            color=discord.Color.from_rgb(0, 123, 255)
        )
        if note:
            embed.add_field(name="💡 تنبيه خاص", value=note, inline=False)
        return embed


# 16. إنشاء فاتورة جديدة
class InvoiceModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None, image_bytes: bytes = None, filename: str = None):
        self.user = user
        super().__init__(image_bytes=image_bytes, filename=filename, title="🔔 إنشاء فاتورة جديدة", formatter=self.format_msg, panel_message=panel_message)
        self.invoice_num = TextInput(
            label="رقم العملية", 
            placeholder="مثال: #293 أو 293", 
            max_length=50, 
            required=True
        )
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        self.invoice_date = TextInput(
            label="التاريخ", 
            default=today_str, 
            max_length=50, 
            required=True
        )
        self.product_type = TextInput(
            label="نوع المنتج", 
            placeholder="مثال: يوزر رباعي / حساب ديسكورد / نيترو...", 
            max_length=150, 
            required=True
        )
        self.notes = TextInput(
            label="ملاحظات أو السعر (اختياري)", 
            placeholder="أي تفاصيل إضافية أو اتركها فارغة...", 
            max_length=150, 
            required=False
        )

        self.add_item(self.invoice_num)
        self.add_item(self.invoice_date)
        self.add_item(self.product_type)
        self.add_item(self.notes)

    def format_msg(self, invoice_num, invoice_date, product_type, notes=""):
        num_str = invoice_num if invoice_num.startswith("#") else f"#{invoice_num}"

        # تصميم الإمبد المطابق تماماً للصورة المعروضة
        embed = discord.Embed(
            title="🔔 فاتورة جديدة",
            color=discord.Color.from_rgb(235, 10, 10)  # خط جانبي أحمر فاقع مثل الصورة
        )

        # إضافة حقول الفاتورة بنفس التنسيق والايموجيات
        embed.add_field(
            name="🪅 رقم العملية",
            value=f"`{num_str}`",
            inline=False
        )

        embed.add_field(
            name="⏱️ التاريخ",
            value=f"`{invoice_date}`",
            inline=False
        )

        embed.add_field(
            name="👨🏻‍💼 العميل",
            value=f"{self.user.mention}",
            inline=False
        )

        embed.add_field(
            name="📦 نوع المنتج",
            value=f"`{product_type}`",
            inline=False
        )

        if notes:
            embed.add_field(
                name="📝 ملاحظات",
                value=notes,
                inline=False
            )

        # وضع شعار متجر أوهارا في أعلى يمين الفاتورة (Thumbnail)
        logo_path = os.path.join("assets", "store_logo.png")
        if os.path.exists(logo_path):
            self.extra_files = [discord.File(logo_path, filename="store_logo.png")]
            embed.set_thumbnail(url="attachment://store_logo.png")
        elif self.user.guild and self.user.guild.icon:
            embed.set_thumbnail(url=self.user.guild.icon.url)

        # بدون أي منشن خارج الإمبد
        return embed


# ==============================================================================

# تعريف القرارات وتصنيفها

# ==============================================================================



# نوع كل قرار: (الاسم, الوصف, هل يحتاج عضو, هل يحتاج رتبة, فئة المودال)

ADMIN_DECISIONS = {

    "1": ("🎪 إنشاء فعالية", "إعلان فعالية جديدة مع رابط روم التكت وموعدها", False, False, EventModal),

    "2": ("⭐ ترقية عضو (ترقية إدارية)", "إعلان ترقية عضو إداري ومنحه رتبة جديدة", True, True, PromotionModal),

    "3": ("🌟 أدمن الأسبوع / نجم الأسبوع", "إعلان وتكريم أدمن الأسبوع أو نجم الأسبوع", True, True, StarOfWeekModal),

    "4": ("⚠️ تحذير إداري", "تسجيل إنذار وتحذير رسمي لعضو مخالف", True, False, WarningModal),

    "5": ("🔻 سحب رتبة / إعفاء", "إعلان سحب رتبة أو إعفاء من المهام الإدارية", True, True, DemoteModal),

    "6": ("⛔ حظر عضو (BAN)", "إعلان حظر عضو نهائياً أو مؤقتاً من السيرفر", True, False, BanModal),

    "7": ("🛑 طرد عضو (KICK)", "إعلان طرد عضو كإجراء تأديبي", True, False, KickModal),

    "8": ("🔇 إسكات مؤقت (MUTE)", "إعلان كتم وإسكات عضو مخالف", True, False, MuteModal),

    "9": ("📢 اجتماع إداري رسمي", "دعوة الإداريين لاجتماع رسمي هام", False, False, MeetingModal),

    "10": ("📥 فتح التقديم للإدارة", "إعلان فتح باب الانضمام لطاقم الإدارة", False, False, ApplyOpenModal),

    "11": ("🔒 إغلاق التقديم للإدارة", "إعلان انتهاء التقديم وتحديد موعد النتائج", False, False, ApplyCloseModal),

    "12": ("👑 تكريم عضو متميز", "تكريم عضو الشهر أو عضو متفاعل ومبدع", True, False, HonorModal),

    "13": ("🛠️ إعلان صيانة وتحديث", "إعلان صيانة في البوتات أو السيرفر", False, False, MaintenanceModal),

    "14": ("📜 تحديث القوانين والأنظمة", "إشعار الأعضاء بتحديث أو تعديل بند قانوني", False, False, RulesModal),

    "15": ("📢 تعميم إداري عام", "بيان أو توجيه إداري عام لجميع الأعضاء", False, False, AnnouncementModal),

    "16": ("🔔 فاتورة جديدة", "إصدار فاتورة بيع وتوثيق عملية شراء لعميل", True, False, InvoiceModal),

}



# ==============================================================================

# واجهة اختيار العضو والرتبة من قوائم السيرفر التفاعلية (RoleSelect & UserSelect)

# ==============================================================================



class EntitySelectView(View):

    def __init__(self, author_id: int, decision_key: str, need_user: bool = True, need_role: bool = False, panel_message: discord.Message = None, image_bytes: bytes = None, filename: str = None):

        super().__init__(timeout=180)

        self.author_id = author_id

        self.decision_key = decision_key

        self.need_user = need_user

        self.need_role = need_role

        self.panel_message = panel_message

        self.image_bytes = image_bytes

        self.filename = filename

        self.selected_user = None

        self.selected_role = None



        if need_user:

            self.user_select = UserSelect(placeholder="👤 اضغط هنا لاختيار العضو من السيرفر...", row=0)

            self.user_select.callback = self.on_user_select

            self.add_item(self.user_select)



        if need_role:

            self.role_select = RoleSelect(placeholder="🎖️ اضغط هنا لاختيار الرتبة من رتب السيرفر...", row=1)

            self.role_select.callback = self.on_role_select

            self.add_item(self.role_select)



        self.submit_btn = Button(

            label="📝 إكمال البيانات وإرسال الإعلان", 

            style=discord.ButtonStyle.success, 

            row=2

        )

        self.submit_btn.callback = self.on_submit_btn

        self.add_item(self.submit_btn)



        self.back_btn = Button(

            label="🔙 رجوع للقائمة الرئيسية", 

            style=discord.ButtonStyle.secondary, 

            row=2

        )

        self.back_btn.callback = self.on_back_btn

        self.add_item(self.back_btn)



    async def update_view_message(self, interaction: discord.Interaction):

        user_txt = self.selected_user.mention if self.selected_user else "⏳ *لم يتم الاختيار بعد*"

        role_txt = self.selected_role.mention if self.selected_role else "⏳ *لم يتم الاختيار بعد*"

        

        desc = "### ⚙️ خطوة تحديد العضو والرتبة من السيرفر:\n\n"

        if self.need_user:

            desc += f"👤 **العضو المختار:** {user_txt}\n"

        if self.need_role:

            desc += f"🎖️ **الرتبة المختارة:** {role_txt}\n"

        desc += "\nاختر من القوائم المنسدلة أعلاه، ثم اضغط على زر **📝 إكمال البيانات** لتعبئة السبب والتفاصيل."

        

        embed = discord.Embed(

            title=f"📋 تجهيز: {ADMIN_DECISIONS[self.decision_key][0]}",

            description=desc,

            color=discord.Color.dark_purple()

        )

        await interaction.response.edit_message(embed=embed, view=self)



    async def on_user_select(self, interaction: discord.Interaction):

        if not is_admin_member(interaction.user):

            return await interaction.response.send_message("❌ هذا الأمر مخصص للإداريين فقط.", ephemeral=True)

        self.selected_user = self.user_select.values[0]

        await self.update_view_message(interaction)



    async def on_role_select(self, interaction: discord.Interaction):

        if not is_admin_member(interaction.user):

            return await interaction.response.send_message("❌ هذا الأمر مخصص للإداريين فقط.", ephemeral=True)

        self.selected_role = self.role_select.values[0]

        await self.update_view_message(interaction)



    async def on_submit_btn(self, interaction: discord.Interaction):

        if not is_admin_member(interaction.user):

            return await interaction.response.send_message("❌ هذا الأمر مخصص للإداريين فقط.", ephemeral=True)

        

        if self.need_user and not self.selected_user:

            return await interaction.response.send_message("⚠️ يرجى اختيار العضو أولاً من القائمة المنسدلة بالأسفل!", ephemeral=True)

        

        if self.need_role and not self.selected_role:

            return await interaction.response.send_message("⚠️ يرجى اختيار الرتبة أولاً من القائمة المنسدلة بالأسفل!", ephemeral=True)



        target_message = self.panel_message or interaction.message

        name, desc, need_user, need_role, modal_cls = ADMIN_DECISIONS[self.decision_key]



        # إنشاء المودال ديناميكياً بناءً على الاحتياجات مع تمرير الصورة المرفقة إن وُجدت

        if need_user and need_role:

            modal = modal_cls(self.selected_user, self.selected_role, panel_message=target_message, image_bytes=self.image_bytes, filename=self.filename)

        elif need_user:

            modal = modal_cls(self.selected_user, panel_message=target_message, image_bytes=self.image_bytes, filename=self.filename)

        else:

            modal = modal_cls(panel_message=target_message, image_bytes=self.image_bytes, filename=self.filename)



        await interaction.response.send_modal(modal)



    async def on_back_btn(self, interaction: discord.Interaction):

        if not is_admin_member(interaction.user):

            return await interaction.response.send_message("❌ هذا الأمر مخصص للإداريين فقط.", ephemeral=True)

        embed = get_main_admin_embed(interaction.user)

        view = AdminControlView(self.author_id, panel_message=self.panel_message or interaction.message, image_bytes=self.image_bytes, filename=self.filename)

        await interaction.response.edit_message(embed=embed, view=view)



# ==============================================================================

# القائمة المنسدلة الرئيسية للخيارات الـ 15

# ==============================================================================



class AdminSelect(Select):

    def __init__(self, author_id: int, panel_message: discord.Message = None, image_bytes: bytes = None, filename: str = None):

        self.author_id = author_id

        self.panel_message = panel_message

        self.image_bytes = image_bytes

        self.filename = filename

        options = [

            discord.SelectOption(

                label=data[0],

                value=key,

                description=data[1][:100]

            )

            for key, data in ADMIN_DECISIONS.items()

        ]

        super().__init__(

            placeholder="⚙️ اختر نوع القرار أو الإعلان الإداري...",

            min_values=1,

            max_values=1,

            options=options

        )



    async def callback(self, interaction: discord.Interaction):

        if not is_admin_member(interaction.user):

            return await interaction.response.send_message("❌ عذراً، هذا الخيار متاح للإداريين فقط.", ephemeral=True)

        

        choice = self.values[0]

        if choice not in ADMIN_DECISIONS:

            return



        name, desc, need_user, need_role, modal_cls = ADMIN_DECISIONS[choice]

        target_message = self.panel_message or interaction.message



        # إذا كان القرار يتطلب اختيار عضو أو رتبة من السيرفر

        if need_user or need_role:

            select_view = EntitySelectView(

                self.author_id, 

                choice, 

                need_user=need_user, 

                need_role=need_role, 

                panel_message=target_message,

                image_bytes=self.image_bytes,

                filename=self.filename

            )

            embed = discord.Embed(

                title=f"📋 تجهيز: {name}",

                description=(

                    "### ⚙️ خطوة تحديد العضو والرتبة من السيرفر:\n\n"

                    + ("👤 **العضو المختار:** ⏳ *لم يتم الاختيار بعد*\n" if need_user else "")

                    + ("🎖️ **الرتبة المختارة:** ⏳ *لم يتم الاختيار بعد*\n" if need_role else "")

                    + "\nاختر من القوائم المنسدلة بالأسفل، ثم اضغط على زر **📝 إكمال البيانات** لإدخال التفاصيل."

                ),

                color=discord.Color.dark_purple()

            )

            await interaction.response.edit_message(embed=embed, view=select_view)

        else:

            # فتح المودال المباشر للقرارات النصية

            modal = modal_cls(panel_message=target_message, image_bytes=self.image_bytes, filename=self.filename)

            await interaction.response.send_modal(modal)



class AdminControlView(View):

    def __init__(self, author_id: int, panel_message: discord.Message = None, image_bytes: bytes = None, filename: str = None):

        super().__init__(timeout=180)

        self.image_bytes = image_bytes

        self.filename = filename

        self.add_item(AdminSelect(author_id, panel_message=panel_message, image_bytes=image_bytes, filename=filename))



# ==============================================================================

# الـ Cog الأساسي

# ==============================================================================





# ==============================================================================

# نظام أمر _ارسال التفاعلي (سري وخاص 100% عبر الرسائل الخاصة DM)

# ==============================================================================



class SendMessageModal(Modal):

    def __init__(self, bot, target_channel: discord.TextChannel, image_bytes: bytes = None, filename: str = None, dm_msg: discord.Message = None):

        super().__init__(title="📢 إرسال رسالة باسم البوت")

        self.bot = bot

        self.target_channel = target_channel

        self.image_bytes = image_bytes

        self.filename = filename

        self.dm_msg = dm_msg

        self.msg_content = TextInput(

            label="نص الرسالة المراد نشرها",

            placeholder="اكتب رسالتك هنا بالتفصيل وبأي تنسيق تريده...",

            style=discord.TextStyle.paragraph,

            required=True,

            max_length=2000

        )

        self.add_item(self.msg_content)



    async def on_submit(self, interaction: discord.Interaction):

        text = self.msg_content.value.strip()



        # إرسال الرسالة في القناة الأصلية بالسيرفر باسم البوت

        try:

            if self.image_bytes and self.filename:

                file = discord.File(io.BytesIO(self.image_bytes), filename=self.filename)

                await self.target_channel.send(content=text, file=file)

            else:

                await self.target_channel.send(content=text)

        except Exception as e:

            return await interaction.response.send_message(f"❌ حدث خطأ أثناء الإرسال في القناة: {e}", ephemeral=True)



        # تحديث رسالة الخاص للتأكيد

        if self.dm_msg:

            try:

                await self.dm_msg.edit(

                    content=f"✅ **تم نشر رسالتك بنجاح في القناة:** {self.target_channel.mention}",

                    view=None

                )

            except Exception:

                pass



        await interaction.response.send_message("✅ تم نشر الرسالة بنجاح في السيرفر!", ephemeral=True)





class AdminCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot



    @commands.command(name="اداره", aliases=["إدارة", "ادارة", "إداره", "admin", "الاداره", "الإدارة"])

    async def admin_panel(self, ctx):

        """لوحة التحكم الإدارية لاختيار وتجهيز الإعلانات والقرارات الإدارية"""

        if not is_admin_member(ctx.author):

            return await ctx.send("❌ هذا الأمر مخصص فقط لمن يمتلكون صلاحية الإدارة (Administrator).")



        # فحص إذا تم إرفاق صورة مع رسالة _اداره

        image_bytes = None

        filename = None

        if ctx.message.attachments:

            att = ctx.message.attachments[0]

            if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):

                image_bytes = await att.read()

                filename = att.filename



        # حذف رسالة الأمر _اداره تلقائياً للحفاظ على نظافة الروم

        try:

            await ctx.message.delete()

        except Exception:

            pass



        embed = get_main_admin_embed(ctx.author)

        view = AdminControlView(ctx.author.id, image_bytes=image_bytes, filename=filename)

        panel_msg = await ctx.send(embed=embed, view=view)

        view.panel_message = panel_msg

        if view.children and isinstance(view.children[0], AdminSelect):

            view.children[0].panel_message = panel_msg



    @commands.command(name="ارسال", aliases=["إرسال", "نشر", "broadcast", "say"])

    async def send_command(self, ctx):

        """أمر كتابة وإرسال رسالة وصورة باسم البوت (سري وخاص في DM للأدمن فقط)"""

        if not is_admin_member(ctx.author):

            try:

                await ctx.message.delete()

            except Exception:

                pass

            return



        # فحص إذا كان العضو أرفق صورة مع أمر _ارسال

        image_bytes = None

        filename = None

        if ctx.message.attachments:

            att = ctx.message.attachments[0]

            if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):

                image_bytes = await att.read()

                filename = att.filename



        # حذف رسالة الأمر _ارسال فوراً من الشات لكي لا يظهر أي أثر في السيرفر

        try:

            await ctx.message.delete()

        except Exception:

            pass



        target_channel = ctx.channel



        class OpenModalDMView(View):

            def __init__(self, bot, author_id, channel, img_data, fname):

                super().__init__(timeout=180)

                self.bot = bot

                self.author_id = author_id

                self.channel = channel

                self.img_data = img_data

                self.fname = fname

                self.dm_msg = None



            @discord.ui.button(label="📝 اضغط هنا لكتابة الرسالة", style=discord.ButtonStyle.success, emoji="✍️")

            async def open_btn(self, interaction: discord.Interaction, button: Button):

                modal = SendMessageModal(

                    self.bot, 

                    target_channel=self.channel, 

                    image_bytes=self.img_data, 

                    filename=self.fname, 

                    dm_msg=self.dm_msg

                )

                await interaction.response.send_modal(modal)



        view = OpenModalDMView(self.bot, ctx.author.id, target_channel, image_bytes, filename)

        img_status = "🖼️ تم التقاط صورتك المرفقة بنجاح!" if image_bytes else "ℹ️ (بدون صورة مرفقة)"

        dm_text = (

            f"🔒 **طلب إرسال رسالة في سيرفر:** `{ctx.guild.name}`\n"

            f"📌 **القناة المستهدفة للنشر:** {target_channel.mention}\n"

            f"{img_status}\n\n"

            f"اضغط على الزر بالأسفل لكتابة نص الرسالة في النافذة المنبثقة، وسيتم نشرها في القناة باسم البوت:"

        )



        try:

            dm_msg = await ctx.author.send(dm_text, view=view)

            view.dm_msg = dm_msg

        except discord.Forbidden:

            # في حال كان خاص العضو مغلقاً تماماً

            warn = await ctx.send(

                f"⚠️ {ctx.author.mention} لا يمكن للبوت إرسال رسالة في الخاص لك لأن رسائلك الخاصة مغلقة! يرجى فتح الخاص لتتمكن من استخدام الأمر بسرية.",

                delete_after=10

            )



async def setup(bot):

    await bot.add_cog(AdminCog(bot))

