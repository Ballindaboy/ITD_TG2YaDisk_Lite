import logging
import os
import tempfile
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """Класс для распознавания речи из голосовых сообщений"""
    def __init__(self, language="ru-RU"):
        """Инициализация распознавателя речи с указанным языком"""
        self.recognizer = sr.Recognizer()
        self.language = language
    
    async def recognize_voice(self, voice_file_path):
        """
        Распознает речь из голосового файла
        
        Args:
            voice_file_path: Путь к голосовому файлу (обычно ogg для Telegram)
        
        Returns:
            str: Распознанный текст или None в случае ошибки
        """
        try:
            # Создаем временный файл WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                wav_path = wav_file.name
                
            # Конвертируем OGG -> WAV
            audio = AudioSegment.from_file(voice_file_path, format="ogg")
            audio.export(wav_path, format="wav")
            
            # Распознаем речь
            with sr.AudioFile(wav_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=self.language)
                logger.info(f"Голосовое сообщение успешно распознано: {text[:50]}...")
                return text
                
        except sr.UnknownValueError:
            logger.warning("Не удалось распознать речь из аудиофайла")
            return None
        except sr.RequestError as e:
            logger.error(f"Ошибка API распознавания речи: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при распознавании речи: {e}", exc_info=True)
            return None
        finally:
            # Очистка временных файлов
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)

    @staticmethod
    async def download_voice_message(file, dest_path):
        """
        Загружает голосовое сообщение в локальный файл
        
        Args:
            file: Объект File из Telegram
            dest_path: Путь для сохранения файла
        
        Returns:
            str: Путь к сохраненному файлу или None в случае ошибки
        """
        try:
            # Используем download_to_drive вместо download
            await file.download_to_drive(dest_path)
            logger.debug(f"Голосовое сообщение загружено в {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Ошибка при загрузке голосового сообщения: {e}", exc_info=True)
            return None 