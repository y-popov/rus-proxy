import logging
from pathlib import Path
from yandexcloud import SDK

from telegram import Update
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction
from telegram.helpers import escape_markdown
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, Application

from src.service import Service


LAUNCH = "launch"
STOP   = "stop"

BOTDATA_CHAT_WHITELIST = "chat_whitelist"
BOTDATA_SERVICE = "service"


async def start(update: Update):
    keyboard = [[
        KeyboardButton(f"/{LAUNCH}"),
        KeyboardButton(f"/{STOP}")
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text('Start and stop proxy!', reply_markup=reply_markup)


def is_authorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    whitelist: list[int] = context.application.bot_data[BOTDATA_CHAT_WHITELIST]
    return update.effective_chat.id in whitelist


async def reject_unauthorized(update: Update) -> None:
    logging.warning(f"Unauthorized access denied for {update.effective_user.name} in {update.effective_chat.id}.")
    await update.effective_message.reply_text(text="You are not allowed to interact with a service.", do_quote=False)


async def reply_proxy_ip(update: Update, ip: str) -> None:
    ip_string = escape_markdown(ip, version=2)
    message = escape_markdown("Proxy launched. IP address:", version=2)
    text = f"{message} `{ip_string}`"
    await update.effective_message.reply_text(text=text, parse_mode="MarkdownV2", do_quote=False)


async def reply_client_link(update: Update, client_link: str) -> None:
    header = "Open v2rayNG → + → Import from Clipboard"
    message = f"{header}\n\n`{client_link}`"
    await update.effective_message.reply_text(message, do_quote=False)


async def launch_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update, context):
        await reject_unauthorized(update)
        return

    logging.info(f"Got launch request from user {update.effective_user.name} in chat {update.effective_chat.id}")

    await update.effective_message.reply_text("Launching server...", do_quote=False)
    await update.effective_message.reply_chat_action(action=ChatAction.TYPING)

    service: Service = context.application.bot_data[BOTDATA_SERVICE]
    result = service.launch()

    await reply_proxy_ip(update, ip=result.ip)
    await reply_client_link(update, client_link=result.client_link)


async def stop_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update, context):
        await reject_unauthorized(update)
        return

    service: Service = context.application.bot_data[BOTDATA_SERVICE]

    try:
        service.stop()
        text = "Proxy removed successfully."
    except Exception:
        logging.exception("Failed to stop service")
        text = "Proxy not removed due to an internal error."

    await update.effective_message.reply_text(text=text, do_quote=False)


def build_app(tg_token: str, folder_id: str, metadata_template: Path, chat_whitelist: list[int], yc_token: str = None) -> Application:
    if tg_token is None or folder_id is None or metadata_template is None:
        raise ValueError("Telegram token, Folder ID and metadata_template must be provided")

    application = ApplicationBuilder().token(tg_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    service = Service(
        sdk=SDK(token=yc_token),
        folder_id=folder_id,
        metadata_template=metadata_template
    )

    application.bot_data[BOTDATA_SERVICE] = service
    application.bot_data[BOTDATA_CHAT_WHITELIST] = chat_whitelist

    launcher = CommandHandler(LAUNCH, launch_proxy)
    application.add_handler(launcher)

    stopper = CommandHandler(STOP, stop_proxy)
    application.add_handler(stopper)

    return application
