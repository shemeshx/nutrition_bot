import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

import db.repository as repo

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Jerusalem")


async def _send(bot: Bot, user_id: int, text: str):
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.warning(f"[Reminder] Failed to send to {user_id}: {e}")


async def morning_reminder(bot: Bot):
    """08:00 — Good morning + daily target"""
    for user in await repo.get_all_onboarded_users():
        await _send(bot, user["user_id"],
            f"🌅 *בוקר טוב, {user['name']}!*\n\n"
            f"היעד שלך היום: *{user['cal_target']:.0f} קק\"ל*\n"
            f"💧 שתה לפחות {user['water_ml']:.0f} מ\"ל מים\n\n"
            f"כתוב לי מה אכלת לארוחת בוקר 🍳"
        )


async def midday_reminder(bot: Bot):
    """13:00 — Lunch reminder"""
    for user in await repo.get_all_onboarded_users():
        meals      = await repo.get_today_meals(user["user_id"])
        total_cal  = sum(m["calories"] for m in meals)
        remaining  = user["cal_target"] - total_cal
        if remaining > 0:
            await _send(bot, user["user_id"],
                f"🕐 *תזכורת ארוחת צהריים!*\n\n"
                f"עד עכשיו: {total_cal:.0f} קק\"ל\n"
                f"נותרו: *{remaining:.0f} קק\"ל*\n\n"
                f"מה אכלת לצהריים? 🥗"
            )


async def evening_summary(bot: Bot):
    """21:00 — Daily wrap-up"""
    for user in await repo.get_all_onboarded_users():
        meals      = await repo.get_today_meals(user["user_id"])
        water      = await repo.get_today_water(user["user_id"])
        total_cal  = sum(m["calories"] for m in meals)
        remaining  = user["cal_target"] - total_cal
        water_pct  = (water / user["water_ml"] * 100) if user["water_ml"] else 0
        status     = (
            "🟢 כל הכבוד!" if abs(remaining) < 200
            else "🔴 קצת חרגת" if remaining < -200
            else "🟡 קצת פחות מהיעד"
        )
        await _send(bot, user["user_id"],
            f"🌙 *סיכום יומי — {user['name']}*\n\n"
            f"🔥 קלוריות: {total_cal:.0f} / {user['cal_target']:.0f} {status}\n"
            f"💧 מים: {water:.0f} מ\"ל ({water_pct:.0f}%)\n\n"
            f"{'שמור על הקצב מחר! 💪' if remaining >= -200 else 'מחר יהיה יום חדש 🌟'}"
        )


async def water_reminder(bot: Bot):
    """Every 2h between 10:00-20:00 — nudge if below 50% water target"""
    for user in await repo.get_all_onboarded_users():
        water  = await repo.get_today_water(user["user_id"])
        target = user["water_ml"]
        if water < target * 0.5:
            await _send(bot, user["user_id"],
                f"💧 שתית {water:.0f} מ\"ל מים היום — זכור לשתות! (יעד: {target:.0f})"
            )


def setup_scheduler(bot: Bot):
    scheduler.add_job(morning_reminder, CronTrigger(hour=8,  minute=0),                       args=[bot])
    scheduler.add_job(midday_reminder,  CronTrigger(hour=13, minute=0),                       args=[bot])
    scheduler.add_job(evening_summary,  CronTrigger(hour=21, minute=0),                       args=[bot])
    scheduler.add_job(water_reminder,   CronTrigger(hour="10,12,14,16,18,20", minute=0),      args=[bot])
    scheduler.start()
    logger.info("✅ Scheduler started (Asia/Jerusalem)")
