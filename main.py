import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from config.config import TELEGRAM_TOKEN, validate_config
from config.logging_config import configure_logging
from src.utils.yadisk_helper import YaDiskHelper
from src.utils.folder_navigation import FolderNavigator
from src.utils.error_utils import handle_error
from src.utils.access_control import access_control

from src.handlers.command_handler import (
    start, help_command, new_meeting, handle_folder_selection, 
    create_folder, current_meeting, 
    end_session, cancel, handle_session_callback, init_handlers,
    CHOOSE_FOLDER, CREATE_FOLDER,
    admin_command, handle_admin_menu, add_user, remove_user,
    ADMIN_MENU, ADD_USER, REMOVE_USER, ADD_FOLDER, REMOVE_FOLDER,
    add_folder, remove_folder, show_allowed_folders
)
from src.handlers.file_handler import handle_file
from src.handlers.text_handler import handle_text

# Настройка логирования
configure_logging()
logger = logging.getLogger(__name__)

async def setup_application():
    """Настраивает и возвращает приложение"""
    # Проверяем конфигурацию
    validate_config()
    
    # Инициализируем Яндекс.Диск
    yadisk_helper = YaDiskHelper()
    
    # Инициализируем навигатор папок
    folder_navigator = FolderNavigator(yadisk_helper)
    
    # Инициализируем обработчики команд
    init_handlers(folder_navigator, yadisk_helper)
    
    # Создаем экземпляр приложения
    builder = Application.builder().token(TELEGRAM_TOKEN)
    # Отключаем JobQueue, так как она не нужна
    builder.job_queue(None)
    application = builder.build()
    
    # Добавляем yadisk_helper в контекст бота для использования в обработчиках
    application.bot_data['yadisk_helper'] = yadisk_helper
    application.bot_data['folder_navigator'] = folder_navigator
    
    # Запускаем кэширование разрешенных папок асинхронно
    asyncio.create_task(start_caching(folder_navigator))
    
    # Регистрируем обработчики команд с проверкой доступа
    application.add_handler(CommandHandler("start", access_control_middleware(start)))
    application.add_handler(CommandHandler("help", access_control_middleware(help_command)))
    application.add_handler(CommandHandler("current", access_control_middleware(current_meeting)))
    application.add_handler(CommandHandler("end", access_control_middleware(end_session)))
    
    # Регистрация обработчика админ-команд
    admin_conversation = ConversationHandler(
        entry_points=[CommandHandler("admin", access_control_middleware(admin_command))],
        states={
            ADMIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, access_control_middleware(handle_admin_menu))],
            ADD_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, access_control_middleware(add_user))],
            REMOVE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, access_control_middleware(remove_user))],
            ADD_FOLDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, access_control_middleware(add_folder))],
            REMOVE_FOLDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, access_control_middleware(remove_folder))]
        },
        fallbacks=[CommandHandler("cancel", access_control_middleware(cancel))]
    )
    application.add_handler(admin_conversation)
    
    # Регистрируем обработчик для callback-запросов
    application.add_handler(CallbackQueryHandler(access_control_middleware(handle_session_callback)))
    
    # Регистрируем обработчик выбора папки как ConversationHandler
    folder_conversation = ConversationHandler(
        entry_points=[CommandHandler("new", access_control_middleware(new_meeting))],
        states={
            CHOOSE_FOLDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, access_control_middleware(handle_folder_selection))],
            CREATE_FOLDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, access_control_middleware(create_folder))]
        },
        fallbacks=[CommandHandler("cancel", access_control_middleware(cancel))]
    )
    application.add_handler(folder_conversation)
    
    # Регистрируем обработчики для файлов
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VOICE | filters.Document.ALL,
        access_control_middleware(handle_file)
    ))
    
    # Регистрируем обработчик для текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        access_control_middleware(handle_text)
    ))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(lambda update, context: handle_error(update, context.error, context.bot))
    
    logger.info("Приложение настроено")
    return application

# Middleware для проверки доступа
def access_control_middleware(handler):
    """
    Middleware для проверки доступа пользователей
    
    Args:
        handler: обработчик команды или сообщения
        
    Returns:
        Функция-обертка, которая проверяет доступ перед вызовом обработчика
    """
    async def wrapped(update: Update, context):
        # Проверяем доступ пользователя
        if await access_control.check_access(update):
            # Если доступ разрешен, вызываем обработчик
            return await handler(update, context)
        else:
            # Если доступ запрещен, отправляем сообщение об отказе
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⛔ У вас нет доступа к этому боту. Обратитесь к администратору."
                )
            return ConversationHandler.END
    
    return wrapped

async def start_caching(folder_navigator):
    """Запускает кэширование папок в фоновом режиме"""
    try:
        logger.info("Начало асинхронного кэширования папок")
        await folder_navigator.cache_allowed_folders()
        logger.info("Асинхронное кэширование папок завершено")
    except Exception as e:
        logger.error(f"Ошибка при кэшировании папок: {e}", exc_info=True)

def main():
    """Запускает бота"""
    try:
        # Создаем новый event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаем и настраиваем приложение
        application = loop.run_until_complete(setup_application())
        logger.info("Бот запущен")
        
        # Запускаем бота (не как корутину)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 