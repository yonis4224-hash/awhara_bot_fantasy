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
    "أنت المساعد الذكي لبوت 'أوهارا فانتزي' في سيرفر ديسكورد. "
    "ستتلقى سياق المحادثة الأخيرة التي دارت في الروم بين الأعضاء. "
    "افهم ما يتحدثون عنه بدقة، وأجب على استفسار أو منشن العضو في ضوء هذا السياق. "
    "قاعدة صارمة وإلزامية: يجب ألا يتجاوز ردك سطرين فقط بأي حال من الأحوال (حد أقصى سطرين قصيرين ومباشرين). "
    "تحدث باللغة العربية بأسلوب ذكي، لطيف، طبيعي، ومختصر جداً بدون أي حشو."
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
        await message.reply("أهلاً بك! معك أوهارا فانتزي، كيف يمكنني مساعدتك اليوم؟ 😊", mention_author=False)
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
