import asyncio
import logging
from telegram import Message, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def send_temp_message(update: Update, text: str, timeout: int = 5) -> None:
    """
    Отправляет временное сообщение, которое автоматически удаляется через указанное время
    
    Args:
        update (Update): Объект обновления Telegram
        text (str): Текст сообщения
        timeout (int): Время в секундах, через которое сообщение будет удалено
    """
    try:
        # Отправляем сообщение
        message = await update.message.reply_text(text)
        
        # Ожидаем указанное время
        await asyncio.sleep(timeout)
        
        # Удаляем сообщение
        await message.delete()
    except Exception as e:
        logger.error(f"Ошибка при работе с временным сообщением: {e}", exc_info=True)

async def update_processing_message(message: Message, new_text: str) -> Message:
    """
    Обновляет текст сообщения для индикации прогресса обработки
    
    Args:
        message (Message): Объект сообщения Telegram для обновления
        new_text (str): Новый текст сообщения
        
    Returns:
        Message: Обновленное сообщение
    """
    try:
        return await message.edit_text(new_text)
    except Exception as e:
        logger.error(f"Ошибка при обновлении сообщения: {e}", exc_info=True)
        return message

async def send_processing_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              initial_text: str = "⏳ Обработка...") -> Message:
    """
    Отправляет сообщение о начале обработки, которое можно обновлять для отображения прогресса
    
    Args:
        update (Update): Объект обновления Telegram
        context (ContextTypes.DEFAULT_TYPE): Контекст обработчика
        initial_text (str): Начальный текст сообщения
        
    Returns:
        Message: Объект сообщения для дальнейшего обновления
    """
    try:
        return await update.message.reply_text(initial_text)
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения о прогрессе: {e}", exc_info=True)
        return None 