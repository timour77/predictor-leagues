# CM Predictor — Telegram Mini App

Telegram Mini App для прогнозов на футбольные матчи.

## Запуск

### Backend

Нужен Postgres (локально: `docker run -d --name pl-pg -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=pl -p 5432:5432 postgres:16`).

```bash
cd backend
python3.12 -m venv venv                              # только первый раз
venv/bin/pip install -r requirements-dev.txt         # только первый раз
cp .env.example .env                                 # заполнить DATABASE_URL, DATABASE_URL_DIRECT, BOT_TOKEN
venv/bin/alembic upgrade head                        # миграции (прямой URL)
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API доступен на http://localhost:8000  
Документация: http://localhost:8000/docs

Авторизация: каждый запрос несёт `Authorization: tma <Telegram.WebApp.initData>`; бэкенд проверяет HMAC и `auth_date` (без паролей, JWT и сессий).

Тесты (интеграционные нужен пустой Postgres — схема пересоздаётся!):

```bash
TEST_DATABASE_URL=postgresql://postgres:pw@localhost:5432/pl venv/bin/pytest
```

Миграции на проде выполняет job `migrate` в `.github/workflows/backend.yml` (секрет `DATABASE_URL_DIRECT`). Операторские действия — скрипты в `backend/scripts/`, HTTP admin нет.

### Frontend

```bash
cd frontend
npm install    # только первый раз
npm run dev
```

Приложение на http://localhost:5173

## API ключ

football-data.org API ключ — в `backend/.env` (см. `backend/.env.example`).

## Чемпионаты (реальные ID)

| ID   | Название              |
|------|-----------------------|
| 2000 | FIFA World Cup        |
| 2001 | UEFA Champions League |
| 2002 | Bundesliga            |
| 2014 | Primera Division (ES) |
| 2015 | Ligue 1               |
| 2019 | Serie A               |
| 2021 | Premier League        |

## Система очков

- ✅ Правильный исход (1/X/2): **1 очко**
- ✅ Точный счёт: **+3 очка** (дополнительно)
