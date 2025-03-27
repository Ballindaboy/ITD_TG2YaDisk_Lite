import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.utils.session_utils import state_manager
from src.utils.message_utils import send_temp_message

logger = logging.getLogger(__name__)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает текстовые сообщения
    """
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Получаем активную сессию пользователя
    session = state_manager.get_session(user_id)
    
    if not session:
        # Если нет активной сессии, просто игнорируем текстовое сообщение
        # или отправляем подсказку
        await update.message.reply_text(
            "У вас нет активной встречи. Используйте /new, чтобы начать новую встречу."
        )
        return
    
    # Получаем yadisk_helper из context
    yadisk_helper = context.bot_data.get('yadisk_helper')
    
    if not yadisk_helper:
        logger.error("yadisk_helper не инициализирован в bot_data")
        await update.message.reply_text("Внутренняя ошибка: не удалось получить доступ к Яндекс.Диску.")
        return
    
    try:
        # Добавляем сообщение в историю сессии
        username = update.effective_user.username or update.effective_user.first_name
        timestamp = session.add_message(message_text, author=username)
        
        # Добавляем сообщение в файл на Яндекс.Диске
        message_to_append = f"{timestamp}\n"
        yadisk_helper.append_to_text_file(message_to_append, session.txt_file_path)
        
        # Отправляем временное сообщение
        await send_temp_message(update, "📝 Сообщение записано в протокол", 2)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке текстового сообщения: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Не удалось сохранить сообщение: {str(e)}") 