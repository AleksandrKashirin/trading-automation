@echo off
REM start_bot_background.bat - Запуск бота в фоновом режиме

echo Запуск Portfolio Telegram Bot в фоновом режиме...

REM Проверяем существование Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Python не найден в PATH
    echo Установите Python или добавьте его в переменную PATH
    pause
    exit /b 1
)

REM Переходим в директорию проекта
cd /d "%~dp0"

REM Проверяем существование главного файла
if not exist "main.py" (
    echo Ошибка: main.py не найден в текущей директории
    echo Убедитесь, что вы запускаете скрипт из корня проекта
    pause
    exit /b 1
)

REM Запускаем бота в фоновом режиме (без окна консоли)
echo Запуск бота...
start /min pythonw.exe main.py

REM Ждем 3 секунды для инициализации
timeout /t 3 /nobreak >nul

REM Проверяем, запустился ли процесс
tasklist /fi "imagename eq pythonw.exe" | find /i "pythonw.exe" >nul
if errorlevel 1 (
    echo Ошибка: Бот не удалось запустить
    pause
    exit /b 1
) else (
    echo ✅ Бот успешно запущен в фоновом режиме
    echo 📱 Проверьте Telegram для подтверждения работы
    echo 🛑 Для остановки используйте stop_bot.bat
)

timeout /t 5
exit /b 0