#!/bin/bash

# Скрипт для удаленного развертывания ITD_TG2YaDisk_Lite по SSH

# Настройки сервера
SERVER_IP="89.46.131.135"
SERVER_USER="root"
SERVER_PASS=$(grep "VPS_PASSWORD" .env | cut -d '=' -f2 | tr -d '\r')

# Проверка наличия файла .env и пароля
if [ ! -f ".env" ]; then
    echo "Файл .env не найден. Создайте файл .env с переменной VPS_PASSWORD."
    exit 1
fi

if [ -z "$SERVER_PASS" ]; then
    echo "Пароль VPS_PASSWORD не найден в файле .env."
    exit 1
fi

# Проверка наличия sshpass
if ! command -v sshpass &> /dev/null; then
    echo "Утилита sshpass не установлена. Установка..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install hudochenkov/sshpass/sshpass
    else
        # Linux
        apt-get update && apt-get install -y sshpass
    fi
fi

# Создание временного deploy.sh
TMP_DEPLOY_FILE=$(mktemp)
cat > "$TMP_DEPLOY_FILE" << 'EOF'
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
EOF

# Добавление содержимого .env в скрипт развертывания
echo "cat > .env << EOF" >> "$TMP_DEPLOY_FILE"
cat .env >> "$TMP_DEPLOY_FILE"
echo "EOF" >> "$TMP_DEPLOY_FILE"

# Добавление остальной части скрипта
cat >> "$TMP_DEPLOY_FILE" << 'EOF'

# Создание директорий для логов и загрузок
echo "Создание необходимых директорий..."
mkdir -p logs
mkdir -p upload_temp

# Настройка systemd для автозапуска
echo "Настройка автозапуска через systemd..."
cat > /etc/systemd/system/itd-tgbot.service << EOF2
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
EOF2

# Перезагрузка systemd и запуск сервиса
echo "Включение и запуск сервиса..."
systemctl daemon-reload
systemctl enable itd-tgbot
systemctl start itd-tgbot

echo "Статус сервиса:"
systemctl status itd-tgbot

echo "Развертывание завершено!"
echo "Для просмотра логов используйте команду: journalctl -u itd-tgbot -f"
EOF

echo "Загрузка и выполнение скрипта на удаленном сервере..."
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no "$TMP_DEPLOY_FILE" $SERVER_USER@$SERVER_IP:/root/deploy.sh
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "chmod +x /root/deploy.sh && /root/deploy.sh"

# Удаление временного файла
rm "$TMP_DEPLOY_FILE"

echo "Скрипт развертывания выполнен." 