import logging
from pathlib import Path

from telegram import Update
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction
from telegram.helpers import escape_markdown
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, Application

from yandexcloud import SDK
from src.vm import create_proxy_vm, delete_proxy_vm


LAUNCH = "launch"
STOP   = "stop"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        KeyboardButton(f"/{LAUNCH}"),
        KeyboardButton(f"/{STOP}")
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text('Start and stop proxy!', reply_markup=reply_markup)


async def launch_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in context.application.bot_data["chat_whitelist"]:
        logging.warning(f"Unauthorized access denied for {update.effective_user.name} in {update.effective_chat.id}.")
        await update.effective_message.reply_text(text="You are not allowed to start a proxy.")
        return

    logging.info(f"Got launch request from user {update.effective_user.name} in chat {update.effective_chat.id}")

    await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)

    instance = create_proxy_vm(
        sdk=context.application.bot_data["sdk"],
        folder_id=context.application.bot_data["folder_id"],
        script=context.application.bot_data["script"]
    )

    ip = instance.network_interfaces[0].primary_v4_address.one_to_one_nat.address
    ip = escape_markdown(ip, version=2)
    message = escape_markdown("Proxy launched. IP address:", version=2)

    text = f"{message} `{ip}`"
    await update.effective_message.reply_text(text=text, parse_mode="MarkdownV2")


async def stop_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_proxy_vm(
        sdk=context.application.bot_data["sdk"],
        folder_id=context.application.bot_data["folder_id"]
    )

    text = "Proxy removed successfully."
    await update.effective_message.reply_text(text=text)


def build_app(tg_token: str, folder_id: str, script: Path, chat_whitelist: list[int], yc_token: str = None) -> Application:
    if tg_token is None or folder_id is None or script is None:
        raise ValueError("Telegram token, Folder ID and script must be provided")
    if not script.exists():
        raise ValueError("Script file does not exist")

    application = ApplicationBuilder().token(tg_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    application.bot_data["sdk"] = SDK(token=yc_token)
    application.bot_data["folder_id"] = folder_id
    application.bot_data["script"] = script
    application.bot_data["chat_whitelist"] = chat_whitelist

    launcher = CommandHandler(LAUNCH, launch_proxy)
    application.add_handler(launcher)

    stopper = CommandHandler(STOP, stop_proxy)
    application.add_handler(stopper)

    return application
