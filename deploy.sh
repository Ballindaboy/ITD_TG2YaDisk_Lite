#!/bin/bash

# Скрипт развертывания ITD_TG2YaDisk_Lite на VPS сервере

# Обновление системы
echo "Обновление системы..."
apt update && apt upgrade -y

# Установка необходимых зависимостей
echo "Установка необходимых зависимостей..."
apt install -y python3-pip python3-venv git ffmpeg

# Установка portaudio для поддержки аудио (если необходимо)
apt install -y portaudio19-dev

# Клонирование репозитория
echo "Клонирование репозитория..."
cd /opt
if [ -d "ITD_TG2YaDisk_Lite" ]; then
  echo "Репозиторий уже существует, обновление..."
  cd ITD_TG2YaDisk_Lite
  git pull
else
  echo "Клонирование нового репозитория..."
  git clone https://github.com/Ballindaboy/ITD_TG2YaDisk_Lite.git
  cd ITD_TG2YaDisk_Lite
fi

# Создание виртуального окружения
echo "Настройка виртуального окружения..."
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# Активация виртуального окружения и установка зависимостей
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Создание .env файла
echo "Создание .env файла..."
cat > .env << EOF
TELEGRAM_TOKEN=7531432449:AAEuLLFLbvDTNO6mabSl_MkvTQ8UEBUMfEg
YANDEX_DISK_TOKEN=y0__xDWpaSgqveAAhiipjYgvurBzhL9pHCE7cB31vERm4snP6VWb_cHxA
LOG_LEVEL=DEBUG
ADMIN_IDS=112737057
EOF

# Создание директорий для логов и загрузок
echo "Создание необходимых директорий..."
mkdir -p logs
mkdir -p upload_temp

# Настройка systemd для автозапуска
echo "Настройка автозапуска через systemd..."
cat > /etc/systemd/system/itd-tgbot.service << EOF
[Unit]
Description=ITD Telegram to Yandex.Disk Bot
After=network.target

[Service]
User=root
WorkingDirectory=/opt/ITD_TG2YaDisk_Lite
ExecStart=/opt/ITD_TG2YaDisk_Lite/venv/bin/python -m main
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=itd-tgbot

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd и запуск сервиса
echo "Включение и запуск сервиса..."
systemctl daemon-reload
systemctl enable itd-tgbot
systemctl start itd-tgbot

echo "Статус сервиса:"
systemctl status itd-tgbot

echo "Развертывание завершено!"
echo "Для просмотра логов используйте команду: journalctl -u itd-tgbot -f" 