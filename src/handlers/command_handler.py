import logging
import json
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config.config import FOLDERS_FILE, is_admin, ADMIN_IDS, UPLOAD_DIR
from src.utils.session_utils import state_manager, SessionState
from src.utils.folder_navigation import FolderNavigator
from src.utils.access_control import access_control
from src.utils.message_utils import send_temp_message, send_processing_message, update_processing_message

logger = logging.getLogger(__name__)

# Состояния для диалога
CHOOSE_FOLDER = "CHOOSE_FOLDER"
CREATE_FOLDER = "CREATE_FOLDER"
ADMIN_MENU = "ADMIN_MENU"
ADD_USER = "ADD_USER"
REMOVE_USER = "REMOVE_USER"
SHOW_FOLDERS = "SHOW_FOLDERS"
ADD_FOLDER = "ADD_FOLDER"
REMOVE_FOLDER = "REMOVE_FOLDER"

# Инициализация навигатора папок (будет установлен в main.py)
folder_navigator = None
yadisk_helper = None

def init_handlers(navigator, yadisk):
    """Инициализирует глобальные объекты для обработчиков"""
    global folder_navigator, yadisk_helper
    folder_navigator = navigator
    yadisk_helper = yadisk

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /start
    """
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username or user.first_name}) запустил бота")
    
    await update.message.reply_html(
        f"Привет, {user.mention_html()}!\n\n"
        "Я бот для записи протоколов встреч и сохранения всех материалов в одном месте.\n\n"
        "Основные команды:\n"
        "/new - Создать новую встречу\n"
        "/current - Просмотреть информацию о текущей встрече\n"
        "/end - Завершить текущую встречу\n"
        "/help - Показать справку",
        reply_markup=ReplyKeyboardRemove()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /help
    """
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    
    help_text = "Справка по командам бота:\n\n" \
                "/new - Создать новую встречу и выбрать папку для сохранения записей\n" \
                "/current - Просмотреть информацию о текущей встрече\n" \
                "/end - Завершить текущую встречу\n" \
                "/cancel - Отменить текущее действие\n"
    
    if is_user_admin:
        help_text += "\nДля администраторов:\n" \
                     "/admin - Административные функции (управление пользователями)"
    
    await update.message.reply_text(
        help_text,
        reply_markup=ReplyKeyboardRemove()
    )

async def new_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Начинает процесс создания новой встречи
    """
    user_id = update.effective_user.id
    
    # Проверяем, есть ли уже активная сессия
    if state_manager.has_active_session(user_id):
        await update.message.reply_text(
            "У вас уже есть активная встреча. Сначала завершите её командой /end, "
            "прежде чем начинать новую."
        )
        return ConversationHandler.END
    
    # Начинаем выбор папки
    await folder_navigator.show_folders(update, context)
    
    # Устанавливаем состояние
    state_manager.set_state(user_id, CHOOSE_FOLDER)
    return CHOOSE_FOLDER

async def handle_folder_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Обрабатывает выбор папки (универсальный обработчик для всех уровней)
    """
    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    
    folders = context.user_data.get("folders", [])
    current_path = context.user_data.get("current_path", "/")
    
    # Добавляем логирование для отладки
    logger.debug(f"Обработка выбора папки от пользователя {user_id}. Текст: '{user_text}', текущий путь: '{current_path}'")
    
    # Функция для повторных попыток отправки сообщения
    async def send_message_with_retry(text, keyboard=None, retries=3):
        for attempt in range(retries):
            try:
                if keyboard:
                    return await update.message.reply_text(
                        text,
                        reply_markup=keyboard
                    )
                else:
                    return await update.message.reply_text(
                        text,
                        reply_markup=ReplyKeyboardRemove()
                    )
            except Exception as e:
                logger.warning(f"Ошибка при отправке сообщения (попытка {attempt+1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(1.5)
                else:
                    logger.error(f"Не удалось отправить сообщение после {retries} попыток: {str(e)}", exc_info=True)
                    return None
    
    # Обработка специальных кнопок
    if user_text == "❌ Отмена":
        return await cancel(update, context)
    
    if user_text == "⬆️ Вверх":
        # Переходим на уровень выше
        parent_path = folder_navigator.get_parent_path(current_path)
        logger.debug(f"Переход на уровень выше из '{current_path}' в '{parent_path}'")
        
        # Проверяем на случай корневого пути
        if parent_path == current_path and current_path != "/":
            parent_path = "/"
            logger.warning(f"Обнаружен потенциальный цикл в пути. Принудительно возвращаемся в корень.")
        
        try:
            await folder_navigator.show_folders(update, context, parent_path)
            return CHOOSE_FOLDER
        except Exception as e:
            logger.error(f"Ошибка при переходе на уровень выше: {str(e)}", exc_info=True)
            await send_message_with_retry("Произошла ошибка при навигации. Возвращаемся к корневым папкам.")
            await folder_navigator.show_folders(update, context, "/")
            return CHOOSE_FOLDER
    
    if user_text == "➕ Новая папка":
        await send_message_with_retry(
            f"Введите название новой папки (текущий путь: {current_path}):"
        )
        # Сохраняем текущий путь для создания папки
        context.user_data["folder_to_create_path"] = current_path
        logger.debug(f"Установлен путь для создания папки: '{current_path}'")
        state_manager.set_state(user_id, CREATE_FOLDER)
        return CREATE_FOLDER
    
    if user_text == "✅ Выбрать эту папку":
        # Проверяем, находится ли текущий путь в разрешенных папках
        if not folder_navigator.is_path_allowed(current_path) and current_path != "/":
            await send_message_with_retry(
                f"Эта папка недоступна для выбора: {current_path}. Пожалуйста, выберите другую папку."
            )
            await folder_navigator.show_folders(update, context)
            return CHOOSE_FOLDER
        
        # Выбор текущей папки для встречи
        folder_name = folder_navigator.get_folder_name(current_path)
        try:
            await create_meeting(update, context, current_path, folder_name)
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка при создании встречи: {str(e)}", exc_info=True)
            await send_message_with_retry(f"Произошла ошибка при создании встречи: {str(e)}. Пожалуйста, попробуйте снова.")
            return CHOOSE_FOLDER
    
    # Обработка выбора папки по названию (все кнопки начинаются с эмодзи и имени папки)
    if user_text.startswith("📁 "):
        folder_name = user_text[2:].strip()  # Убираем эмодзи и пробел
        
        # Ищем соответствующую папку по имени
        selected_folder = None
        for folder in folders:
            folder_display_name = folder.name if hasattr(folder, 'name') else folder.get('name', "")
            if folder_display_name == folder_name:
                selected_folder = folder
                break
        
        if selected_folder:
            # Получаем путь к выбранной папке
            folder_path = selected_folder.path if hasattr(selected_folder, 'path') else selected_folder.get('path', '/')
            
            # Дополнительная проверка пути
            if not folder_path:
                logger.warning(f"Получен пустой путь для папки '{folder_name}'")
                # Используем текущий путь и имя папки для формирования полного пути
                folder_path = folder_navigator.safe_join_path_static(current_path, folder_name)
                logger.debug(f"Сформирован путь на основе текущего: {folder_path}")
            
            # Нормализуем путь для предотвращения проблем с нотацией
            folder_path = folder_navigator.normalize_path(folder_path)
            logger.debug(f"Переход в папку: {folder_path}")
            
            try:
                # Переходим в выбранную папку
                await folder_navigator.show_folders(update, context, folder_path)
                return CHOOSE_FOLDER
            except Exception as e:
                logger.error(f"Ошибка при переходе в папку '{folder_path}': {str(e)}", exc_info=True)
                await send_message_with_retry(f"Произошла ошибка при переходе в папку. Возвращаемся к текущей папке.")
                await folder_navigator.show_folders(update, context, current_path)
                return CHOOSE_FOLDER
        else:
            logger.warning(f"Не найдена папка с именем '{folder_name}' в текущем списке папок на пути '{current_path}'")
            await send_message_with_retry(
                f"Не удалось найти папку '{folder_name}'. Попробуйте снова.",
                ReplyKeyboardMarkup(
                    folder_navigator.build_keyboard(folders),
                    resize_keyboard=True
                )
            )
            return CHOOSE_FOLDER
    
    # Если пользователь ввел что-то другое, показываем текущие папки снова
    await send_message_with_retry(
        f"Пожалуйста, выберите папку из клавиатуры или используйте кнопку отмены.\nТекущий путь: {current_path}",
        ReplyKeyboardMarkup(
            folder_navigator.build_keyboard(folders),
            resize_keyboard=True
        )
    )
    return CHOOSE_FOLDER

async def create_folder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Создает новую папку и продолжает навигацию
    """
    folder_name = update.message.text.strip()
    current_path = context.user_data.get("folder_to_create_path", "/")
    
    logger.info(f"Создание папки: '{folder_name}' в пути: '{current_path}'")
    
    if "/" in folder_name or "\\" in folder_name:
        await update.message.reply_text(
            "Название папки не должно содержать символы / или \\. Пожалуйста, введите другое название:"
        )
        return CREATE_FOLDER
    
    # Создаем полный путь новой папки
    try:
        new_folder_path = folder_navigator.safe_join_path_static(current_path, folder_name)
        logger.info(f"Полный путь новой папки: '{new_folder_path}'")
        
        # Проверяем, находится ли путь в пределах разрешенных папок
        is_allowed = folder_navigator.is_path_allowed(new_folder_path)
        logger.info(f"Путь разрешен: {is_allowed}")
        
        if not is_allowed:
            await update.message.reply_text(
                f"Нельзя создать папку в этом месте. Текущий путь: {current_path}.\nПожалуйста, выберите другую папку для создания."
            )
            # Возвращаемся к выбору папки
            await folder_navigator.show_folders(update, context, current_path)
            return CHOOSE_FOLDER
        
        # Проверяем существование родительского пути
        parent_exists = await folder_navigator.yadisk_helper.ensure_directory_exists_async(current_path)
        logger.info(f"Родительский путь '{current_path}' существует: {parent_exists}")
        
        if not parent_exists:
            await update.message.reply_text(
                f"Не удалось найти или создать родительскую папку '{current_path}'. Пожалуйста, попробуйте снова."
            )
            await folder_navigator.show_folders(update, context)
            return CHOOSE_FOLDER
        
        # Создаем папку асинхронно
        logger.info(f"Создание папки на Яндекс.Диске: '{new_folder_path}'")
        success = await folder_navigator.yadisk_helper.create_dir_async(new_folder_path)
        
        if success:
            await update.message.reply_text(f"Папка '{folder_name}' успешно создана!")
            
            # Обновляем кэш папок
            if current_path in folder_navigator.folder_cache:
                logger.debug(f"Удаляем кэш для пути '{current_path}'")
                del folder_navigator.folder_cache[current_path]
                
            # Продолжаем навигацию, показывая содержимое текущей папки
            await folder_navigator.show_folders(update, context, current_path)
            return CHOOSE_FOLDER
        else:
            raise Exception("Не удалось создать папку на Яндекс.Диске")
    
    except Exception as e:
        logger.error(f"Ошибка при создании папки '{folder_name}' в пути '{current_path}': {e}", exc_info=True)
        await update.message.reply_text(
            f"Не удалось создать папку: {str(e)}. Пожалуйста, попробуйте еще раз или используйте /cancel."
        )
        return CREATE_FOLDER

async def create_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE, folder_path: str, folder_name: str) -> None:
    """
    Создает новую встречу в выбранной папке
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Показываем индикатор прогресса
    progress_message = await send_processing_message(update, context, "⏳ Создание новой встречи...")
    
    # Создаем сессию для пользователя
    root_folder = folder_path.split("/")[1] if folder_path.startswith("/") and len(folder_path.split("/")) > 1 else ""
    session = SessionState(root_folder, folder_path, folder_name, user_id)
    
    # Сохраняем сессию
    state_manager.set_session(user_id, session)
    
    # Добавляем первое сообщение в лог
    message = f"Начало встречи в папке: {folder_path}"
    formatted_message = session.add_message(message, author=username)
    
    # Сбрасываем состояние выбора папки
    state_manager.reset_state(user_id)
    
    try:
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Создание файла протокола...")
        
        # Создаем файл на Яндекс.Диске
        header = f"=== Протокол встречи от {session.timestamp} ===\n\n"
        header += f"Место: {folder_path}\n\n"
        header += f"Участник: {username} (ID: {user_id})\n\n"
        
        # Сохраняем полный текст с первым сообщением
        full_text = f"{header}{formatted_message}\n"
        
        await yadisk_helper.create_text_file_async(full_text, session.txt_file_path)

        # Удаляем сообщение о прогрессе
        await progress_message.delete()
        
        # Отправляем сообщение о начале встречи
        await update.message.reply_text(
            f"✅ Встреча начата!\n\n"
            f"📁 Папка: {folder_path}\n"
            f"📝 Все сообщения и файлы будут сохранены в этой папке.\n\n"
            f"Для завершения встречи используйте команду /end",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Отправляем временное сообщение
        await send_temp_message(update, "📝 Файл протокола создан", 3)
        
    except Exception as e:
        logger.error(f"Ошибка при создании файла протокола: {e}", exc_info=True)
        
        # Удаляем сообщение о прогрессе
        if 'progress_message' in locals():
            await progress_message.delete()
            
        await update.message.reply_text(
            "❌ Не удалось создать файл протокола на Яндекс.Диске. "
            "Встреча начата, но могут быть проблемы с сохранением данных."
        )

async def current_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает информацию о текущей встрече
    """
    user_id = update.effective_user.id
    session = state_manager.get_session(user_id)
    
    if not session:
        await update.message.reply_text(
            "У вас нет активной встречи. Создайте новую с помощью команды /new"
        )
        return
    
    # Получаем сводку по сессии
    summary = session.get_session_summary()
    
    await update.message.reply_text(
        f"Информация о текущей встрече:\n\n{summary}\n\n"
        f"Для завершения встречи используйте команду /end",
        reply_markup=ReplyKeyboardRemove()
    )

async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Завершает текущую встречу
    """
    user_id = update.effective_user.id
    session = state_manager.get_session(user_id)
    
    if not session:
        await update.message.reply_text(
            "У вас нет активной встречи. Создайте новую с помощью команды /new"
        )
        return
    
    # Показываем индикатор прогресса
    progress_message = await send_processing_message(update, context, "⏳ Завершение встречи...")
    
    username = update.effective_user.username or update.effective_user.first_name
    
    # Добавляем сообщение о завершении встречи
    session.add_message("Завершение встречи", author=username)
    
    # Получаем сводку по сессии
    summary = session.get_session_summary()
    
    # Завершаем сессию
    try:
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Обновление файла протокола...")
        
        # Обновляем файл на Яндекс.Диске
        footer = "\n\n=== Завершение встречи ===\n"
        duration = summary.split('Продолжительность: ')[1].split('\n')[0]
        footer += f"Продолжительность: {duration}\n"
        records_count = summary.split('Количество записей: ')[1].split('\n')[0]
        footer += f"Количество записей: {records_count}\n"
        
        # Добавляем только завершающую информацию
        await yadisk_helper.append_to_text_file_async(footer, session.txt_file_path)
        
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Получение содержимого протокола...")
        
        # Получаем содержимое файла для отображения в сообщении
        try:
            local_file_path = os.path.join(UPLOAD_DIR, os.path.basename(session.txt_file_path))
            yadisk_helper.disk.download(session.txt_file_path, local_file_path)
            
            with open(local_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
                
            # Если содержимое слишком большое, обрезаем его
            if len(file_content) > 3000:
                file_content = file_content[:3000] + "...\n[Файл слишком большой, показана только часть]"
        except Exception as e:
            logger.error(f"Ошибка при чтении файла протокола: {e}", exc_info=True)
            file_content = "[Не удалось получить содержимое файла]"
        
        # Очищаем сессию
        state_manager.clear_session(user_id)
        
        # Удаляем сообщение о прогрессе
        await progress_message.delete()
        
        await update.message.reply_text(
            f"✅ Встреча завершена!\n\n"
            f"📄 Файл: {session.txt_file_path}\n\n"
            f"Содержание файла:\n\n"
            f"{file_content}\n\n"
            f"Все данные сохранены на Яндекс.Диске.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Отправляем временное сообщение
        await send_temp_message(update, "🔄 Сессия завершена", 3)
        
    except Exception as e:
        logger.error(f"Ошибка при завершении встречи: {e}", exc_info=True)
        
        # Удаляем сообщение о прогрессе, если оно есть
        if 'progress_message' in locals():
            await progress_message.delete()
            
        await update.message.reply_text(
            f"❌ Встреча завершена, но возникли проблемы при сохранении данных: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
        # Всё равно очищаем сессию
        state_manager.clear_session(user_id)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет текущее действие
    """
    user_id = update.effective_user.id
    
    # Сбрасываем состояние
    state_manager.reset_state(user_id)
    
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def handle_session_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает callback-запросы, связанные с сессиями
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Извлекаем данные из callback
    callback_data = query.data
    
    # Отвечаем, чтобы убрать часы загрузки в Telegram
    await query.answer()
    
    # Обрабатываем callback_data
    if callback_data == "session_info":
        session = state_manager.get_session(user_id)
        if session:
            summary = session.get_session_summary()
            await query.edit_message_text(
                f"Информация о текущей встрече:\n\n{summary}"
            )
        else:
            await query.edit_message_text(
                "У вас нет активной встречи."
            )
    elif callback_data == "session_end":
        # Завершаем сессию
        session = state_manager.get_session(user_id)
        if session:
            summary = session.get_session_summary()
            state_manager.clear_session(user_id)
            await query.edit_message_text(
                f"Встреча завершена!\n\n{summary}"
            )
        else:
            await query.edit_message_text(
                "У вас нет активной встречи."
            )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Обрабатывает команду /admin для доступа к административным функциям
    """
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    if not is_admin(user_id):
        await update.message.reply_text(
            "У вас нет прав доступа к административным функциям.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Создаем клавиатуру для административных функций
    keyboard = [
        ["👥 Список пользователей"],
        ["➕ Добавить пользователя", "➖ Удалить пользователя"],
        ["📁 Список папок"],
        ["📁➕ Добавить папку", "📁➖ Удалить папку"],
        ["🔄 Перезагрузить списки"],
        ["❌ Выход"]
    ]
    
    await update.message.reply_text(
        "Панель администратора. Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    # Устанавливаем состояние диалога
    state_manager.set_state(user_id, ADMIN_MENU)
    return ADMIN_MENU

async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Обрабатывает выбор действия в административном меню
    """
    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    
    # Проверяем, является ли пользователь администратором
    if not is_admin(user_id):
        await update.message.reply_text(
            "У вас нет прав доступа к административным функциям.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    if user_text == "👥 Список пользователей":
        return await show_allowed_users(update, context)
    
    elif user_text == "➕ Добавить пользователя":
        await update.message.reply_text(
            "Введите ID пользователя, которого нужно добавить:",
            reply_markup=ReplyKeyboardRemove()
        )
        state_manager.set_state(user_id, ADD_USER)
        return ADD_USER
    
    elif user_text == "➖ Удалить пользователя":
        await update.message.reply_text(
            "Введите ID пользователя, которого нужно удалить:",
            reply_markup=ReplyKeyboardRemove()
        )
        state_manager.set_state(user_id, REMOVE_USER)
        return REMOVE_USER
    
    elif user_text == "📁 Список папок":
        return await show_allowed_folders(update, context)
    
    elif user_text == "📁➕ Добавить папку":
        await update.message.reply_text(
            "Введите путь к папке, которую нужно добавить (например: /TD/Имя.Папки):",
            reply_markup=ReplyKeyboardRemove()
        )
        state_manager.set_state(user_id, ADD_FOLDER)
        return ADD_FOLDER
    
    elif user_text == "📁➖ Удалить папку":
        await update.message.reply_text(
            "Введите путь к папке, которую нужно удалить из списка разрешенных:",
            reply_markup=ReplyKeyboardRemove()
        )
        state_manager.set_state(user_id, REMOVE_FOLDER)
        return REMOVE_FOLDER
    
    elif user_text == "🔄 Перезагрузить списки":
        access_control.reload_users()
        folder_navigator.reload_allowed_folders()
        await update.message.reply_text(
            f"Списки перезагружены.\n"
            f"Текущее количество пользователей: {len(access_control.allowed_users)}\n"
            f"Текущее количество папок: {len(folder_navigator.allowed_folders)}",
            reply_markup=ReplyKeyboardRemove()
        )
        return await admin_command(update, context)
    
    elif user_text == "❌ Выход":
        await update.message.reply_text(
            "Выход из режима администратора.",
            reply_markup=ReplyKeyboardRemove()
        )
        state_manager.reset_state(user_id)
        return ConversationHandler.END
    
    else:
        # Создаем клавиатуру для административных функций
        keyboard = [
            ["👥 Список пользователей"],
            ["➕ Добавить пользователя", "➖ Удалить пользователя"],
            ["📁 Список папок"],
            ["📁➕ Добавить папку", "📁➖ Удалить папку"],
            ["🔄 Перезагрузить списки"],
            ["❌ Выход"]
        ]
        
        await update.message.reply_text(
            "Неизвестная команда. Пожалуйста, используйте предоставленные кнопки.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return ADMIN_MENU

async def show_allowed_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Отображает список разрешенных пользователей
    """
    allowed_users = access_control.allowed_users
    admin_ids = ADMIN_IDS
    
    users_text = "Разрешенные пользователи:\n\n"
    
    if not allowed_users and not admin_ids:
        users_text += "Список пуст. Все пользователи имеют доступ."
    else:
        # Добавляем админов
        if admin_ids:
            users_text += "Администраторы:\n"
            for admin_id in admin_ids:
                users_text += f"- {admin_id} (админ)\n"
            users_text += "\n"
        
        # Добавляем обычных пользователей
        if allowed_users:
            users_text += "Пользователи:\n"
            for user_id in allowed_users:
                if user_id not in admin_ids:
                    users_text += f"- {user_id}\n"
        else:
            users_text += "Нет обычных пользователей в списке доступа.\n"
    
    # Создаем клавиатуру для административных функций
    keyboard = [
        ["👥 Список пользователей"],
        ["➕ Добавить пользователя", "➖ Удалить пользователя"],
        ["📁 Список папок"],
        ["📁➕ Добавить папку", "📁➖ Удалить папку"],
        ["🔄 Перезагрузить списки"],
        ["❌ Выход"]
    ]
    
    await update.message.reply_text(
        users_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    return ADMIN_MENU

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Добавляет пользователя в список разрешенных
    """
    user_text = update.message.text.strip()
    
    try:
        user_id = int(user_text)
        
        if access_control.add_allowed_user(user_id):
            await update.message.reply_text(
                f"Пользователь с ID {user_id} успешно добавлен в список разрешенных."
            )
        else:
            await update.message.reply_text(
                f"Не удалось добавить пользователя с ID {user_id}. Проверьте журнал."
            )
    except ValueError:
        await update.message.reply_text(
            "Введите корректный числовой ID пользователя."
        )
    
    # Возвращаемся в административное меню
    return await admin_command(update, context)

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Удаляет пользователя из списка разрешенных
    """
    user_text = update.message.text.strip()
    
    try:
        user_id = int(user_text)
        
        # Проверяем, не пытаемся ли удалить администратора
        if user_id in ADMIN_IDS:
            await update.message.reply_text(
                f"Нельзя удалить пользователя с ID {user_id}, так как он является администратором."
            )
        else:
            if access_control.remove_allowed_user(user_id):
                await update.message.reply_text(
                    f"Пользователь с ID {user_id} успешно удален из списка разрешенных."
                )
            else:
                await update.message.reply_text(
                    f"Не удалось удалить пользователя с ID {user_id}. Проверьте журнал."
                )
    except ValueError:
        await update.message.reply_text(
            "Введите корректный числовой ID пользователя."
        )
    
    # Возвращаемся в административное меню
    return await admin_command(update, context)

async def show_allowed_folders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Отображает список разрешенных папок
    """
    allowed_folders = folder_navigator.allowed_folders
    
    folders_text = "Разрешенные папки:\n\n"
    
    if not allowed_folders:
        folders_text += "Список пуст. Нет разрешенных папок."
    else:
        for i, folder in enumerate(allowed_folders, 1):
            folders_text += f"{i}. {folder}\n"
    
    # Создаем клавиатуру для административных функций
    keyboard = [
        ["👥 Список пользователей"],
        ["➕ Добавить пользователя", "➖ Удалить пользователя"],
        ["📁 Список папок"],
        ["📁➕ Добавить папку", "📁➖ Удалить папку"],
        ["🔄 Перезагрузить списки"],
        ["❌ Выход"]
    ]
    
    await update.message.reply_text(
        folders_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    return ADMIN_MENU

async def add_folder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Добавляет папку в список разрешенных с проверкой существования
    """
    folder_path = update.message.text.strip()
    
    # Используем новый асинхронный метод для добавления папки
    success, message = await folder_navigator.add_allowed_folder(folder_path)
    
    await update.message.reply_text(message)
    
    # Возвращаемся в административное меню
    return await admin_command(update, context)

async def remove_folder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Удаляет папку из списка разрешенных
    """
    folder_path = update.message.text.strip()
    
    # Используем новый асинхронный метод для удаления папки
    success, message = await folder_navigator.remove_allowed_folder(folder_path)
    
    await update.message.reply_text(message)
    
    # Возвращаемся в административное меню
    return await admin_command(update, context) 