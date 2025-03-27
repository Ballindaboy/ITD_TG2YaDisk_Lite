import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает различные типы файлов, перенаправляя их в соответствующие обработчики
    """
    from src.handlers.media_handlers.photo_handler import handle_photo
    from src.handlers.media_handlers.voice_handler import handle_voice
    from src.handlers.media_handlers.document_handler import handle_document
    
    # Получаем yadisk_helper из context
    yadisk_helper = context.bot_data.get('yadisk_helper')
    
    if not yadisk_helper:
        logger.error("yadisk_helper не инициализирован в bot_data")
        await update.message.reply_text("Внутренняя ошибка: не удалось получить доступ к Яндекс.Диску.")
        return
    
    # Перенаправляем в соответствующий обработчик в зависимости от типа файла
    if update.message.photo:
        await handle_photo(update, context, yadisk_helper)
    elif update.message.voice:
        await handle_voice(update, context, yadisk_helper)
    elif update.message.document:
        await handle_document(update, context, yadisk_helper)
    else:
        logger.warning(f"Получен неподдерживаемый тип файла: {update.message}")
        await update.message.reply_text("Этот тип файла не поддерживается.") 