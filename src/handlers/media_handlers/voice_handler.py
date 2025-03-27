import logging
import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes

from config.config import UPLOAD_DIR
from src.utils.session_utils import state_manager
from src.utils.speech_recognition import SpeechRecognizer
from src.utils.message_utils import send_temp_message, send_processing_message, update_processing_message

logger = logging.getLogger(__name__)

# Создаем объект распознавателя речи
speech_recognizer = SpeechRecognizer(language="ru-RU")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE, yadisk_helper) -> None:
    """
    Обрабатывает голосовые сообщения и распознает речь
    """
    user_id = update.effective_user.id
    session = state_manager.get_session(user_id)
    
    if not session:
        await update.message.reply_text("Сначала нужно начать встречу с помощью команды /new")
        return
    
    try:
        # Показываем индикатор прогресса
        progress_message = await send_processing_message(update, context, "⏳ Получение голосового сообщения...")
        
        # Получаем голосовое сообщение
        voice_file = await update.message.voice.get_file()
        
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Загрузка голосового сообщения...")
        
        # Создаем временный путь для сохранения OGG файла
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ogg_file_path = os.path.join(UPLOAD_DIR, f"voice_{session.timestamp}_{voice_file.file_unique_id}.ogg")
        
        # Загружаем ogg файл
        await voice_file.download_to_drive(ogg_file_path)
        
        # Обновляем сообщение о прогрессе
        progress_message = await update_processing_message(progress_message, "⏳ Загрузка на Яндекс.Диск...")
        
        # Формируем путь на Яндекс.Диске для голосового сообщения
        yadisk_voice_path = f"{session.folder_path}/{session.file_prefix}_{voice_file.file_unique_id}.ogg"
        
        # Загружаем голосовое сообщение на Яндекс.Диск асинхронно
        await yadisk_helper.upload_file_async(ogg_file_path, yadisk_voice_path)
        
        # Распознаем речь
        progress_message = await update_processing_message(progress_message, "🔊 Распознаю речь...")
        text = await speech_recognizer.recognize_voice(ogg_file_path)
        
        username = update.effective_user.username or update.effective_user.first_name
        
        if text:
            # Добавляем сообщение в лог
            formatted_message = session.add_message(f"Голосовое сообщение ({voice_file.file_unique_id}): {text}", author=username)
            
            # Добавляем запись в файл на Яндекс.Диске
            await yadisk_helper.append_to_text_file_async(formatted_message + "\n", session.txt_file_path)
            
            # Удаляем сообщение о прогрессе и показываем результат
            await progress_message.delete()
            await update.message.reply_text(f"✅ Распознанный текст:\n\n{text}")

            # Отправляем временное сообщение
            await send_temp_message(update, "📝 Сообщение сохранено в протоколе", 3)
        else:
            # Если распознавание не удалось, добавляем запись об этом
            formatted_message = session.add_message(f"Голосовое сообщение ({voice_file.file_unique_id}): [Не удалось распознать]", author=username)
            
            # Добавляем запись в файл на Яндекс.Диске
            await yadisk_helper.append_to_text_file_async(formatted_message + "\n", session.txt_file_path)
            
            # Удаляем сообщение о прогрессе и показываем результат
            await progress_message.delete()
            await update.message.reply_text("❌ Не удалось распознать речь. Возможно, запись слишком тихая или содержит шум.")
        
        # Удаляем временный файл
        if os.path.exists(ogg_file_path):
            os.remove(ogg_file_path)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        await update.message.reply_text(f"Произошла ошибка при обработке голосового сообщения: {str(e)}") 