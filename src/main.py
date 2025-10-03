import asyncio
import json
import logging
import os
from pathlib import Path

from typing import Optional
from telegram import Update
from telegram.ext import Application

from tg import build_app

logging.basicConfig(level=logging.INFO)

# Global application and event loop for Yandex Cloud Functions
_application: Optional[Application] = None
_app_initialized: bool = False
_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def _get_application():
    """Create and initialize the Telegram Application once per cold start."""
    global _application, _app_initialized

    if _application is None:
        _application = build_app(
            tg_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            folder_id=os.getenv("YC_FOLDER_ID"),
            script=Path("../terraform/metadata.yml").absolute(),
            chat_whitelist=get_whitelist()
        )

    if not _app_initialized:
        loop = _get_loop()
        loop.run_until_complete(_application.initialize())
        _app_initialized = True

    return _application


def get_whitelist():
    whitelist = os.getenv("TELEGRAM_CHAT_WHITELIST")
    return list(map(int, whitelist.split(",")))


def telegram_webhook(event: dict, context: dict):
    try:
        if event["httpMethod"] != "POST":
            logging.error("Received request with method %s", event["httpMethod"])
            return "Method Not Allowed", 405

        try:
            data = json.loads(event["body"])
        except json.JSONDecodeError:
            logging.error("Received request with no JSON payload")
            return "Bad Request: no JSON payload", 400

        application = _get_application()
        update = Update.de_json(data, application.bot)

        loop = _get_loop()
        loop.run_until_complete(application.process_update(update))

        return "", 204

    except Exception as e:
        logging.exception("Error handling webhook: %s", e)
        return "", 204


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO)

    app = build_app(
        tg_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        yc_token=os.getenv("YC_OAUTH_TOKEN"),
        folder_id=os.getenv("YC_FOLDER_ID"),
        script=Path("../terraform/metadata.yml"),
        chat_whitelist=get_whitelist()
    )

    app.run_polling()
