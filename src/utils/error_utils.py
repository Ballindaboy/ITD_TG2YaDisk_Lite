import logging
import traceback
from telegram import Update, Bot
from telegram.error import TelegramError, NetworkError, BadRequest

logger = logging.getLogger(__name__)

async def handle_error(update: Update, error, bot: Bot = None):
    """
    Обрабатывает ошибки, возникающие в процессе работы бота
    
    Args:
        update: объект обновления
        error: возникшая ошибка
        bot: экземпляр бота (опционально)
    """
    # Получаем chat_id из объекта update
    chat_id = None
    if update and update.effective_chat:
        chat_id = update.effective_chat.id
    
    # Формируем сообщение для пользователя
    user_message = "Произошла ошибка. Пожалуйста, попробуйте позже."
    
    # Обрабатываем ошибки Telegram
    if isinstance(error, TelegramError):
        if isinstance(error, NetworkError):
            logger.error(f"Сетевая ошибка в обработчике: {error}", exc_info=True)
            user_message = "Возникла проблема с соединением. Пожалуйста, попробуйте позже."
        elif isinstance(error, BadRequest):
            logger.error(f"Неверный запрос к API Telegram: {error}", exc_info=True)
            user_message = "Неверный запрос. Пожалуйста, сообщите об этой ошибке администратору."
        else:
            logger.error(f"Ошибка Telegram в обработчике: {error}", exc_info=True)
    else:
        # Логирование других ошибок
        logger.error(f"Необработанная ошибка: {error}", exc_info=True)
        
        # Добавляем полный стек-трейс
        error_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        logger.debug(f"Стек-трейс ошибки:\n{error_trace}")
    
    # Отправляем сообщение пользователю, если указан chat_id и bot
    if chat_id and bot:
        try:
            await bot.send_message(chat_id=chat_id, text=user_message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}", exc_info=True) 