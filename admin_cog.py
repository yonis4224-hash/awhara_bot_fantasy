import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, UserSelect, RoleSelect, Button

# المعرفات الثابتة المعطاة
TICKET_CHANNEL_ID = 1499527310011924540
ADMIN_ROLE_1 = 1137970284402585615
ADMIN_ROLE_2 = 1137970284402585614

ADMIN_ROLES = {ADMIN_ROLE_1, ADMIN_ROLE_2}

def is_admin_member(member: discord.Member) -> bool:
    """التحقق مما إذا كان العضو إدارياً (بصلاحيات ديسكورد أو بالرتب الإدارية)"""
    if not isinstance(member, discord.Member):
        return False
    if (member.guild_permissions.administrator or 
        member.guild_permissions.manage_guild or 
        member.guild_permissions.manage_messages or 
        member.id == member.guild.owner_id):
        return True
    return any(role.id in ADMIN_ROLES for role in member.roles)

def get_main_admin_embed(author: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ لوحة القرارات والإعلانات الإدارية",
        description=(
            "اختر من القائمة المنسدلة بالأسفل نوع الإعلان أو القرار الإداري الذي تريد نشره.\n"
            "إذا كان القرار يتطلب عضواً أو رتبة، **ستظهر لك قائمة فورية برتب وأعضاء السيرفر لاختيارهم بضغطة زر** بدون الحاجة لنسخ أي تاغ! ✨\n\n"
            "**📋 الخيارات المتاحة (15 قرار إداري مرتبة بدون أي تداخل):**\n"
            "• `1` 🎪 إنشاء فعالية • `2` ⭐ ترقية عضو • `3` 🌟 نجم/أدمن الأسبوع\n"
            "• `4` ⚠️ تحذير إداري • `5` 🔻 سحب رتبة • `6` ⛔ حظر عضو (BAN)\n"
            "• `7` 🛑 طرد عضو (KICK) • `8` 🔇 إسكات مؤقت (MUTE) • `9` 📢 اجتماع إداري\n"
            "• `10` 📥 فتح التقديم • `11` 🔒 إغلاق التقديم • `12` 👑 تكريم متميز\n"
            "• `13` 🛠️ صيانة وتحديث • `14` 📜 تحديث قوانين • `15` 📢 تعميم عام"
        ),
        color=discord.Color.dark_purple()
    )
    embed.set_footer(text=f"طلب بواسطة: {author.display_name} • اختر من القائمة للمتابعة", icon_url=author.display_avatar.url)
    return embed

# ==============================================================================
# نماذج الإدخال (Modals)
# ==============================================================================

class BaseAdminModal(Modal):
    def __init__(self, title: str, formatter, panel_message: discord.Message = None):
        super().__init__(title=title[:45])
        self.formatter = formatter
        self.panel_message = panel_message

    async def on_submit(self, interaction: discord.Interaction):
        values = [child.value.strip() for child in self.children if isinstance(child, TextInput)]
        announcement_text = self.formatter(*values)
        
        # إرسال الإعلان في القناة
        await interaction.channel.send(announcement_text)
        
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
    def __init__(self, panel_message=None):
        super().__init__(title="🎪 إنشاء إعلان فعالية", formatter=self.format_msg, panel_message=panel_message)
        self.name = TextInput(label="اسم الفعالية", placeholder="مثلاً: فعالية ألعاب وتحديات", max_length=100, required=True)
        self.desc = TextInput(label="الشرح وتفاصيل الفعالية", placeholder="اكتب نبذة عن الفعالية وكيفية التنافس...", style=discord.TextStyle.paragraph, required=True)
        self.time = TextInput(label="الساعة والموعد", placeholder="مثلاً: اليوم الساعة 9:00 مساءً", max_length=100, required=True)
        self.prize = TextInput(label="الجوائز (اختياري)", placeholder="مثلاً: رتبة مميزة + نقاط روليت", max_length=100, required=False)

        self.add_item(self.name)
        self.add_item(self.desc)
        self.add_item(self.time)
        self.add_item(self.prize)

    def format_msg(self, name, desc, time_val, prize):
        prize_line = f"\n\n🎁 **الجوائز :** {prize}" if prize else ""
        return (
            f"**``` 🎪 إعلان فعالية جديدة 🎪 ```\n\n"
            f"الفعاليه : {name}\n\n"
            f"الشرح : {desc}\n\n"
            f"طريقة لمشاركه : لتقديم تكت مشاركة توجه إلى <#{TICKET_CHANNEL_ID}>\n\n"
            f"ساعه : {time_val}"
            f"{prize_line}\n\n"
            f"نتمنى التوفيق والروح الرياضية لجميع المشاركين! 🔥\n**\n"
            f"@everyone"
        )

# 2. ترقية عضو (ترقية إدارية حقيقية منفصلة تماماً)
class PromotionModal(BaseAdminModal):
    def __init__(self, user: discord.Member, role: discord.Role, panel_message=None):
        self.user = user
        self.role = role
        super().__init__(title="⭐ قرار إداري: ترقية عضو", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الترقية", placeholder="مثال: مجتهد ويستحق الترقية لتفاعله ونشاطه المميز", max_length=150, required=True)
        self.add_item(self.reason)

    def format_msg(self, reason):
        return (
            f"** ``` ⭐ قرار إداري: ترقية عضو ⭐ ``` \n\n"
            f"👤 الاسم :  {self.user.mention} \n\n"
            f"📋 السبب : {reason}\n\n"
            f"⚖️ القرار : ترقية ومنح رتبة إدارية جديدة \n\n"
            f"🎖️ الرتبة الجديدة :  {self.role.mention} \n\n"
            f"بتوفيق لك ومن الأفضل للأفضل بإذن الله، ومبارك لك! 🎉\n\n"
            f"**\n"
            f"@everyone"
        )

# 3. نجم الأسبوع / أدمن الأسبوع (مستقل تماماً)
class StarOfWeekModal(BaseAdminModal):
    def __init__(self, user: discord.Member, role: discord.Role, panel_message=None):
        self.user = user
        self.role = role
        super().__init__(title="🌟 اختيار نجم / أدمن الأسبوع", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الاختيار والتميز", placeholder="مثال: تفاعل استثنائي ومجهود رائع خلال هذا الأسبوع", max_length=150, required=True)
        self.add_item(self.reason)

    def format_msg(self, reason):
        return (
            f"** ``` 🌟 أدمن الأسبوع / نجم الأسبوع 🌟 ``` \n\n"
            f"👤 الاسم :  {self.user.mention} \n\n"
            f"✨ آلسبب : {reason}\n\n"
            f"القرار : اعطاء رتبة أدمن الأسبوع \n\n"
            f"رتبه :  {self.role.mention} \n\n"
            f"بتوفيق لك ومن الافضل اللافضل باذن الله ومبروك! 👏\n\n"
            f"**\n"
            f"@everyone"
        )

# 4. تحذير إداري
class WarningModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None):
        self.user = user
        super().__init__(title="⚠️ تسجيل تحذير إداري", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب التحذير", placeholder="سبب مخالفة القوانين بالتفصيل...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="المدة / درجة الإنذار", placeholder="مثلاً: 24 ساعة / إنذار ثاني / دائم", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, reason, duration):
        return (
            f"** ``` ⚠️ إنذار إداري رسمي ⚠️ ``` \n\n"
            f"👤 الاسم : {self.user.mention}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"⏳ المدة : {duration}\n\n"
            f"القرار : تسجيل إنذار رسمي في السجل التأديبي\n\n"
            f"⚠️ تنبيه : نرجو الالتزام بقوانين السيرفر لتجنب العقوبات الأشد.\n\n"
            f"**\n"
            f"@everyone"
        )

# 5. سحب رتبة / إعفاء إداري
class DemoteModal(BaseAdminModal):
    def __init__(self, user: discord.Member, role: discord.Role, panel_message=None):
        self.user = user
        self.role = role
        super().__init__(title="🔻 سحب رتبة وإعفاء إداري", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="السبب وملاحظات الإعفاء", placeholder="سبب سحب الرتبة أو طلب الإعفاء...", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.reason)

    def format_msg(self, reason):
        return (
            f"** ``` 🔻 قرار إداري: سحب رتبة / إعفاء 🔻 ``` \n\n"
            f"👤 الاسم : {self.user.mention}\n\n"
            f"🎖️ الرتبة المسحوبة : {self.role.mention}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"القرار : سحب الرتبة والإعفاء من المهام الإدارية.\n\n"
            f"شاكرين له جهوده السابقة ونتمنى له التوفيق.\n\n"
            f"**\n"
            f"@everyone"
        )

# 6. حظر عضو (Ban)
class BanModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None):
        self.user = user
        super().__init__(title="⛔ حظر عضو (BAN)", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الحظر", placeholder="السبب المفصل للحظر...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="نوع الحظر / المدة", placeholder="مثلاً: حظر نهائي / 7 أيام", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, reason, duration):
        return (
            f"** ``` ⛔ قرار إداري: حظر عضو (BAN) ⛔ ``` \n\n"
            f"👤 الاسم : {self.user.mention}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"⏳ المدة : {duration}\n\n"
            f"القرار : حظر العضو من السيرفر لمخالفته الصريحة للأنظمة والقوانين.\n\n"
            f"**\n"
            f"@everyone"
        )

# 7. طرد عضو (Kick)
class KickModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None):
        self.user = user
        super().__init__(title="🛑 طرد عضو (KICK)", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الطرد", placeholder="السبب ومخالفة التعليمات...", style=discord.TextStyle.paragraph, required=True)
        self.admin = TextInput(label="الإداري المنفذ", placeholder="اسمك أو منشن الإداري المسؤول", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.admin)

    def format_msg(self, reason, admin):
        return (
            f"** ``` 🛑 قرار إداري: طرد عضو (KICK) 🛑 ``` \n\n"
            f"👤 الاسم : {self.user.mention}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"👮 الإداري المنفذ : {admin}\n\n"
            f"القرار : طرد العضو كإجراء تأديبي.\n\n"
            f"**\n"
            f"@everyone"
        )

# 8. إسكات مؤقت (Mute)
class MuteModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None):
        self.user = user
        super().__init__(title="🔇 إسكات مؤقت (MUTE)", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب الإسكات", placeholder="مثلاً: سبام / ألفاظ غير لائقة...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="مدة الإسكات", placeholder="مثلاً: ساعتين / 24 ساعة", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, reason, duration):
        return (
            f"** ``` 🔇 قرار إداري: إسكات مؤقت (MUTE) 🔇 ``` \n\n"
            f"👤 الاسم : {self.user.mention}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"⏳ المدة : {duration}\n\n"
            f"القرار : كتم العضو ومنعه من الكتابة والتحدث لحين انقضاء المدة.\n\n"
            f"**\n"
            f"@everyone"
        )

# 9. اجتماع إداري
class MeetingModal(BaseAdminModal):
    def __init__(self, panel_message=None):
        super().__init__(title="📢 دعوة اجتماع إداري", formatter=self.format_msg, panel_message=panel_message)
        self.title_input = TextInput(label="موضوع الاجتماع", placeholder="مثلاً: مناقشة خطة الفعاليات وتطوير السيرفر", max_length=100, required=True)
        self.time = TextInput(label="الموعد والوقت", placeholder="مثلاً: غداً الساعة 10:00 مساءً", max_length=100, required=True)
        self.roles = TextInput(label="الرتب المطلوبة للحضور", placeholder="مثلاً: جميع الإداريين / المشرفين", max_length=100, required=True)
        self.topics = TextInput(label="أهم المحاور", placeholder="اكتب المحاور أو جدول الأعمال باختصار...", style=discord.TextStyle.paragraph, required=True)

        self.add_item(self.title_input)
        self.add_item(self.time)
        self.add_item(self.roles)
        self.add_item(self.topics)

    def format_msg(self, title, time_val, roles, topics):
        return (
            f"** ``` 📢 إعلان: اجتماع إداري هام 📢 ``` \n\n"
            f"📌 الموضوع : {title}\n\n"
            f"⏰ الموعد : {time_val}\n\n"
            f"👥 الرتب المطلوبة : {roles}\n\n"
            f"📝 أهم المحاور :\n{topics}\n\n"
            f"⚠️ تنبيه : الحضور إجباري ومن يتعذر عليه إبلاغ المسؤول مسبقاً.\n\n"
            f"**\n"
            f"@everyone"
        )

# 10. فتح التقديم للإدارة
class ApplyOpenModal(BaseAdminModal):
    def __init__(self, panel_message=None):
        super().__init__(title="🌟 فتح باب التقديم للإدارة", formatter=self.format_msg, panel_message=panel_message)
        self.roles = TextInput(label="الرتب والأقسام المتاحة", placeholder="مثلاً: مشرف شات / مشرف فعاليات", max_length=100, required=True)
        self.reqs = TextInput(label="الشروط المطلوبة", placeholder="التفاعل، اللباقة، الخبرة السابقة...", style=discord.TextStyle.paragraph, required=True)
        self.deadline = TextInput(label="آخر موعد للتقديم", placeholder="مثلاً: يوم الجمعة القادم الساعة 12 منتصف الليل", max_length=100, required=True)

        self.add_item(self.roles)
        self.add_item(self.reqs)
        self.add_item(self.deadline)

    def format_msg(self, roles, reqs, deadline):
        return (
            f"** ``` 🌟 فتح باب التقديم لطاقم الإدارة 🌟 ``` \n\n"
            f"💼 الرتب المتاحة : {roles}\n\n"
            f"📜 أهم الشروط :\n{reqs}\n\n"
            f"🎫 طريقة التقديم : توجه إلى روم التكت <#{TICKET_CHANNEL_ID}> لتقديم طلبك.\n\n"
            f"⏳ آخر موعد للتقديم : {deadline}\n\n"
            f"نتمنى التوفيق للجميع ومن يرى في نفسه الكفاءة أهلاً به في طاقمنا! 🚀\n\n"
            f"**\n"
            f"@everyone"
        )

# 11. إغلاق التقديم للإدارة
class ApplyCloseModal(BaseAdminModal):
    def __init__(self, panel_message=None):
        super().__init__(title="🔒 إغلاق باب التقديم للإدارة", formatter=self.format_msg, panel_message=panel_message)
        self.notes = TextInput(label="ملاحظات الإدارة", placeholder="نشكر كل من تقدم وسنراجع جميع الطلبات...", style=discord.TextStyle.paragraph, required=True)
        self.date = TextInput(label="موعد إعلان المقبولين", placeholder="مثلاً: بعد غدٍ بإذن الله", max_length=100, required=True)

        self.add_item(self.notes)
        self.add_item(self.date)

    def format_msg(self, notes, date):
        return (
            f"** ``` 🔒 إغلاق باب التقديم للإدارة 🔒 ``` \n\n"
            f"تم إغلاق باب التقديم رسمياً لطاقم الإدارة.\n\n"
            f"📝 ملاحظات : {notes}\n\n"
            f"📅 موعد إعلان النتائج : {date}\n\n"
            f"شاكرين لكم جميعاً ونتمنى التوفيق لكل من تقدم! 🌟\n\n"
            f"**\n"
            f"@everyone"
        )

# 12. تكريم عضو متميز
class HonorModal(BaseAdminModal):
    def __init__(self, user: discord.Member, panel_message=None):
        self.user = user
        super().__init__(title="👑 تكريم عضو متميز", formatter=self.format_msg, panel_message=panel_message)
        self.reason = TextInput(label="سبب التكريم والتميز", placeholder="تفاعله المميز وأخلاقه العالية...", style=discord.TextStyle.paragraph, required=True)
        self.reward = TextInput(label="المكافأة المقدمة", placeholder="مثلاً: رتبة خاصة + نقاط في الروليت", max_length=100, required=True)

        self.add_item(self.reason)
        self.add_item(self.reward)

    def format_msg(self, reason, reward):
        return (
            f"** ``` 👑 تكريم العضو المتميز 👑 ``` \n\n"
            f"👤 الاسم : {self.user.mention}\n\n"
            f"✨ سبب التميز : {reason}\n\n"
            f"🎁 المكافأة : {reward}\n\n"
            f"نشكرك على تفاعلك وأخلاقك العالية ونتمنى لك دوام التألق في مجتمعنا! 💐\n\n"
            f"**\n"
            f"@everyone"
        )

# 13. إعلان صيانة وتحديث
class MaintenanceModal(BaseAdminModal):
    def __init__(self, panel_message=None):
        super().__init__(title="🛠️ إعلان صيانة وتحديث", formatter=self.format_msg, panel_message=panel_message)
        self.details = TextInput(label="تفاصيل الصيانة والتطوير", placeholder="تحديث البوتات وإعادة تنظيم الرومات...", style=discord.TextStyle.paragraph, required=True)
        self.time = TextInput(label="الموعد والمدة المتوقعة", placeholder="مثلاً: الليلة من 2:00 إلى 4:00 فجراً", max_length=100, required=True)
        self.affected = TextInput(label="الخدمات أو الرومات المتأثرة", placeholder="مثلاً: روم الألعاب وبوت الروليت", max_length=100, required=True)

        self.add_item(self.details)
        self.add_item(self.time)
        self.add_item(self.affected)

    def format_msg(self, details, time_val, affected):
        return (
            f"** ``` 🛠️ إعلان صيانة وتحديث في السيرفر 🛠️ ``` \n\n"
            f"🔧 تفاصيل الصيانة : {details}\n\n"
            f"⏰ الموعد والمدة : {time_val}\n\n"
            f"⚠️ الخدمات المتأثرة : {affected}\n\n"
            f"نعتذر عن أي إزعاج مؤقت، ونعمل دائماً لتوفير أفضل تجربة لكم! ⚙️\n\n"
            f"**\n"
            f"@everyone"
        )

# 14. تحديث القوانين
class RulesModal(BaseAdminModal):
    def __init__(self, panel_message=None):
        super().__init__(title="📜 تحديث قوانين السيرفر", formatter=self.format_msg, panel_message=panel_message)
        self.rule = TextInput(label="البند أو القانون المعدل", placeholder="مثلاً: البند رقم 4 (قوانين الإعلانات)", max_length=100, required=True)
        self.content = TextInput(label="نص التعديل الجديد", placeholder="اكتب التعديل الجديد بوضوح...", style=discord.TextStyle.paragraph, required=True)
        self.notes = TextInput(label="ملاحظات وتنبيهات", placeholder="يرجى الالتزام لتجنب العقوبات...", style=discord.TextStyle.paragraph, required=True)

        self.add_item(self.rule)
        self.add_item(self.content)
        self.add_item(self.notes)

    def format_msg(self, rule, content, notes):
        return (
            f"** ``` 📜 تنويه هام: تحديث في قوانين السيرفر 📜 ``` \n\n"
            f"📌 البند : {rule}\n\n"
            f"⚖️ نص التعديل الجديد :\n{content}\n\n"
            f"💡 ملاحظات الإدارة : {notes}\n\n"
            f"⚠️ نرجو من الجميع الاطلاع والالتزام التام بالقوانين تجنباً لأي مخالفة.\n\n"
            f"**\n"
            f"@everyone"
        )

# 15. تعميم إداري عام
class AnnouncementModal(BaseAdminModal):
    def __init__(self, panel_message=None):
        super().__init__(title="📢 تعميم إداري عام", formatter=self.format_msg, panel_message=panel_message)
        self.title_input = TextInput(label="عنوان البيان / التعميم", placeholder="مثلاً: تنبيه بخصوص الفعاليات القادمة", max_length=100, required=True)
        self.text = TextInput(label="نص البيان والتوجيهات", placeholder="اكتب نص التعميم بالتفصيل...", style=discord.TextStyle.paragraph, required=True)
        self.note = TextInput(label="تنبيه أو توجيه خاص", placeholder="مثلاً: يرجى التفاعل والالتزام", max_length=150, required=False)

        self.add_item(self.title_input)
        self.add_item(self.text)
        self.add_item(self.note)

    def format_msg(self, title, text, note):
        note_line = f"\n\n⚠️ توجيه خاص : {note}" if note else ""
        return (
            f"** ``` 📢 تعميم إداري عام 📢 ``` \n\n"
            f"📌 العنوان : {title}\n\n"
            f"📝 البيان :\n{text}"
            f"{note_line}\n\n"
            f"شاكرين للجميع حسن التعاون والالتزام الدائم.\n\n"
            f"**\n"
            f"@everyone"
        )

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
}

# ==============================================================================
# واجهة اختيار العضو والرتبة من قوائم السيرفر التفاعلية (RoleSelect & UserSelect)
# ==============================================================================

class EntitySelectView(View):
    def __init__(self, author_id: int, decision_key: str, need_user: bool = True, need_role: bool = False, panel_message: discord.Message = None):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.decision_key = decision_key
        self.need_user = need_user
        self.need_role = need_role
        self.panel_message = panel_message
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

        # إنشاء المودال ديناميكياً بناءً على الاحتياجات
        if need_user and need_role:
            modal = modal_cls(self.selected_user, self.selected_role, panel_message=target_message)
        elif need_user:
            modal = modal_cls(self.selected_user, panel_message=target_message)
        else:
            modal = modal_cls(panel_message=target_message)

        await interaction.response.send_modal(modal)

    async def on_back_btn(self, interaction: discord.Interaction):
        if not is_admin_member(interaction.user):
            return await interaction.response.send_message("❌ هذا الأمر مخصص للإداريين فقط.", ephemeral=True)
        embed = get_main_admin_embed(interaction.user)
        view = AdminControlView(self.author_id, panel_message=self.panel_message or interaction.message)
        await interaction.response.edit_message(embed=embed, view=view)

# ==============================================================================
# القائمة المنسدلة الرئيسية للخيارات الـ 15
# ==============================================================================

class AdminSelect(Select):
    def __init__(self, author_id: int, panel_message: discord.Message = None):
        self.author_id = author_id
        self.panel_message = panel_message
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
                panel_message=target_message
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
            modal = modal_cls(panel_message=target_message)
            await interaction.response.send_modal(modal)

class AdminControlView(View):
    def __init__(self, author_id: int, panel_message: discord.Message = None):
        super().__init__(timeout=180)
        self.add_item(AdminSelect(author_id, panel_message=panel_message))

# ==============================================================================
# الـ Cog الأساسي
# ==============================================================================

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="اداره", aliases=["إدارة", "ادارة", "إداره", "admin", "الاداره", "الإدارة"])
    async def admin_panel(self, ctx):
        """لوحة التحكم الإدارية لاختيار وتجهيز الإعلانات والقرارات الإدارية"""
        if not is_admin_member(ctx.author):
            return await ctx.send("❌ هذا الأمر مخصص لطاقم الإدارة فقط.")

        # حذف رسالة الأمر _اداره تلقائياً للحفاظ على نظافة الروم
        try:
            await ctx.message.delete()
        except Exception:
            pass

        embed = get_main_admin_embed(ctx.author)
        view = AdminControlView(ctx.author.id)
        panel_msg = await ctx.send(embed=embed, view=view)
        # حفظ رسالة اللوحة في الـ View للتمكن من حذفها بعد النشر
        view.panel_message = panel_msg
        if view.children and isinstance(view.children[0], AdminSelect):
            view.children[0].panel_message = panel_msg

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
