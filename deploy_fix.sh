#!/bin/bash

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

# Отправляем файл исправления на сервер
echo "Отправка скрипта исправления на сервер..."
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no fix_error.sh $SERVER_USER@$SERVER_IP:/root/fix_error.sh

# Запускаем скрипт исправления на сервере
echo "Запуск скрипта исправления на сервере..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "chmod +x /root/fix_error.sh && /root/fix_error.sh"

echo "Исправление ошибки event loop выполнено на сервере."