#!/bin/bash

# Путь к файлу
FILE="/opt/ITD_TG2YaDisk_Lite/main.py"

# Создаем резервную копию
cp "$FILE" "${FILE}.bak"

# Заменяем проблемные строки
sed -i -e '150,158s/def main().*application = asyncio.run(setup_application())/def main():\
    """Запускает бота"""\
    try:\
        # Создаем новый event loop\
        loop = asyncio.new_event_loop()\
        asyncio.set_event_loop(loop)\
        \
        # Создаем и настраиваем приложение\
        application = loop.run_until_complete(setup_application())/' "$FILE"

# Перезапускаем сервис
systemctl restart ITD_TG2YaDisk_Lite

# Проверяем статус
systemctl status ITD_TG2YaDisk_Lite

echo "Исправление ошибки event loop выполнено. Проверьте логи: journalctl -u ITD_TG2YaDisk_Lite -n 20"