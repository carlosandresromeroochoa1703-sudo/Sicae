@echo off
setlocal
title SICAE WEB
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No se encontro el entorno de Python de SICAE.
    echo Ejecuta primero instalar_sicae.bat en esta computadora.
    pause
    exit /b 1
)

if not exist ".env" (
    echo No se encontro .env. Copia .env.example a .env y configura PostgreSQL.
    pause
    exit /b 1
)

if not defined PORT set "PORT=8000"
set "SICAE_HOST=0.0.0.0"

powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%PORT%/' -TimeoutSec 3; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { exit 0 } } catch { if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -lt 400) { exit 0 } }; exit 1"
if not errorlevel 1 goto SERVIDOR_ACTIVO

powershell -NoProfile -Command "$client = New-Object Net.Sockets.TcpClient; try { $client.Connect('127.0.0.1',%PORT%); if ($client.Connected) { exit 0 } } catch { } finally { $client.Dispose() }; exit 1"
if not errorlevel 1 goto PUERTO_OCUPADO

for /f %%I in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceOperationalStatus -eq 'Up' } ^| Select-Object -First 1 -ExpandProperty IPAddress)"') do set "SICAE_LAN_IP=%%I"
echo Iniciando SICAE en el puerto %PORT%...
echo El servidor escucha en las interfaces de red de esta computadora.
if defined SICAE_LAN_IP echo Direccion para otros dispositivos de la misma red: http://%SICAE_LAN_IP%:%PORT%
echo Deja esta ventana abierta mientras uses SICAE.
echo.
start "" "http://127.0.0.1:%PORT%"
".venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port %PORT%
if errorlevel 1 (
    echo.
    echo SICAE se detuvo por un error. Revisa PostgreSQL y el mensaje anterior.
    pause
)
endlocal
exit /b

:SERVIDOR_ACTIVO
echo SICAE ya esta en ejecucion en http://127.0.0.1:%PORT%.
start "" "http://127.0.0.1:%PORT%"
pause
endlocal
exit /b 0

:PUERTO_OCUPADO
echo El puerto %PORT% esta ocupado, pero SICAE no responde ahi.
echo Cierra la aplicacion que usa ese puerto o inicia SICAE con otro PORT.
pause
endlocal
exit /b 1
