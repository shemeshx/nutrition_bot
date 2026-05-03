from langchain_core.tools import tool
from typing import Literal
import db.repository as repo


def get_tools_for_user(user_id: int) -> list:
    """
    Factory: creates a list of tools specific to a user_id.
    Each tool is a closure that captures the user_id.
    """

    @tool
    async def log_meal(
        description: str,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = "snack",
    ) -> str:
        """
        Logs a meal to the database.
        Use this tool when the user reports eating something.
        Estimate nutritional values from your knowledge if the user didn't specify them.
        """
        meal_id = await repo.add_meal(
            user_id, description, calories, protein_g, carbs_g, fat_g, meal_type
        )
        return (
            f"✅ נרשם בהצלחה (ID #{meal_id}): {description}\n"
            f"   🔥 {calories:.0f} קק\"ל | 🥩 {protein_g:.1f}g חלבון | "
            f"🍞 {carbs_g:.1f}g פחמימות | 🫙 {fat_g:.1f}g שומן"
        )

    @tool
    async def get_daily_summary() -> str:
        """
        Returns a full nutritional summary for today: meals, macro totals, water, vs target.
        Use when user asks 'how much did I eat?' or 'what's my status today?'
        """
        user = await repo.get_user(user_id)
        meals = await repo.get_today_meals(user_id)
        water = await repo.get_today_water(user_id)

        if not meals:
            return "📭 לא נרשמו ארוחות היום עדיין."

        total_cal   = sum(m["calories"]  for m in meals)
        total_prot  = sum(m["protein_g"] for m in meals)
        total_carbs = sum(m["carbs_g"]   for m in meals)
        total_fat   = sum(m["fat_g"]     for m in meals)

        cal_target = user.get("cal_target", 2000) if user else 2000
        remaining  = cal_target - total_cal

        meals_text = "\n".join(
            f"  • {m['meal_type'].capitalize()}: {m['description']} ({m['calories']:.0f} קק\"ל)"
            for m in meals
        )

        water_target = user.get("water_ml", 2500) if user else 2500
        water_pct    = (water / water_target * 100) if water_target else 0

        return (
            f"📊 *סיכום יומי*\n\n"
            f"🍽️ *ארוחות:*\n{meals_text}\n\n"
            f"📈 *סה\"כ:*\n"
            f"  🔥 קלוריות: {total_cal:.0f} / {cal_target:.0f} קק\"ל "
            f"({'🟢 נותרו' if remaining >= 0 else '🔴 חריגה'} {abs(remaining):.0f})\n"
            f"  🥩 חלבון: {total_prot:.1f}g\n"
            f"  🍞 פחמימות: {total_carbs:.1f}g\n"
            f"  🫙 שומן: {total_fat:.1f}g\n\n"
            f"💧 מים: {water:.0f} / {water_target:.0f} מ\"ל ({water_pct:.0f}%)"
        )

    @tool
    async def log_water(amount_ml: float) -> str:
        """
        Logs water intake. amount_ml is the amount in milliliters.
        Examples: glass = 250ml, bottle = 500-750ml, liter = 1000ml.
        Use when user says 'I drank water / coffee / shake' etc.
        """
        await repo.add_water(user_id, amount_ml)
        total = await repo.get_today_water(user_id)
        user  = await repo.get_user(user_id)
        target = user.get("water_ml", 2500) if user else 2500
        pct    = total / target * 100
        bar    = "💧" * int(pct / 20)
        return (
            f"✅ נרשם {amount_ml:.0f} מ\"ל\n"
            f"{bar} סה\"כ היום: {total:.0f} / {target:.0f} מ\"ל ({pct:.0f}%)"
        )

    @tool
    async def log_weight(weight_kg: float) -> str:
        """
        Logs new weight and shows comparison to previous measurement.
        Use when user reports weighing themselves.
        """
        user = await repo.get_user(user_id)
        old_weight = user.get("weight_kg") if user else None

        await repo.add_weight(user_id, weight_kg)

        if old_weight and old_weight != weight_kg:
            diff  = weight_kg - old_weight
            trend = "⬆️" if diff > 0 else "⬇️"
            return (
                f"⚖️ משקל נרשם: *{weight_kg} ק\"ג*\n"
                f"{trend} שינוי: {diff:+.1f} ק\"ג מהמדידה הקודמת ({old_weight} ק\"ג)"
            )
        return f"⚖️ משקל נרשם: *{weight_kg} ק\"ג*"

    @tool
    async def get_weight_trend() -> str:
        """
        Shows weight history of the last 10 measurements.
        Use when user asks about trend / progress.
        """
        history = await repo.get_weight_history(user_id, limit=10)
        if not history:
            return "📭 לא נרשמו מדידות משקל עדיין."

        lines = [
            f"  {i+1}. {r['weight_kg']} ק\"ג — {r['logged_at'][:10]}"
            for i, r in enumerate(reversed(history))
        ]
        first = history[-1]["weight_kg"]
        last  = history[0]["weight_kg"]
        total_change = last - first
        return (
            f"📉 *היסטוריית משקל:*\n"
            + "\n".join(lines)
            + f"\n\n📊 שינוי כולל: {total_change:+.1f} ק\"ג"
        )

    @tool
    async def get_weekly_report() -> str:
        """
        Returns nutritional report for the last 7 days with averages.
        Use when user asks about the past week.
        """
        days = await repo.get_meals_range(user_id, days=7)
        if not days:
            return "📭 אין נתונים לשבוע האחרון."

        lines = [
            f"  📅 {d['day']}: {d['total_cal']:.0f} קק\"ל | "
            f"P:{d['total_protein']:.0f}g C:{d['total_carbs']:.0f}g F:{d['total_fat']:.0f}g"
            for d in days
        ]
        avg_cal = sum(d["total_cal"] for d in days) / len(days)
        return (
            f"📊 *דוח שבועי ({len(days)} ימים):*\n"
            + "\n".join(lines)
            + f"\n\n📈 ממוצע יומי: {avg_cal:.0f} קק\"ל"
        )

    @tool
    async def delete_last_entry() -> str:
        """
        Deletes the most recently logged meal entry.
        Use when user says 'cancel' / 'delete' / 'I made a mistake'.
        """
        success = await repo.delete_last_meal(user_id)
        if success:
            return "✅ רישום הארוחה האחרון נמחק בהצלחה."
        return "❌ לא נמצאו רשומות למחיקה."

    @tool
    async def calculate_nutrition_info(food_item: str, amount_grams: float) -> str:
        """
        Calculates nutritional values for a food item by grams.
        Use when user asks 'how many calories in X?'
        Base your answer on your training knowledge — note it's an estimate.
        """
        return (
            f"📋 בקשה: {food_item} ({amount_grams}g) — "
            f"חשב לפי הידע שלך והצג בפורמט: קק\"ל | חלבון | פחמימות | שומן"
        )

    @tool
    async def update_profile(
        field: Literal["goal", "activity", "weight_kg", "cal_target", "water_ml"],
        value: str,
    ) -> str:
        """
        Updates a field in the user profile.
        Use when user says 'change my goal' / 'update my activity level'.
        """
        parsed_value: float | str = value
        if field in ("weight_kg", "cal_target", "water_ml"):
            parsed_value = float(value)
        await repo.upsert_user(user_id, **{field: parsed_value})
        return f"✅ הפרופיל עודכן: {field} = {value}"

    return [
        log_meal,
        get_daily_summary,
        log_water,
        log_weight,
        get_weight_trend,
        get_weekly_report,
        delete_last_entry,
        calculate_nutrition_info,
        update_profile,
    ]
