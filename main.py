import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import get_settings
from db.repository import init_db
from bot.handlers import start_handler, message_handler, onboarding_callback
from scheduler.reminders import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

ptb_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ptb_app

    # 1. Init DB
    await init_db()
    logger.info("✅ DB initialized")

    # 2. Build Telegram Application (webhook mode — no polling)
    ptb_app = (
        Application.builder()
        .token(settings.TELEGRAM_TOKEN)
        .updater(None)
        .build()
    )

    # 3. Register handlers
    ptb_app.add_handler(CommandHandler("start",   start_handler))
    ptb_app.add_handler(CommandHandler("summary", message_handler))
    ptb_app.add_handler(CommandHandler("history", message_handler))
    ptb_app.add_handler(CommandHandler("undo",    message_handler))
    ptb_app.add_handler(CallbackQueryHandler(onboarding_callback))
    ptb_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    # 4. Initialize + set webhook
    await ptb_app.initialize()
    webhook_url = f"{settings.WEBHOOK_URL}/webhook/{settings.TELEGRAM_TOKEN}"
    await ptb_app.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook set: {webhook_url}")

    # 5. Scheduler
    setup_scheduler(ptb_app.bot)

    await ptb_app.start()

    yield  # ← app is running

    # Cleanup
    await ptb_app.bot.delete_webhook()
    await ptb_app.stop()
    await ptb_app.shutdown()
    logger.info("🛑 Bot stopped")


app = FastAPI(lifespan=lifespan)


@app.post(f"/webhook/{{{settings.TELEGRAM_TOKEN}}}")
async def webhook_handler(request: Request):
    """Telegram sends every update here"""
    data   = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}
