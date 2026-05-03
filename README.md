# 🥗 Nutrition Bot — בוט תזונה אישי בטלגרם

בוט טלגרם מבוסס LangGraph + ReAct Agent לניהול תזונה אישית.

## ✨ פיצ'רים

- 📝 רישום ארוחות בשפה טבעית (טקסט / תמונה / קול)
- 📊 מעקב קלוריות ומאקרו (חלבון / פחמימות / שומן)
- 💧 מעקב שתיית מים
- ⚖️ מעקב משקל ומגמות
- ⏰ תזכורות חכמות (בוקר / צהריים / ערב / מים)
- 🧮 חישוב BMR / TDEE / יעד קלורי אוטומטי
- 🔄 תמיכה במרובה providers: OpenRouter, OpenAI, Anthropic, Ollama

## 🏗️ ארכיטקטורה

```
Telegram User
     │
     ▼ (webhook POST)
FastAPI (Railway)
     │
     ▼
LangGraph ReAct Agent ◄──► Tools (log_meal, get_summary, log_water...)
     │                           │
     │                           ▼
     │                      SQLite (Railway Volume)
     │
APScheduler (reminders, Asia/Jerusalem)
```

## 🚀 דיפלוי מהיר ל-Railway

### דרישות מוקדמות
- חשבון [Railway.app](https://railway.app)
- בוט טלגרם (מ-[@BotFather](https://t.me/BotFather))
- מפתח API של [OpenRouter](https://openrouter.ai) (יש גם מודלים חינמיים)

### שלבים

```bash
# 1. Clone
git clone https://github.com/YOUR_USER/nutrition-bot
cd nutrition-bot

# 2. התקן Railway CLI
npm install -g @railway/cli
railway login

# 3. צור פרויקט
railway init

# 4. הוסף Volume ב-Railway Dashboard
#    New → Volume → Mount Path: /app/data

# 5. הגדר משתני סביבה
railway variables set \
  TELEGRAM_TOKEN="YOUR_TOKEN" \
  LLM_PROVIDER="openrouter" \
  OPENROUTER_API_KEY="YOUR_KEY" \
  LLM_MODEL="meta-llama/llama-3.3-70b-instruct"

# 6. Deploy
railway up

# 7. קבל URL והגדר webhook
railway domain
railway variables set WEBHOOK_URL="https://YOUR-APP.up.railway.app"
railway up --detach

# 8. בדוק לוגים
railway logs --tail
```

## 🔄 החלפת מודל LLM

```bash
# Llama 3.3 70B (חינמי דרך OpenRouter)
railway variables set LLM_MODEL="meta-llama/llama-3.3-70b-instruct"

# Claude Haiku (מהיר + עברית מצוינת)
railway variables set LLM_MODEL="anthropic/claude-haiku-4-5"

# GPT-4o mini
railway variables set LLM_MODEL="openai/gpt-4o-mini"

# Claude ישיר
railway variables set LLM_PROVIDER="anthropic" ANTHROPIC_API_KEY="sk-ant-..." LLM_MODEL="claude-haiku-4-5-20251001"

# Ollama לוקאלי
railway variables set LLM_PROVIDER="ollama" OLLAMA_BASE_URL="http://YOUR-SERVER:11434" LLM_MODEL="llama3.2"
```

## 🛠️ פיתוח מקומי

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# ערוך .env עם הערכים שלך

# לtest מקומי — שנה DB_PATH ל-./data/nutrition.db
mkdir -p data
uvicorn main:app --reload
```

## 📁 מבנה הפרויקט

```
nutrition_bot/
├── main.py                 # FastAPI + Telegram webhook
├── config.py               # Settings (pydantic-settings)
├── agent/
│   ├── llm_factory.py      # Multi-provider LLM factory
│   ├── graph.py            # LangGraph ReAct agent
│   ├── tools.py            # Nutrition tools (log_meal, etc.)
│   └── prompts.py          # System prompt builder
├── db/
│   └── repository.py       # Async SQLite via aiosqlite
├── bot/
│   ├── handlers.py         # Telegram handlers + onboarding
│   └── keyboards.py        # Inline/reply keyboards
├── scheduler/
│   └── reminders.py        # APScheduler daily reminders
├── requirements.txt
├── railway.toml
└── .env.example
```

## 📊 השוואת עלויות

| Provider | מודל | עלות ל-1M tokens |
|---|---|---|
| OpenRouter | Llama 3.3 70B | **חינמי** |
| OpenRouter | Claude Haiku | $0.25 / $1.25 |
| Anthropic | Claude Haiku | $0.25 / $1.25 |
| OpenAI | GPT-4o mini | $0.15 / $0.60 |
| Ollama | כל מודל | **$0 לחלוטין** |

Railway Hobby plan: **$5/חודש** (ללא sleep mode).
