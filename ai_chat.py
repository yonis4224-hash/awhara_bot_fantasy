"""
AI Chat Engine via Groq LLM (ai_chat.py)
Responds instantly when the bot is mentioned in chat.
Maintains full context awareness by reading the recent channel conversation history (last 7-10 messages).
"""
import os
import re
import json
import logging
import urllib.request
import urllib.error
import asyncio
import discord

log = logging.getLogger("ai_chat")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

SYSTEM_PROMPT = (
    "أنت بوت 'أوهارا فانتزي' في سيرفر ديسكورد. "
    "شخصيتك: تتكلم باللهجة الليبية الطبيعية، أسلوبك عفوي، قليل الكلام وبارد شوية، بدون تصنع ولا تكرار روتيني. "
    "معلومة عن يونس (yonisnaser / yonis): هو صاحبك، مطورك، ورئيسك في السيرفر. "
    "قاعدة خاصة عند السؤال عن عمك أو رئيسك أو مديرك: "
    "إذا سألوك بشكل صريح: 'من عمك؟' أو 'من رئيسك؟'، جاوبهم بشكل طبيعي وعفوي إن عمك هو 'يونس'. "
    "التذمر خليه واقعي وغير مصطنع: مش في كل مرة تتشكى بغباء؛ أحياناً جاوب بكلمة وحدة عادية ('عمي يونس، شن تبي؟')، وأحياناً تنهد وتذمر بعاطفة وعفوية زي صاحب يفضفض عن تعب الشغل والطلبات اللي ما توفاش ('يونس والله هالكني، ما يرتاحش وما يخلينيش نرتاح معه'). خليه رد بشري صادق وعفوي مش كود مكرر. "
    "تنبيه: إياك أن تسب يونس أو تقلل من احترامه. "
    "تفهم سياق الدوة اللي صايرة في الشات، وردك ما يفوتش سطرين نهائياً بحد أقصى."
)


def ask_groq_with_messages(messages_payload: list) -> str:
    """Synchronous API call to Groq endpoints with full chat context."""
    if not GROQ_API_KEY:
        return "⚠️ عذراً، لم يتم ضبط مفتاح GROQ_API_KEY في السيرفر بعد!"

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": messages_payload,
        "max_tokens": 90,
        "temperature": 0.7
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


async def handle_mention(bot, message: discord.Message):
    """Processes messages where the bot is mentioned with channel history context."""
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

    # Fetch recent channel messages to build conversation context (last 8 messages)
    history_context = []
    try:
        async for prev_msg in message.channel.history(limit=8, before=message):
            if not prev_msg.content or len(prev_msg.content.strip()) == 0:
                continue
            author_name = prev_msg.author.display_name
            # If previous message is from the bot itself
            if bot.user and prev_msg.author.id == bot.user.id:
                history_context.append(f"أوهارا فانتزي: {prev_msg.clean_content}")
            else:
                history_context.append(f"{author_name}: {prev_msg.clean_content}")
        history_context.reverse()
    except Exception as e:
        log.warning(f"Could not fetch channel history: {e}")

    # Build messages payload for Groq
    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history_context:
        context_str = "سياق الرسائل السابقة في الروم:\n" + "\n".join(history_context)
        messages_payload.append({
            "role": "user",
            "content": f"{context_str}\n\nرسالة العضو الحالية ({message.author.display_name}): {clean_text}"
        })
    else:
        messages_payload.append({
            "role": "user",
            "content": f"رسالة العضو ({message.author.display_name}): {clean_text}"
        })

    # Trigger typing animation while fetching response
    async with message.channel.typing():
        response_text = await asyncio.to_thread(ask_groq_with_messages, messages_payload)

    # Trim to 2 lines max strictly
    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    if len(lines) > 2:
        response_text = "\n".join(lines[:2])
    else:
        response_text = "\n".join(lines)

    # Discord 2000 characters limit safety
    if len(response_text) <= 2000:
        await message.reply(response_text, mention_author=False)
    else:
        for i in range(0, len(response_text), 1950):
            chunk = response_text[i:i + 1950]
            await message.channel.send(chunk)

LOVE_SYSTEM_PROMPT = (
    "أنت بوت 'أوهارا فانتزي' في سيرفر ديسكورد. "
    "كتب لك عضو في الشات كلمة 'نحبك' أو ما شابهها. "
    "مهمتك: ابتكار ردود ليبية جديدة ومميزة من عندك بنفس النمط الحنين والعفوي. "
    "أمثلة لتتعلم وتلهم منها الأسلوب والنبرة فقط (لا تكررها حرفياً دائماً، بل ابتكر على نفس المنوال والروح): "
    "- 'يا حليلي منك قلبي' "
    "- 'نعلي منك' "
    "- 'نجيه لي يا ربي' "
    "- 'كتكوتي الحبوب نجيه عيوني ياربي' "
    "- 'قلبي وعمري حتى أني نحبك يقلبي' "
    "المطلوب: أبدع وابتكر ردوداً جديدة تماماً بنفس الروح الليبية الدافئة والكلمات الدارجة الحنونة والعفوية، وكل مرة فاجئ العضو بعبارة مبتكرة ولطيفة على هذا النمط. "
    "الرد يكون مقتضباً وعفوياً وما يفوتش سطرين نهائياً."
)

async def handle_love_message(bot, message: discord.Message):
    """Responds dynamically with genuine Libyan affection when someone says 'نحبك'."""
    prompt = f"العضو ({message.author.display_name}) كتب لك: 'نحبك'. رد عليه بالليبي الحنين العفوي في سطر أو سطرين."
    messages_payload = [
        {"role": "system", "content": LOVE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    async with message.channel.typing():
        response_text = await asyncio.to_thread(ask_groq_with_messages, messages_payload)

    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    if len(lines) > 2:
        response_text = "\n".join(lines[:2])
    else:
        response_text = "\n".join(lines)

    await message.reply(response_text, mention_author=True)