import logging
import asyncio
import json
from functools import partial
from typing import List, Dict, Any, Tuple, Optional, Callable
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config.config import FOLDERS_FILE

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
        # Удаляем префикс диска, который может быть добавлен API Яндекс.Диска
        path = path.replace("disk:", "")
        
        # И принимает пути как с начальными и конечными слешами, так и без них
        # Для единообразия мы приводим все пути к формату с начальным '/'
        # и без конечного '/' (кроме корневого пути)
        if not path.startswith("/"):
            path = "/" + path
            
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
        parent_path = self.normalize_path(parent_path)
        
        if parent_path == "/":
            return f"/{folder_name}"
        return f"{parent_path}/{folder_name}"
    
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
    
    async def cache_allowed_folders(self) -> None:
        """Кэширует структуру разрешенных папок"""
        if not self.allowed_folders:
            logger.warning("Нет разрешенных папок для кэширования")
            return
        
        logger.info("Начало кэширования разрешенных папок...")
        for allowed_folder in self.allowed_folders:
            try:
                logger.info(f"Кэширование папки: {allowed_folder}")
                await self.get_folders(allowed_folder)
            except Exception as e:
                logger.error(f"Ошибка при кэшировании папки {allowed_folder}: {str(e)}", exc_info=True)
        
        logger.info("Кэширование папок завершено")
    
    async def clear_cache(self) -> None:
        """Очищает кэш папок"""
        self.folder_cache.clear()
        logger.info("Кэш папок очищен")
    
    def build_keyboard(self, folders: List[Any], include_current_folder: bool = True) -> List[List[str]]:
        """Формирует клавиатуру для выбора папок"""
        keyboard = []
        
        # Ограничиваем количество папок для отображения
        max_folders = 30
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