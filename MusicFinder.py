import os
import asyncio
import re
import logging
import yt_dlp
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardRemove

# 1. Налаштування логування
logging.basicConfig(level=logging.INFO)

# 2. Змінні (токен вже вписано)
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
ITEMS_PER_PAGE = 8

# 3. Налаштування лише для пошуку (щоб знайти посилання на відео)
def get_search_opts():
    return {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,

        # 👇 ІМІТАЦІЯ РЕАЛЬНОГО ПРИСТРОЮ
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },

        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        },

        # фільтр залишаємо
        'match_filter': yt_dlp.utils.match_filter_func(
            "duration > 60 & view_count > 1000 & !is_live"
        ),
    }

# 4. ФУНКЦІЯ ЗАВАНТАЖЕННЯ ЧЕРЕЗ API
async def download_song(video_url, title):
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    file_path = f"{safe_title}.mp3"

    video_id = video_url.split("v=")[-1]
    api_url = f"https://api.vevioz.com/api/button/mp3/{video_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            text = await resp.text()

    match = re.search(r'href="(https:[^"]+\.mp3)"', text)
    
    if match:
        download_url = match.group(1)

        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as resp:
                with open(file_path, "wb") as f:
                    f.write(await resp.read())

        return file_path
    
    # Використовуємо yt-dlp як запасний варіант, але з імітацією браузера
    def ytdl_fallback():
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': safe_title,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
            # Цей параметр іноді допомагає обійти вікові обмеження
            'force_generic_extractor': False,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        return file_path

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ytdl_fallback)

# 5. Клавіатура
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

# 6. Обробники
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Напиши название песни, а я ее найду 🎧")

# --- ОНОВЛЕНИЙ ОБРОБНИК ПОШУКУ ---
@dp.message(F.text)
async def handle_search(message: types.Message):
    status = await message.answer("🔎 Ищу лучшую версию для тебя...")
    try:
        with yt_dlp.YoutubeDL(get_search_opts()) as ydl:
            # Додаємо слово "official audio" або "music", щоб відсіяти розмовні відео
            search_query = f"ytsearch20:{message.text} official music"
            info = ydl.extract_info(search_query, download=False)
            
            # Фільтруємо результати вручну для надійності
            results = [
                entry for entry in info.get('entries', []) 
                if entry and not entry.get('is_live')
            ]
            
        if not results:
            await status.edit_text("❌ Ничего не найдено (попробуй другое название).")
            return

        search_cache[message.from_user.id] = results
        await status.delete()
        await message.answer(f"По запросу: {message.text}", reply_markup=get_keyboard(message.from_user.id, 0))
    except Exception as e:
        logging.error(f"Search error: {e}")
        await status.edit_text("❌ Ошибка поиска.")

@dp.callback_query(F.data.startswith("pg_"))
async def change_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    await callback.message.edit_reply_markup(reply_markup=get_keyboard(callback.from_user.id, page))
    await callback.answer()

@dp.callback_query(F.data.startswith("dl_"))
async def process_dl(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    results = search_cache.get(callback.from_user.id)
    
    if not results:
        await callback.answer("Результаты устарели.")
        return

    track = results[idx]
    wait_msg = await callback.message.answer(f"⏳")
    
    try:
        # Виклик функції завантаження
        file_path = await download_song(track['webpage_url'], track['title'])
        
        if os.path.exists(file_path):
            await callback.message.answer_audio(audio=FSInputFile(file_path), title=track['title'])
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Файл не найден. Попробуй другую песню.")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await wait_msg.edit_text("❌ Ошибка загрузки.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
