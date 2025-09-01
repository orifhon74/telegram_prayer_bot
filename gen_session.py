# gen_session.py
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("API_ID: ").strip())
api_hash = input("API_HASH: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n✅ Logged in.")
    print("\nPaste this value into Railway as TELEGRAM_STRING_SESSION:\n")
    print(client.session.save())