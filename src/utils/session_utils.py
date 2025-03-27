import logging
import time
from typing import Dict, Optional
from config.config import get_current_timestamp

logger = logging.getLogger(__name__)

class SessionState:
    """Класс для хранения данных о текущей сессии встречи"""
    def __init__(self, root_folder: str, folder_path: str, folder_name: str, user_id: int):
        self.root_folder = root_folder
        self.folder_path = folder_path
        self.folder_name = folder_name
        self.timestamp = get_current_timestamp()
        self.txt_file_path = f"{folder_path}/{self.timestamp}_visit_{folder_name}_{user_id}.txt"
        self.file_prefix = f"{self.timestamp}_Files_{folder_name}_{user_id}"
        self.user_id = user_id
        self.messages = []  # Список сообщений в сессии
        self.start_time = time.time()
    
    def get_txt_filename(self) -> str:
        """Возвращает имя текстового файла"""
        return f"{self.timestamp}_visit_{self.folder_name}_{self.user_id}.txt"
    
    def get_media_prefix(self) -> str:
        """Возвращает префикс для медиафайлов"""
        return f"{self.timestamp}_Files_{self.folder_name}_{self.user_id}"
    
    def add_message(self, message: str, author: str = "") -> str:
        """Добавляет сообщение в историю сессии и возвращает отформатированное сообщение"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        author_prefix = f"[{author}] " if author else ""
        formatted_message = f"[{timestamp}] {author_prefix}{message}"
        self.messages.append(formatted_message)
        logger.debug(f"Добавлено сообщение в сессию: {formatted_message[:50]}...")
        return formatted_message
    
    def get_session_summary(self) -> str:
        """Возвращает сводку по сессии"""
        duration = time.time() - self.start_time
        hours, remainder = divmod(int(duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Получаем количество сообщений
        total_messages = len(self.messages)
        
        summary = [
            f"📁 Папка: {self.folder_path}",
            f"📄 Файл: {self.get_txt_filename()}",
            f"⏱ Продолжительность: {hours}ч {minutes}м {seconds}с",
            f"✍️ Количество записей: {total_messages}"
        ]
        
        return "\n".join(summary)

class StateManager:
    """Класс для управления состояниями пользователей"""
    def __init__(self):
        # Ключ: user_id, Значение: текущая сессия
        self.sessions: Dict[int, SessionState] = {}
        # Ключ: user_id, Значение: текущее состояние в диалоге
        self.states: Dict[int, str] = {}
        # Ключ: user_id, Значение: временные данные
        self.data: Dict[int, Dict] = {}
    
    def set_state(self, user_id: int, state: str) -> None:
        """Устанавливает состояние для пользователя"""
        self.states[user_id] = state
        logger.debug(f"Установлено состояние {state} для пользователя {user_id}")
    
    def get_state(self, user_id: int) -> Optional[str]:
        """Возвращает текущее состояние пользователя"""
        return self.states.get(user_id)
    
    def reset_state(self, user_id: int) -> None:
        """Сбрасывает состояние пользователя"""
        if user_id in self.states:
            del self.states[user_id]
    
    def set_session(self, user_id: int, session: SessionState) -> None:
        """Устанавливает сессию для пользователя"""
        # Сначала завершаем текущую сессию, если она существует
        self.clear_session(user_id)
        # Затем устанавливаем новую
        self.sessions[user_id] = session
        logger.info(f"Установлена новая сессия для пользователя {user_id}: {session.folder_path}")
    
    def get_session(self, user_id: int) -> Optional[SessionState]:
        """Возвращает текущую сессию пользователя"""
        return self.sessions.get(user_id)
    
    def clear_session(self, user_id: int) -> None:
        """Удаляет сессию пользователя"""
        if user_id in self.sessions:
            logger.info(f"Сессия пользователя {user_id} завершена: {self.sessions[user_id].folder_path}")
            del self.sessions[user_id]
    
    def has_active_session(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя активная сессия"""
        return user_id in self.sessions

# Создаем глобальный экземпляр менеджера состояний
state_manager = StateManager() 