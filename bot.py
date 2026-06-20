import os
import asyncio
import logging
from typing import Dict, List

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from openai import OpenAI

# === ЛОГИ ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === ЗАГРУЗКА ENV ===
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat-v3-0324:free")

if not BOT_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Необходимо установить BOT_TOKEN и OPENROUTER_API_KEY в переменных окружения")

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# OpenRouter клиент (OpenAI-совместимый)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://bothost.ru",
        "X-Title": "AI Telegram Bot"
    }
)

# === КОНФИГУРАЦИЯ МОДЕЛЕЙ ===
MODELS = {
    "deepseek": "deepseek/deepseek-chat-v3-0324:free",
    "gemini": "google/gemini-2.0-flash-exp:free",
    "r1": "deepseek/deepseek-r1:free",
}

MODEL_NAMES = {
    "deepseek": "DeepSeek V3 (лучший универсальный)",
    "gemini": "Gemini 2.0 Flash (быстрый + большой контекст)",
    "r1": "DeepSeek R1 (сложные рассуждения)",
}

# === СИСТЕМНЫЕ ПРОМПТЫ (отдельные для разных режимов) ===
SYSTEM_PROMPTS = {
    "default": """Ты — полезный, дружелюбный и умный ИИ-ассистент. 
Отвечай кратко и по делу, но подробно когда нужно. 
Отвечай на русском языке, если пользователь пишет на русском.
Будь полезным и честным.""",

    "code": """Ты — эксперт-программист. 
Помогаешь писать, отлаживать и объяснять код на любом языке.
Давай чистый, рабочий код с комментариями.
Объясняй сложные моменты просто.
Если пользователь просит код — предоставляй его в блоках markdown.
Всегда указывай язык программирования.""",

    "creative": """Ты — креативный писатель и рассказчик.
Генерируешь интересные истории, сценарии, стихи, идеи.
Будь креативным, ярким и эмоциональным.
Можешь придумывать персонажей, диалоги и неожиданные повороты.
Отвечай творчески и вдохновляюще.""",

    "translator": """Ты — профессиональный переводчик.
Переводи точно и естественно.
Сохраняй смысл, стиль и тон оригинала.
Если текст на русском — переводи на английский, и наоборот.
Если язык не указан — спрашивай или определяй.
Можешь предлагать альтернативные варианты перевода.""",
}

# === ХРАНИЛИЩЕ (в памяти) ===
# Формат: chat_id -> {"mode": str, "model": str, "history": list, "custom_prompt": str | None}
user_data: Dict[int, Dict] = {}

def get_user_data(chat_id: int) -> Dict:
    if chat_id not in user_data:
        user_data[chat_id] = {
            "mode": "default",
            "model": DEFAULT_MODEL,
            "history": [],
            "custom_prompt": None,
        }
    return user_data[chat_id]

def get_system_prompt(chat_id: int) -> str:
    data = get_user_data(chat_id)
    if data["custom_prompt"]:
        return data["custom_prompt"]
    return SYSTEM_PROMPTS.get(data["mode"], SYSTEM_PROMPTS["default"])

def get_model_id(chat_id: int) -> str:
    data = get_user_data(chat_id)
    return data["model"]

def get_model_name(chat_id: int) -> str:
    data = get_user_data(chat_id)
    current_model = data["model"]
    for key, val in MODELS.items():
        if val == current_model:
            return MODEL_NAMES.get(key, key)
    return current_model

# === КЛАВИАТУРЫ ===
def get_modes_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔹 Обычный", callback_data="mode_default")
    builder.button(text="💻 Код", callback_data="mode_code")
    builder.button(text="🎨 Творческий", callback_data="mode_creative")
    builder.button(text="🌐 Переводчик", callback_data="mode_translator")
    builder.button(text="✏️ Свой промпт", callback_data="mode_custom")
    builder.adjust(2)
    return builder.as_markup()

def get_models_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="DeepSeek V3", callback_data="model_deepseek")
    builder.button(text="Gemini 2.0", callback_data="model_gemini")
    builder.button(text="DeepSeek R1", callback_data="model_r1")
    builder.adjust(1)
    return builder.as_markup()

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎭 Режимы", callback_data="show_modes")
    builder.button(text="🧠 Модели", callback_data="show_models")
    builder.button(text="🔄 Сбросить чат", callback_data="reset_chat")
    builder.button(text="📋 Текущие настройки", callback_data="show_current")
    builder.adjust(2)
    return builder.as_markup()

# === ФУНКЦИЯ ВЫЗОВА ИИ ===
async def call_openrouter(messages: List[dict], model: str, system_prompt: str) -> str:
    """Вызов OpenRouter через OpenAI-совместимый API"""
    try:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Используем синхронный клиент в потоке
        def sync_call():
            return client.chat.completions.create(
                model=model,
                messages=full_messages,
                max_tokens=2500,
                temperature=0.75,
                top_p=0.95,
            )
        
        response = await asyncio.to_thread(sync_call)
        
        if response.choices and response.choices[0].message:
            return response.choices[0].message.content.strip()
        return "Извини, не удалось получить ответ от ИИ."
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"OpenRouter error: {error_msg}")
        
        if "rate" in error_msg.lower() or "429" in error_msg:
            return "⚠️ Превышен лимит запросов к бесплатной модели. Подожди 30-60 секунд и попробуй снова."
        elif "401" in error_msg or "api key" in error_msg.lower():
            return "❌ Проблема с API ключом OpenRouter. Проверь ключ."
        else:
            return f"❌ Ошибка при обращении к ИИ: {error_msg[:150]}"

# === ОБРАБОТЧИКИ ===
@dp.message(Command("start"))
async def cmd_start(message: Message):
    chat_id = message.chat.id
    get_user_data(chat_id)  # инициализация
    
    welcome_text = (
        "🤖 Привет! Я **AI-бот** на базе бесплатных моделей OpenRouter.\n\n"
        "Доступные модели:\n"
        "• DeepSeek V3 — лучший универсальный\n"
        "• Gemini 2.0 Flash — быстрый и мощный\n"
        "• DeepSeek R1 — для сложных задач\n\n"
        "У меня есть разные режимы с отдельными промптами.\n\n"
        "Просто пиши мне сообщение, и я отвечу!\n"
        "Используй кнопки ниже или команды /help"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 **Команды бота:**\n\n"
        "/start — запуск\n"
        "/help — эта помощь\n"
        "/modes — список режимов\n"
        "/mode <режим> — сменить режим\n"
        "/model <deepseek|gemini|r1> — сменить модель\n"
        "/setprompt <текст> — установить свой системный промпт\n"
        "/reset — очистить историю чата\n"
        "/current — показать текущие настройки\n\n"
        "💡 Просто пиши сообщения — я отвечу как ИИ.\n"
        "Можно использовать разные режимы для разных задач!"
    )
    await message.answer(help_text, reply_markup=get_main_keyboard())

@dp.message(Command("modes"))
async def cmd_modes(message: Message):
    text = "🎭 **Выбери режим (отдельный промпт):**"
    await message.answer(text, reply_markup=get_modes_keyboard())

@dp.message(Command("model"))
async def cmd_model(message: Message, command: CommandObject):
    chat_id = message.chat.id
    data = get_user_data(chat_id)
    
    if not command.args:
        text = "🧠 **Доступные модели:**\n\n"
        for key, name in MODEL_NAMES.items():
            current = " ✅" if MODELS[key] == data["model"] else ""
            text += f"• `{key}` — {name}{current}\n"
        text += "\nИспользуй: `/model deepseek` или кнопки ниже"
        await message.answer(text, reply_markup=get_models_keyboard())
        return
    
    arg = command.args.strip().lower()
    if arg in MODELS:
        data["model"] = MODELS[arg]
        await message.answer(
            f"✅ Модель изменена на **{MODEL_NAMES[arg]}**",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer("❌ Неизвестная модель. Доступны: deepseek, gemini, r1")

@dp.message(Command("setprompt"))
async def cmd_setprompt(message: Message, command: CommandObject):
    chat_id = message.chat.id
    data = get_user_data(chat_id)
    
    if not command.args:
        await message.answer(
            "✏️ Чтобы установить свой промпт:\n\n"
            "`/setprompt Ты — эксперт по маркетингу...`\n\n"
            "Чтобы сбросить свой промпт:\n"
            "`/setprompt reset`"
        )
        return
    
    new_prompt = command.args.strip()
    
    if new_prompt.lower() == "reset":
        data["custom_prompt"] = None
        await message.answer("✅ Свой промпт сброшен. Используется промпт текущего режима.")
    else:
        data["custom_prompt"] = new_prompt
        await message.answer(
            "✅ **Свой системный промпт установлен!**\n\n"
            "Теперь все ответы будут использовать этот промпт.\n"
            "Чтобы сбросить — `/setprompt reset`"
        )

@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    chat_id = message.chat.id
    data = get_user_data(chat_id)
    data["history"] = []
    await message.answer("🧹 История чата очищена. Начинаем с чистого листа!")

@dp.message(Command("current"))
async def cmd_current(message: Message):
    chat_id = message.chat.id
    data = get_user_data(chat_id)
    
    mode = data["mode"]
    model_name = get_model_name(chat_id)
    custom = "Да (свой)" if data["custom_prompt"] else "Нет"
    
    text = (
        f"📋 **Текущие настройки:**\n\n"
        f"• Режим: **{mode}**\n"
        f"• Модель: **{model_name}**\n"
        f"• Свой промпт: **{custom}**\n"
        f"• Сообщений в истории: **{len(data['history'])}**\n\n"
        "Используй кнопки или команды для изменения."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message(Command("mode"))
async def cmd_mode(message: Message, command: CommandObject):
    chat_id = message.chat.id
    data = get_user_data(chat_id)
    
    if not command.args:
        await message.answer("🎭 Выбери режим:", reply_markup=get_modes_keyboard())
        return
    
    mode = command.args.strip().lower()
    if mode in SYSTEM_PROMPTS:
        data["mode"] = mode
        data["custom_prompt"] = None
        await message.answer(
            f"✅ Режим изменён на **{mode}**\n"
            f"Теперь используется соответствующий промпт.",
            reply_markup=get_main_keyboard()
        )
    else:
        available = ", ".join(SYSTEM_PROMPTS.keys())
        await message.answer(f"❌ Неизвестный режим. Доступны: {available}")

# === ОБРАБОТКА КНОПОК ===
@dp.callback_query(F.data.startswith("mode_"))
async def callback_mode(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    data = get_user_data(chat_id)
    
    mode = callback.data.replace("mode_", "")
    
    if mode == "custom":
        await callback.message.edit_text(
            "✏️ Отправь команду:\n\n"
            "`/setprompt Твой промпт здесь`\n\n"
            "Или `/setprompt reset` чтобы отменить."
        )
        await callback.answer()
        return
    
    if mode in SYSTEM_PROMPTS:
        data["mode"] = mode
        data["custom_prompt"] = None
        await callback.message.edit_text(
            f"✅ Режим успешно изменён на **{mode}**!\n\n"
            "Теперь пиши мне сообщение.",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@dp.callback_query(F.data.startswith("model_"))
async def callback_model(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    data = get_user_data(chat_id)
    
    model_key = callback.data.replace("model_", "")
    
    if model_key in MODELS:
        data["model"] = MODELS[model_key]
        await callback.message.edit_text(
            f"✅ Модель изменена на **{MODEL_NAMES[model_key]}**",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@dp.callback_query(F.data == "show_modes")
async def callback_show_modes(callback: CallbackQuery):
    await callback.message.edit_text("🎭 Выбери режим:", reply_markup=get_modes_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "show_models")
async def callback_show_models(callback: CallbackQuery):
    await callback.message.edit_text("🧠 Выбери модель:", reply_markup=get_models_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "reset_chat")
async def callback_reset(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    data = get_user_data(chat_id)
    data["history"] = []
    await callback.message.edit_text("🧹 История очищена!")
    await callback.answer("Чат сброшен ✅")

@dp.callback_query(F.data == "show_current")
async def callback_current(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    data = get_user_data(chat_id)
    
    mode = data["mode"]
    model_name = get_model_name(chat_id)
    custom = "Да" if data["custom_prompt"] else "Нет"
    
    text = (
        f"📋 **Текущие настройки:**\n\n"
        f"• Режим: **{mode}**\n"
        f"• Модель: **{model_name}**\n"
        f"• Свой промпт: **{custom}**\n"
        f"• Сообщений в истории: **{len(data['history'])}**"
    )
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())
    await callback.answer()

# === ОСНОВНОЙ ЧАТ ===
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message):
    chat_id = message.chat.id
    user_text = message.text
    
    data = get_user_data(chat_id)
    
    # Добавляем сообщение пользователя в историю
    data["history"].append({"role": "user", "content": user_text})
    
    # Ограничиваем историю
    if len(data["history"]) > 12:
        data["history"] = data["history"][-12:]
    
    # Получаем текущие параметры
    system_prompt = get_system_prompt(chat_id)
    model_id = get_model_id(chat_id)
    
    # Показываем "печатает..."
    await bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Вызываем ИИ
    ai_response = await call_openrouter(
        messages=data["history"],
        model=model_id,
        system_prompt=system_prompt
    )
    
    # Добавляем ответ в историю
    data["history"].append({"role": "assistant", "content": ai_response})
    
    # Отправляем ответ
    try:
        await message.answer(ai_response, parse_mode="Markdown")
    except Exception:
        await message.answer(ai_response)

# === ЗАПУСК ===
async def main():
    logger.info("🚀 Запуск AI Telegram бота...")
    logger.info(f"Используется модель по умолчанию: {DEFAULT_MODEL}")
    
    # Polling — надёжный способ для Bothost.ru
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())