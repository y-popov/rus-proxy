import logging
from pathlib import Path
from yandexcloud import SDK

from telegram import Update
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction
from telegram.helpers import escape_markdown
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, Application

from src.template import load_template
from src.vpn import generate_wg_keypair
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

    await update.effective_message.reply_text("Launching server...", do_quote=False)
    await update.effective_message.reply_chat_action(action=ChatAction.TYPING)

    server_keypair = generate_wg_keypair()
    client_keypair = generate_wg_keypair()

    metadata_template = context.application.bot_data["metadata-template"]
    metadata = metadata_template.render(
        server_private_key=server_keypair.private_key,
        client_public_key=client_keypair.public_key,
    )

    instance = create_proxy_vm(sdk=context.application.bot_data["sdk"],
                               folder_id=context.application.bot_data["folder_id"], cloud_config=metadata)

    ip = instance.network_interfaces[0].primary_v4_address.one_to_one_nat.address
    ip_string = escape_markdown(ip, version=2)
    message = escape_markdown("Proxy launched. IP address:", version=2)

    text = f"{message} `{ip_string}`"
    await update.effective_message.reply_text(text=text, parse_mode="MarkdownV2", do_quote=False)

    client_config_template = context.application.bot_data["client-config-template"]
    client_config = client_config_template.render(
        client_private_key=client_keypair.private_key,
        server_public_key=server_keypair.public_key,
        instance_ip=ip
    )

    await update.effective_message.reply_text(text=client_config, do_quote=False)


async def stop_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_proxy_vm(
        sdk=context.application.bot_data["sdk"],
        folder_id=context.application.bot_data["folder_id"]
    )

    text = "Proxy removed successfully."
    await update.effective_message.reply_text(text=text)


def build_app(tg_token: str, folder_id: str, metadata_template: Path, client_config_template: Path, chat_whitelist: list[int], yc_token: str = None) -> Application:
    if tg_token is None or folder_id is None or metadata_template is None or client_config_template is None:
        raise ValueError("Telegram token, Folder ID, metadata_template and client_config_template must be provided")

    application = ApplicationBuilder().token(tg_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    application.bot_data["sdk"] = SDK(token=yc_token)
    application.bot_data["folder_id"] = folder_id
    application.bot_data["metadata-template"] = load_template(metadata_template)
    application.bot_data["client-config-template"] = load_template(client_config_template)
    application.bot_data["chat_whitelist"] = chat_whitelist

    launcher = CommandHandler(LAUNCH, launch_proxy)
    application.add_handler(launcher)

    stopper = CommandHandler(STOP, stop_proxy)
    application.add_handler(stopper)

    return application
