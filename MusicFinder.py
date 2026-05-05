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
YT_API_KEY = os.getenv("YT_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}
ITEMS_PER_PAGE = 8

def clean_display_name(text):
    """Очищає назву від HTML-символів та технічного сміття"""
    text = html.unescape(text)
    text = re.sub(r'[\(\[][^\\\)\(\]]*[\)\]]', '', text)
    garbage = ["official", "video", "audio", "lyrics", "remastered", "music", "премьера", "новинка"]
    for word in garbage:
        text = re.compile(re.escape(word), re.IGNORECASE).sub('', text)
    return re.sub(r'\s+', ' ', text).strip().strip('-').strip()

# 3. Функція пошуку через YouTube Data API v3
def search_youtube_api(query):
    """Пошук через YouTube API"""
    try:
        youtube = build('youtube', 'v3', developerKey=YT_API_KEY)
        full_query = f"{query} full track audio"
        
        request = youtube.search().list(
            q=full_query,
            part='snippet',
            type='video',
            videoCategoryId='10',
            videoDuration='medium',
            maxResults=10
        )
        response = request.execute()
        
        results = []
        for item in response.get('items', []):
            snippet = item['snippet']
            clean_title = clean_display_name(snippet['title'])
            author = snippet['channelTitle'].replace(" - Topic", "")
            display_name = f"{clean_title} • {author}"
            
            results.append({
                'title': display_name[:50], 
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        return results
    except Exception as e:
        logging.error(f"YouTube API Error: {e}")
        return []

# 4. Функція завантаження
async def download_song(video_url, title):
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    temp_filename = f"track_{hash(video_url)}" 
    final_file = f"{safe_title}.mp3"
    
    cookies_content = os.getenv("YT_COOKIES", "")
    logging.info(f"Перевірка Cookies. Довжина рядка: {len(cookies_content)}")
    cookie_file_path = "temp_cookies.txt"

    # Внутрішня функція для yt-dlp
    def ytdl_download():
        # ОСЬ ТУТ БУЛА ПОМИЛКА: додано відступи для всього блоку нижче
        if len(cookies_content) > 10:
            with open(cookie_file_path, "w", encoding="utf-8") as f:
                f.write(cookies_content)
        
        opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': temp_filename,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
            'quiet': False,
            'nocheckcertificate': True,
            'cookiefile': cookie_file_path if len(cookies_content) > 10 else None,
            'cachedir': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded', 'ios']
                }
            },
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        
        return f"{temp_filename}.mp3"

    try:
        loop = asyncio.get_event_loop()
        downloaded_file = await loop.run_in_executor(None, ytdl_download)
        
        if downloaded_file and os.path.exists(downloaded_file):
            if os.path.exists(final_file):
                os.remove(final_file)
            os.rename(downloaded_file, final_file)
            
            if os.path.exists(cookie_file_path):
                os.remove(cookie_file_path)
            return final_file
        return None
        
    except Exception as e:
        logging.error(f"Помилка завантаження: {e}")
        if os.path.exists(cookie_file_path):
            os.remove(cookie_file_path)
        return None

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

# 6. Обробники (Handler)
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Напиши назву пісні, і я її знайду 🎧")

@dp.message(F.text)
async def handle_search(message: types.Message):
    status = await message.answer("🔎 Шукаю найкращу версію для тебе...")
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, search_youtube_api, message.text)
            
    if not results:
        await status.edit_text("❌ Нічого не знайдено (спробуй іншу назву).")
        return

    search_cache[message.from_user.id] = results
    await status.delete()
    await message.answer(f"За запитом: {message.text}", reply_markup=get_keyboard(message.from_user.id, 0))

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
        await callback.answer("Результати застаріли.")
        return

    track = results[idx]
    wait_msg = await callback.message.answer(f"⏳ Завантажую: {track['title']}...")
    
    try:
        file_path = await download_song(track['url'], track['title'])
        
        if file_path and os.path.exists(file_path):
            await callback.message.answer_audio(
                audio=FSInputFile(file_path), 
                title=track['title']
            )
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Помилка завантаження (можливо, YouTube блокує сервер).")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await wait_msg.edit_text("❌ Сталася внутрішня помилка.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
