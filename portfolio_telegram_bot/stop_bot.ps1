@echo off
REM stop_bot.bat - Остановка Portfolio Telegram Bot

echo Остановка Portfolio Telegram Bot...

REM Находим и завершаем процессы Python, которые могут быть ботом
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq pythonw.exe" /fo table /nh 2^>nul') do (
    if not "%%i"=="INFO:" (
        echo Завершение процесса %%i...
        taskkill /pid %%i /f >nul 2>&1
    )
)

REM Также проверяем обычные процессы python.exe
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo table /nh 2^>nul') do (
    if not "%%i"=="INFO:" (
        echo Проверка процесса %%i...
        REM Здесь можно добавить более точную проверку, если нужно
    )
)

echo ✅ Бот остановлен
timeout /t 3
exit /b 0