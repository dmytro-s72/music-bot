import os
import asyncio
import re
import logging
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение токена
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище
search_cache = {}
last_requests = {} 
ITEMS_PER_PAGE = 8

# 🔍 ЕДИНЫЕ НАСТРОЙКИ (Для поиска и загрузки)
def get_ytdl_opts(for_download=False, out_name=None):
    cookie_path = 'cookies.txt'
    
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
        'source_address': '0.0.0.0',
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'android'],
                'skip': ['webpage', 'configs'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }

    if for_download:
        opts.update({
            'outtmpl': f"{out_name}.%(ext)s",
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
        })
    return opts

# 🎧 ФУНКЦИЯ ЗАГРУЗКИ (Исправлено)
async def download_song(video_url, title):
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    file_path = f"{safe_title}.mp3"

    def ytdl_run():
        # Используем те же куки, что и в поиске!
        with yt_dlp.YoutubeDL(get_ytdl_opts(for_download=True, out_name=safe_title)) as ydl:
            ydl.download([video_url])
        return file_path

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ytdl_run)

def verify_cookie_format():
    if os.path.exists('cookies.txt'):
        with open('cookies.txt', 'r') as f:
            line = f.readline()
            if "# Netscape HTTP Cookie File" in line:
                logging.info("✅ Файл куков найден и имеет верный заголовок")
            else:
                logging.warning("⚠️ Заголовок куков не совпадает с форматом Netscape!")
    else:
        logging.error("❌ Файл cookies.txt отсутствует в корне проекта!")

verify_cookie_format()

# 🎛 ГЕНЕРАЦИЯ КЛАВИАТУРЫ
def get_keyboard(user_id, page=0):
    data = search_cache.get(user_id, {})
    results = data.get('items', [])
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

# ▶️ КОМАНДА /START
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Напиши название песни, а я её найду 🎧")

# 🔎 ОБРАБОТКА ПОИСКА
@dp.message(F.text)
async def handle_search(message: types.Message):
    user_id = message.from_user.id
    query_text = message.text.strip().lower()

    if last_requests.get(user_id) == query_text:
        return 
    last_requests[user_id] = query_text

    status = await message.answer("🔎 Ищу...")

    try:
        # Используем единые настройки с куками
        with yt_dlp.YoutubeDL(get_ytdl_opts()) as ydl:
            search_query = f"ytsearch10:{message.text} audio"
            info = ydl.extract_info(search_query, download=False)
            results = [e for e in info.get('entries', []) if e and not e.get('is_live')]

        if not results:
            await status.edit_text("❌ Ничего не найдено")
            last_requests[user_id] = None
            return

        search_cache[user_id] = {'items': results}
        await status.delete()
        await message.answer(
            f"Результаты по запросу: {message.text}",
            reply_markup=get_keyboard(user_id, 0)
        )
    except Exception as e:
        logging.error(f"Search error: {e}")
        await status.edit_text("❌ Ошибка поиска. Попробуйте позже.")
        last_requests[user_id] = None

# 🔄 ПЕРЕКЛЮЧЕНИЕ СТРАНИЦ
@dp.callback_query(F.data.startswith("pg_"))
async def change_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_keyboard(callback.from_user.id, page)
        )
    except:
        pass 
    await callback.answer()

# ⬇️ ЗАГРУЗКА И ОТПРАВКА
@dp.callback_query(F.data.startswith("dl_"))
async def process_dl(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    data = search_cache.get(callback.from_user.id)

    if not data:
        await callback.answer("Результаты устарели, выполните поиск снова", show_alert=True)
        return

    track = data['items'][idx]
    wait_msg = await callback.message.answer("⏳ Загружаю аудио...")

    try:
        file_path = await download_song(track['webpage_url'], track['title'])
        if os.path.exists(file_path):
            await callback.message.answer_audio(
                audio=FSInputFile(file_path),
                title=track['title']
            )
            await wait_msg.delete()
            os.remove(file_path)
        else:
            await wait_msg.edit_text("❌ Файл не найден")
    except Exception as e:
        logging.error(f"Download error: {e}")
        await wait_msg.edit_text("❌ Ошибка при загрузке аудио")

# 🚀 ЗАПУСК
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
