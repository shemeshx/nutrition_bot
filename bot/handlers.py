import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from agent.graph import run_agent
import db.repository as repo
from bot.keyboards import (
    main_menu_keyboard,
    onboarding_activity_keyboard,
    onboarding_goal_keyboard,
    onboarding_gender_keyboard,
)

logger = logging.getLogger(__name__)


def _calc_targets(profile: dict) -> dict:
    """Calculate BMR → TDEE → calorie target + macros using Mifflin-St Jeor"""
    w = profile["weight_kg"]
    h = profile["height_cm"]
    a = profile["age"]

    if profile["gender"] == "male":
        bmr = 10 * w + 6.25 * h - 5 * a + 5
    else:
        bmr = 10 * w + 6.25 * h - 5 * a - 161

    activity_factors = {
        "sedentary":  1.2,
        "light":      1.375,
        "moderate":   1.55,
        "active":     1.725,
        "very_active": 1.9,
    }
    tdee = bmr * activity_factors.get(profile["activity"], 1.55)

    goal_delta = {"lose": -500, "maintain": 0, "gain": +300}
    cal_target = tdee + goal_delta.get(profile["goal"], 0)

    # Macro split: 30% protein, 40% carbs, 30% fat
    protein_g = (cal_target * 0.30) / 4
    carbs_g   = (cal_target * 0.40) / 4
    fat_g     = (cal_target * 0.30) / 9

    return {
        "cal_target": round(cal_target),
        "protein_g":  round(protein_g, 1),
        "carbs_g":    round(carbs_g, 1),
        "fat_g":      round(fat_g, 1),
        "water_ml":   round(w * 35),  # 35ml per kg body weight
    }


# ─── /start ───────────────────────────────────────────────────────────────────

async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user    = await repo.get_user(user_id)

    if user and user.get("onboarded"):
        await update.message.reply_text(
            f"ברוך שובך, {user['name']}! 👋\nאני כאן לעזור לך לנהל את התזונה שלך.",
            reply_markup=main_menu_keyboard(),
        )
        return

    ctx.user_data["onboarding"] = {"step": "name"}
    await update.message.reply_text(
        "👋 *ברוך הבא לבוט התזונה שלך!*\n\n"
        "אני אעזור לך לנהל את התזונה, לעקוב אחר קלוריות ולהשיג את המטרות שלך.\n\n"
        "📝 בואנו נתחיל — *מה שמך?*",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── Onboarding inline callbacks ──────────────────────────────────────────────

async def onboarding_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    ob   = ctx.user_data.get("onboarding", {})

    if data.startswith("gender_"):
        ob["gender"] = data.split("_")[1]
        ob["step"]   = "age"
        ctx.user_data["onboarding"] = ob
        await query.edit_message_text("מה גילך? (שנים)")

    elif data.startswith("activity_"):
        ob["activity"] = data.split("_", 1)[1]
        ob["step"]     = "goal"
        ctx.user_data["onboarding"] = ob
        await query.edit_message_text(
            "מה המטרה שלך?", reply_markup=onboarding_goal_keyboard()
        )

    elif data.startswith("goal_"):
        ob["goal"] = data.split("_")[1]
        await _finish_onboarding(query, ctx, ob)


async def _finish_onboarding(query, ctx, ob: dict):
    user_id = query.from_user.id
    targets = _calc_targets(ob)

    await repo.upsert_user(
        user_id,
        name=ob["name"],
        gender=ob["gender"],
        age=ob["age"],
        height_cm=ob["height_cm"],
        weight_kg=ob["weight_kg"],
        activity=ob["activity"],
        goal=ob["goal"],
        onboarded=1,
        **targets,
    )
    ctx.user_data.pop("onboarding", None)

    goal_text = {"lose": "ירידה במשקל", "maintain": "שמירה", "gain": "עלייה במסה"}
    await query.edit_message_text(
        f"✅ *הפרופיל שלך נשמר!*\n\n"
        f"🎯 מטרה: {goal_text.get(ob['goal'])}\n"
        f"🔥 יעד קלורי: *{targets['cal_target']} קק\"ל ליום*\n"
        f"🥩 חלבון: {targets['protein_g']}g | "
        f"🍞 פחמימות: {targets['carbs_g']}g | "
        f"🫙 שומן: {targets['fat_g']}g\n"
        f"💧 מים: {targets['water_ml']} מ\"ל\n\n"
        f"עכשיו פשוט כתוב לי מה אכלת, שאל שאלות, או השתמש בתפריט! 🎉",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── Main message handler ─────────────────────────────────────────────────────

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text    = update.message.text.strip()

    # Onboarding flow
    ob = ctx.user_data.get("onboarding")
    if ob:
        await _handle_onboarding_text(update, ctx, ob, text)
        return

    # Quick menu buttons → natural language
    quick_commands = {
        "📊 סיכום יומי": "תן לי סיכום יומי",
        "💧 עדכן מים":   "עדכן מים",
        "⚖️ דווח משקל": "דווח משקל",
        "📅 היסטוריה":  "הצג לי את ההיסטוריה שלי",
        "🍽️ הצע ארוחה": "הצע לי ארוחה מתאימה עכשיו",
        "⚙️ פרופיל":    "הצג את הפרופיל שלי",
    }
    text = quick_commands.get(text, text)

    await update.message.chat.send_action("typing")

    try:
        response = await run_agent(user_id, text)
        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        await update.message.reply_text(
            "😕 קרתה שגיאה, נסה שוב בעוד רגע."
        )


# ─── Onboarding text steps ────────────────────────────────────────────────────

async def _handle_onboarding_text(update, ctx, ob, text):
    step = ob.get("step")

    if step == "name":
        ob["name"] = text
        ob["step"] = "gender"
        ctx.user_data["onboarding"] = ob
        await update.message.reply_text(
            f"נעים להכיר, {text}! 😊\n\nמה המין שלך?",
            reply_markup=onboarding_gender_keyboard(),
        )

    elif step == "age":
        try:
            ob["age"] = int(text)
            ob["step"] = "height"
            ctx.user_data["onboarding"] = ob
            await update.message.reply_text('מה גובהך? (ס"מ — למשל: 175)')
        except ValueError:
            await update.message.reply_text("⚠️ אנא הכנס מספר תקין לגיל.")

    elif step == "height":
        try:
            ob["height_cm"] = float(text)
            ob["step"] = "weight"
            ctx.user_data["onboarding"] = ob
            await update.message.reply_text('מה משקלך הנוכחי? (ק"ג — למשל: 75.5)')
        except ValueError:
            await update.message.reply_text("⚠️ אנא הכנס מספר תקין לגובה.")

    elif step == "weight":
        try:
            ob["weight_kg"] = float(text)
            ob["step"] = "activity"
            ctx.user_data["onboarding"] = ob
            await update.message.reply_text(
                "מה רמת הפעילות הגופנית שלך?",
                reply_markup=onboarding_activity_keyboard(),
            )
        except ValueError:
            await update.message.reply_text("⚠️ אנא הכנס מספר תקין למשקל.")
