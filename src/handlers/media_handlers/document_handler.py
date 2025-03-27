import logging
import os
from telegram import Update
from telegram.ext import ContextTypes

from config.config import UPLOAD_DIR
from src.utils.session_utils import state_manager
from src.utils.message_utils import send_temp_message, send_processing_message, update_processing_message

logger = logging.getLogger(__name__)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE, yadisk_helper) -> None:
    """
    Обрабатывает документы, отправленные пользователем
    """
    user_id = update.effective_user.id
    session = state_manager.get_session(user_id)
    
    if not session:
        await update.message.reply_text("Сначала нужно начать встречу с помощью команды /new")
        return
    
    try:
        # Показываем индикатор прогресса
        progress_message = await send_processing_message(update, context, "⏳ Получение документа...")
        
        # Получаем документ
        document = update.message.document
        document_file = await document.get_file()
        
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Загрузка документа...")
        
        # Создаем временный путь для сохранения
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # Сохраняем оригинальное имя файла, но добавляем уникальный идентификатор
        original_filename = document.file_name or f"document_{document_file.file_unique_id}"
        file_path = os.path.join(UPLOAD_DIR, f"{session.timestamp}_{original_filename}")
        
        # Загружаем документ
        await document_file.download_to_drive(file_path)
        
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Загрузка на Яндекс.Диск...")
        
        # Формируем путь на Яндекс.Диске
        yadisk_path = f"{session.folder_path}/{session.file_prefix}_{original_filename}"
        
        # Загружаем на Яндекс.Диск асинхронно
        await yadisk_helper.upload_file_async(file_path, yadisk_path)
        
        # Добавляем сообщение в лог
        username = update.effective_user.username or update.effective_user.first_name
        formatted_message = session.add_message(f"Загружен документ: {yadisk_path}", author=username)
        
        # Добавляем запись в файл на Яндекс.Диске
        await yadisk_helper.append_to_text_file_async(formatted_message + "\n", session.txt_file_path)
        
        # Удаляем сообщение о прогрессе
        await progress_message.delete()
        
        # Отвечаем пользователю
        await update.message.reply_text(f"📄 Документ '{original_filename}' успешно сохранен!")
        
        # Отправляем временное сообщение
        await send_temp_message(update, "📝 Сообщение о документе добавлено в протокол", 3)
        
        # Удаляем временный файл
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке документа: {e}", exc_info=True)
        await update.message.reply_text(f"Не удалось сохранить документ: {str(e)}") 