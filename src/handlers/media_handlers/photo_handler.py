import logging
import os
from telegram import Update
from telegram.ext import ContextTypes

from config.config import UPLOAD_DIR
from src.utils.session_utils import state_manager
from src.utils.message_utils import send_temp_message, send_processing_message, update_processing_message
from src.utils.folder_navigation import FolderNavigator

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, yadisk_helper) -> None:
    """
    Обрабатывает фотографии, отправленные пользователем
    """
    user_id = update.effective_user.id
    session = state_manager.get_session(user_id)
    
    if not session:
        await update.message.reply_text("Сначала нужно начать встречу с помощью команды /new")
        return
    
    try:
        # Показываем индикатор прогресса
        progress_message = await send_processing_message(update, context, "⏳ Получение фотографии...")
        
        # Получаем самое большое доступное изображение
        photo_file = await update.message.photo[-1].get_file()
        
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Загрузка фотографии...")
        
        # Создаем временный путь для сохранения
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # Генерируем безопасное имя файла
        safe_file_id = FolderNavigator.sanitize_filename(photo_file.file_unique_id)
        local_filename = f"photo_{session.timestamp}_{safe_file_id}.jpg"
        file_path = os.path.join(UPLOAD_DIR, local_filename)
        
        # Загружаем фото
        await photo_file.download_to_drive(file_path)
        
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Загрузка на Яндекс.Диск...")
        
        # Формируем путь на Яндекс.Диске, используя безопасное соединение путей
        yadisk_filename = f"{session.file_prefix}_{safe_file_id}.jpg"
        yadisk_path = FolderNavigator.safe_join_path_static(session.folder_path, yadisk_filename)
        
        # Загружаем на Яндекс.Диск асинхронно
        await yadisk_helper.upload_file_async(file_path, yadisk_path)
        
        # Добавляем сообщение в лог
        username = update.effective_user.username or update.effective_user.first_name
        formatted_message = session.add_message(f"Загружено фото: {yadisk_path}", author=username)
        
        # Добавляем запись в файл на Яндекс.Диске
        await yadisk_helper.append_to_text_file_async(formatted_message + "\n", session.txt_file_path)
        
        # Удаляем сообщение о прогрессе
        await progress_message.delete()
        
        # Отвечаем пользователю
        await update.message.reply_text("📷 Фото успешно сохранено!")
        
        # Отправляем временное сообщение
        await send_temp_message(update, "📝 Сообщение о фото добавлено в протокол", 3)
        
        # Удаляем временный файл
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
        await update.message.reply_text(f"Не удалось сохранить фото: {str(e)}") 