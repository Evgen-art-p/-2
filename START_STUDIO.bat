@echo off
chcp 65001
cls

echo [1] ПРОВЕРЯЮ PYTHON...
python --version
IF %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Windows не видит команду 'python'.
    echo Попробуй использовать 'py' вместо 'python'.
    goto :error
)

echo.
echo [2] ПРОБУЮ ЗАПУСТИТЬ СТУДИЮ...
python main.py

:error
echo.
echo ==========================================
echo ЕСЛИ СТУДИЯ УПАЛА - СДЕЛАЙ СКРИНШОТ ЭТОГО ЭКРАНА
echo ==========================================
pause

:: 3. Если Студия упала или закрылась - не закрываем окно сразу
echo.
echo ==================================================
echo [STOP] Studio process finished.
echo If you see an error above, take a screenshot!
echo ==================================================
pause