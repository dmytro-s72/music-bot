import asyncio
import os
import re
import logging
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# Настройка логирования
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
# Укажи правильный путь к ffmpeg.exe
FFMPEG_EXE_PATH = "ffmpeg"

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
ITEMS_PER_PAGE = 8 

def format_duration(seconds):
    """Навчання: Преобразуем секунды в формат 3:45, исправляя ошибку float."""
    if not seconds: return "0:00"
    mins, secs = int(seconds // 60), int(seconds % 60)
    return f"{mins}:{secs:02d}"

def clean_title(title):
    """Ведення документації: Очистка названия от лишнего мусора."""
    title = re.sub(r'\(.*?\)|\[.*?\]', '', title)
    junk = ['Official Video', 'Music Video', 'Audio', 'Lyrics', 'Full HD', 'concierto', 'live']
    for word in junk:
        title = re.sub(word, '', title, flags=re.IGNORECASE)
    title = title.replace('||', '').replace('•', '').strip()
    return re.sub(r'\s+', ' ', title)

def download_audio_task(url, title):
    """Навчання: Загрузка через yt_dlp с конвертацией в MP3."""
    file_name = re.sub(r'[\\/*?:"<>|]', "", title) + ".mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': file_name.replace(".mp3", ""),
        'ffmpeg_location': FFMPEG_EXE_PATH,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return file_name

def get_pro_keyboard(user_id, page=0):
    """Опис рішення: Создание кнопок в формате 'Время | Название'."""
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

@dp.message(F.text)
async def handle_search(message: types.Message):
    """Поиск треков на YouTube с фильтром по времени (от 1 до 10 минут)."""
    status = await message.answer("🔎 Ищу...")
    
    # Ведення документації:
    # duration > 60 — исключает "огрызки" и Shorts (меньше минуты)
    # duration < 600 — исключает длинные концерты (больше 10 минут)
    ydl_opts = {
        'quiet': True, 
        'noplaylist': True, 
        'extract_flat': True, 
        'match_filter': yt_dlp.utils.match_filter_func("duration > 60 & duration < 600")
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Навчання: Добавляем слово "music" к запросу, чтобы улучшить выдачу популярных треков
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
        await status.edit_text(f"Ошибка поиска: {e}")

@dp.callback_query(F.data.startswith("page_"))
async def change_page(callback: types.CallbackQuery):
    """Листание страниц поиска."""
    page = int(callback.data.split("_")[1])
    if callback.from_user.id in search_cache:
        await callback.message.edit_reply_markup(reply_markup=get_pro_keyboard(callback.from_user.id, page))
    await callback.answer()

@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    """Обработка выбора трека и визуализация загрузки."""
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    
    if user_id not in search_cache:
        await callback.answer("Результаты устарели, попробуйте еще раз.")
        return

    track = search_cache[user_id]['results'][idx]
    title = clean_title(track['title'])
    url = track.get('url') or track.get('webpage_url')

    # Визуальный эффект ожидания
    await callback.message.edit_text(f"⌛️")

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_audio_task, url, title)
        
        audio = FSInputFile(file_path)
        await callback.message.answer_audio(audio=audio, title=title)
        
        # Удаляем сообщение с песочными часами после отправки
        await callback.message.delete()
        
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка загрузки: {e}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
