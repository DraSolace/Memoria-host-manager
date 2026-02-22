@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MEMORIA Host Manager
setlocal EnableDelayedExpansion

net session >nul 2>&1
if %errorlevel% NEQ 0 goto NO_ADMIN
goto MAIN_MENU

:NO_ADMIN
cls
echo ==========================================
echo MEMORIA Host Manager
echo ==========================================
echo.
echo Скрипт запущен БЕЗ прав администратора.
echo Настройка hosts будет недоступна. 
echo MEMORIA host manager можно сбилдить без права администратора.
echo.
echo [1] Перезапустить с правами администратора
echo [2] Продолжить без прав администратора
echo.
set /p ADMIN_CHOICE=Выберите вариант (1-2): 

if "%ADMIN_CHOICE%"=="1" goto RESTART_ADMIN
if "%ADMIN_CHOICE%"=="2" goto MAIN_MENU
goto NO_ADMIN

:RESTART_ADMIN
echo Перезапуск с правами администратора...
timeout /t 1 >nul

powershell -Command "Start-Process -FilePath '%COMSPEC%' -ArgumentList '/c ""%~f0""' -Verb RunAs -WorkingDirectory '%~dp0'"

pause
exit

:: ===============================
:: Главное меню
:: ===============================
:MAIN_MENU
cls
echo ==========================================
echo        MEMORIA Host Manager
echo ==========================================
echo.
echo [1] Сбилдить MEMORIA Host Manager
echo [2] Настроить hosts (MEMORIA)
echo [3] Выход
echo.
set /p MAIN_CHOICE=Выберите пункт (1-3): 

if "%MAIN_CHOICE%"=="1" goto BUILD
if "%MAIN_CHOICE%"=="2" goto HOSTS_MENU
if "%MAIN_CHOICE%"=="3" goto EXIT
goto MAIN_MENU

:: ===============================
:: BUILD
:: ===============================
:BUILD
cls
echo Проверка Python в PATH...
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Python не найден. Установите Python и добавьте его в PATH.
    pause
    goto MAIN_MENU
)

echo Python найден.
echo Проверка PyInstaller в PATH...
pyinstaller --version >nul 2>&1
set PYINST=%errorlevel%
if "%PYINST%" NEQ "0" goto PY_NOT_FOUND

:PY_FOUND
echo Все необходимые инструменты найдены.
echo Установка зависимостей из requirements.txt...
pip install --quiet --disable-pip-version-check --no-warn-script-location -r requirements.txt

echo.
echo Сборка MEMORIA Host Manager...
pyinstaller --noconfirm --onefile --windowed --name MEMORIA_Host_Manager main.py

echo.
echo Готово. Проверь папку "dist".
pause
goto MAIN_MENU

:PY_NOT_FOUND
echo PyInstaller не найден.
echo [1] Установить PyInstaller через pip
echo [2] Вернуться в главное меню
set /p PIP_CHOICE=Выберите вариант (1-2): 
if "%PIP_CHOICE%"=="1" (
    pip install pyinstaller
)
goto MAIN_MENU

:: ===============================
:: HOSTS
:: ===============================
:HOSTS_MENU
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    cls
    echo ==========================================
    echo Настройка hosts недоступна
    echo ==========================================
    echo.
    echo Для изменения файла hosts требуются права администратора.
    pause
    goto MAIN_MENU
)

cls
echo ==========================================
echo Настройка hosts (MEMORIA)
echo ==========================================
echo.
echo Для чайничков:
echo Memoria Host Manager будет слушать порт 80 на всех интерфейсах (0.0.0.0:80).
echo 1. Если вы хостите MEMORIA, выберите ваш локальный IP. Он будет занесен в hosts под домен MEMORIA на 80 порту.
echo 2. Если вы клиент, введите локальный IP хостера, который он выбрал в этом меню. Он будет занесен в hosts под домен MEMORIA на 80 порту.
echo После этого, введите в любом браузере MEMORIA:80
echo.
echo [1] Выбрать свой локальный IP (если хостишь)
echo [2] Ввести IP хостера вручную (если клиент)
echo [0] Назад
echo.
set /p HOST_MODE=Выберите вариант: 

if "%HOST_MODE%"=="0" goto MAIN_MENU
if "%HOST_MODE%"=="1" goto PICK_LOCAL_IP
if "%HOST_MODE%"=="2" goto MANUAL_IP
goto HOSTS_MENU

:: ===============================
:: HOSTS: выбор локального IPv4
:: ===============================
:PICK_LOCAL_IP
cls
echo ==========================================
echo Выбор локального IPv4
echo ==========================================
echo.

setlocal EnableDelayedExpansion
set COUNT=0

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4"') do (
    set "ip=%%i"
    set "ip=!ip: =!"
    set /a COUNT+=1
    set "IP!COUNT!=!ip!"
    echo [!COUNT!] !ip!
)

if %COUNT%==0 (
    echo.
    echo IPv4 адреса не найдены.
    pause
    endlocal
    goto HOSTS_MENU
)

echo.
echo [0] Назад
echo.
set /p IP_CHOICE=Выберите IP: 

if "%IP_CHOICE%"=="0" (
    endlocal
    goto HOSTS_MENU
)

set TARGET_IP=!IP%IP_CHOICE%!
if "%TARGET_IP%"=="" (
    echo Неверный выбор!
    pause
    endlocal
    goto HOSTS_MENU
)

endlocal
goto ADD_HOSTS

:: ===============================
:: HOSTS: ручной ввод IP
:: ===============================
:MANUAL_IP
cls
set /p TARGET_IP=Введите IP хостера: 
goto ADD_HOSTS

:: ===============================
:: HOSTS: добавление записи
:: ===============================
:ADD_HOSTS
cls
set HOSTNAME=MEMORIA
set HOSTS_FILE=%windir%\System32\drivers\etc\hosts

findstr /i "%HOSTNAME%" "%HOSTS_FILE%" >nul
if %errorlevel% EQU 0 (
    echo Запись MEMORIA уже существует в hosts.
    pause
    goto MAIN_MENU
)

echo %TARGET_IP% %HOSTNAME% >> "%HOSTS_FILE%"

echo.
echo ==========================================
echo ГОТОВО
echo ==========================================
echo MEMORIA указывает на %TARGET_IP%
echo.
echo В браузере откройте:
echo   http://MEMORIA:80
echo.
pause
goto MAIN_MENU

:: ===============================
:: EXIT
:: ===============================
:EXIT
cls
echo До встречи.
timeout /t 1 >nul
exit