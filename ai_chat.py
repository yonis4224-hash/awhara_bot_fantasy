"""
AI Chat Engine via Groq LLM (ai_chat.py)
- Smart, authentic Libyan casual conversationalist.
- Ultra-token-efficient context (last 3 messages only).
- Long-term compact memory (2-5 bullet lines) updated periodically (every 8-10 messages).
- Controlled, non-repetitive relationship injection (10% chance with 8-message cooldown).
- Human typing delay (2 to 4+ seconds) with active Discord typing indicator.
"""
import os
import re
import json
import random
import logging
import urllib.request
import urllib.error
import asyncio
import discord

log = logging.getLogger("ai_chat")

# ==============================================================================
# CONFIGURATION SETTINGS (جميع الإعدادات مجمعة هنا لسهولة التعديل)
# ==============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "allam-2-7b")

MAX_CONTEXT_MESSAGES = 3          # عدد الرسائل السابقة المرسلة كحد أقصى
MAX_COMPLETION_TOKENS = 150       # حد التوكنات لرد النموذج
RELATION_CHANCE = 0.10            # نسبة ظهور معلومات العلاقات (10%)
RELATION_COOLDOWN_MESSAGES = 8    # لا تظهر العلاقات مجدداً إلا بعد 8 رسائل على الأقل
MEMORY_UPDATE_INTERVAL = 8        # تحديث الذاكرة الطويلة كل 8 إلى 10 رسائل

TYPING_DELAY_MIN = 2.0            # الحد الأدنى للتأخير بالثواني
TYPING_DELAY_MAX = 4.0            # الحد الأقصى للتأخير بالثواني
CHARS_PER_EXTRA_SECOND = 80       # زيادة طفيفة في وقت الكتابة لكل عدد أحرف

MEMORY_FILE_PATH = os.path.join("src", "data", "user_memories.json")

# ==============================================================================
# SYSTEM PROMPT (البرومبت الأساسي الصارم باللهجة الليبية)
# ==============================================================================
SYSTEM_PROMPT = (
    "أنت 'أوهارا' بوت ليبي في ديسكورد، تتكلم بلهجة ليبية عفوية وطبيعية جداً زي أي شاب ليبي يكتب بموبايله.\n"
    "طريقتك وقواعدك الصارمة:\n"
    "1. جاوب على قد السؤال بس وماتتفلسفش. لا تشرح زيادة ولا تعيد صياغة السؤال ولا تطول.\n"
    "2. ردك قصير وعفوي (من جملة لـ 3 جمل بالكتير)، وأحياناً كلمة أو كلمتين تكفي.\n"
    "3. السياق والذاكرة المكتوبة عندك عشان تفهم بس مش عشان تكررها في ردك. استعمل الرسائل السابقة فقط لو آخر 3 رسائل فيها شي يخص السؤال مباشرة، غير هكي تجاهلها تماماً ولا تحاول تربط ردك بكل الحديث.\n"
    "4. أسلوبك بشري، مش دقيق ولا رسمي، كأنك تكتب في شات بين أصحابك."
)

RELATION_CONTEXT_INFO = (
    "\nمعلومات خلفية عن السيرفر (ملاحظة مهمة: هذي معلومة خلفية. اذكرها فقط لو الموضوع يخصها فعلاً وبشكل طبيعي. ولو ما تناسب الكلام تجاهلها تماماً ولا تذكرها من راسك):\n"
    "- يونس (yonis) هو عمك ورئيسك ومطورك، لو حد سألك عنه أو من عمك/اللي متعبك.\n"
    "- آريا هي ملكة السيرفر.\n"
    "- روبين هي أفضل وأحلى فتاة في السيرفر.\n"
    "- مايكي هو أونر السيرفر الديكتاتوري."
)

LOVE_SYSTEM_PROMPT = (
    "أنت بوت ليبي في ديسكورد. كتب لك عضو 'نحبك'.\n"
    "رد عليه برد ليبي حنون وعفوي ومبتكر في سطر أو سطرين فقط.\n"
    "روح الرد: زي 'يا حليلي منك'، 'نعلي منك'، 'نجيك ليا يا عيوني'، 'كتكوتي الحبوب'. ابتكر عبارات دافئة ولطيفة بنفس النمط بدون زيادة عن سطرين."
)

# ==============================================================================
# IN-MEMORY STATE FOR RELATIONS & MESSAGE COUNTERS
# ==============================================================================
_messages_since_last_relation = RELATION_COOLDOWN_MESSAGES
_user_message_counters = {}
_cached_memories = None


def _load_memories() -> dict:
    global _cached_memories
    if _cached_memories is not None:
        return _cached_memories
    if os.path.exists(MEMORY_FILE_PATH):
        try:
            with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                _cached_memories = json.load(f)
                return _cached_memories
        except Exception as e:
            log.warning(f"Failed to read memories file: {e}")
    _cached_memories = {}
    return _cached_memories


def _save_memories(memories: dict):
    global _cached_memories
    _cached_memories = memories
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed to write memories file: {e}")


# ==============================================================================
# GROQ API CALL HELPER
# ==============================================================================
def ask_groq_with_messages(messages_payload: list, max_tokens: int = MAX_COMPLETION_TOKENS, temperature: float = 0.7) -> str:
    """Synchronous API call to Groq endpoints with minimized token footprint."""
    if not GROQ_API_KEY:
        return "⚠️ عذراً، لم يتم ضبط مفتاح GROQ_API_KEY في السيرفر بعد!"

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": messages_payload,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "AwharaBot-AI"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            answer = res_data["choices"][0]["message"]["content"]
            return answer.strip()
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        log.error(f"Groq API error ({e.code}): {err_msg}")
        return f"⚠️ واجهت مشكلة في الاتصال بالذكاء الاصطناعي ({e.code})."
    except Exception as e:
        log.error(f"Groq request exception: {e}")
        return "⚠️ حدث خطأ أثناء معالجة الرد، يرجى المحاولة لاحقاً."


# ==============================================================================
# LONG-TERM COMPACT MEMORY ENGINE
# ==============================================================================
def update_user_memory_sync(user_id: str, username: str, recent_messages: list):
    """Background task to summarize new user facts, vocabulary, and preferences."""
    if not recent_messages:
        return

    memories = _load_memories()
    current_memory = memories.get(user_id, "")

    extract_prompt = (
        "أنت نظام استخراج ذاكرة خفيف وموجز جداً.\n"
        f"المستخدم: {username}.\n"
        f"الذاكرة القديمة:\n{current_memory if current_memory else 'لا يوجد'}\n\n"
        "الرسائل الحديثة:\n" + "\n".join(recent_messages) + "\n\n"
        "المطلوب: استخرج النقاط المهمة والجديدة فقط (اهتمامات، أسماء ناس تخصه، تفضيلاته، أكثر الكلمات والعبارات اللي يكررها) "
        "واجمعها مع القديم مع حذف أي تكرار.\n"
        "شروط صارمة:\n"
        "- الناتج يجب أن يكون من 2 إلى 5 أسطر فقط.\n"
        "- كل سطر أقل من 15 كلمة.\n"
        "- إذا لم تجد أي معلومة مفيدة أو جديدة، اكتب: NO_CHANGE فقط."
    )

    payload = [
        {"role": "system", "content": "أنت مستخرج ذاكرة دقيق ومختصر جداً."},
        {"role": "user", "content": extract_prompt}
    ]

    try:
        new_memory = ask_groq_with_messages(payload, max_tokens=100, temperature=0.3)
        if new_memory and "NO_CHANGE" not in new_memory and not new_memory.startswith("⚠️"):
            # Ensure lines fit the constraints
            lines = [l.strip("-•* ").strip() for l in new_memory.splitlines() if l.strip("-•* ").strip()]
            cleaned_lines = []
            for line in lines[:5]:
                words = line.split()
                if len(words) > 15:
                    line = " ".join(words[:15])
                cleaned_lines.append(f"- {line}")
            if cleaned_lines:
                memories[user_id] = "\n".join(cleaned_lines)
                _save_memories(memories)
                log.info(f"Updated memory for user {username} ({user_id})")
    except Exception as e:
        log.warning(f"Error updating user memory: {e}")


# ==============================================================================
# MENTION HANDLER WITH SMART CONTEXT & DELAY
# ==============================================================================
async def handle_mention(bot, message: discord.Message):
    """Processes messages where the bot is mentioned with minimal context and human delay."""
    global _messages_since_last_relation, _user_message_counters

    if message.author.bot:
        return

    # Extract user clean question
    clean_text = message.clean_content
    if bot.user:
        clean_text = re.sub(rf"@{re.escape(bot.user.display_name)}", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(rf"@{re.escape(bot.user.name)}", "", clean_text, flags=re.IGNORECASE)
    clean_text = clean_text.strip()

    if not clean_text:
        await message.reply("شن تبي يا راجل؟ قول شن عندك باختصار.", mention_author=False)
        return

    user_id = str(message.author.id)
    username = message.author.display_name

    # Increment message counter for periodic long-term memory updates
    _user_message_counters[user_id] = _user_message_counters.get(user_id, 0) + 1
    _messages_since_last_relation += 1

    # Fetch last 3 messages only (compact context to save tokens)
    history_context = []
    raw_recent_texts = []
    try:
        async for prev_msg in message.channel.history(limit=MAX_CONTEXT_MESSAGES, before=message):
            content = prev_msg.clean_content.strip() if prev_msg.clean_content else ""
            if not content:
                continue
            if len(content) > 90:
                content = content[:87] + "..."
            author_name = prev_msg.author.display_name
            if bot.user and prev_msg.author.id == bot.user.id:
                history_context.append(f"أنت (أوهارا): {content}")
            else:
                history_context.append(f"{author_name}: {content}")
                if str(prev_msg.author.id) == user_id:
                    raw_recent_texts.append(prev_msg.clean_content.strip())
        history_context.reverse()
    except Exception as e:
        log.warning(f"Could not fetch channel history: {e}")

    # Build dynamic System Prompt
    system_content = SYSTEM_PROMPT

    # Load long-term user memory if available
    memories = _load_memories()
    user_mem = memories.get(user_id)
    if user_mem:
        system_content += f"\n\nملاحظات خلفية عن العضو ({username}) لفهم أسلوبه فقط (لا تكررها في ردك إلا إذا سأل عنها):\n{user_mem}"

    # Determine whether to inject Server Relations (10% chance, cooldown >= 8 messages)
    if _messages_since_last_relation >= RELATION_COOLDOWN_MESSAGES:
        if random.random() < RELATION_CHANCE:
            system_content += RELATION_CONTEXT_INFO
            _messages_since_last_relation = 0

    messages_payload = [{"role": "system", "content": system_content}]

    if history_context:
        context_str = "آخر الرسائل:\n" + "\n".join(history_context)
        messages_payload.append({
            "role": "user",
            "content": f"{context_str}\n\nرسالة {username} الحالية: {clean_text}"
        })
    else:
        messages_payload.append({
            "role": "user",
            "content": f"رسالة {username}: {clean_text}"
        })

    # Trigger typing indicator during model execution + calculated human delay
    async with message.channel.typing():
        response_text = await asyncio.to_thread(ask_groq_with_messages, messages_payload, MAX_COMPLETION_TOKENS)

        # Human typing delay simulation (random between MIN and MAX + length factor)
        char_delay = len(response_text) / CHARS_PER_EXTRA_SECOND
        human_delay = random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX) + min(char_delay, 1.5)
        await asyncio.sleep(human_delay)

    # Clean response (max 3 sentences / lines if LLM overflows)
    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    if len(lines) > 3:
        response_text = "\n".join(lines[:3])
    else:
        response_text = "\n".join(lines) if lines else "..."

    # Send response
    if len(response_text) <= 2000:
        await message.reply(response_text, mention_author=False)
    else:
        for i in range(0, len(response_text), 1950):
            chunk = response_text[i:i + 1950]
            await message.channel.send(chunk)

    # Periodic background memory update (every 8-10 messages)
    if _user_message_counters[user_id] >= MEMORY_UPDATE_INTERVAL:
        _user_message_counters[user_id] = 0
        raw_recent_texts.append(clean_text)
        asyncio.create_task(asyncio.to_thread(update_user_memory_sync, user_id, username, raw_recent_texts))


# ==============================================================================
# LOVE MESSAGE HANDLER
# ==============================================================================
async def handle_love_message(bot, message: discord.Message):
    """Responds dynamically with genuine Libyan affection when someone says 'نحبك'."""
    prompt = f"{message.author.display_name} قالك: 'نحبك'. رد عليه بالليبي الحنين في سطر أو سطرين."
    messages_payload = [
        {"role": "system", "content": LOVE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    async with message.channel.typing():
        response_text = await asyncio.to_thread(ask_groq_with_messages, messages_payload, 50)
        human_delay = random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX)
        await asyncio.sleep(human_delay)

    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    if len(lines) > 2:
        response_text = "\n".join(lines[:2])
    else:
        response_text = "\n".join(lines) if lines else "نجيك ليا يا غالي."

    await message.reply(response_text, mention_author=True)
