import logging
import sys
from config.config import LOG_LEVEL, DATA_DIR

def configure_logging():
    """Настройка логирования"""
    # Настраиваем форматтер для логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                                 datefmt='%Y-%m-%d %H:%M:%S')
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Настраиваем вывод в файл
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Устанавливаем уровень DEBUG для модуля folder_navigation
    folder_logger = logging.getLogger('src.utils.folder_navigation')
    folder_logger.setLevel(logging.DEBUG)
    
    # Отключаем ненужные внешние логи
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logging.info("Логирование настроено") 