import logging
import json
from typing import List, Union
from telegram import Update
from config.config import USERS_FILE, ADMIN_IDS

logger = logging.getLogger(__name__)

class AccessControl:
    """Класс для управления доступом пользователей к боту"""
    
    def __init__(self):
        """Инициализация контроля доступа"""
        self.allowed_users = self._load_allowed_users()
        logger.info(f"Загружено {len(self.allowed_users)} разрешенных пользователей")
        
    def _load_allowed_users(self) -> List[int]:
        """Загружает список разрешенных пользователей из файла"""
        try:
            with open(USERS_FILE, 'r') as f:
                user_ids = json.load(f)
                # Преобразуем ID в числовые, поддерживая и строковые и числовые значения
                return [int(user_id) for user_id in user_ids if user_id]
        except Exception as e:
            logger.error(f"Ошибка при загрузке разрешенных пользователей: {e}", exc_info=True)
            return []
    
    def save_allowed_users(self) -> bool:
        """Сохраняет список разрешенных пользователей в файл"""
        try:
            with open(USERS_FILE, 'w') as f:
                json.dump([str(user_id) for user_id in self.allowed_users], f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении разрешенных пользователей: {e}", exc_info=True)
            return False
    
    def add_allowed_user(self, user_id: int) -> bool:
        """Добавляет пользователя в список разрешенных"""
        if user_id not in self.allowed_users:
            self.allowed_users.append(user_id)
            logger.info(f"Пользователь {user_id} добавлен в список разрешенных")
            return self.save_allowed_users()
        return True
    
    def remove_allowed_user(self, user_id: int) -> bool:
        """Удаляет пользователя из списка разрешенных"""
        if user_id in self.allowed_users:
            self.allowed_users.remove(user_id)
            logger.info(f"Пользователь {user_id} удален из списка разрешенных")
            return self.save_allowed_users()
        return True
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Проверяет, разрешен ли доступ пользователю"""
        # Админы всегда имеют доступ
        if user_id in ADMIN_IDS:
            return True
            
        # Если список разрешенных пользователей пуст, разрешаем всем
        if not self.allowed_users:
            return True
            
        # Проверяем, есть ли пользователь в списке разрешенных
        return user_id in self.allowed_users
    
    def reload_users(self) -> None:
        """Перезагружает список разрешенных пользователей из файла"""
        self.allowed_users = self._load_allowed_users()
        logger.info(f"Список разрешенных пользователей перезагружен, {len(self.allowed_users)} пользователей")
    
    async def check_access(self, update: Update) -> bool:
        """Проверяет доступ пользователя к боту"""
        if not update.effective_user:
            logger.warning("Попытка доступа без данных пользователя")
            return False
            
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        allowed = self.is_user_allowed(user_id)
        
        if allowed:
            logger.debug(f"Доступ разрешен: пользователь {username} (ID: {user_id})")
        else:
            logger.warning(f"Доступ запрещен: пользователь {username} (ID: {user_id})")
            
        return allowed

# Создаем экземпляр контроля доступа
access_control = AccessControl() 