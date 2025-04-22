import logging
import os
import time
import asyncio
from functools import partial
import yadisk
from config.config import YANDEX_DISK_TOKEN, UPLOAD_DIR
from typing import List, Any

logger = logging.getLogger(__name__)

class YaDiskHelper:
    """Класс для работы с API Яндекс.Диска"""
    def __init__(self):
        self.disk = yadisk.YaDisk(token=YANDEX_DISK_TOKEN)
        self._check_connection()
    
    def _check_connection(self):
        """Проверяет соединение с Яндекс.Диском"""
        try:
            if not self.disk.check_token():
                logger.error("Токен Яндекс.Диска недействителен")
                raise ValueError("Токен Яндекс.Диска недействителен")
            logger.info("Соединение с Яндекс.Диском установлено")
        except Exception as e:
            logger.error(f"Ошибка соединения с Яндекс.Диском: {e}", exc_info=True)
            raise
    
    def upload_file(self, local_path, remote_path, retry_count=3, retry_delay=2):
        """Загружает файл на Яндекс.Диск с повторными попытками при ошибке"""
        for attempt in range(retry_count):
            try:
                # Проверяем существование директории
                self._ensure_directory_exists(os.path.dirname(remote_path))
                
                # Загружаем файл
                self.disk.upload(local_path, remote_path, overwrite=True)
                logger.info(f"Файл успешно загружен: {remote_path}")
                return True
            except Exception as e:
                logger.warning(f"Попытка {attempt+1}/{retry_count} загрузки файла не удалась: {e}")
                if attempt < retry_count - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Не удалось загрузить файл после {retry_count} попыток: {e}", exc_info=True)
                    raise
    
    async def upload_file_async(self, local_path, remote_path, retry_count=3, retry_delay=2):
        """Асинхронно загружает файл на Яндекс.Диск"""
        loop = asyncio.get_event_loop()
        upload_func = partial(self.upload_file, local_path, remote_path, retry_count, retry_delay)
        return await loop.run_in_executor(None, upload_func)
    
    def _ensure_directory_exists(self, directory_path):
        """Проверяет существование директории и создает её при необходимости"""
        try:
            # Если путь пустой или корневой, то проверка не нужна
            if not directory_path or directory_path == "/":
                return
            
            # Проверяем существование директории
            try:
                self.disk.get_meta(directory_path)
            except yadisk.exceptions.PathNotFoundError:
                # Если директория не существует, создаём её
                logger.info(f"Создаем директорию: {directory_path}")
                parent_dir = os.path.dirname(directory_path)
                self._ensure_directory_exists(parent_dir)  # Рекурсивно создаем родительские директории
                self.disk.mkdir(directory_path)
        except Exception as e:
            logger.error(f"Ошибка при проверке/создании директории {directory_path}: {e}", exc_info=True)
            raise
    
    async def ensure_directory_exists_async(self, directory_path):
        """Асинхронно проверяет существование директории и создает её при необходимости"""
        logger.info(f"Проверка существования директории: {directory_path}")
        try:
            loop = asyncio.get_event_loop()
            ensure_dir_func = partial(self._ensure_directory_exists, directory_path)
            result = await loop.run_in_executor(None, ensure_dir_func)
            logger.info(f"Директория {directory_path} проверена и при необходимости создана")
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке/создании директории {directory_path}: {e}", exc_info=True)
            return False
    
    def create_text_file(self, text, remote_path, retry_count=3, retry_delay=2):
        """Создает текстовый файл на Яндекс.Диске"""
        # Создаем временный локальный файл
        local_path = os.path.join(UPLOAD_DIR, os.path.basename(remote_path))
        try:
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Загружаем файл на Яндекс.Диск
            return self.upload_file(local_path, remote_path, retry_count, retry_delay)
        finally:
            # Удаляем временный файл
            if os.path.exists(local_path):
                os.remove(local_path)
    
    async def create_text_file_async(self, text, remote_path, retry_count=3, retry_delay=2):
        """Асинхронно создает текстовый файл на Яндекс.Диске"""
        loop = asyncio.get_event_loop()
        create_file_func = partial(self.create_text_file, text, remote_path, retry_count, retry_delay)
        return await loop.run_in_executor(None, create_file_func)
    
    def append_to_text_file(self, text, remote_path, retry_count=3, retry_delay=2):
        """Добавляет текст в существующий файл на Яндекс.Диске"""
        try:
            # Проверяем существование файла
            file_exists = True
            try:
                self.disk.get_meta(remote_path)
            except yadisk.exceptions.PathNotFoundError:
                file_exists = False
            
            if file_exists:
                # Сначала загружаем файл
                local_path = os.path.join(UPLOAD_DIR, os.path.basename(remote_path))
                try:
                    self.disk.download(remote_path, local_path)
                    
                    # Добавляем текст
                    with open(local_path, 'a', encoding='utf-8') as f:
                        f.write(text)
                    
                    # Загружаем обратно
                    return self.upload_file(local_path, remote_path, retry_count, retry_delay)
                finally:
                    # Удаляем временный файл
                    if os.path.exists(local_path):
                        os.remove(local_path)
            else:
                # Если файл не существует, просто создаем новый
                return self.create_text_file(text, remote_path, retry_count, retry_delay)
        except Exception as e:
            logger.error(f"Ошибка при добавлении текста в файл {remote_path}: {e}", exc_info=True)
            raise
    
    async def append_to_text_file_async(self, text, remote_path, retry_count=3, retry_delay=2):
        """Асинхронно добавляет текст в существующий файл на Яндекс.Диске"""
        loop = asyncio.get_event_loop()
        append_func = partial(self.append_to_text_file, text, remote_path, retry_count, retry_delay)
        return await loop.run_in_executor(None, append_func)
    
    def list_dirs(self, path="/"):
        """Возвращает список папок в указанном пути"""
        try:
            items = list(self.disk.listdir(path))
            return [item for item in items if item.type == "dir"]
        except Exception as e:
            logger.error(f"Ошибка при получении списка папок из {path}: {e}", exc_info=True)
            raise
    
    async def list_dirs_async(self, path: str) -> List[Any]:
        """
        Асинхронная версия для получения списка папок
        """
        logger.debug(f"Запрос списка папок по пути: {path}")
        
        max_retries = 3
        retry_delay = 1.5
        
        for attempt in range(max_retries):
            try:
                # Преобразуем синхронный вызов в асинхронный
                loop = asyncio.get_event_loop()
                
                # Используем ThreadPoolExecutor для запуска блокирующего вызова API в отдельном потоке
                result = await loop.run_in_executor(
                    None, 
                    partial(self._list_dirs_sync, path)
                )
                
                logger.debug(f"Получено {len(result)} папок по пути: {path}")
                return result
                
            except yadisk.exceptions.ConnectionError as e:
                logger.warning(f"Ошибка соединения при получении списка папок (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Не удалось получить список папок после {max_retries} попыток: {e}", exc_info=True)
                    raise
                    
            except yadisk.exceptions.TimeoutError as e:
                logger.warning(f"Таймаут при получении списка папок (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Таймаут при получении списка папок после {max_retries} попыток: {e}", exc_info=True)
                    raise
                    
            except Exception as e:
                logger.error(f"Неожиданная ошибка при получении списка папок: {e}", exc_info=True)
                raise
    
    def create_dir(self, path):
        """Создает директорию на Яндекс.Диске"""
        try:
            logger.info(f"Создание директории: {path}")
            # Проверяем, существует ли директория
            try:
                meta = self.disk.get_meta(path)
                logger.info(f"Директория {path} уже существует")
                return True
            except yadisk.exceptions.PathNotFoundError:
                # Если директория не существует, убеждаемся, что родительские директории существуют
                parent_dir = os.path.dirname(path)
                logger.info(f"Директория {path} не существует. Проверяем родительскую директорию: {parent_dir}")
                self._ensure_directory_exists(os.path.dirname(path))
                # Создаем директорию
                logger.info(f"Создаем новую директорию: {path}")
                self.disk.mkdir(path)
                logger.info(f"Директория {path} успешно создана")
                return True
        except Exception as e:
            logger.error(f"Ошибка при создании директории {path}: {e}", exc_info=True)
            return False
    
    async def create_dir_async(self, path):
        """Асинхронно создает директорию на Яндекс.Диске"""
        logger.info(f"Асинхронное создание директории: {path}")
        try:
            loop = asyncio.get_event_loop()
            create_dir_func = partial(self.create_dir, path)
            result = await loop.run_in_executor(None, create_dir_func)
            logger.info(f"Результат создания директории {path}: {result}")
            return result
        except Exception as e:
            logger.error(f"Исключение при асинхронном создании директории {path}: {e}", exc_info=True)
            return False
    
    def _list_dirs_sync(self, path: str) -> List[Any]:
        """
        Синхронная версия для получения списка папок
        
        Args:
            path: Путь на Яндекс.Диске
            
        Returns:
            Список объектов папок
        """
        try:
            # Проверяем, что путь существует
            if not self.disk.exists(path):
                logger.warning(f"Путь {path} не существует на Яндекс.Диске")
                return []
            
            # Получаем список объектов в директории
            items = list(self.disk.listdir(path))
            
            # Фильтруем только папки
            folders = [item for item in items if item.type == "dir"]
            
            return folders
        except yadisk.exceptions.PathNotFoundError:
            logger.warning(f"Путь {path} не найден на Яндекс.Диске")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении списка папок для {path}: {e}", exc_info=True)
            raise 