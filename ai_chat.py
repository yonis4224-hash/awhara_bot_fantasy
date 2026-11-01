"""
AI Chat Engine via Groq LLM (ai_chat.py)
Responds instantly when the bot is mentioned in any allowed channel or general conversation.
Supports Arabic language fluency and fast inference via Groq.
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
    "أنت المساعد الذكي الخاص ببوت 'أوهارا فانتزي' في سيرفر الديسكورد. "
    "تحدث باللغة العربية بأسلوب ودود، ذكي، ومختصر ومباشر. "
    "ساعد الأعضاء في الإجابة على أي أسئلة، وأجب بسرعة ودقة."
)


def ask_groq(prompt: str) -> str:
    """Synchronous API call to Groq endpoints."""
    if not GROQ_API_KEY:
        return "⚠️ عذراً، لم يتم ضبط مفتاح GROQ_API_KEY في السيرفر بعد!"

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800,
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
    """Processes messages where the bot is mentioned and replies in chat."""
    if message.author.bot:
        return

    # Extract user question by stripping mentions
    clean_text = message.clean_content
    # Remove bot mention text
    if bot.user:
        clean_text = re.sub(rf"@{re.escape(bot.user.display_name)}", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(rf"@{re.escape(bot.user.name)}", "", clean_text, flags=re.IGNORECASE)
    clean_text = clean_text.strip()

    if not clean_text:
        await message.reply("أهلاً بك! معك أوهارا فانتزي، كيف يمكنني مساعدتك اليوم؟ 😊", mention_author=False)
        return

    # Trigger typing animation while fetching response
    async with message.channel.typing():
        response_text = await asyncio.to_thread(ask_groq, clean_text)

    # Discord 2000 characters limit safety
    if len(response_text) <= 2000:
        await message.reply(response_text, mention_author=False)
    else:
        # Split message into chunks
        for i in range(0, len(response_text), 1950):
            chunk = response_text[i:i + 1950]
            await message.channel.send(chunk)
