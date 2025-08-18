@echo off
REM check_bot_status.bat - Проверка статуса Portfolio Telegram Bot

echo Проверка статуса Portfolio Telegram Bot...
echo.

REM Проверяем процессы Python
tasklist /fi "imagename eq pythonw.exe" | find /i "pythonw.exe" >nul
if not errorlevel 1 (
    echo ✅ Обнаружены фоновые процессы Python:
    tasklist /fi "imagename eq pythonw.exe"
    echo.
) else (
    echo ❌ Фоновые процессы Python не найдены
)

REM Проверяем обычные процессы Python  
tasklist /fi "imagename eq python.exe" | find /i "python.exe" >nul
if not errorlevel 1 (
    echo ✅ Обнаружены активные процессы Python:
    tasklist /fi "imagename eq python.exe"
    echo.
) else (
    echo ❌ Активные процессы Python не найдены
)

REM Проверяем логи, если они есть
if exist "logs" (
    echo 📋 Последние записи в логах:
    for %%f in (logs\*.log) do (
        echo Файл: %%f
        for /f "delims=" %%i in ('type "%%f" ^| findstr /n ".*" ^| tail -3') do echo   %%i
    )
    echo.
)

echo 💡 Совет: Проверьте Telegram, отправив команду /status боту
echo.
pause
exit /b 0