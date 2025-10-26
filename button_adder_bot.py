#!/usr/bin/env python3
import os
import time
import re
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from telethon.errors import RPCError

# ========== LOAD KONFIGURASI DARI .ENV ==========
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_RAW = os.getenv("TARGET_CHANNEL", "").strip()

BUTTON_TEXT = os.getenv("BUTTON_TEXT", "📢 Join Backup Channel")
BUTTON_URL = os.getenv("BUTTON_URL", "https://t.me/YourBackupChannel")
LOGFILE = os.getenv("BOT_LOGFILE", "buttombot2.log")

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOGFILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ========== INISIALISASI TELETHON CLIENT ==========
bot = TelegramClient("button_adder2", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ========== ANTI DUPLIKAT ==========
recent_messages = {}
TIMEOUT = 5  # detik

# ========== PARSER TARGET CHANNEL ==========
def parse_target(raw: str):
    """
    Bisa menerima format:
    - -100xxxxxxxxxx
    - 123456789 (akan ditambah -100)
    - @username
    - https://t.me/username
    - https://t.me/c/xxxxxx (private link)
    """
    if not raw:
        return None

    raw = raw.strip()

    # Link t.me
    match = re.search(r"(?:https?://)?t\.me/(c/)?([\w\d\-_]+)", raw)
    if match:
        is_private = match.group(1)
        part = match.group(2)
        if is_private:  # t.me/c/<id>
            return int(f"-100{part}")
        if part.startswith("@"):
            return part
        return f"@{part}"

    # @username
    if raw.startswith("@"):
        return raw

    # angka
    if raw.replace("-", "").isdigit():
        if raw.startswith("-100"):
            return int(raw)
        return int(f"-100{raw}")

    return raw


async def resolve_target():
    """Validasi target & pastikan bot bisa akses"""
    parsed = parse_target(TARGET_RAW)
    if not parsed:
        logging.error("❌ TARGET_CHANNEL kosong atau tidak valid di .env")
        return None

    try:
        await bot.get_entity(parsed)
        logging.info(f"✅ TARGET_CHANNEL berhasil diakses: {parsed}")
        return parsed
    except Exception as e:
        logging.warning(f"⚠️ Gagal akses target ({parsed}): {e}")
        return parsed


# ========== EVENT HANDLER ==========
@bot.on(events.NewMessage)
async def handler(event):
    try:
        # hanya tanggapi pesan dari akun (bukan group / channel)
        if not event.is_private:
            return

        # anti duplikat (hindari spam / pengulangan)
        key = f"{event.chat_id}:{event.id}"
        now = time.time()
        if key in recent_messages and now - recent_messages[key] < TIMEOUT:
            logging.info(f"⚠️ Duplikat abaikan pesan {event.id}")
            return
        recent_messages[key] = now

        # ambil isi pesan
        text = event.message.message or ""
        media = event.message.media

        # tombol inline
        buttons = [[Button.url(BUTTON_TEXT, BUTTON_URL)]]

        # target channel
        target = await resolve_target()
        if not target:
            await event.reply("❌ TARGET_CHANNEL tidak valid. Periksa file .env kamu.")
            return

        # kirim ke channel (ikutkan media bila ada)
        await bot.send_message(
            target,
            text,
            file=media,
            buttons=buttons,
            link_preview=False
        )

        if media:
            logging.info(f"✅ Pesan {event.id} (dengan media) dikirim ke {target}")
        else:
            logging.info(f"✅ Pesan {event.id} (teks saja) dikirim ke {target}")

    except RPCError as rpc_e:
        logging.error(f"❌ RPCError: {rpc_e}")
        await event.reply("❌ Gagal kirim — pastikan bot jadi admin di channel target.")
    except Exception as e:
        logging.exception(f"❌ Error umum: {e}")


# ========== JALANKAN BOT ==========
if __name__ == "__main__":
    logging.info("🤖 Button Adder Bot aktif! Menunggu pesan dari akun forwarder...")
    bot.run_until_disconnected()
