
import logging
import os
import random
import json
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

SONGS_FOLDER = "songs"
SESSIONS_FOLDER = "user_sessions"

os.makedirs(SONGS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER, exist_ok=True)

def get_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("▶️ Next", callback_data="next"),
        types.InlineKeyboardButton("🔁 Replay", callback_data="replay")
    )
    return kb

def get_session_path(user_id):
    return os.path.join(SESSIONS_FOLDER, f"{user_id}.json")

def save_user_session(user_id, group_id):
    os.makedirs(SESSIONS_FOLDER, exist_ok=True)
    with open(get_session_path(user_id), "w") as f:
        json.dump({"group_id": group_id}, f)
    logging.info(f"✅ Group ID {group_id} saved for user {user_id}")

def load_user_session(user_id):
    path = get_session_path(user_id)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("group_id")
    return None

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        "👋 Welcome to Squonk Radio V0.3.6!\n"
        "Use /setup in private chat or /play in group."
    )

@dp.message_handler(commands=["setup"])
async def setup(message: types.Message):
    if message.chat.type != "private":
        return await message.reply("❗ Please use /setup in a private chat.")
    await message.reply("📥 Send me `GroupID: <your_group_id>` first, then upload .mp3 files.")

@dp.message_handler(lambda msg: msg.text and msg.text.startswith("GroupID:"))
async def receive_group_id(message: types.Message):
    group_id = message.text.replace("GroupID:", "").strip()
    if not group_id.lstrip("-").isdigit():
        return await message.reply("❌ Invalid group ID format. Use `GroupID: 123456789`")
    save_user_session(message.from_user.id, group_id)
    await message.reply(f"✅ Group ID `{group_id}` saved. Now send me .mp3 files!")

@dp.message_handler(content_types=types.ContentType.AUDIO)
async def handle_audio(message: types.Message):
    user_id = message.from_user.id
    group_id = load_user_session(user_id)
    if not group_id:
        return await message.reply("❗ Please first send `GroupID: <your_group_id>` in this private chat.")

    group_folder = os.path.join(SONGS_FOLDER, group_id)
    os.makedirs(group_folder, exist_ok=True)
    file_path = os.path.join(group_folder, f"{message.audio.file_unique_id}.mp3")
    await message.audio.download(destination_file=file_path)
    logging.info(f"🎵 Saved to: {file_path}")
    await message.reply(f"✅ Saved `{message.audio.file_name}` for group {group_id}")

@dp.message_handler(commands=["play"])
async def play(message: types.Message):
    group_id = str(message.chat.id)
    folder = os.path.join(SONGS_FOLDER, group_id)
    if not os.path.exists(folder) or not os.listdir(folder):
        return await message.reply("❌ No songs found for this group. Use /setup in private chat to add some.")
    song = random.choice(os.listdir(folder))
    logging.info(f"▶️ Playing {song} in group {group_id}")
    await message.reply_audio(open(os.path.join(folder, song), "rb"), caption="🎶 Squonking time!", reply_markup=get_keyboard())

@dp.callback_query_handler(lambda c: c.data in ["next", "replay"])
async def callback_buttons(call: types.CallbackQuery):
    group_id = str(call.message.chat.id)
    folder = os.path.join(SONGS_FOLDER, group_id)
    if not os.path.exists(folder) or not os.listdir(folder):
        return await call.answer("❌ No songs found for this group.", show_alert=True)
    song = random.choice(os.listdir(folder)) if call.data == "next" else os.listdir(folder)[0]
    await bot.send_audio(call.message.chat.id, open(os.path.join(folder, song), "rb"), caption="🎵 Replay mode!" if call.data == "replay" else "▶️ Next beat!", reply_markup=get_keyboard())
    await call.answer()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
