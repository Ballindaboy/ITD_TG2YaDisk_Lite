import logging
import asyncio
import json
from functools import partial
from typing import List, Dict, Any, Tuple, Optional, Callable
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config.config import FOLDERS_FILE
import yadisk
import os

logger = logging.getLogger(__name__)

class FolderNavigator:
    """Класс для работы с навигацией по папкам Яндекс.Диска в Telegram боте."""
    def __init__(
        self, 
        yadisk_helper,
        folder_selected_callback: Optional[Callable] = None,
        title: str = "Выберите папку:",
        add_current_folder_button: bool = True,
        create_folder_button: bool = True,
        extra_buttons: List[str] = None
    ):
        """Инициализация навигатора по папкам."""
        self.yadisk_helper = yadisk_helper
        self.title = title
        self.add_current_folder_button = add_current_folder_button
        self.create_folder_button = create_folder_button
        self.extra_buttons = extra_buttons or []
        self.folder_selected_callback = folder_selected_callback
        self.allowed_folders = self._load_allowed_folders()
        # Кэш для хранения структуры папок
        self.folder_cache = {}
    
    def _load_allowed_folders(self) -> List[str]:
        """Загружает список разрешенных папок из файла allowed_folders.json"""
        try:
            with open(FOLDERS_FILE, 'r') as f:
                folders = json.load(f)
                # Убеждаемся, что все пути начинаются с / и не заканчиваются на /
                return [self.normalize_path(folder) for folder in folders]
        except Exception as e:
            logger.error(f"Ошибка при загрузке разрешенных папок: {e}", exc_info=True)
            return []
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """Нормализует путь для Яндекс.Диска"""
        if not path:
            return "/"
            
        # Удаляем префикс диска и очищаем от лишних пробелов
        path = path.replace("disk:", "").strip()
        
        # Преобразуем последовательные слеши в один слеш
        while '//' in path:
            path = path.replace('//', '/')
        
        # Добавляем начальный слеш, если его нет
        if not path.startswith("/"):
            path = "/" + path
            
        # Удаляем конечный слеш (кроме корневого пути)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
            
        return path
    
    def get_folder_name(self, path: str) -> str:
        """Извлекает имя папки из пути"""
        if path == "/":
            return "Корень"
        
        path = self.normalize_path(path)
        parts = path.split("/")
        return parts[-1] if parts and parts[-1] else ""
    
    def get_parent_path(self, path: str) -> str:
        """Получает родительский путь"""
        path = self.normalize_path(path)
        
        if path == "/":
            return "/"
            
        parts = path.split("/")
        if len(parts) <= 2:  # ['', 'имя_папки']
            return "/"
            
        return "/".join(parts[:-1])
    
    def join_paths(self, parent_path: str, folder_name: str) -> str:
        """Соединяет родительский путь и имя папки в полный путь"""
        # Используем более надежный метод для объединения путей
        return self.safe_join_path(parent_path, folder_name)
    
    async def get_folders(self, path: str, retry_count: int = 2, retry_delay: float = 1.0) -> List[Any]:
        """Получает список папок по указанному пути, с использованием кэша"""
        normalized_path = self.normalize_path(path)
        
        # Проверяем, есть ли путь в кэше
        if normalized_path in self.folder_cache:
            logger.info(f"Получение папок из кэша для пути: {normalized_path}")
            return self.folder_cache[normalized_path]
        
        for attempt in range(retry_count + 1):
            try:
                # Используем асинхронную версию list_dirs
                folders = await self.yadisk_helper.list_dirs_async(normalized_path)
                
                # Сохраняем в кэш
                self.folder_cache[normalized_path] = folders
                
                return folders
            except Exception as e:
                logger.warning(f"Попытка {attempt+1}/{retry_count+1} получения папок для {normalized_path} не удалась: {str(e)}")
                if attempt < retry_count:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Ошибка при получении списка папок для {normalized_path} после {retry_count+1} попыток: {str(e)}", exc_info=True)
        
        # Возвращаем пустой список, если все попытки не удались
        return []
    
    async def cache_allowed_folders(self, force_refresh=False) -> Dict[str, Any]:
        """
        Кэширует структуру разрешенных папок с улучшенным логированием
        
        Args:
            force_refresh: Принудительное обновление кэша
            
        Returns:
            Словарь со статистикой кэширования
        """
        if not self.allowed_folders:
            logger.warning("Нет разрешенных папок для кэширования")
            return {"status": "warning", "message": "Нет разрешенных папок", "success": 0, "failed": 0}
        
        logger.info(f"Начало кэширования {len(self.allowed_folders)} разрешенных папок...")
        
        # Если требуется принудительное обновление, очищаем кэш
        if force_refresh:
            await self.clear_cache()
        
        successful_cache = 0
        failed_cache = 0
        
        for allowed_folder in self.allowed_folders:
            try:
                logger.info(f"Кэширование папки: {allowed_folder}")
                folders = await self.get_folders(allowed_folder)
                
                # Добавляем в статистику
                if folders is not None:
                    successful_cache += 1
                    logger.debug(f"Успешно кэшировано {len(folders)} подпапок для {allowed_folder}")
                else:
                    failed_cache += 1
            except Exception as e:
                failed_cache += 1
                logger.error(f"Ошибка при кэшировании папки {allowed_folder}: {str(e)}", exc_info=True)
        
        result = {
            "status": "success",
            "message": f"Кэширование папок завершено. Успешно: {successful_cache}, с ошибками: {failed_cache}",
            "success": successful_cache,
            "failed": failed_cache,
            "total": len(self.allowed_folders)
        }
        
        logger.info(result["message"])
        return result
    
    async def clear_cache(self) -> None:
        """Очищает кэш папок"""
        self.folder_cache.clear()
        logger.info("Кэш папок очищен")
    
    def build_keyboard(self, folders: List[Any], include_current_folder: bool = True) -> List[List[str]]:
        """Формирует клавиатуру для выбора папок"""
        keyboard = []
        
        # Ограничиваем количество папок для отображения
        max_folders = 200
        display_folders = folders[:max_folders]
        
        # Добавляем папки в клавиатуру (по 2 в строке для компактности)
        row = []
        for i, folder in enumerate(display_folders, 1):
            # Получаем имя папки в зависимости от типа объекта
            folder_name = folder.name if hasattr(folder, 'name') else folder.get('name', str(i))
            button_text = f"📁 {folder_name}"
            
            row.append(button_text)
            
            # Добавляем по 2 папки в строку
            if len(row) == 2 or i == len(display_folders):
                keyboard.append(row)
                row = []
        
        # Добавляем специальные кнопки
        special_buttons = []
        
        if include_current_folder and self.add_current_folder_button:
            special_buttons.append("✅ Выбрать эту папку")
        
        if self.create_folder_button:
            special_buttons.append("➕ Новая папка")
        
        if special_buttons:
            keyboard.append(special_buttons)
        
        # Добавляем дополнительные кнопки
        for button in self.extra_buttons:
            keyboard.append([button])
        
        # Добавляем кнопку отмены
        keyboard.append(["❌ Отмена"])
        
        return keyboard
    
    def is_path_allowed(self, path: str) -> bool:
        """Проверяет, входит ли указанный путь в список разрешенных папок"""
        # Если список разрешенных папок пуст, разрешаем любой путь
        if not self.allowed_folders:
            return True
            
        normalized_path = self.normalize_path(path)
        
        # Логируем проверку пути
        logger.debug(f"Проверка пути: {path} -> нормализован в: {normalized_path}")
        logger.debug(f"Разрешенные папки: {self.allowed_folders}")
        
        # Сначала проверяем, является ли путь одним из разрешенных
        if normalized_path in self.allowed_folders:
            logger.debug(f"Путь {normalized_path} найден в списке разрешенных папок")
            return True
            
        # Затем проверяем, находится ли путь внутри одной из разрешенных папок
        for allowed_folder in self.allowed_folders:
            # Проверяем, что путь начинается с разрешенной папки и после неё идет слеш или ничего
            if normalized_path.startswith(allowed_folder + "/") or normalized_path == allowed_folder:
                logger.debug(f"Путь {normalized_path} находится внутри разрешенной папки {allowed_folder}")
                return True
        
        logger.debug(f"Путь {normalized_path} не разрешен")        
        return False
    
    async def show_folders(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        path: str = "/"
    ) -> None:
        """Отображает список папок по указанному пути"""
        normalized_path = self.normalize_path(path)
        
        # Если путь корневой, проверяем есть ли разрешенные папки
        if normalized_path == "/" and self.allowed_folders:
            # Формируем сообщение с разрешенными папками
            message = f"{self.title}"
            allowed_folders_display = []
            
            # Создаем список разрешенных папок для отображения
            for folder in self.allowed_folders:
                folder_name = self.get_folder_name(folder)
                allowed_folders_display.append({"name": folder_name, "path": folder})
            
            # Сохраняем список папок и путь в контексте
            context.user_data["folders"] = allowed_folders_display
            context.user_data["current_path"] = normalized_path
            
            # Отправляем сообщение с папками
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(
                    self.build_keyboard(allowed_folders_display),
                    resize_keyboard=True
                )
            )
            return
        
        # Проверяем, разрешен ли выбранный путь
        if not self.is_path_allowed(normalized_path) and normalized_path != "/":
            await update.message.reply_text(
                "⛔ Папка недоступна",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Показываем доступные папки
            await self.show_folders(update, context)
            return
        
        try:
            # Получаем список папок по указанному пути
            folders = await self.get_folders(normalized_path)
            
            if not folders:
                await update.message.reply_text(
                    "📂 Папка пуста",
                    reply_markup=ReplyKeyboardRemove()
                )
                if normalized_path != "/":
                    # Показываем доступные папки
                    await self.show_folders(update, context)
                return
            
            # Формируем краткое сообщение
            if path == "/":
                message = self.title
            else:
                folder_name = self.get_folder_name(normalized_path)
                message = f"📂 {folder_name}"
            
            # Сохраняем список папок и путь в контексте
            context.user_data["folders"] = folders
            context.user_data["current_path"] = normalized_path
            
            # Отправляем сообщение с папками
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(
                    self.build_keyboard(folders),
                    resize_keyboard=True
                )
            )
        except Exception as e:
            logger.error(f"Ошибка при отображении папок для {normalized_path}: {str(e)}", exc_info=True)
            await update.message.reply_text(
                "🚫 Ошибка соединения",
                reply_markup=ReplyKeyboardRemove()
            )
    
    def reload_allowed_folders(self) -> None:
        """Перезагружает список разрешенных папок из файла"""
        try:
            self.allowed_folders = self._load_allowed_folders()
            logger.info(f"Список разрешенных папок перезагружен. Загружено {len(self.allowed_folders)} папок")
        except Exception as e:
            logger.error(f"Ошибка при перезагрузке разрешенных папок: {e}", exc_info=True)
    
    def validate_folder_name(self, folder_name: str) -> Tuple[bool, str]:
        """Проверяет допустимость имени папки для Яндекс.Диска
        
        Возвращает: (валидно, сообщение об ошибке)
        """
        # Недопустимые символы в именах файлов/папок на Яндекс.Диске
        invalid_chars = ['\\', ':', '*', '?', '"', '<', '>', '|']
        
        # Проверка на пустое имя
        if not folder_name.strip():
            return False, "Имя папки не может быть пустым"
        
        # Проверка на недопустимые символы
        for char in invalid_chars:
            if char in folder_name:
                return False, f"Имя папки содержит недопустимый символ: '{char}'"
        
        # Проверка на слишком длинное имя
        if len(folder_name) > 255:
            return False, "Имя папки слишком длинное (более 255 символов)"
        
        return True, ""
    
    async def validate_folder_path(self, path: str) -> Tuple[bool, str, bool]:
        """Проверяет существование и доступность пути на Яндекс.Диске
        
        Возвращает кортеж: (валидность, сообщение об ошибке, существует ли путь)
        """
        normalized_path = self.normalize_path(path)
        
        # Проверка длины пути
        if len(normalized_path) > 255:
            return False, "Путь слишком длинный (более 255 символов)", False
        
        # Проверка допустимости каждой части пути
        parts = normalized_path.split("/")
        for part in parts:
            if part:  # Пропускаем пустые части (например, между двумя слешами)
                valid, message = self.validate_folder_name(part)
                if not valid:
                    return False, f"Недопустимая часть пути '{part}': {message}", False
        
        # Проверка существования папки на Яндекс.Диске
        try:
            # Корневой путь всегда существует
            if normalized_path == "/":
                return True, "", True
            
            # Проверяем существование через API
            try:
                await self.yadisk_helper.disk.get_meta_async(normalized_path)
                return True, "", True
            except AttributeError:
                # Если нет асинхронного метода, используем неасинхронный через executor
                try:
                    loop = asyncio.get_event_loop()
                    get_meta_func = partial(self.yadisk_helper.disk.get_meta, normalized_path)
                    await loop.run_in_executor(None, get_meta_func)
                    return True, "", True
                except yadisk.exceptions.PathNotFoundError:
                    return True, "", False
        except yadisk.exceptions.PathNotFoundError:
            return True, "", False
        except Exception as e:
            logger.error(f"Ошибка при проверке пути {normalized_path}: {e}", exc_info=True)
            return False, f"Ошибка при проверке пути: {str(e)}", False 
    
    async def add_allowed_folder(self, folder_path: str) -> Tuple[bool, str]:
        """
        Добавляет папку в список разрешенных с проверкой существования
        
        Возвращает: (успех операции, сообщение)
        """
        # Нормализуем путь
        normalized_path = self.normalize_path(folder_path)
        
        # Проверяем валидность и существование папки
        is_valid, error_msg, exists = await self.validate_folder_path(normalized_path)
        
        if not is_valid:
            return False, error_msg
        
        if not exists:
            return False, f"Папка '{normalized_path}' не существует на Яндекс.Диске"
        
        # Проверяем, не добавлена ли уже эта папка
        if normalized_path in self.allowed_folders:
            return False, f"Папка '{normalized_path}' уже добавлена в список разрешенных"
        
        try:
            # Загружаем текущий список папок
            with open(FOLDERS_FILE, 'r', encoding='utf-8') as f:
                folders = json.load(f)
            
            # Добавляем новую папку
            folders.append(normalized_path)
            
            # Сохраняем обновленный список
            with open(FOLDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(folders, f, indent=4, ensure_ascii=False)
            
            # Обновляем список в памяти
            self.allowed_folders = [self.normalize_path(folder) for folder in folders]
            
            # Кэшируем новую папку
            try:
                await self.get_folders(normalized_path)
            except Exception as e:
                logger.warning(f"Не удалось кэшировать новую папку {normalized_path}: {e}")
            
            return True, f"Папка '{normalized_path}' успешно добавлена в список разрешенных"
        except Exception as e:
            logger.error(f"Ошибка при добавлении папки {normalized_path}: {e}", exc_info=True)
            return False, f"Ошибка при добавлении папки: {str(e)}"
    
    async def remove_allowed_folder(self, folder_path: str) -> Tuple[bool, str]:
        """
        Удаляет папку из списка разрешенных
        
        Возвращает: (успех операции, сообщение)
        """
        # Нормализуем путь
        normalized_path = self.normalize_path(folder_path)
        
        # Проверяем, есть ли папка в списке
        if normalized_path not in self.allowed_folders:
            return False, f"Папка '{normalized_path}' не найдена в списке разрешенных"
        
        try:
            # Загружаем текущий список папок
            with open(FOLDERS_FILE, 'r', encoding='utf-8') as f:
                folders = json.load(f)
            
            # Удаляем папку из списка (нужно учесть разные форматы пути)
            for i, folder in enumerate(folders):
                if self.normalize_path(folder) == normalized_path:
                    removed_folder = folders.pop(i)
                    break
            
            # Сохраняем обновленный список
            with open(FOLDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(folders, f, indent=4, ensure_ascii=False)
            
            # Обновляем список в памяти
            self.allowed_folders = [self.normalize_path(folder) for folder in folders]
            
            # Очищаем кэш для этой папки
            if normalized_path in self.folder_cache:
                del self.folder_cache[normalized_path]
            
            return True, f"Папка '{normalized_path}' успешно удалена из списка разрешенных"
        except Exception as e:
            logger.error(f"Ошибка при удалении папки {normalized_path}: {e}", exc_info=True)
            return False, f"Ошибка при удалении папки: {str(e)}"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Очищает имя файла от недопустимых символов
        
        Args:
            filename: Исходное имя файла
            
        Returns:
            Очищенное имя файла
        """
        if not filename:
            return "unnamed_file"
            
        # Недопустимые символы в именах файлов на Яндекс.Диске
        invalid_chars = ['\\', ':', '*', '?', '"', '<', '>', '|', '/']
        
        # Заменяем недопустимые символы на нижнее подчеркивание
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Ограничиваем длину имени файла
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:100 - len(ext)] + ext
        
        return filename
        
    def safe_join_path(self, *parts: str) -> str:
        """
        Безопасно объединяет части пути, избегая проблем с двойными слешами
        
        Args:
            *parts: Части пути для объединения
            
        Returns:
            Объединенный путь
        """
        return self.__class__.safe_join_path_static(*parts)
        
    @staticmethod
    def safe_join_path_static(*parts: str) -> str:
        """
        Статический метод для безопасного объединения частей пути
        
        Args:
            *parts: Части пути для объединения
            
        Returns:
            Объединенный путь
        """
        # Убираем пустые части пути
        filtered_parts = [p for p in parts if p]
        
        if not filtered_parts:
            return "/"
        
        # Собираем путь
        result = ""
        for part in filtered_parts:
            part = str(part).strip().strip('/')  # Убираем начальные и конечные слеши
            if part:
                result = result.rstrip('/') + '/' + part
                
        # Если путь пуст, возвращаем корневой путь
        if not result:
            return "/"
            
        # Убеждаемся, что путь начинается с /
        if not result.startswith('/'):
            result = '/' + result
            
        return result 