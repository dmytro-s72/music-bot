import os
import asyncio
import re
import logging
import yt_dlp
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
last_requests = {}  # Анти-дубль
ITEMS_PER_PAGE = 8

# 🔍 НАЛАШТУВАННЯ ПОШУКУ
def get_search_opts():
    return {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                # Спробуємо 'ios' клієнт, він зараз найбільш живучий без кукі
                'player_client': ['ios', 'android'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
        },
    }

# 🎧 ЗАВАНТАЖЕННЯ
async def download_song(video_url, title):
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    file_path = f"{safe_title}.mp3"

    def ytdl_fallback():
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{safe_title}.%(ext)s", # Правильне розширення
            'quiet': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android']
                }
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])

        return file_path

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ytdl_fallback)

# 🎛 КНОПКИ
def get_keyboard(user_id, page=0):
    results = search_cache.get(user_id, [])
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_items = results[start:end]

    buttons = []
    for i, track in enumerate(current_items):
        name = track.get('title', 'Unknown')[:40]
        buttons.append([InlineKeyboardButton(text=f"🎵 {name}", callback_data=f"dl_{start + i}")])

    total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    nav = [
        InlineKeyboardButton(text="⬅️", callback_data=f"pg_{max(0, page-1)}"),
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none"),
        InlineKeyboardButton(text="➡️", callback_data=f"pg_{min(total_pages-1, page+1)}")
    ]
    buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ▶️ СТАРТ
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Напиши название песни, которую хочеш найти 🎧")

# 🔎 ПОШУК
@dp.message(F.text)
async def handle_search(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip().lower()

    if last_requests.get(user_id) == text:
        return
    last_requests[user_id] = text

    status = await message.answer("🔎 Ищу...")

    try:
        with yt_dlp.YoutubeDL(get_search_opts()) as ydl:
            search_query = f"ytsearch10:{message.text} audio"
            info = ydl.extract_info(search_query, download=False)
            results = [e for e in info.get('entries', []) if e]

        if not results:
            await status.edit_text("❌ Ничего не найдено")
            return

        search_cache[user_id] = results
        await status.delete()
        await message.answer(f"По запросу: {message.text}", reply_markup=get_keyboard(user_id, 0))

    except Exception as e:
        logging.error(f"Search error: {e}")
        await status.edit_text("❌ Ошибка поиска. Может быть, YouTube блокирует запрос.")

# 🔄 СТОРІНКИ
@dp.callback_query(F.data.startswith("pg_"))
async def change_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    try:
        await callback.message.edit_reply_markup(reply_markup=get_keyboard(callback.from_user.id, page))
    except:
        pass # Якщо повідомлення не змінилося, просто ігноруємо
    await callback.answer()

# ⬇️ ЗАВАНТАЖЕННЯ
@dp.callback_query(F.data.startswith("dl_"))
async def process_dl(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    results = search_cache.get(callback.from_user.id)

    if not results:
        await callback.answer("Данные устарели")
        return

    track = results[idx]
    wait_msg = await callback.message.answer("⏳")

    try:
        file_path = await download_song(track['webpage_url'], track['title'])

        if os.path.exists(file_path):
            audio = FSInputFile(file_path)
            await callback.message.answer_audio(audio=audio, title=track['title'])
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Ошибка: файл не создан")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await wait_msg.edit_text("❌ Ошибка загрузки. Попробуйте другую песню.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
