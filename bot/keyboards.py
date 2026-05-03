from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📊 סיכום יומי", "💧 עדכן מים"],
            ["⚖️ דווח משקל", "📅 היסטוריה"],
            ["🍽️ הצע ארוחה", "⚙️ פרופיל"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def onboarding_activity_keyboard() -> InlineKeyboardMarkup:
    levels = [
        ("🪑 יושבני (עבודה במשרד, ללא ספורט)", "sedentary"),
        ("🚶 קל (ספורט 1-2 פעמים בשבוע)",       "light"),
        ("🏃 בינוני (ספורט 3-5 פעמים בשבוע)",   "moderate"),
        ("💪 פעיל (ספורט כל יום)",               "active"),
        ("🏋️ ספורטאי (אימונים אינטנסיביים)",      "very_active"),
    ]
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"activity_{val}")]
         for label, val in levels]
    )


def onboarding_goal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📉 ירידה במשקל",      callback_data="goal_lose")],
        [InlineKeyboardButton("⚖️ שמירה על משקל",    callback_data="goal_maintain")],
        [InlineKeyboardButton("📈 עלייה במסת שריר",  callback_data="goal_gain")],
    ])


def onboarding_gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👨 זכר",  callback_data="gender_male"),
        InlineKeyboardButton("👩 נקבה", callback_data="gender_female"),
    ]])
