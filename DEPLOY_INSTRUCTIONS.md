# Инструкции по развертыванию ITD_TG2YaDisk_Lite на VPS

## Предварительные требования

Для развертывания бота на VPS вам понадобится:
1. Удаленный сервер (VPS) с доступом по SSH
2. Учетные данные для доступа к серверу (IP-адрес, имя пользователя, пароль)
3. Клонированный репозиторий проекта на вашем локальном компьютере

## Метод 1: Автоматическое развертывание с помощью скрипта deploy_ssh.sh

### Подготовка

1. Убедитесь, что на вашем компьютере установлен `sshpass`:
   ```bash
   # На macOS
   brew install hudochenkov/sshpass/sshpass
   
   # На Linux (Debian/Ubuntu)
   sudo apt-get install sshpass
   ```

2. Добавьте параметр `VPS_PASSWORD` в ваш файл `.env`:
   ```
   VPS_PASSWORD=ваш_пароль_от_сервера
   ```

3. Отредактируйте файл `deploy_ssh.sh`, указав правильный IP-адрес вашего сервера:
   ```bash
   SERVER_IP="ваш_ip_адрес"
   SERVER_USER="ваш_пользователь" # обычно "root"
   ```

### Запуск развертывания

1. Сделайте скрипт исполняемым:
   ```bash
   chmod +x deploy_ssh.sh
   ```

2. Запустите скрипт:
   ```bash
   ./deploy_ssh.sh
   ```

3. Скрипт автоматически подключится к серверу, установит необходимые зависимости и настроит автозапуск бота.

## Метод 2: Ручное развертывание на сервере

### Шаг 1: Подключение к серверу

```bash
ssh root@ваш_ip_адрес
```

### Шаг 2: Обновление системы и установка зависимостей

```bash
apt update && apt upgrade -y
apt install -y python3-pip python3-venv git ffmpeg portaudio19-dev
```

### Шаг 3: Клонирование репозитория

```bash
cd /opt
git clone https://github.com/Ballindaboy/ITD_TG2YaDisk_Lite.git
cd ITD_TG2YaDisk_Lite
```

### Шаг 4: Настройка окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 5: Создание конфигурационного файла

Создайте файл `.env` с вашими параметрами:

```bash
cat > .env << EOF
TELEGRAM_TOKEN=ваш_токен_telegram
YANDEX_DISK_TOKEN=ваш_токен_yandex_disk
LOG_LEVEL=DEBUG
ADMIN_IDS=ваш_id_телеграм
EOF
```

### Шаг 6: Создание необходимых директорий

```bash
mkdir -p logs
mkdir -p upload_temp
```

### Шаг 7: Настройка systemd для автозапуска

Создайте файл конфигурации службы:

```bash
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
```

### Шаг 8: Включение и запуск сервиса

```bash
systemctl daemon-reload
systemctl enable itd-tgbot
systemctl start itd-tgbot
```

## Проверка статуса и управление ботом

### Проверка статуса

```bash
systemctl status itd-tgbot
```

### Просмотр логов

```bash
journalctl -u itd-tgbot -f
```

### Перезапуск бота

```bash
systemctl restart itd-tgbot
```

### Остановка бота

```bash
systemctl stop itd-tgbot
```

## Обновление бота

Для обновления бота выполните следующие команды на сервере:

```bash
cd /opt/ITD_TG2YaDisk_Lite
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart itd-tgbot
```

## Устранение неполадок

### Проблема: Бот не запускается

1. Проверьте логи:
   ```bash
   journalctl -u itd-tgbot -e
   ```

2. Проверьте правильность токенов в файле `.env`

3. Проверьте наличие всех необходимых директорий и файлов

### Проблема: Ошибки в файле конфигурации

Если вы видите ошибки связанные с файлами конфигурации, проверьте:

1. Правильно ли созданы файлы JSON в директории `data/`:
   ```bash
   cat /opt/ITD_TG2YaDisk_Lite/data/allowed_users.json
   cat /opt/ITD_TG2YaDisk_Lite/data/allowed_folders.json
   ```

2. При необходимости пересоздайте их:
   ```bash
   echo "[]" > /opt/ITD_TG2YaDisk_Lite/data/allowed_users.json
   echo "[]" > /opt/ITD_TG2YaDisk_Lite/data/allowed_folders.json
   ``` 