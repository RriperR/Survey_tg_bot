# Q Tg Bot

Telegram-бот для автоматизации опросов сотрудников, сбора ответов и рассылки отчётов.

---

## 📦 Структура проекта

```
Q_tg_bot/
├── app/
│   ├── bot.py               # Точка входа: инициализация бота, планировщика и логирования
│   ├── logger.py            # Конфигурация именованных логгеров и ротации файлов
│   ├── utils.py             # Утилиты для работы с Google Sheets (gspread)
│   ├── keyboards.py         # Построение InlineKeyboard для опросов и регистрации
│   ├── handlers/            # Обработчики Telegram-команд и callback'ов
│   │   ├── register_handlers.py
│   │   ├── survey_handlers.py
│   │   └── admin_handlers.py
│   ├── services/            # Бизнес-логика и задачи планировщика
│   │   ├── survey_scheduler.py  # Расписание и отправка опросов
│   │   ├── reports.py           # Генерация и отправка ежемесячных отчётов
│   │   └── survey_reset.py      # Сброс незавершённых опросов и уведомления
│   └── database/            # Слой доступа к данным
│       ├── models.py        # SQLAlchemy-модели: Worker, Survey, Pair, Answer
│       └── requests.py      # Асинхронные CRUD-функции и helper'ы
├── logs/                    # Папка для логов, монтируется в Docker
├── .env                     # Переменные окружения
├── .gitignore               # Исключения для Git (venv, pycache и т.п.)
├── docker-compose.yml       # Docker-сборка для бота и БД
├── Dockerfile               # Инструкция сборки образа бота
├── q-bot-key2.json          # Ключ сервисного аккаунта Google Sheets
├── requirements.txt         # Зависимости проекта
└── README.md                # Документация
```

---

## 🚀 Установка и запуск

1. Клонируйте репозиторий и перейдите в корень:

   ```bash
   git clone <repo_url>
   cd Q_tg_bot
   ```
2. Создайте виртуальное окружение и активируйте его:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```
4. Создайте файл `.env` с параметрами:

   ```env
   BOT_TOKEN=<your-telegram-token>
   DB_HOST=...
   DB_PORT=5432
   DB_NAME=...
   DB_USER=...
   DB_PASSWORD=...
   TABLE=<google_sheet-table-name>
   ANSWERS_TABLE=<google_sheet-table-name>
   REPORT_CHAT_ID=<tg-chat-id>
   ```
5. Поместите `q-bot-key2.json` рядом с `.env`.
6. Запустите бота:

   ```bash
   python -m app.bot
   ```

---

## 🔧 Логирование

В `app/logger.py` используется функция `setup_logger(name, filename)`, которая настраивает:

* Уровень `INFO`
* `TimedRotatingFileHandler` (ротация в полночь, 7 backup)
* Отдельные файлы для каждого модуля:

  * `bot.log`, `reports.log`, `survey.log`, `reset.log`, и т.д.

В каждом модуле создаётся логгер:

```python
from app.logger import setup_logger
logger = setup_logger(__name__, "<module>.log")
```

---

## 🗄️ Работа с базой данных: `database/requests.py`

Набор функций для CRUD и выборок:

| Функция                                  | Описание                                          |
| ---------------------------------------- | ------------------------------------------------- |
| `get_worker_by_fullname(name)`           | Возвращает `Worker` по `full_name` или `None`.    |
| `get_worker_by_chat_id(chat_id)`         | Поиск сотрудника по `chat_id`.                    |
| `get_unregistered_workers()`             | Список `Worker` без `chat_id`.                    |
| `set_chat_id(worker_id, chat_id)`        | Привязка `chat_id` к работнику (не дублирует).    |
| `set_worker_file_id(worker_id, file_id)` | Сохранение `file_id` (ID картинки).               |
| `get_survey_by_name(name)`               | Возврат `Survey` по имени (`speciality`).         |
| `get_ready_pairs_by_date(date)`          | Получить очередные пары для опроса по дате.       |
| `get_next_ready_pair(subject)`           | Первая готовая пара `Pair` для данного `subject`. |
| `get_in_progress_pairs()`                | Список `Pair` со статусом `in_progress`.          |
| `update_pair_status(pair_id, status)`    | Обновление статуса пары.                          |
| `reset_incomplete_surveys()`             | Сброс всех `in_progress` → `ready`.               |
| `save_answer(answer)`                    | Сохранение объекта `Answer` в БД.                 |
| `get_all_answers()`                      | Все записи `Answer`.                              |

---

## 📤 Расписание опросов: `survey_scheduler.py`

1. **Сброс незавершённых**: вызывает `reset_incomplete_surveys()` перед рассылкой.
2. **Выборка активных работников**: все `Worker` с заполненным `chat_id`.
3. **Получение готовых пар**: `get_ready_pairs_by_date(today_str)` возвращает список `Pair` для опроса.
4. **Отправка опросов**:

   * Для каждого `subject из Pair` берётся текст вопроса из `Survey` и строится клавиатура 1–5, если вопрос типа int.
   * Статус пары меняется на `in_progress` через `update_pair_status(pair_id, "in_progress")`.
5. **Обработка ошибок** и логирование каждого шага.

---

## 📝 Обработка ответов: `survey_handlers.py`

* **FSM (Finite State Machine)** из `aiogram.fsm.state` для последовательного задавания вопросов:

  1. При запуске опроса создаётся состояние `SurveyStates.Q1`, `Q2`, ...
  2. Для каждого состояния отправляется вопрос из `Survey`.
  3. Ответ по кнопке или текст сохраняется в FSM.
  4. После `Q5` завершение состояния, статус `Pair` обновляется в БД, и сразу запускается следующий опрос (если есть).

* **Обработчики**:

  * `@dp.message(lambda message: state == SurveyStates.Qn)` — проверка состояния
  * `@dp.callback_query` для кнопок с `data="answer:<n>:<value>"`

---

## 🔄 Админские утилиты: `admin_handlers.py`

* `/upd` — полная синхронизация таблиц из Google Sheets.
* `/upd_surveys` — только таблица опросов.
* `/export` — экспорт результатов из БД в Google Sheets.

---

## 📈 Ежемесячные отчёты: `reports.py`

Для каждого сотрудника генерирует средние оценки по `int` вопросам за месяц, полгода и всё время. Также включает `str` ответы (рекомендации) и статистику смен: с какими врачами и сколько раз ассистент работал за последний месяц. Формирует Markdown и отправляет отдельными сообщениями через `safe_send_long_message()`.

---

## ⚙️ Docker и деплой

* Пример `docker-compose.yml` в корне для бота и PostgreSQL.
* Логи монтируются в том же `logs/`.
* Планировщик (`apscheduler`) запускается вместе с ботом.

---

## 🛠️ Поддержка и расширение

1. Поменять структуру БД и логику работы так, чтобы не зависеть от количества вопросов в опросе.
2. Web-интерфейс для управления опросами и просмотра отчётов.
