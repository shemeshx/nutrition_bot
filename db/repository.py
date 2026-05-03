import aiosqlite
import json
from datetime import date, datetime
from typing import Optional
from config import get_settings

settings = get_settings()
DB = settings.DB_PATH


async def init_db():
    import os
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id             INTEGER PRIMARY KEY,
                name                TEXT,
                age                 INTEGER,
                gender              TEXT,
                height_cm           REAL,
                weight_kg           REAL,
                activity            TEXT,
                goal                TEXT,
                dietary             TEXT,
                cal_target          REAL,
                protein_g           REAL,
                carbs_g             REAL,
                fat_g               REAL,
                water_ml            REAL DEFAULT 2500,
                reminder_morning    TEXT,
                reminder_evening    TEXT,
                onboarded           INTEGER DEFAULT 0,
                onboarding_state    TEXT,
                updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS meals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                description TEXT,
                calories    REAL,
                protein_g   REAL,
                carbs_g     REAL,
                fat_g       REAL,
                meal_type   TEXT DEFAULT 'snack',
                logged_at   TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS water_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount_ml   REAL,
                logged_at   TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS weight_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                weight_kg   REAL,
                logged_at   TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        await db.commit()


# ─── Onboarding state (persisted in DB) ──────────────────────────────────────

async def get_onboarding_state(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT onboarding_state FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None


async def set_onboarding_state(user_id: int, state: Optional[dict]) -> None:
    value = json.dumps(state) if state else None
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """INSERT INTO users (user_id, onboarding_state)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET onboarding_state = excluded.onboarding_state""",
            (user_id, value),
        )
        await db.commit()


# ─── Users ────────────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def upsert_user(user_id: int, **fields) -> None:
    existing = await get_user(user_id)
    fields["updated_at"] = datetime.now().isoformat()
    if not existing:
        fields["user_id"] = user_id
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" * len(fields))
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                f"INSERT INTO users ({cols}) VALUES ({placeholders})",
                list(fields.values()),
            )
            await db.commit()
    else:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                f"UPDATE users SET {set_clause} WHERE user_id = ?",
                [*fields.values(), user_id],
            )
            await db.commit()


# ─── Meals ────────────────────────────────────────────────────────────────────

async def add_meal(
    user_id: int,
    description: str,
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    meal_type: str = "snack",
) -> int:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            """INSERT INTO meals
               (user_id, description, calories, protein_g, carbs_g, fat_g, meal_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, description, calories, protein_g, carbs_g, fat_g, meal_type),
        )
        await db.commit()
        return cur.lastrowid


async def get_today_meals(user_id: int) -> list[dict]:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM meals
               WHERE user_id = ? AND date(logged_at) = ?
               ORDER BY logged_at""",
            (user_id, today),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_meals_range(user_id: int, days: int = 7) -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT date(logged_at) as day,
                      SUM(calories)  as total_cal,
                      SUM(protein_g) as total_protein,
                      SUM(carbs_g)   as total_carbs,
                      SUM(fat_g)     as total_fat
               FROM meals
               WHERE user_id = ?
                 AND date(logged_at) >= date('now', ?)
               GROUP BY day ORDER BY day""",
            (user_id, f"-{days} days"),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def delete_last_meal(user_id: int) -> bool:
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT id FROM meals WHERE user_id = ? ORDER BY logged_at DESC LIMIT 1",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        await db.execute("DELETE FROM meals WHERE id = ?", (row[0],))
        await db.commit()
        return True


# ─── Water ────────────────────────────────────────────────────────────────────

async def add_water(user_id: int, amount_ml: float) -> None:
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO water_logs (user_id, amount_ml) VALUES (?, ?)",
            (user_id, amount_ml),
        )
        await db.commit()


async def get_today_water(user_id: int) -> float:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            """SELECT COALESCE(SUM(amount_ml), 0) FROM water_logs
               WHERE user_id = ? AND date(logged_at) = ?""",
            (user_id, today),
        ) as cur:
            return (await cur.fetchone())[0]


# ─── Weight ───────────────────────────────────────────────────────────────────

async def add_weight(user_id: int, weight_kg: float) -> None:
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO weight_logs (user_id, weight_kg) VALUES (?, ?)",
            (user_id, weight_kg),
        )
        await db.execute(
            "UPDATE users SET weight_kg = ?, updated_at = ? WHERE user_id = ?",
            (weight_kg, datetime.now().isoformat(), user_id),
        )
        await db.commit()


async def get_weight_history(user_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM weight_logs WHERE user_id = ? ORDER BY logged_at DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ─── All onboarded users (for scheduler) ─────────────────────────────────────

async def get_all_onboarded_users() -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE onboarded = 1") as cur:
            return [dict(r) for r in await cur.fetchall()]
