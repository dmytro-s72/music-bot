import os
import asyncio
import re
import logging
import yt_dlp
import html
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from googleapiclient.discovery import build

# 1. Налаштування логування
logging.basicConfig(level=logging.INFO)

# 2. Змінні конфігурації
TOKEN = os.getenv("BOT_TOKEN")
# Встав сюди свій API ключ, який ми створили раніше
YT_API_KEY = os.getenv("YT_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
ITEMS_PER_PAGE = 8

def clean_display_name(text):
    """Очищає назву від HTML-символів та сміття"""
    # Перетворюємо &quot; на лапки та інші символи
    text = html.unescape(text)
    # Видаляємо текст у дужках
    text = re.sub(r'[\(\[][^\\\)\(\]]*[\)\]]', '', text)
    # Список слів-паразитів
    garbage = ["official", "video", "audio", "lyrics", "remastered", "music", "премьера", "новинка"]
    for word in garbage:
        text = re.compile(re.escape(word), re.IGNORECASE).sub('', text)
    return re.sub(r'\s+', ' ', text).strip().strip('-').strip()

# 3. Функція пошуку через YouTube Data API v3
def search_youtube_api(query):
    """Покращений пошук для знаходження конкретних треків"""
    try:
        youtube = build('youtube', 'v3', developerKey=YT_API_KEY)
        
        # Додаємо "full track audio" для максимальної точності
        full_query = f"{query} full track audio"
        
        request = youtube.search().list(
            q=full_query,
            part='snippet',
            type='video',
            videoCategoryId='10',
            videoDuration='medium',
            maxResults=10  # Менше результатів, але точніші
        )
        response = request.execute()
        
        results = []
        for item in response.get('items', []):
            snippet = item['snippet']
            # Очищуємо назву від &quot; та іншого
            clean_title = clean_display_name(snippet['title'])
            author = snippet['channelTitle'].replace(" - Topic", "")
            
            display_name = f"{clean_title} • {author}"
            
            results.append({
                'title': display_name[:50], 
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        return results
    except Exception as e:
        import logging
        logging.error(f"YouTube API Error: {e}")
        return []

# 4. Функція завантаження
async def download_song(video_url, title):
    # Очищення назви для файлової системи
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    # Важливо: використовуємо унікальне ім'я для завантаження
    temp_filename = f"track_{hash(video_url)}" 
    final_file = f"{safe_title}.mp3"
    
    def ytdl_download():
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_filename, # Тимчасова назва без розширення
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
            'quiet': True,
            'nocheckcertificate': True,
            'extractor_args': {
              'youtube': {
                   'player_client': ['android'],
              }
            },
            # Додаткові налаштування для стабільності
            'socket_timeout': 30,
            'retries': 3,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        return f"{temp_filename}.mp3"

    try:
        loop = asyncio.get_event_loop()
        downloaded_file = await loop.run_in_executor(None, ytdl_download)
        
        # Перейменовуємо файл у красиву назву перед відправкою
        if os.path.exists(downloaded_file):
            if os.path.exists(final_file):
                os.remove(final_file) # Видаляємо старий, якщо є
            os.rename(downloaded_file, final_file)
            return final_file
        return None
    except Exception as e:
        logging.error(f"Критична помилка yt-dlp: {e}")
        return None

# 5. Клавіатура (логіка залишена без змін)
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

# 6. Обробники (Handler)
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Напиши название песни, а я ее найду 🎧")

@dp.message(F.text)
async def handle_search(message: types.Message):
    status = await message.answer("🔎 Ищу лучшую версию для тебя...")
    
    # Використовуємо нову функцію пошуку
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
            await callback.message.answer_audio(
                audio=FSInputFile(file_path), 
                title=track['title']
            )
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Ошибка: файл не создался.")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await wait_msg.edit_text("❌ Ошибка при загрузке или конвертации.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
