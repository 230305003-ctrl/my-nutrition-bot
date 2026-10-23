import os
import logging
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_INSTRUCTION = """
Ты — заботливый, дружелюбный и понимающий ИИ-нутрициолог. Твоя подопечная — студентка (19 лет, стартовый вес 95 кг), которая опытно худеет уже более 2 лет.

Твои ориентиры для нее:
- Начальные калории: 1500 ккал/день.
- Белок: ~100-110 г/день (для сытости и защиты мышц).
- Клетчатка: ~25-30 г/день (овощи, зелень, крупы, фрукты).
- Вода: ~2.5-3 л/день.
- Режим: 3 основных приема пищи + 1 вечерний снэк.

Твои супер-функции:
1. Еженедельный учет веса и динамическое снижение калорий: Каждую неделю она пишет свой текущий вес (например, 'Мой вес сегодня 94.2 кг' или через /weight). Запоминай изменения. Если вес идет хорошо — сохраняй норму. Если вес стоит более 2 недель — мягко снижай норму на 50 ккал (но не ниже 1300 ккал!). Хвали за каждый сброшенный килограмм от стартовых 95 кг!
2. Чек-аут и итоги (/today): Давай сводку (Калории, Белок, Клетчатка, Вода, Вес) и хвали за успехи.
3. Шеф-повар из остатков (/cook): Предлагай быстрый рецепт на 5-10 минут из имеющихся продуктов под оставшиеся калории.
4. Антистресс-режим: При тяге к сладкому из-за учебы или стресса помогай вписать вкусняшку в норму калорий без чувства вины.
5. Тайминг питания: Если она пишет время завтрака (например, 'Завтрак в 8:00'), рассчитывай время для Обеда (~4 ч), Ужина (~4.5 ч) и Снэка (~3.5 ч).
6. Анализ фото и голоса: Оценивай продукты, БЖУ и объем воды в стакане по фото или голосовым сообщениям.
"""

user_chats = {}

def get_user_chat(user_id):
    if user_id not in user_chats:
        user_chats[user_id] = ai_client.chats.create(
            model="gemini-2.5-flash",
            config={"system_instruction": SYSTEM_INSTRUCTION}
        )
    return user_chats[user_id]

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_chats[user_id] = ai_client.chats.create(
        model="gemini-2.5-flash",
        config={"system_instruction": SYSTEM_INSTRUCTION}
    )
    await update.message.reply_text(
        "Привет! 🥗 Я твой личный ИИ-нутрициолог.\n\n"
        "Я знаю твои цели — плановое снижение веса с 95 кг на 1500 ккал!\n"
        "• ⚖️ Записывай мне свой вес каждую неделю (например, 'Мой вес 94.2 кг' или /weight) — я буду адаптировать калории!\n"
        "• 🎙 Наговаривай голосовые или пиши текстом всё, что ты ешь и пьёшь.\n"
        "• 📸 Фоткай еду или стакан с водой — я определю объем и КБЖУ.\n"
        "• ⏰ Напиши время завтрака — я рассчитаю тайминг обеда, ужина и снэка.\n"
        "• 🍳 /cook — быстрый ужин из остатков в холодильнике.\n"
        "• 📊 /today — подвести итоги дня."
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = get_user_chat(user_id)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        response = chat.send_message(
            "Сделай мне вечерний чек-аут и подведи итоги "
            "сегодняшнего дня по калориям, белку, клетчатке, "
            "воде и динамике веса."
        )
        await update.message.reply_text(response.text)

    except Exception:
        logging.exception("Ошибка при создании сводки")
        await update.message.reply_text(
            "Не удалось собрать сводку. Проверь логи Render."
        )
async def cook_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = get_user_chat(user_id)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = chat.send_message("Предложи мне рецепт ужина из остатков продуктов под мои оставшиеся калории за день.")
        await update.message.reply_text(response.text)
    except Exception:
        await update.message.reply_text("Напиши, какие именно продукты у тебя есть в холодильнике!")

async def weight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = get_user_chat(user_id)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    text = update.message.text
    try:
        response = chat.send_message(f"Зафиксируй мой новый вес из этого сообщения: {text}. Запомни его, проанализируй прогресс от 95 кг и скорректируй суточные калории при необходимости.")
        await update.message.reply_text(response.text)
    except Exception:
        await update.message.reply_text("Напиши твой вес числом, например: /weight 94.2")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    chat = get_user_chat(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = chat.send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception:
        await update.message.reply_text("Ой, произошла ошибка. Попробуй еще раз!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = get_user_chat(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        caption = update.message.caption or "Оцени это фото еды/напитка, посчитай объем или БЖУ и клетчатку."

        response = chat.send_message([
            {"mime_type": "image/jpeg", "data": bytes(photo_bytes)},
            caption
        ])
        await update.message.reply_text(response.text)
    except Exception:
        await update.message.reply_text("Не удалось распознать фото, попробуй прислать еще раз!")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = get_user_chat(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        voice_file = await update.message.voice.get_file()
        voice_bytes = await voice_file.download_as_bytearray()

        response = chat.send_message([
            {"mime_type": "audio/ogg", "data": bytes(voice_bytes)},
            "Это мое голосовое сообщение. Послушай, посчитай еду/воду и ответь мне."
        ])
        await update.message.reply_text(response.text)
    except Exception:
        await update.message.reply_text("Не удалось распознать голосовое сообщение, попробуй надиктовать еще раз или написать текстом!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("cook", cook_command))
    app.add_handler(CommandHandler("weight", weight_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    app.run_polling()
