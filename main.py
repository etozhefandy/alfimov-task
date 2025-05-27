import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime, timedelta
import openai
import locale

# locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")

TELEGRAM_TOKEN = "7663432453:AAGI8NSXu3I4Xz4ufzZ9Sc1Xxs68P9M5q7s"
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

task_storage = {}

def parse_time(text):
    text = text.lower()
    now = datetime.now()
    if "через" in text and "секунд" in text:
        n = int(''.join([s for s in text.split() if s.isdigit()]))
        return now + timedelta(seconds=n)
    elif "через" in text and "минут" in text:
        n = int(''.join([s for s in text.split() if s.isdigit()]))
        return now + timedelta(minutes=n)
    elif "сегодня в" in text:
        h, m = [int(x) for x in text.split("сегодня в")[-1].strip().split(":")]
        return now.replace(hour=h, minute=m, second=0)
    return None

def get_icon_and_caption(dt):
    now = datetime.now()
    date_str = dt.strftime("%d.%m")
    time_str = dt.strftime("%H:%M")
    weekday = dt.strftime("%A").capitalize()
    icon = "📒"  # today by default
    if dt < now:
        icon = "📕"  # overdue (red)
    elif dt.date() == now.date():
        icon = "📒"  # today (yellow)
    else:
        icon = "📘"  # future (blue)
    return icon, f"{icon} {date_str} {weekday}, в {time_str}"

def sort_tasks(tasks):
    return sorted(tasks, key=lambda t: t.get('time', datetime.now()))

def format_task_message(task):
    dt = task.get('time')
    if not dt:
        return f"📝 {task['text']}"
    icon, caption = get_icon_and_caption(dt)
    return f"{caption} — {task['text']}"

async def send_tasks_list(user_id, filter_type, message=None):
    now = datetime.now()
    tasks = [t for t in task_storage.get(user_id, []) if not t.get('done')]
    if filter_type == 'today':
        filtered = [t for t in tasks if t.get('time') and t['time'].date() == now.date()]
    elif filter_type == 'week':
        filtered = [t for t in tasks if t.get('time') and t['time'].isocalendar()[1] == now.isocalendar()[1]]
    elif filter_type == 'future':
        filtered = [t for t in tasks if t.get('time') and t['time'].date() > now.date()]
    else:
        filtered = tasks
    filtered = sort_tasks(filtered)
    if not filtered:
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="⬅️ Назад")]
        ], resize_keyboard=True)
        await bot.send_message(user_id, "Задач нет.", reply_markup=kb)
        return
    for task in filtered:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{task['id']}")]]
        )
        await bot.send_message(user_id, format_task_message(task), reply_markup=kb)
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)
    await bot.send_message(user_id, "Выберите действие:", reply_markup=kb)

async def notify_loop():
    while True:
        now = datetime.now()
        for user_id, tasks in task_storage.items():
            for task in tasks:
                if not task.get('done') and 'time' in task and task['time'] <= now and not task.get('reminded'):
                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{task['id']}")]]
                    )
                    await bot.send_message(user_id, f"❗ Напоминаю: {task['text']}", reply_markup=kb)
                    task['reminded'] = True
        await asyncio.sleep(2)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📋 Задачи")]], resize_keyboard=True)
    await message.answer("Привет! Отправь текст или голос, чтобы добавить задачу.", reply_markup=kb)

@dp.message(F.text.lower() == "📋 задачи")
async def show_menu(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="На сегодня"), KeyboardButton(text="На эту неделю"), KeyboardButton(text="На будущее")]
    ], resize_keyboard=True)
    await message.answer("Выберите список задач:", reply_markup=kb)

@dp.message(F.text.lower() == "на сегодня")
async def tasks_today(message: types.Message):
    await send_tasks_list(message.from_user.id, 'today', message)

@dp.message(F.text.lower() == "на эту неделю")
async def tasks_week(message: types.Message):
    await send_tasks_list(message.from_user.id, 'week', message)

@dp.message(F.text.lower() == "на будущее")
async def tasks_future(message: types.Message):
    await send_tasks_list(message.from_user.id, 'future', message)

@dp.message(F.text.lower() == "⬅️ назад")
async def back_to_menu(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="На сегодня"), KeyboardButton(text="На эту неделю"), KeyboardButton(text="На будущее")]
    ], resize_keyboard=True)
    await message.answer("Выберите список задач:", reply_markup=kb)

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    # Скачиваем файл
    file_info = await bot.get_file(message.voice.file_id)
    file_path = file_info.file_path
    downloaded_file = await bot.download_file(file_path)

    ogg_path = "audio.ogg"
    with open(ogg_path, "wb") as f:
        f.write(downloaded_file.read())

    # Переводим в mp3 через ffmpeg (он должен быть установлен в Railway или локально)
    mp3_path = "audio.mp3"
    import subprocess
    subprocess.run(["ffmpeg", "-i", ogg_path, mp3_path, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Отправляем в OpenAI на распознавание
    with open(mp3_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru"
        )
        text = transcript.text

    if text:
        await handle_task(message, override_text=text)
    else:
        await message.answer("Не удалось распознать задачу.")


@dp.message(F.text)
async def handle_task(message: types.Message, override_text=None):
    text = override_text or message.text
    if text in ["📋 задачи", "На сегодня", "На эту неделю", "На будущее", "⬅️ назад"]:
        return
    user_id = message.from_user.id
    task_id = f"{user_id}_{datetime.now().timestamp()}"
    task = {'id': task_id, 'text': text, 'done': False}

    dt = parse_time(text)
    if dt:
        task['time'] = dt
        await message.answer(f"✅ Добавлено: {text}")
    else:
        await message.answer(f"📝 Задача добавлена: {text}")

    task_storage.setdefault(user_id, []).append(task)

@dp.callback_query(F.data.startswith("done_"))
async def done_task(call: types.CallbackQuery):
    task_id = call.data.split("_", 1)[1]
    user_tasks = task_storage.get(call.from_user.id, [])
    for task in user_tasks:
        if task['id'] == task_id:
            task['done'] = True
            break
    await call.answer("✅ Выполнено")
    await call.message.delete()

async def main():
    loop = asyncio.get_event_loop()
    loop.create_task(notify_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
