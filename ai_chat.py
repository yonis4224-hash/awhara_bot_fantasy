"""
AI Chat Engine via Groq LLM (ai_chat.py)
Responds when mentioned or when someone says 'نحبك'.
Uses SDAIA ALLaM 2 7B model optimized for Arabic/dialects with minimal token usage.
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
GROQ_MODEL = os.getenv("GROQ_MODEL", "allam-2-7b")

SYSTEM_PROMPT = (
    "أنت 'أوهارا'، مساعد ذكي ومفيد في سيرفر ديسكورد، تتكلم بأسلوب ليبي بسيط ومباشر.\n"
    "قواعدك:\n"
    "1. خليك مفيد وجاوب بسلاسة واختصار بدون تكلف أو تعقيد.\n"
    "2. ردك خفيف وموجز، لا يتجاوز سطرين بحد أقصى لتوفير الكلام.\n"
    "3. لا تذكر يونس تلقائياً؛ فقط إذا سألوك صراحة وبشكل مباشر: 'من عمك؟' أو 'من رئيسك؟' أو 'من اللي متعبك؟'، قل بعفوية إن عمك يونس (yonis) بدون أي سب.\n"
    "4. تابع سياق الحديث ورد بطريقة ذكية وعفوية."
)

LOVE_SYSTEM_PROMPT = (
    "أنت بوت ليبي في ديسكورد. كتب لك عضو 'نحبك'.\n"
    "رد عليه برد ليبي حنون وعفوي ومبتكر في سطر أو سطرين فقط.\n"
    "روح الرد: زي 'يا حليلي منك'، 'نعلي منك'، 'نجيك ليا يا عيوني'، 'كتكوتي الحبوب'. ابتكر عبارات دافئة ولطيفة بنفس النمط بدون زيادة عن سطرين."
)


def ask_groq_with_messages(messages_payload: list, max_tokens: int = 55) -> str:
    """Synchronous API call to Groq endpoints with minimized token footprint."""
    if not GROQ_API_KEY:
        return "⚠️ عذراً، لم يتم ضبط مفتاح GROQ_API_KEY في السيرفر بعد!"

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": messages_payload,
        "max_tokens": max_tokens,
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
    """Processes messages where the bot is mentioned with compact channel history."""
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

    # Fetch last 4 messages and truncate each to 100 chars to save tokens
    history_context = []
    try:
        async for prev_msg in message.channel.history(limit=4, before=message):
            content = prev_msg.clean_content.strip() if prev_msg.clean_content else ""
            if not content:
                continue
            if len(content) > 100:
                content = content[:97] + "..."
            author_name = prev_msg.author.display_name
            if bot.user and prev_msg.author.id == bot.user.id:
                history_context.append(f"البوت: {content}")
            else:
                history_context.append(f"{author_name}: {content}")
        history_context.reverse()
    except Exception as e:
        log.warning(f"Could not fetch channel history: {e}")

    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history_context:
        context_str = "سياق الشات:\n" + "\n".join(history_context)
        messages_payload.append({
            "role": "user",
            "content": f"{context_str}\n{message.author.display_name}: {clean_text}"
        })
    else:
        messages_payload.append({
            "role": "user",
            "content": f"{message.author.display_name}: {clean_text}"
        })

    # Trigger typing animation while fetching response
    async with message.channel.typing():
        response_text = await asyncio.to_thread(ask_groq_with_messages, messages_payload, 55)

    # Trim to 2 lines max strictly
    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    if len(lines) > 2:
        response_text = "\n".join(lines[:2])
    else:
        response_text = "\n".join(lines) if lines else "..."

    if len(response_text) <= 2000:
        await message.reply(response_text, mention_author=False)
    else:
        for i in range(0, len(response_text), 1950):
            chunk = response_text[i:i + 1950]
            await message.channel.send(chunk)


async def handle_love_message(bot, message: discord.Message):
    """Responds dynamically with genuine Libyan affection when someone says 'نحبك'."""
    prompt = f"{message.author.display_name} قالك: 'نحبك'. رد عليه بالليبي الحنين في سطر أو سطرين."
    messages_payload = [
        {"role": "system", "content": LOVE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    async with message.channel.typing():
        response_text = await asyncio.to_thread(ask_groq_with_messages, messages_payload, 50)

    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    if len(lines) > 2:
        response_text = "\n".join(lines[:2])
    else:
        response_text = "\n".join(lines) if lines else "نجيك ليا يا غالي."

    await message.reply(response_text, mention_author=True)
