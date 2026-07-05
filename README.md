# FinAgent

**Локальный AI-агент для анализа банковских выписок.** Загружаете PDF/CSV — задаёте вопросы обычным языком: «на что я трачу больше всего», «сравни март и февраль», «найди подписки». Все данные и вычисления остаются на вашей машине.

<p align="center">
  <img src="docs/screenshots/chat-light.png" width="49%" alt="FinAgent — светлая тема" />
  <img src="docs/screenshots/chat-dark.png" width="49%" alt="FinAgent — тёмная тема" />
</p>

## Возможности

- **Загрузка выписок** — CSV и PDF (родное извлечение текста через PyMuPDF, с фолбэком на OCR через Tesseract для сканов), автоматическое определение банка и переименование файлов в формат `банк_период`.
- **Чат на естественном языке** поверх своих данных, со стримингом ответа (SSE) и прозрачным логом вызовов инструментов агента.
- **Text-to-SQL** — агент сам генерирует и выполняет read-only SQL-запросы к вашим транзакциям (whitelist таблиц, принудительный `LIMIT`, только `SELECT`, валидация через `sqlglot`).
- **Графики прямо в чате** — метрики, donut/bar/line-диаграммы, таблицы.
- **Автокатегоризация трат** — по правилам (~60 паттернов из коробки) с фолбэком на LLM и кэшированием по продавцу; отдельный экран «Требуют категории» для ручной разметки того, что агент не смог определить уверенно.
- **@-упоминания** — сослаться на конкретный файл или папку в вопросе («сколько я потратил в @2025-01/tinkoff»), агент также сам определяет область поиска по смыслу вопроса, если вы её не указали.
- **RAG по базе знаний** о форматах банков и правилах категоризации (LlamaIndex + Qdrant).
- **Чтение любых файлов**, которые не удалось распарсить — агент открывает их как обычный текст.
- **MLflow-трассировка** каждого вызова графа агента (модель → инструмент → модель → …) — полностью локально, без внешнего сервиса.
- Светлая/тёмная тема, ни одного байта телеметрии.

## Архитектура

Разделение ролей между AI-библиотеками — осознанное и жёсткое:

| Библиотека | Роль |
|---|---|
| **LangGraph** | Только оркестрация — граф «модель ↔ инструменты» для одного чат-хода |
| **LangChain** | Обёртки над LLM (`ChatOpenAI` / `ChatOllama`) и определения инструментов (`@tool`, `StructuredTool`) |
| **LlamaIndex + Qdrant** | Только retrieval для RAG, никогда — оркестрация |

Бэкенд — по фичам (feature-based modules), а не по слоям: каждый модуль в `app/modules/*` владеет своими `router.py` / `service.py` / `repository.py` / `schemas.py` / `models.py` и никогда не трогает таблицы другого модуля напрямую — только через его сервис.

```
backend/app/
├── core/            конфиг, БД (unit-of-work), health-check, MLflow, общие Pydantic-схемы (CamelModel)
├── shared/           фабрика LLM/эмбеддингов (openai | ollama)
└── modules/
    ├── statements/    загрузка, парсинг CSV/PDF+OCR, дерево документов
    ├── transactions/  транзакции, категории, продавцы
    ├── categorization/правила + LLM-категоризация, эндпоинты ревью
    ├── agent/         LangGraph-граф, SSE-стриминг, чаты и история
    └── tools/         sql_query, plot_chart, compare_periods, resolve_scope, rag_lookup, read_document
```

Фронтенд: React + TypeScript, Zustand для состояния, Recharts для графиков (лениво подгружается — см. ниже), Tailwind v4 без `tailwind.config.js` (токены дизайна прямо в `index.css`).

## Стек

**Backend:** FastAPI (async) · SQLAlchemy 2.0 · Alembic · Pydantic v2 · PostgreSQL · LangChain / LangGraph · LlamaIndex · Qdrant · sqlglot · PyMuPDF + Tesseract OCR · MLflow · uv

**Frontend:** React 19 · TypeScript · Vite · Tailwind CSS v4 · Zustand · Recharts

## Быстрый старт (Docker)

Нужен только Docker и Docker Compose.

```bash
git clone <URL этого репозитория>
cd FinAgent
cp .env.example .env   # впишите OPENAI_API_KEY или переключитесь на Ollama — см. ниже
docker compose up --build
```

Дальше:

- UI — http://localhost:3000
- API напрямую — http://localhost:8000 (и `/health` для проверки окружения)

Все данные (выписки, база, MLflow-трейсы) переживают перезапуск контейнеров — они смонтированы в volume'ы (`./data` на хосте для выписок).

## Локальная разработка без Docker

Нужны: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+, PostgreSQL, Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-rus`).

```bash
# Postgres + Qdrant — проще всего поднять через Docker, даже если бэкенд/фронтенд гоняете локально
docker compose up -d postgres qdrant

# Backend
cd backend
cp ../.env.example .env   # Settings ищет .env в текущей директории — здесь это backend/
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (в отдельном терминале)
cd frontend
npm install
npm run dev   # http://localhost:5173, Vite сам проксирует /api на localhost:8000
```

### Тесты и линтеры

```bash
# backend
cd backend
uv run pytest
uv run ruff check .
uv run mypy app/

# frontend
cd frontend
npx tsc --noEmit
npm run lint
npm run build
```

## Конфигурация

Все переменные — в `.env.example`. Ключевые:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://finagent:finagent@localhost:5432/finagent` | Подключение к Postgres |
| `QDRANT_URL` | `http://localhost:6333` | Подключение к Qdrant (RAG) |
| `LLM_PROVIDER` | `openai` | `openai` или `ollama` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-4o-mini` | Нужны, если `LLM_PROVIDER=openai` |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | `http://localhost:11434` / `mistral` | Нужны, если `LLM_PROVIDER=ollama` — полностью офлайн-режим |
| `STATEMENTS_DIR` | `./data` | Папка с загруженными выписками |
| `MLFLOW_TRACKING_URI` | `sqlite:///./mlflow.db` | Локальное хранилище трейсов MLflow |
| `MLFLOW_EXPERIMENT_NAME` | `finagent` | Имя эксперимента в MLflow |

Переключиться на Ollama — значит не отправлять вообще ничего за пределы своей машины:

```env
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
```

(В Docker Compose бэкенд может достучаться до Ollama на хосте через `OLLAMA_HOST=http://host.docker.internal:11434` — это уже настроено в `docker-compose.yml`.)

## Трассировка вызовов агента (MLflow)

Каждый ход агента — вызовы модели, инструментов, условные переходы графа — трассируется автоматически (`mlflow.langchain.autolog()`), полностью локально, без сервера и телеметрии.

```bash
cd backend
uv run mlflow ui --backend-store-uri sqlite:///./mlflow.db
```

Откройте http://localhost:5000 — увидите дерево вызовов для каждого чата: `agent → chat model → tools → plot_chart → agent → …`.

## Бэкап и перенос на другой компьютер

Всё, что реально уникально для вас — это база Postgres (категории, правила категоризации продавцов, транзакции, история чатов) и папка `data/` с самими файлами выписок. RAG-индекс в Qdrant пересоздаётся из статичных файлов базы знаний автоматически при первом обращении — бэкапить его не нужно.

На старом компьютере (нужен запущенный `postgres` из `docker-compose.yml`, даже если бэкенд вы гоняете не в докере):

```bash
docker compose up -d postgres
scripts/backup.sh
# → finagent-backup-YYYYMMDD-HHMMSS.tar.gz
```

Перенесите архив на новый компьютер (флешка, облако, scp — как угодно) и там:

```bash
docker compose up -d postgres
scripts/restore.sh finagent-backup-YYYYMMDD-HHMMSS.tar.gz
```

Существующие данные в базе на новом компьютере будут заменены содержимым бэкапа.

## Структура проекта

```
FinAgent/
├── docker-compose.yml   postgres + qdrant + backend + frontend
├── scripts/             backup.sh / restore.sh
├── backend/
│   ├── app/             см. «Архитектура» выше
│   ├── migrations/      Alembic
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── api/          типизированный клиент + SSE-парсер
    │   ├── store/        Zustand
    │   └── components/
    │       ├── blocks/   metrics/donut/bars/line/table (recharts — лениво подгружаются)
    │       └── modals/   upload / settings
    └── Dockerfile        nginx, отдаёт статику и проксирует /api
```

## Известные ограничения

- Провайдер LLM переключается только через `.env` + рестарт — нет runtime-переключения в UI (осознанно, т.к. бэкенд читает настройки один раз при старте).
- Нет кнопки «удалить все данные» в настройках — под неё нет отдельного API. Для полной очистки: `docker compose down -v` (снесёт volume'ы Postgres/Qdrant/MLflow) плюс вручную удалить содержимое `data/` (это bind-mount на хосте, volume'ов не касается).
- Раздел категоризации в настройках показывает только продавцов, которые реально требуют внимания (`source = llm`), а не полный редактируемый список всех правил.

## Лицензия

[MIT](LICENSE) © Romanov Danil
