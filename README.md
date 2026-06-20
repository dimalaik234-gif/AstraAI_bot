# Telegram AI Bot на Bothost.ru

AI-бот для Telegram с интеграцией **OpenRouter** (бесплатные модели: DeepSeek, Gemini и др.).

## Возможности
- 💬 Умный чат с ИИ (DeepSeek / Gemini / DeepSeek-R1)
- 🎭 Несколько режимов с отдельными системными промптами:
  - Default (обычный помощник)
  - Code (программист)
  - Creative (творческий писатель)
  - Translator (переводчик RU↔EN)
  - Custom (свой промпт)
- 📝 Установка своего системного промпта командой `/setprompt`
- 🔄 Смена модели: `/model deepseek`, `/model gemini`, `/model r1`
- 🧠 Контекст разговора (история сообщений)
- 🔄 Сброс истории `/reset`
- 📋 Клавиатуры для удобного управления

## Установка и запуск на Bothost.ru

### 1. Получи токены
1. Создай бота в @BotFather → скопируй `BOT_TOKEN`
2. Перейди на [openrouter.ai](https://openrouter.ai) → войди → создай API Key (бесплатно, без карты)
3. Скопируй ключ

### 2. Подготовь код
Склонируй или загрузи этот репозиторий.

### 3. Развёртывание на Bothost.ru

1. Зарегистрируйся на [bothost.ru](https://bothost.ru)
2. Создай новый проект (бесплатный тариф)
3. Загрузи код:
   - Через Git (рекомендуется): подключи GitHub репозиторий
   - Или загрузи файлы вручную через панель
4. В настройках проекта добавь переменные окружения:
   - `BOT_TOKEN` = твой токен
   - `OPENROUTER_API_KEY` = твой ключ OpenRouter
   - `DEFAULT_MODEL` = `deepseek/deepseek-chat-v3-0324:free` (или другой)
5. Укажи entrypoint: `bot.py`
6. Нажми **Deploy** (или "Развернуть")

Платформа автоматически:
- Выдаст публичный URL с HTTPS
- Настроит Webhook (или поддерживает polling)
- Запустит бота

### Локальный запуск (для теста)
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
# или venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# отредактируй .env
python bot.py
```

### Полезные команды бота
- `/start` — приветствие
- `/help` — помощь
- `/modes` — список режимов
- `/mode <название>` — сменить режим
- `/model <deepseek|gemini|r1>` — сменить модель
- `/setprompt <текст>` — установить свой промпт (только для текущего чата)
- `/reset` — сбросить историю чата
- `/current` — показать текущий режим и модель

### Советы
- Бесплатные модели имеют лимиты (rate limits). При превышении бот скажет "Подожди немного".
- История чата хранится в памяти (сбрасывается при перезапуске).
- Для продакшена можно добавить SQLite (по желанию).

## Рекомендуемые бесплатные модели (OpenRouter)
- `deepseek/deepseek-chat-v3-0324:free` — лучший универсальный
- `google/gemini-2.0-flash-exp:free` — быстрый + большой контекст
- `deepseek/deepseek-r1:free` — для сложных рассуждений

---

Создано для хостинга Bothost.ru + OpenRouter (2026)