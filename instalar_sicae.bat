@echo off
setlocal
title Instalador SICAE WEB
cd /d "%~dp0"

echo ==========================================
echo          INSTALADOR SICAE WEB
echo ==========================================
echo.

where py >nul 2>&1
if not errorlevel 1 (
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=py -3.12"
        goto PYTHON_OK
    )
)
where python >nul 2>&1
if errorlevel 1 goto PYTHON_MISSING
python --version
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 goto PYTHON_VERSION
set "PYTHON=python"

:PYTHON_OK
echo Usando Python:
%PYTHON% --version

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno local para esta computadora...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto VENV_ERROR
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto PIP_ERROR
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto PIP_ERROR

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Se creo .env desde .env.example.
)
echo.
echo Instalacion de Python completada.
echo Abre .env y configura el host, usuario y contrasena de PostgreSQL.
echo La base PostgreSQL debe existir y ser accesible desde esta computadora.
echo Despues ejecuta: .venv\Scripts\python.exe -m app.database.init_db
echo Para iniciar SICAE ejecuta iniciar_sicae.bat.
echo.
pause
exit /b 0

:PYTHON_MISSING
echo ERROR: Instala Python 3.12 o superior y vuelve a ejecutar este instalador.
echo Durante la instalacion de Python activa la opcion para agregarlo al PATH.
goto ERROR

:PYTHON_VERSION
echo ERROR: Se requiere Python 3.12 o superior.
goto ERROR

:VENV_ERROR
echo ERROR: No se pudo crear el entorno virtual de Python.
goto ERROR

:PIP_ERROR
echo ERROR: No se pudieron instalar las dependencias. Revisa la conexion a Internet.
goto ERROR

:ERROR
pause
exit /b 1
