import os
import asyncio
import re
import logging
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from googleapiclient.discovery import build

# 1. Налаштування логування
logging.basicConfig(level=logging.INFO)

# 2. Отримання змінних оточення (Безпечний метод)
# Програма шукає змінні в системі. Якщо не знаходить — видасть помилку.
TOKEN = os.getenv("BOT_TOKEN")
YT_API_KEY = os.getenv("YT_API_KEY")

if not TOKEN or not YT_API_KEY:
    logging.error("Помилка: Змінні BOT_TOKEN або YT_API_KEY не знайдені!")
    # Якщо ти запускаєш локально і забув налаштувати змінні, можна закоментувати 
    # рядки вище і тимчасово вписати їх сюди, але НЕ відправляй це на GitHub!

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
ITEMS_PER_PAGE = 8

# 

# 3. Функція пошуку через YouTube Data API v3
def search_youtube_api(query):
    """Шукає відео через офіційне API"""
    try:
        youtube = build('youtube', 'v3', developerKey=YT_API_KEY)
        full_query = f"{query} official music"
        
        request = youtube.search().list(
            q=full_query,
            part='snippet',
            type='video',
            maxResults=20
        )
        response = request.execute()
        
        results = []
        for item in response.get('items', []):
            results.append({
                'title': item['snippet']['title'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        return results
    except Exception as e:
        logging.error(f"YouTube API Error: {e}")
        return []

# 4. Функція завантаження (залишається без змін)
async def download_song(video_url, title):
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    file_path = f"{safe_title}.mp3"
    
    def ytdl_download():
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': safe_title,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
            'quiet': True,
            'nocheckcertificate': True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        return f"{safe_title}.mp3"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ytdl_download)

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
    if total_pages == 0: total_pages = 1
    
    nav = [
        InlineKeyboardButton(text="⬅️", callback_data=f"pg_{max(0, page-1)}"),
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none"),
        InlineKeyboardButton(text="➡️", callback_data=f"pg_{min(total_pages-1, page+1)}")
    ]
    buttons.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# 6. Обробники (Русифікований інтерфейс)
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Напиши название песни, а я ее найду 🎧")

@dp.message(F.text)
async def handle_search(message: types.Message):
    status = await message.answer("🔎 Ищу лучшую версию для тебя...")
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_youtube_api, message.text)
            
    if not results:
        await status.edit_text("❌ Ничего не найдено (попробуй другое название).")
        return

    search_cache[message.from_user.id] = results
    await status.delete()
    await message.answer(f"По запросу: {message.text}", reply_markup=get_keyboard(message.from_user.id, 0))

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
    wait_msg = await callback.message.answer(f"⏳ Загружаю: {track['title']}...")
    
    try:
        file_path = await download_song(track['url'], track['title'])
        if os.path.exists(file_path):
            await callback.message.answer_audio(audio=FSInputFile(file_path), title=track['title'])
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Ошибка: файл не создан.")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await wait_msg.edit_text("❌ Ошибка при загрузке.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
