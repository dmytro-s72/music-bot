import os
import asyncio
import re
import logging
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

logging.basicConfig(level=logging.ERROR)

TOKEN = os.getenv("BOT_TOKEN")
FFMPEG_EXE_PATH = "ffmpeg" 
COOKIES_FILE = "cookies.txt"

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
ITEMS_PER_PAGE = 8 

def format_duration(seconds):
    if not seconds: return "0:00"
    mins, secs = int(seconds // 60), int(seconds % 60)
    return f"{mins}:{secs:02d}"

def clean_title(title):
    title = re.sub(r'\(.*?\)|\[.*?\]', '', title)
    junk = ['Official Video', 'Music Video', 'Audio', 'Lyrics', 'Full HD', 'concierto', 'live']
    for word in junk:
        title = re.sub(word, '', title, flags=re.IGNORECASE)
    title = title.replace('||', '').replace('•', '').strip()
    return re.sub(r'\s+', ' ', title)

def get_ydl_opts(file_name=None):
    opts = {
        'format': 'bestaudio/best',
        'cookiefile': COOKIES_FILE,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    if file_name:
        opts['outtmpl'] = file_name.replace(".mp3", "")
        opts['ffmpeg_location'] = FFMPEG_EXE_PATH
    return opts

def download_audio_task(url, title):
    file_name = re.sub(r'[\\/*?:"<>|]', "", title) + ".mp3"
    opts = get_ydl_opts(file_name)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return file_name

def get_pro_keyboard(user_id, page=0):
    data = search_cache.get(user_id, {})
    results = data.get('results', [])
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_items = results[start:end]
    
    buttons = []
    for i, track in enumerate(current_items):
        time = format_duration(track.get('duration'))
        name = clean_title(track.get('title', 'Unknown'))
        btn_text = f"{time} | {name}"
        buttons.append([InlineKeyboardButton(text=btn_text[:45], callback_data=f"dl_{start + i}")])
    
    total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    nav = [
        InlineKeyboardButton(text="<", callback_data=f"page_{max(0, page-1)}"),
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none"),
        InlineKeyboardButton(text=">", callback_data=f"page_{min(total_pages-1, page+1)}")
    ]
    buttons.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Напиши название песни или исполнителя, и я найду музыку для тебя.")

@dp.message(F.text)
async def handle_search(message: types.Message):
    status = await message.answer("🔎 Ищу...")
    opts = get_ydl_opts()
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            search_query = f"ytsearch40:{message.text} music"
            info = ydl.extract_info(search_query, download=False)
            results = info.get('entries', [])
            
        if not results:
            await status.edit_text("❌ Ничего не найдено (попробуйте другой запрос).")
            return

        search_cache[message.from_user.id] = {'results': results, 'page': 0}
        await status.delete()
        await message.answer(f"Результаты по запросу: {message.text}", reply_markup=get_pro_keyboard(message.from_user.id, 0))
    except Exception as e:
        logging.error(f"Возникла ошибка. {e}")
        await status.edit_text("❌ Ошибка поиска (попробуйте позже или проверьте запрос).")

@dp.callback_query(F.data.startswith("page_"))
async def change_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    if callback.from_user.id in search_cache:
        await callback.message.edit_reply_markup(reply_markup=get_pro_keyboard(callback.from_user.id, page))
    await callback.answer()

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    
    if user_id not in search_cache:
        await callback.answer("Результаты устарели, попробуйте еще раз.")
        return

    track = search_cache[user_id]['results'][idx]
    title = clean_title(track['title'])
    url = track.get('url') or track.get('webpage_url')

    await callback.message.edit_text("⌛️")

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_audio_task, url, title)
        
        audio = FSInputFile(file_path)
        await callback.message.answer_audio(audio=audio, title=title)
        await callback.message.delete()
        
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logging.error(f"Возникла ошибка. {e}")
        await callback.message.edit_text("❌ Возникла ошибка при загрузки трека.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
