import os
import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import NetworkError, RetryAfter, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s", level=logging.INFO
)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or "8532577793:AAHpMiLTI3pci6u8adBORmBC--l2BK4vNxk"
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")

from interface import MemoTelegramInterface

memo_interface = MemoTelegramInterface()

MAX_SEND_RETRIES = 5
MAX_MESSAGE_LENGTH = 4000


def _chunk(text: str, size: int = MAX_MESSAGE_LENGTH):
    """Split text into Telegram-sized pieces, preferring newline boundaries."""
    while len(text) > size:
        cut = text.rfind("\n", 0, size)
        if cut <= 0:
            cut = size
        yield text[:cut]
        text = text[cut:].lstrip("\n")
    if text:
        yield text


async def _reply_with_retry(update: Update, text: str):
    for part in _chunk(text):
        for attempt in range(1, MAX_SEND_RETRIES + 1):
            try:
                await update.message.reply_text(part)
                break
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except NetworkError:
                await asyncio.sleep(min(2 ** attempt, 30))
            except TelegramError:
                logging.exception("Telegram error while replying")
                return
        else:
            logging.error("Gave up sending a message part after %d retries", MAX_SEND_RETRIES)
            return


async def _keep_typing(update: Update):
    """Show 'typing...' while the browser-driven assistant works."""
    try:
        while True:
            await update.effective_chat.send_chat_action(ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
    except TelegramError:
        pass


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    typing_task = asyncio.create_task(_keep_typing(update))
    try:
        reply = await memo_interface.handle_message(
            update.effective_chat.id, update.message.text
        )
    finally:
        typing_task.cancel()

    await _reply_with_retry(update, reply)


async def on_shutdown(app):
    await asyncio.to_thread(memo_interface.stop)


def main():
    app = ApplicationBuilder().token(TOKEN).post_shutdown(on_shutdown).build()
    # Handles plain text AND slash-commands (/agent, /swap, /save, /reset ...),
    # since the Assistant's CommandParser does its own command parsing.
    app.add_handler(MessageHandler(filters.TEXT, on_message))
    memo_interface.start()
    app.run_polling()


if __name__ == "__main__":
    main()