import os
import asyncio
import re
import logging
import spotdl
from spotdl import Spotdl
from spotdl.types.song import Song
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
ITEMS_PER_PAGE = 8

def get_spotdl_client():
    return Spotdl(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        downloader_settings={
            "output": "/tmp",
            "format": "mp3",
            "bitrate": "192k",
            "print_errors": True,
        }
    )

def search_songs(query):
    try:
        client = get_spotdl_client()
        songs = client.search([query])
        results = []
        for song in songs[:10]:
            results.append({
                'title': f"{song.name} • {song.artist}",
                'song': song
            })
        return results
    except Exception as e:
        logging.error(f"Search error: {e}")
        return []

def download_song_spotdl(song):
    try:
        client = get_spotdl_client()
        _, path = client.download(song)
        return str(path) if path else None
    except Exception as e:
        logging.error(f"Download error: {e}")
        return None

def get_keyboard(user_id, page=0):
    results = search_cache.get(user_id, [])
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_items = results[start:end]

    buttons = []
    for i, track in enumerate(current_items):
        name = track.get('title', 'Unknown')[:40]
        buttons.append([InlineKeyboardButton(
            text=f"🎵 {name}",
            callback_data=f"dl_{start + i}"
        )])

    total_pages = max(1, (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    nav = [
        InlineKeyboardButton(text="⬅️", callback_data=f"pg_{max(0, page-1)}"),
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none"),
        InlineKeyboardButton(text="➡️", callback_data=f"pg_{min(total_pages-1, page+1)}")
    ]
    buttons.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("🎧 Напиши название песни и я её найду!")

@dp.message(F.text)
async def handle_search(message: types.Message):
    if message.text.startswith("/"):
        return
    
    status = await message.answer("🔎 Ищу...")

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_songs, message.text)

    if not results:
        await status.edit_text("❌ Ничего не найдено.")
        return

    search_cache[message.from_user.id] = results
    await status.delete()
    await message.answer(
        f"По запросу: {message.text}",
        reply_markup=get_keyboard(message.from_user.id, 0)
    )

@dp.callback_query(F.data.startswith("pg_"))
async def change_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    await callback.message.edit_reply_markup(
        reply_markup=get_keyboard(callback.from_user.id, page)
    )
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
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(
            None, download_song_spotdl, track['song']
        )

        if file_path and os.path.exists(file_path):
            await callback.message.answer_audio(
                audio=FSInputFile(file_path),
                title=track['title']
            )
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Ошибка загрузки.")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await wait_msg.edit_text("❌ Ошибка при загрузке.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
