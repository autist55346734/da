# Вставь сюда свой токен от @BotFather
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import database as db
from ai_checker import check_code, get_hint
from queue_manager import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open('data.json', 'r', encoding='utf-8') as f:
    DATA = json.load(f)

TOPICS = DATA['topics']
TESTS = DATA['tests']

def split_text(text, max_len=4096):
    chunks = []
    while len(text) > max_len:
        split_at = text.rfind('\n', 0, max_len)
        if split_at <= 0:
            split_at = max_len
        candidate = text[:split_at]
        # Don't split inside a code block (odd number of ``` means we're inside one)
        if candidate.count('```') % 2 == 1:
            last_fence = candidate.rfind('```')
            candidate = candidate[:last_fence].rstrip('\n')
        if not candidate:
            candidate = text[:max_len]
        chunks.append(candidate)
        text = text[len(candidate):].lstrip('\n')
    if text:
        chunks.append(text)
    return chunks

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📘 Теория", callback_data='theory')],
        [InlineKeyboardButton("✏️ Практика", callback_data='practice')],
        [InlineKeyboardButton("📝 Тест", callback_data='test')],
        [InlineKeyboardButton("📊 Прогресс", callback_data='progress')],
        [InlineKeyboardButton("💡 Вопрос", callback_data='ask')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update, context):
    user = update.effective_user
    completed = db.get_user_progress(user.id)
    percent = db.calculate_percent(completed, len(TOPICS))
    await update.message.reply_text(
        f"🤖 *Привет, {user.first_name}!*\n\n"
        f"Я помогу тебе выучить Python!\n"
        f"📊 Твой прогресс: {percent}%\n\n"
        f"Выбери действие:",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

async def button_handler(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data.startswith('test_ans_'):
        selected = int(query.data.split('_')[2])
        idx = context.user_data.get('test_index', 0)
        if idx < len(TESTS):
            test = TESTS[idx]
            if selected == test['correct']:
                context.user_data['test_score'] += 1
                await query.answer("✅ Правильно!", show_alert=True)
            else:
                correct = test['options'][test['correct']]
                await query.answer(f"❌ Неправильно. Правильно: {correct}", show_alert=True)
            context.user_data['test_index'] = idx + 1
            await send_test(update, context)
        return

    await query.answer()

    if query.data == 'theory':
        kb = [[InlineKeyboardButton(t['name'], callback_data=f"topic_{t['id']}")] for t in TOPICS]
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data='menu')])
        await query.edit_message_text("📚 *Выбери тему:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith('topic_'):
        topic_id = int(query.data.split('_')[1])
        topic = next(t for t in TOPICS if t['id'] == topic_id)
        chunks = split_text(topic['theory'])
        try:
            await query.edit_message_text(chunks[0], parse_mode='Markdown')
        except Exception:
            pass  # already showing this content
        for chunk in chunks[1:]:
            await query.message.reply_text(chunk, parse_mode='Markdown')
        kb = [[InlineKeyboardButton("✏️ Решать задачи", callback_data=f"practice_{topic_id}")],
              [InlineKeyboardButton("🔙 К темам", callback_data='theory')]]
        await query.message.reply_text("📌 *Что дальше?*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == 'practice':
        completed = db.get_user_progress(user_id)
        kb = []
        for t in TOPICS:
            status = "✅ " if t['id'] in completed else "📘 "
            kb.append([InlineKeyboardButton(f"{status}{t['name']}", callback_data=f"practice_{t['id']}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data='menu')])
        await query.edit_message_text("✏️ *Выбери тему:*", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith('practice_'):
        topic_id = int(query.data.split('_')[1])
        topic = next(t for t in TOPICS if t['id'] == topic_id)
        context.user_data['current_topic'] = topic
        context.user_data['task_index'] = 0
        await send_task(update, context, topic_id, 0)

    elif query.data.startswith('next_'):
        parts = query.data.split('_')
        topic_id = int(parts[1])
        task_idx = int(parts[2]) + 1
        await send_task(update, context, topic_id, task_idx)

    elif query.data == 'test':
        context.user_data['test_index'] = 0
        context.user_data['test_score'] = 0
        await send_test(update, context)

    elif query.data == 'progress':
        completed = db.get_user_progress(user_id)
        percent = db.calculate_percent(completed, len(TOPICS))
        bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
        await query.edit_message_text(
            f"📊 *Твой прогресс*\n\n`{bar}` {percent}%\n\n✅ Тем: {len(completed)}/{len(TOPICS)}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='menu')]])
        )

    elif query.data == 'ask':
        context.user_data['waiting_question'] = True
        await query.edit_message_text(
            "💡 *Задай вопрос по Python*\n\nНапиши свой вопрос в чат, и я помогу!",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='menu')]])
        )

    elif query.data.startswith('hint_'):
        parts = query.data.split('_')
        topic_id = int(parts[1])
        task_idx = int(parts[2])
        topic = next(t for t in TOPICS if t['id'] == topic_id)
        msg = await query.edit_message_text("🤔 *Думаю над подсказкой...*", parse_mode='Markdown')
        hint = await get_hint(topic['name'], topic['tasks'][task_idx], "Как решить это задание?")
        kb = [[InlineKeyboardButton("🔙 Вернуться", callback_data=f"practice_{topic_id}")]]
        await msg.edit_text(hint, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == 'menu':
        await query.edit_message_text("🎯 *Главное меню*\n\nВыбери действие:", parse_mode='Markdown', reply_markup=main_menu())

async def send_task(update, context, topic_id, task_idx):
    topic = next(t for t in TOPICS if t['id'] == topic_id)
    tasks = topic['tasks']
    
    if task_idx >= len(tasks):
        user_id = update.callback_query.from_user.id
        completed = db.get_user_progress(user_id)
        if topic_id not in completed:
            completed.append(topic_id)
            db.update_user_progress(user_id, completed)
        await update.callback_query.edit_message_text(
            f"🎉 *Поздравляю!*\n\nТы прошел тему '{topic['name']}'!",
            parse_mode='Markdown',
            reply_markup=main_menu()
        )
        return
    
    context.user_data['current_task'] = {
        'topic_id': topic_id,
        'topic_name': topic['name'],
        'task_idx': task_idx,
        'task': tasks[task_idx]
    }
    
    kb = [
        [InlineKeyboardButton("💡 Подсказка", callback_data=f"hint_{topic_id}_{task_idx}")],
        [InlineKeyboardButton("➡️ Следующее", callback_data=f"next_{topic_id}_{task_idx}")]
    ]
    
    await update.callback_query.edit_message_text(
        f"*📝 Задание {task_idx + 1} из {len(tasks)}*\n\n"
        f"*Тема:* {topic['name']}\n\n"
        f"*Задача:*\n{tasks[task_idx]}\n\n"
        f"✏️ Напиши свой код в ответ на это сообщение.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def send_test(update, context):
    idx = context.user_data.get('test_index', 0)
    
    if idx >= len(TESTS):
        score = context.user_data['test_score']
        total = len(TESTS)
        percent = int(score / total * 100)
        await update.callback_query.edit_message_text(
            f"📊 *Тест завершен!*\n\n"
            f"✅ Правильно: {score} из {total}\n"
            f"📈 Результат: {percent}%\n\n"
            f"{'🎉 Отлично!' if percent >= 70 else '📚 Попробуй еще раз!'}",
            parse_mode='Markdown',
            reply_markup=main_menu()
        )
        return
    
    test = TESTS[idx]
    kb = [[InlineKeyboardButton(opt, callback_data=f"test_ans_{i}")] for i, opt in enumerate(test['options'])]
    
    await update.callback_query.edit_message_text(
        f"🧠 *Вопрос {idx + 1} из {len(TESTS)}*\n\n{test['question']}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def error_handler(_update, context):
    logger.error(f"Ошибка при обработке апдейта: {context.error}", exc_info=context.error)

async def handle_code(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    if context.user_data.get('waiting_question'):
        del context.user_data['waiting_question']
        msg = await update.message.reply_text("🤔 *Думаю над ответом...*", parse_mode='Markdown')
        hint = await get_hint("Python", "Общий вопрос", text)
        await msg.edit_text(hint, parse_mode='Markdown', reply_markup=main_menu())
        return
    
    if 'current_task' in context.user_data:
        task = context.user_data['current_task']
        msg = await update.message.reply_text("🔍 *Проверяю твой код...*", parse_mode='Markdown')
        position = await queue.add(user_id, check_code, text, task['task'], task['topic_name'])
        
        if position > 1:
            await msg.edit_text(
                f"⏳ *Код в очереди*\n\n"
                f"📋 Позиция: {position}\n"
                f"⏱️ Ответ придет через ~{position * 5} секунд.",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "❓ *Чтобы начать практику*\n\nВыбери задание в разделе '✏️ Практика'.",
            parse_mode='Markdown',
            reply_markup=main_menu()
        )

def main():
    TOKEN = "8341729582:AAHkE-2QUOABbcnMU7m3iQOBuROt313aqJ8"

    if TOKEN != "8341729582:AAHkE-2QUOABbcnMU7m3iQOBuROt313aqJ8":
        print("=" * 50)
        print("❌ ОШИБКА: Вставь свой токен в bot.py!")
        print("📌 Как получить токен:")
        print("   1. Напиши @BotFather в Telegram")
        print("   2. Отправь команду /newbot")
        print("   3. Скопируй полученный токен")
        print("   4. Вставь его в bot.py вместо YOUR_BOT_TOKEN_HERE")
        print("=" * 50)
        return
    
    db.init_db()
    app = Application.builder().token(TOKEN).build()
    queue.set_bot(app.bot)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_error_handler(error_handler)
    
    print("=" * 50)
    print("🤖 Бот запущен!")
    print("📌 Найди бота в Telegram: @..." + TOKEN.split(':')[0])
    print("💡 Для ИИ-проверки установи Ollama: https://ollama.com")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()