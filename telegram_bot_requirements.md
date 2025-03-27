# Промт для проектирования телеграм-бота для ведения журнала встреч

## Функциональные требования

### Основной сценарий использования
- Создание бота для ведения журнала встреч с периодичностью около раза в 10 минут
- Сохранение лога переписки и файлов на Яндекс.Диск
- Средний объем данных за встречу: 5-10 текстовых сообщений и несколько файлов
- Обязательно распознавание речи из голосовых сообщений и сохранение текста в лог



### Управление пользователями и папками
- Администратор должен иметь возможность назначать доступные папки для пользователей
- Администратор управляет списком допущенных пользователей
- Настройка доступа выполняется редко, обычно один раз

### Интеграция с Яндекс.Диском
- Базовые функции для работы с Яндекс.Диском:
  - Создание/чтение/обновление текстовых файлов
  - Загрузка файлов (в основном фото)
  - Навигация по структуре папок (схоже с логикой в folder_navigation.py)
- Структура папок на Яндекс.Диске соответствует бизнес-процессам

### Медиафайлы
- Основной тип медиафайлов: фото и документы
- Сохранение истории добавления файлов в ЛОГ  файл
- Обязательно распознавание речи из голосовых сообщений
- Результаты распознавания сохраняются в лог файл

## Архитектурные требования

### Минимализм и модульность
- Избегать чрезмерного усложнения кода
- Четкое разделение ответственности между модулями
- Минимизировать зависимости между компонентами

### Обработка ошибок
- Надежная система обработки ошибок с логированием
- Корректное восстановление после сбоев в работе API Telegram и Яндекс.Диска

### Хранение состояния
- Упрощенная модель состояния, ориентированная только на необходимый функционал
- Не нужна функциональность восстановления или возврата к предыдущим сессиям 

## Структура проекта

### Корневая структура
```
/
|- config/           # Конфигурационные файлы
|  |- config.py      # Основные настройки и переменные окружения
|  |- logging_config.py # Настройки логирования
|
|- src/
|  |- handlers/      # Обработчики сообщений
|  |  |- command_handler.py  # Обработка команд
|  |  |- file_handler.py     # Обработка файлов
|  |  |- admin_handler.py    # Административные функции
|  |
|  |- utils/         # Утилиты
|  |  |- yadisk_helper.py    # Работа с Яндекс.Диском
|  |  |- folder_navigation.py # Навигация по папкам
|  |  |- speech_recognition.py # Распознавание речи
|  |  |- session_utils.py    # Управление сессиями
|  |
|  |- main.py        # Точка входа приложения
|
|- .env.example      # Пример конфигурационного файла
|- .gitignore        # Файлы, исключаемые из репозитория
|- requirements.txt  # Зависимости проекта
|- README.md         # Документация
```

### Модули и их ответственность

#### config/config.py
- Загрузка переменных окружения
- Базовая валидация конфигурации
- Константы и настройки

#### src/main.py
- Инициализация бота и маршрутизация сообщений
- Настройка обработчиков и middleware
- Обработка глобальных ошибок
- Запуск приложения

#### src/handlers/command_handler.py
- Обработка команд /start, /help, /new (создание встречи)
- Обработка команд /end (завершение)
- Работа с выбором папок

#### src/handlers/file_handler.py
- Обработка входящих файлов (фото, документы)
- Обработка голосовых сообщений с передачей их в модуль распознавания речи
- Загрузка файлов на Яндекс.Диск

#### src/handlers/admin_handler.py
- Административные функции:
  - Добавление/удаление папок
  - Управление пользователями
  - Настройка разрешений

#### src/utils/yadisk_helper.py
- Работа с API Яндекс.Диска
- Создание/чтение/обновление файлов
- Управление папками
- Обработка ошибок API Яндекс.Диска
- Отказоустойчивый режим при отсутствии соединения

#### src/utils/folder_navigation.py
- Навигация по структуре папок
- Построение клавиатуры для выбора папок
- Обработка выбора папок пользователем
- Хранить кэш названий папок для быстрой навигации 

#### src/utils/speech_recognition.py
- Распознавание речи из голосовых сообщений
- Обработка аудиофайлов
- Интеграция с API распознавания речи

#### src/utils/session_utils.py
- Управление состоянием сессий пользователей
- Ведение логов встреч 

## Принципы разработки

### Изоляция состояния
- Каждый модуль должен иметь четко определенное состояние
- Минимизировать глобальное состояние
- Использовать инъекцию зависимостей для тестируемости

### Обработка ошибок
- Каждый метод должен корректно обрабатывать ошибки и не допускать краха приложения
- Логирование всех ошибок с контекстом
- Graceful degradation при недоступности внешних API

### Производительность
- Минимизировать число запросов к API Telegram и Яндекс.Диска
- Оптимизировать загрузку и кэширование данных
- Асинхронная обработка задач для поддержки параллельных сессий

### Простота
- Не усложнять дизайн без необходимости
- Предпочитать простые, понятные подходы сложным решениям
- Избегать преждевременной оптимизации
- Использовать конвенции именования и документирования

## Технический стек

### Базовые библиотеки
- python-telegram-bot (версия 22.0) - для работы с API Telegram
- yadisk (версия 3.2.0) - для работы с API Яндекс.Диска
- python-dotenv (версия 1.0.1) - для загрузки переменных окружения
- requests (версия 2.32.3) - для HTTP-запросов
- SpeechRecognition (версия 3.10.0) - для распознавания речи
- pydub (версия 0.25.1) - для обработки аудиофайлов

### Ограничения
- Ограничить количество зависимостей от внешних библиотек
- По возможности использовать стандартную библиотеку Python

## Примеры реализации из текущего проекта

### Пример конфигурации (config.py)

```python
import os
from dotenv import load_dotenv
from datetime import datetime
import json
from pathlib import Path
import logging

# Загрузка переменных окружения из файла .env
load_dotenv()

# Токены
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
YANDEX_DISK_TOKEN = os.getenv('YANDEX_DISK_TOKEN')

# ID администраторов
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Директории и файлы
DATA_DIR = Path('data')
UPLOAD_DIR = DATA_DIR / 'uploads'  # Директория для временного хранения загружаемых файлов
FOLDERS_FILE = DATA_DIR / 'allowed_folders.json'
USERS_FILE = DATA_DIR / 'allowed_users.json'

# Настройки логирования
LOG_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())

# Генерация текущего таймштампа в формате "дата_время"
def get_current_timestamp():
    """Возвращает текущий таймштамп в формате YYYYMMDD_HHMMSS"""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

# Функция для проверки прав администратора
def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

# Проверка обязательных переменных окружения
def validate_config():
    """Проверяет наличие всех необходимых переменных окружения и создает необходимые директории"""
    required_vars = ['TELEGRAM_TOKEN', 'YANDEX_DISK_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
    
    # Создаем директории, если они еще не существуют
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Создаем файлы с разрешенными папками и пользователями, если они еще не существуют
    if not FOLDERS_FILE.exists():
        with open(FOLDERS_FILE, 'w') as f:
            json.dump([], f)
    
    if not USERS_FILE.exists():
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
```

### Пример основного файла (main.py)

```python
import logging
import os
import signal
import atexit
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler,
    ConversationHandler, 
    MessageHandler, 
    filters
)
from telegram.error import TelegramError, NetworkError

# Внутренние модули
from config.config import validate_config, TELEGRAM_TOKEN, DATA_DIR
from config.logging_config import configure_logging
from src.handlers.command_handler import (
    start, help_command, new_meeting, handle_category, navigate_folders,
    current_meeting, cancel, create_folder, handle_session_callback, end_session
)
from src.handlers.file_handler import handle_file
from src.handlers.media_handlers.photo_handler import handle_photo
from src.handlers.media_handlers.voice_handler import handle_voice
from src.utils.error_utils import handle_error
from src.utils.yadisk_helper import YaDiskHelper

# Настройка логирования
configure_logging()
logger = logging.getLogger(__name__)

# Глобальный объект YaDiskHelper
yadisk_helper = None

def cleanup():
    """Очистка ресурсов при выходе"""
    try:
        # Здесь можно добавить необходимую логику очистки
        logger.info("Выполнение очистки при завершении работы")
    except Exception as e:
        logger.error(f"Ошибка при очистке: {e}")

async def global_error_handler(update: Update, context) -> None:
    """Глобальный обработчик ошибок для приложения"""
    error = context.error
    
    # Логирование ошибки
    logger.error(f"Ошибка в обработчике: {context.error}", exc_info=True)
    
    # Обработка ошибок
    await handle_error(update, error, context.bot)

def main() -> None:
    """Основная функция для запуска бота"""
    try:
        # Проверка конфигурации
        validate_config()
        
        # Инициализация yadisk_helper
        global yadisk_helper
        yadisk_helper = YaDiskHelper()
        
        # Настройка приложения Telegram
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Регистрация глобального обработчика ошибок
        application.add_error_handler(global_error_handler)
        
        # Регистрация обработчиков
        register_handlers(application)
        
        # Запуск бота
        logger.info("Бот запущен")
        application.run_polling()
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {str(e)}", exc_info=True)
        return

def register_handlers(application):
    """Регистрирует все обработчики для приложения"""
    # Базовые команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчик для создания встречи
    new_meeting_handler = ConversationHandler(
        entry_points=[CommandHandler("new", new_meeting)],
        states={
            # Состояния беседы
            "CHOOSE_FOLDER": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category)],
            "NAVIGATE_SUBFOLDERS": [MessageHandler(filters.TEXT & ~filters.COMMAND, navigate_folders)],
            "CREATE_FOLDER": [MessageHandler(filters.TEXT & ~filters.COMMAND, create_folder)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(new_meeting_handler)
    
    # Просмотр и завершение встречи
    application.add_handler(CommandHandler("current", current_meeting))
    application.add_handler(CommandHandler("end", end_session))
    
    # Обработка callback-запросов (кнопок)
    application.add_handler(CallbackQueryHandler(handle_session_callback, pattern=r'^session_'))
    
    # Обработка файлов
    application.add_handler(MessageHandler(filters.PHOTO, lambda update, context: handle_file(update, context, handle_photo)))
    application.add_handler(MessageHandler(filters.VOICE, lambda update, context: handle_file(update, context, handle_voice)))
    
    # Обработка текста (должна быть последней)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    # Регистрация функции очистки и обработчиков сигналов
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())
    
    # Запуск бота
    main() 

### Пример класса для управления сессиями (session_utils.py)

```python
import logging
import time
from typing import Dict, Optional
from config.config import get_current_timestamp

logger = logging.getLogger(__name__)

class SessionState:
    """Класс для хранения данных о текущей сессии встречи"""
    def __init__(self, root_folder: str, folder_path: str, folder_name: str, user_id: int):
        self.root_folder = root_folder
        self.folder_path = folder_path
        self.folder_name = folder_name
        self.timestamp = get_current_timestamp()
        self.txt_file_path = f"{folder_path}/{self.timestamp}_visit_{folder_name}_{user_id}.txt"
        self.file_prefix = f"{self.timestamp}_Files_{folder_name}_{user_id}"
        self.user_id = user_id
        self.messages = []  # Список сообщений в сессии
        self.start_time = time.time()
    
    def get_txt_filename(self) -> str:
        """Возвращает имя текстового файла"""
        return f"{self.timestamp}_visit_{self.folder_name}_{self.user_id}.txt"
    
    def get_media_prefix(self) -> str:
        """Возвращает префикс для медиафайлов"""
        return f"{self.timestamp}_Files_{self.folder_name}_{self.user_id}"
    
    def add_message(self, message: str, author: str = "") -> None:
        """Добавляет сообщение в историю сессии"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        author_prefix = f"[{author}] " if author else ""
        formatted_message = f"[{timestamp}] {author_prefix}{message}"
        self.messages.append(formatted_message)
        logger.debug(f"Добавлено сообщение в сессию: {formatted_message[:50]}...")
    
    def get_session_summary(self) -> str:
        """Возвращает сводку по сессии"""
        duration = time.time() - self.start_time
        hours, remainder = divmod(int(duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Получаем количество сообщений
        total_messages = len(self.messages)
        
        summary = [
            f"📁 Папка: {self.folder_path}",
            f"📄 Файл: {self.get_txt_filename()}",
            f"⏱ Продолжительность: {hours}ч {minutes}м {seconds}с",
            f"✍️ Количество записей: {total_messages}"
        ]
        
        return "\n".join(summary)

class StateManager:
    """Класс для управления состояниями пользователей"""
    def __init__(self):
        # Ключ: user_id, Значение: текущая сессия
        self.sessions: Dict[int, SessionState] = {}
        # Ключ: user_id, Значение: текущее состояние в диалоге
        self.states: Dict[int, str] = {}
        # Ключ: user_id, Значение: временные данные
        self.data: Dict[int, Dict] = {}
    
    def set_state(self, user_id: int, state: str) -> None:
        """Устанавливает состояние для пользователя"""
        self.states[user_id] = state
        logger.debug(f"Установлено состояние {state} для пользователя {user_id}")
    
    def get_state(self, user_id: int) -> Optional[str]:
        """Возвращает текущее состояние пользователя"""
        return self.states.get(user_id)
    
    def reset_state(self, user_id: int) -> None:
        """Сбрасывает состояние пользователя"""
        if user_id in self.states:
            del self.states[user_id]
    
    def set_session(self, user_id: int, session: SessionState) -> None:
        """Устанавливает сессию для пользователя"""
        # Сначала завершаем текущую сессию, если она существует
        self.clear_session(user_id)
        # Затем устанавливаем новую
        self.sessions[user_id] = session
        logger.info(f"Установлена новая сессия для пользователя {user_id}: {session.folder_path}")
    
    def get_session(self, user_id: int) -> Optional[SessionState]:
        """Возвращает текущую сессию пользователя"""
        return self.sessions.get(user_id)
    
    def clear_session(self, user_id: int) -> None:
        """Удаляет сессию пользователя"""
        if user_id in self.sessions:
            logger.info(f"Сессия пользователя {user_id} завершена: {self.sessions[user_id].folder_path}")
            del self.sessions[user_id]
    
    def has_active_session(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя активная сессия"""
        return user_id in self.sessions

# Создаем глобальный экземпляр менеджера состояний
state_manager = StateManager()

### Пример навигации по папкам (folder_navigation.py)

```python
import logging
from typing import List, Dict, Any, Tuple, Optional, Callable
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class FolderNavigator:
    """Класс для работы с навигацией по папкам Яндекс.Диска в Telegram боте."""
    def __init__(
        self, 
        yadisk_helper,
        folder_selected_callback: Optional[Callable] = None,
        title: str = "Выберите папку:",
        add_current_folder_button: bool = True,
        create_folder_button: bool = True,
        extra_buttons: List[str] = None
    ):
        """Инициализация навигатора по папкам."""
        self.yadisk_helper = yadisk_helper
        self.title = title
        self.add_current_folder_button = add_current_folder_button
        self.create_folder_button = create_folder_button
        self.extra_buttons = extra_buttons or []
        self.folder_selected_callback = folder_selected_callback
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """Нормализует путь для Яндекс.Диска"""
        path = path.replace("disk:", "")
        path = path.replace("//", "/")
        path = path.rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return path
    
    async def get_folders(self, path: str) -> List[Any]:
        """Получает список папок по указанному пути"""
        try:
            items = list(self.yadisk_helper.disk.listdir(path))
            return [item for item in items if item.type == "dir"]
        except Exception as e:
            logger.error(f"Ошибка при получении списка папок: {str(e)}", exc_info=True)
            return []
    
    def build_keyboard(self, folders: List[Any], include_current_folder: bool = True) -> List[List[str]]:
        """Формирует клавиатуру для выбора папок"""
        keyboard = []
        
        # Добавляем папки в клавиатуру
        for i, folder in enumerate(folders, 1):
            keyboard.append([f"{i}. {folder.name}"])
        
        # Добавляем дополнительные кнопки
        if include_current_folder and self.add_current_folder_button:
            keyboard.append(["Добавить эту папку"])
        
        if self.create_folder_button:
            keyboard.append(["Создать новую папку"])
        
        # Добавляем дополнительные кнопки
        for button in self.extra_buttons:
            keyboard.append([button])
        
        # Всегда добавляем кнопку "Назад"
        keyboard.append(["Назад"])
        
        return keyboard
    
    async def show_folders(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        path: str = "/"
    ) -> None:
        """Отображает список папок по указанному пути"""
        normalized_path = self.normalize_path(path)
        folders = await self.get_folders(normalized_path)
        
        # Формируем сообщение
        message = f"{self.title}\n\n"
        if path != "/":
            message = f"Подпапки в {normalized_path}:\n\n"
        
        # Добавляем папки в сообщение
        for i, folder in enumerate(folders, 1):
            message += f"{i}. 📁 {folder.name}\n"
        
        # Сохраняем список папок и путь в контексте
        context.user_data["folders"] = folders
        context.user_data["current_path"] = normalized_path
        
        # Отправляем сообщение с папками
        await update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(
                self.build_keyboard(folders),
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
```

### Пример обработки фото (photo_handler.py)

```python
import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from src.utils.state_manager import state_manager
from config.config import UPLOAD_DIR

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает фотографии, отправленные пользователем
    """
    user_id = update.effective_user.id
    session = state_manager.get_session(user_id)
    
    if not session:
        await update.message.reply_text("Сначала нужно начать встречу с помощью команды /new")
        return
    
    try:
        # Получаем самое большое доступное изображение
        photo_file = await update.message.photo[-1].get_file()
        
        # Создаем временный путь для сохранения
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, f"photo_{session.timestamp}.jpg")
        
        # Загружаем фото
        await photo_file.download_to_drive(file_path)
        
        # Формируем путь на Яндекс.Диске
        yadisk_path = f"{session.folder_path}/{session.file_prefix}_{photo_file.file_unique_id}.jpg"
        
        # Загружаем на Яндекс.Диск
        yadisk_helper.upload_file(file_path, yadisk_path)
        
        # Добавляем сообщение в лог
        username = update.effective_user.username or update.effective_user.first_name
        session.add_message(f"Загружено фото: {yadisk_path}", author=username)
        
        # Отвечаем пользователю
        await update.message.reply_text("Фото успешно сохранено!")
        
        # Удаляем временный файл
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        await update.message.reply_text(f"Не удалось сохранить фото: {str(e)}")

### Пример распознавания речи из голосовых сообщений (voice_handler.py)

```python
import logging
import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes
import speech_recognition as sr
from pydub import AudioSegment
from src.utils.state_manager import state_manager

logger = logging.getLogger(__name__)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает голосовые сообщения и распознает речь
    """
    user_id = update.effective_user.id
    session = state_manager.get_session(user_id)
    
    if not session:
        await update.message.reply_text("Сначала нужно начать встречу с помощью команды /new")
        return
    
    try:
        # Получаем голосовое сообщение
        voice_file = await update.message.voice.get_file()
        
        # Создаем временные файлы
        ogg_file = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        
        # Загружаем ogg файл
        await voice_file.download_to_drive(ogg_file.name)
        
        # Конвертируем ogg в wav для распознавания
        audio = AudioSegment.from_file(ogg_file.name, format="ogg")
        audio.export(wav_file.name, format="wav")
        
        # Распознаем речь
        r = sr.Recognizer()
        with sr.AudioFile(wav_file.name) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="ru-RU")
        
        # Сохраняем транскрипцию
        username = update.effective_user.username or update.effective_user.first_name
        session.add_message(f"Голосовое сообщение: {text}", author=username)
        
        # Отправляем расшифровку пользователю
        await update.message.reply_text(f"Распознанный текст: {text}")
        
        # Очищаем временные файлы
        ogg_file.close()
        wav_file.close()
        os.unlink(ogg_file.name)
        os.unlink(wav_file.name)
        
    except sr.UnknownValueError:
        logger.warning("Не удалось распознать речь")
        await update.message.reply_text("Не удалось распознать речь. Попробуйте говорить более четко.")
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        await update.message.reply_text(f"Произошла ошибка при обработке голосового сообщения: {str(e)}")

## Рекомендации по реализации

### Начать с базовой функциональности
1. Настроить обработку команд и базовый цикл работы
2. Реализовать создание/завершение сессии встречи
3. Добавить базовую работу с Яндекс.Диском
4. Реализовать загрузку фотографий
5. Добавить распознавание речи
6. В последнюю очередь реализовать административные функции

### Тестирование
- Написать модульные тесты для критических компонентов
- Создать заглушки для API Telegram и Яндекс.Диска для тестирования без реальных сервисов
- Реализовать режим отладки для локального тестирования

### Документация
- Документировать публичный API каждого модуля
- Создать понятную инструкцию для конечных пользователей
- Документировать схему потока данных

## Уроки из предыдущей реализации
- Избегать избыточного функционала
- Не смешивать ответственность модулей
- Обеспечить централизованную обработку ошибок
- Придерживаться единого стиля кодирования
- Не добавлять функционал "на всякий случай"
- Изолировать внешние зависимости для упрощения тестирования и замены
- Использовать асинхронные операции для улучшения производительности

## Возможный план миграции
1. Создать новый репозиторий для чистой реализации
2. Разработать базовую структуру приложения
3. Реализовать основные функции без избыточного функционала
4. Перенести настройки из старого проекта (токены, списки пользователей и папок)
5. Провести тестирование в параллельном режиме
6. После валидации заменить старую версию новой