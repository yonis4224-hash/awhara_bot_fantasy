import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput

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

# ==============================================================================
# نماذج الإدخال (Modals) لكل قرار إداري من الـ 15
# ==============================================================================

class BaseAdminModal(Modal):
    def __init__(self, title: str, formatter):
        super().__init__(title=title[:45])
        self.formatter = formatter

    async def on_submit(self, interaction: discord.Interaction):
        values = [child.value.strip() for child in self.children if isinstance(child, TextInput)]
        announcement_text = self.formatter(*values)
        
        await interaction.channel.send(announcement_text)
        await interaction.response.send_message("✅ تم تجهيز ونشر الإعلان الإداري بنجاح!", ephemeral=True)

# 1. إنشاء فعالية
class EventModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="🎪 إنشاء إعلان فعالية", formatter=self.format_msg)
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
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>\n"
            f"@everyone"
        )

# 2. ترقية إدارية (ادمن الاسبوع)
class PromotionModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="⭐ ترقية إدارية / أدمن الأسبوع", formatter=self.format_msg)
        self.user = TextInput(label="الاسم / يوزر الشخص", placeholder="مثال: فارس @9f1_g أو منشن الشخص", max_length=100, required=True)
        self.reason = TextInput(label="السبب", placeholder="مثال: مجتهد ويستحق لرتبه", max_length=150, required=True)
        self.role = TextInput(label="الرتبة المعطاة", placeholder="مثال: <@&1515446398718447696> أو اسم الرتبة", max_length=100, required=True)

        self.add_item(self.user)
        self.add_item(self.reason)
        self.add_item(self.role)

    def format_msg(self, user, reason, role):
        return (
            f"** ``` ادمن الاسبوع ``` \n\n"
            f"الاسم :  {user} \n\n"
            f"آلسبب : {reason}\n\n"
            f"القرار : اعطاء رتبه \n\n"
            f"رتبه :  {role} \n\n"
            f"بتوفيق لك ومن الافضل اللافضل باذن الله ومبروك\n\n"
            f"**\n"
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}> \n"
            f"@7_sa\n"
            f"@everyone"
        )

# 3. تحذير إداري
class WarningModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="⚠️ تسجيل تحذير إداري", formatter=self.format_msg)
        self.user = TextInput(label="اسم / يوزر العضو", placeholder="اسم أو منشن العضو المخالف", max_length=100, required=True)
        self.reason = TextInput(label="سبب التحذير", placeholder="سبب مخالفة القوانين بالتفصيل...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="المدة / درجة الإنذار", placeholder="مثلاً: 24 ساعة / إنذار ثاني / دائم", max_length=100, required=True)

        self.add_item(self.user)
        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, user, reason, duration):
        return (
            f"** ``` ⚠️ إنذار إداري رسمي ⚠️ ``` \n\n"
            f"👤 الاسم : {user}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"⏳ المدة : {duration}\n\n"
            f"القرار : تسجيل إنذار رسمي في السجل التأديبي\n\n"
            f"⚠️ تنبيه : نرجو الالتزام بقوانين السيرفر لتجنب العقوبات الأشد.\n\n"
            f"**\n"
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>"
        )

# 4. سحب رتبة / إعفاء إداري
class DemoteModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="🔻 سحب رتبة وإعفاء إداري", formatter=self.format_msg)
        self.user = TextInput(label="اسم / يوزر الشخص", placeholder="الاسم أو المنشن", max_length=100, required=True)
        self.role = TextInput(label="الرتبة المسحوبة", placeholder="مثلاً: مشرف / إدارة فعاليات", max_length=100, required=True)
        self.reason = TextInput(label="السبب", placeholder="سبب سحب الرتبة أو طلب الإعفاء...", style=discord.TextStyle.paragraph, required=True)

        self.add_item(self.user)
        self.add_item(self.role)
        self.add_item(self.reason)

    def format_msg(self, user, role, reason):
        return (
            f"** ``` 🔻 قرار إداري: سحب رتبة / إعفاء 🔻 ``` \n\n"
            f"👤 الاسم : {user}\n\n"
            f"🎖️ الرتبة المسحوبة : {role}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"القرار : سحب الرتبة والإعفاء من المهام الإدارية.\n\n"
            f"شاكرين له جهوده السابقة ونتمنى له التوفيق.\n\n"
            f"**\n"
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>"
        )

# 5. حظر عضو (Ban)
class BanModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="⛔ حظر عضو (BAN)", formatter=self.format_msg)
        self.user = TextInput(label="اسم / يوزر العضو", placeholder="اسم أو آيدي أو منشن العضو", max_length=100, required=True)
        self.reason = TextInput(label="سبب الحظر", placeholder="السبب المفصل للحظر...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="نوع الحظر / المدة", placeholder="مثلاً: حظر نهائي / 7 أيام", max_length=100, required=True)

        self.add_item(self.user)
        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, user, reason, duration):
        return (
            f"** ``` ⛔ قرار إداري: حظر عضو (BAN) ⛔ ``` \n\n"
            f"👤 الاسم : {user}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"⏳ المدة : {duration}\n\n"
            f"القرار : حظر العضو من السيرفر لمخالفته الصريحة للأنظمة والقوانين.\n\n"
            f"**\n"
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>"
        )

# 6. طرد عضو (Kick)
class KickModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="🛑 طرد عضو (KICK)", formatter=self.format_msg)
        self.user = TextInput(label="اسم / يوزر العضو", placeholder="الاسم أو المنشن", max_length=100, required=True)
        self.reason = TextInput(label="سبب الطرد", placeholder="السبب ومخالفة التعليمات...", style=discord.TextStyle.paragraph, required=True)
        self.admin = TextInput(label="الإداري المنفذ", placeholder="اسمك أو منشن الإداري المسؤول", max_length=100, required=True)

        self.add_item(self.user)
        self.add_item(self.reason)
        self.add_item(self.admin)

    def format_msg(self, user, reason, admin):
        return (
            f"** ``` 🛑 قرار إداري: طرد عضو (KICK) 🛑 ``` \n\n"
            f"👤 الاسم : {user}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"👮 الإداري المنفذ : {admin}\n\n"
            f"القرار : طرد العضو كإجراء تأديبي.\n\n"
            f"**\n"
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>"
        )

# 7. إسكات مؤقت (Mute)
class MuteModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="🔇 إسكات مؤقت (MUTE)", formatter=self.format_msg)
        self.user = TextInput(label="اسم / يوزر العضو", placeholder="الاسم أو المنشن", max_length=100, required=True)
        self.reason = TextInput(label="سبب الإسكات", placeholder="مثلاً: سبام / ألفاظ غير لائقة...", style=discord.TextStyle.paragraph, required=True)
        self.duration = TextInput(label="مدة الإسكات", placeholder="مثلاً: ساعتين / 24 ساعة", max_length=100, required=True)

        self.add_item(self.user)
        self.add_item(self.reason)
        self.add_item(self.duration)

    def format_msg(self, user, reason, duration):
        return (
            f"** ``` 🔇 قرار إداري: إسكات مؤقت (MUTE) 🔇 ``` \n\n"
            f"👤 الاسم : {user}\n\n"
            f"📋 السبب : {reason}\n\n"
            f"⏳ المدة : {duration}\n\n"
            f"القرار : كتم العضو ومنعه من الكتابة والتحدث لحين انقضاء المدة.\n\n"
            f"**\n"
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>"
        )

# 8. اجتماع إداري
class MeetingModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="📢 دعوة اجتماع إداري", formatter=self.format_msg)
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
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>"
        )

# 9. فتح التقديم للإدارة
class ApplyOpenModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="🌟 فتح باب التقديم للإدارة", formatter=self.format_msg)
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

# 10. إغلاق التقديم للإدارة
class ApplyCloseModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="🔒 إغلاق باب التقديم للإدارة", formatter=self.format_msg)
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

# 11. تكريم عضو متميز
class HonorModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="👑 تكريم عضو متميز", formatter=self.format_msg)
        self.user = TextInput(label="اسم / يوزر العضو", placeholder="اسم أو منشن العضو المتميز", max_length=100, required=True)
        self.reason = TextInput(label="سبب التكريم والتميز", placeholder="تفاعله المميز وأخلاقه العالية...", style=discord.TextStyle.paragraph, required=True)
        self.reward = TextInput(label="المكافأة المقدمة", placeholder="مثلاً: رتبة خاصة + نقاط في الروليت", max_length=100, required=True)

        self.add_item(self.user)
        self.add_item(self.reason)
        self.add_item(self.reward)

    def format_msg(self, user, reason, reward):
        return (
            f"** ``` 👑 تكريم العضو المتميز 👑 ``` \n\n"
            f"👤 الاسم : {user}\n\n"
            f"✨ سبب التميز : {reason}\n\n"
            f"🎁 المكافأة : {reward}\n\n"
            f"نشكرك على تفاعلك وأخلاقك العالية ونتمنى لك دوام التألق في مجتمعنا! 💐\n\n"
            f"**\n"
            f"@everyone"
        )

# 12. إعلان صيانة وتحديث
class MaintenanceModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="🛠️ إعلان صيانة وتحديث", formatter=self.format_msg)
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

# 13. تحديث القوانين
class RulesModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="📜 تحديث قوانين السيرفر", formatter=self.format_msg)
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

# 14. مسابقة فورية وسريعة
class ContestModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="⚡ مسابقة فورية وسريعة", formatter=self.format_msg)
        self.contest = TextInput(label="اسم وموضوع المسابقة", placeholder="مثلاً: أسرع إجابة عن سؤال ثقافي", max_length=100, required=True)
        self.reqs = TextInput(label="المطلوب للمشاركة", placeholder="اكتب السؤال أو الشروط هنا...", style=discord.TextStyle.paragraph, required=True)
        self.prize = TextInput(label="الجائزة", placeholder="مثلاً: نيترو كلاسيك / رتبة VIP", max_length=100, required=True)
        self.deadline = TextInput(label="وقت المسابقة أو الانتهاء", placeholder="مثلاً: خلال 15 دقيقة من الآن", max_length=100, required=True)

        self.add_item(self.contest)
        self.add_item(self.reqs)
        self.add_item(self.prize)
        self.add_item(self.deadline)

    def format_msg(self, contest, reqs, prize, deadline):
        return (
            f"** ``` ⚡ مسابقة فورية وسريعة ⚡ ``` \n\n"
            f"🎉 المسابقة : {contest}\n\n"
            f"🎯 المطلوب للمشاركة :\n{reqs}\n\n"
            f"🎁 الجائزة : {prize}\n\n"
            f"⏳ وقت الانتهاء : {deadline}\n\n"
            f"للمشاركة والمطالبة بالجائزة توجه إلى <#{TICKET_CHANNEL_ID}> أو تفاعل هنا فوراً! 🔥\n\n"
            f"**\n"
            f"@everyone"
        )

# 15. تعميم إداري عام
class AnnouncementModal(BaseAdminModal):
    def __init__(self):
        super().__init__(title="📢 تعميم إداري عام", formatter=self.format_msg)
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
            f"<@&{ADMIN_ROLE_1}>\n"
            f"<@&{ADMIN_ROLE_2}>\n"
            f"@everyone"
        )

# ==============================================================================
# القائمة المنسدلة للخيارات الـ 15
# ==============================================================================

ADMIN_DECISIONS = {
    "1": ("🎪 إنشاء فعالية", "إعلان فعالية جديدة مع رابط روم التكت وموعدها", EventModal),
    "2": ("⭐ ترقية إدارية (ادمن الاسبوع)", "إعلان ترقية إدارية أو اختيار أدمن الأسبوع", PromotionModal),
    "3": ("⚠️ تحذير إداري", "تسجيل إنذار وتحذير رسمي لعضو مخالف", WarningModal),
    "4": ("🔻 سحب رتبة / إعفاء", "إعلان سحب رتبة أو إعفاء من المهام الإدارية", DemoteModal),
    "5": ("⛔ حظر عضو (BAN)", "إعلان حظر عضو نهائياً أو مؤقتاً من السيرفر", BanModal),
    "6": ("🛑 طرد عضو (KICK)", "إعلان طرد عضو كإجراء تأديبي", KickModal),
    "7": ("🔇 إسكات مؤقت (MUTE)", "إعلان كتم وإسكات عضو مخالف", MuteModal),
    "8": ("📢 اجتماع إداري رسمي", "دعوة الإداريين لاجتماع رسمي هام", MeetingModal),
    "9": ("🌟 فتح التقديم للإدارة", "إعلان فتح باب الانضمام لطاقم الإدارة", ApplyOpenModal),
    "10": ("🔒 إغلاق التقديم للإدارة", "إعلان انتهاء التقديم وتحديد موعد النتائج", ApplyCloseModal),
    "11": ("👑 تكريم عضو متميز", "تكريم عضو الشهر أو عضو متفاعل ومبدع", HonorModal),
    "12": ("🛠️ إعلان صيانة وتحديث", "إعلان صيانة في البوتات أو السيرفر", MaintenanceModal),
    "13": ("📜 تحديث القوانين والأنظمة", "إشعار الأعضاء بتحديث أو تعديل بند قانوني", RulesModal),
    "14": ("⚡ مسابقة فورية وسريعة", "إعلان مسابقة سريعة للأعضاء المتواجدين", ContestModal),
    "15": ("📢 تعميم إداري عام", "بيان أو توجيه إداري عام لجميع الأعضاء", AnnouncementModal),
}

class AdminSelect(Select):
    def __init__(self, author_id: int):
        self.author_id = author_id
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
        if choice in ADMIN_DECISIONS:
            modal_cls = ADMIN_DECISIONS[choice][2]
            modal = modal_cls()
            await interaction.response.send_modal(modal)

class AdminControlView(View):
    def __init__(self, author_id: int):
        super().__init__(timeout=180)
        self.add_item(AdminSelect(author_id))

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

        embed = discord.Embed(
            title="🛡️ لوحة القرارات والإعلانات الإدارية",
            description=(
                "اختر من القائمة المنسدلة بالأسفل نوع الإعلان أو القرار الإداري الذي تريد نشره.\n"
                "ستفتح لك نافذة لإدخال البيانات، وبمجرد الضغط على **إرسال** سيقوم البوت بنشر الرسالة منسقة تلقائياً! ✨\n\n"
                "**📋 الخيارات المتاحة (15 قرار إداري):**\n"
                "• `1` 🎪 إنشاء فعالية • `2` ⭐ ترقية إدارية (ادمن الاسبوع) • `3` ⚠️ تحذير إداري\n"
                "• `4` 🔻 سحب رتبة • `5` ⛔ حظر عضو (BAN) • `6` 🛑 طرد عضو (KICK)\n"
                "• `7` 🔇 إسكات مؤقت (MUTE) • `8` 📢 اجتماع إداري • `9` 🌟 فتح التقديم\n"
                "• `10` 🔒 إغلاق التقديم • `11` 👑 تكريم متميز • `12` 🛠️ صيانة وتحديث\n"
                "• `13` 📜 تحديث قوانين • `14` ⚡ مسابقة فورية • `15` 📢 تعميم عام"
            ),
            color=discord.Color.dark_purple()
        )
        embed.set_footer(text=f"طلب بواسطة: {ctx.author.display_name} • اختر من القائمة لتعبئة البيانات", icon_url=ctx.author.display_avatar.url)

        view = AdminControlView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
