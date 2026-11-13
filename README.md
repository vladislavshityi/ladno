<div align="center">

<img src="frontend/public/favicon.svg" width="96" alt="Ладно">

# Ладно

**Помощник жителя Владивостока по ЖКХ: куда пожаловаться и что в квитанции**

[![CI](https://github.com/vladislavshityi/ladno/actions/workflows/ci.yml/badge.svg)](https://github.com/vladislavshityi/ladno/actions/workflows/ci.yml)
[![Deploy](https://github.com/vladislavshityi/ladno/actions/workflows/deploy.yml/badge.svg)](https://github.com/vladislavshityi/ladno/actions/workflows/deploy.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Mini_App-26A5E4?logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

[Бот @ladnovl_bot](https://t.me/ladnovl_bot)

</div>

## Что умеет

| | |
|---|---|
| 📸 **Кому пожаловаться?** | Фото и пара слов → категория, адресат по правилам региона, нормы, срок ответа и готовый текст обращения для «Решаем вместе». Нет ответа — эскалация на следующую ступень. |
| 🧾 **Объясни мою квитанцию** | Начисления простым языком, сравнение месяцев (тариф, объём или норматив), проверка по тарифам региона и заявление на перерасчёт. |
| 🏠 **Мой дом** | Адрес, управляющая компания и данные для писем — один профиль для сайта и Telegram. |
| 🤖 **Бот** | Открывает Mini App, показывает обращения и напоминает, когда срок ответа истёк. |

Адресатов, нормы, сроки и суммы определяет код по справочникам региона. Языковая модель только распознаёт, пересказывает и объясняет; числа в её текстах сверяются с расчётами. Без модели сервис работает на шаблонах.

## Архитектура

```
Telegram ──► bot ──────────────────────────► backend ──► PostgreSQL
Браузер / Mini App ─► caddy ─► frontend (nginx) ─/api─┘
```

| Часть | Стек |
|---|---|
| `backend/` | FastAPI, SQLAlchemy 2 (asyncpg), Alembic, uv, ruff, pytest. Модули `auth`, `users`, `houses`, `issues`, `receipts`, `assistant`, `bot`; в каждом `router` → `service` → `models` / `schemas` |
| `frontend/` | React 19, Vite, TypeScript, Tailwind v4, shadcn/ui, TanStack Query; типы из OpenAPI |
| `bot/` | aiogram 3, long polling, служебный API backend |
| LLM | любой OpenAI-совместимый API или локальная Ollama (`LLM_PROVIDER`) |

## Быстрый старт

```bash
cp .env.example .env          # POSTGRES_PASSWORD, JWT_SECRET, PII_ENCRYPTION_KEY
docker compose up -d --build  # сайт http://localhost:8080, Swagger http://localhost:8000/docs
```

Вход без Telegram для разработки: `APP_ENV=dev` и `POST /api/auth/dev {"telegram_id": 1}`.

<details>
<summary>Разработка и тесты</summary>

```bash
cd backend  && uv sync && uv run ruff check && uv run pytest
cd frontend && npm ci && npm run lint && npm run typecheck && npm test
cd bot      && uv sync && uv run ruff check && uv run pytest
```

Локальная модель: `docker compose --profile ollama up -d`, затем `LLM_PROVIDER=ollama`.
</details>

## Безопасность и персональные данные

- **Вход только через Telegram**: подпись Login Widget и `initData` проверяется по HMAC и сроку `auth_date`, дальше работает JWT. Из Telegram сохраняется только имя.
- **Шифрование в БД**: ФИО, телефон, email, квартира, подъезд и адрес хранятся зашифрованными (Fernet, ключ `PII_ENCRYPTION_KEY`). Лицевой счёт хранится только последними четырьмя цифрами.
- **Фото**: формат определяется по содержимому, EXIF с координатами вырезается, файлы видит только владелец.
- **Языковая модель** не получает ФИО, телефон, квартиру и полный лицевой счёт. Чтобы данные не покидали сервер, используйте локальную Ollama.
- **Согласие на обработку ПД** обязательно (152-ФЗ); данные можно выгрузить и удалить вместе с аккаунтом.
- **Инъекции**: SQL строится только через ORM с параметрами, ввод проверяет Pydantic, HTML не вставляется в разметку, запросы к LLM ограничены по частоте.
- **Периметр**: наружу открыт только Caddy (HTTPS, HSTS, CSP); БД и backend доступны лишь внутри сети compose; в prod без своих секретов приложение не стартует.

## Источники данных

Справочники лежат в репозитории, при работе сервис ничего не скачивает.

| Данные | Источник |
|---|---|
| Дома Владивостока | [ГАР ФНС](https://fias.nalog.ru) — открытые данные |
| Связь дом → УК | [ГИС ЖКХ](https://dom.gosuslugi.ru), дополнено карточками [vl.ru](https://www.vl.ru); источник показывается пользователю |
| Управляющие компании | [Реформа ЖКХ](https://www.reformagkh.ru), сверка с ЕГРЮЛ |
| Тарифы | постановления Агентства по тарифам Приморского края |
| Нормы и сроки | ЖК РФ, ПП РФ № 354, 290, 491, 59-ФЗ |
| Адресаты | официальные сайты администрации, ГЖИ Приморского края и ресурсоснабжающих организаций |

Значения, ещё не сверенные с текстом первоисточника, помечены в YAML `verified: false`.

## Деплой

```bash
git clone https://github.com/vladislavshityi/ladno.git /opt/ladno && cd /opt/ladno
cp .env.example .env   # APP_ENV=prod, DOMAIN, PUBLIC_URL, секреты и токены
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Caddy сам получает сертификат для `DOMAIN`. В @BotFather выполните `/setdomain`. Push в `main` после зелёного CI публикует образы в GHCR и обновляет сервер по SSH; для этого нужны секреты `DEPLOY_HOST`, `DEPLOY_USER` и `DEPLOY_SSH_KEY`.

Резервная копия: `docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > ladno.sql.gz`. Ключ `PII_ENCRYPTION_KEY` храните отдельно: без него зашифрованные поля не восстановить.
