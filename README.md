# SICAE WEB

Sistema web de control escolar para administrar alumnos, grupos, personal, credenciales, asistencias y eventos fuera del plantel.

## Requisitos del servidor

- Windows 10/11 o un sistema compatible con Python.
- Python 3.12 o superior.
- PostgreSQL 14 o superior, instalado en el servidor o accesible por red.
- Navegador moderno. La cámara requiere HTTPS cuando se accede desde otro dispositivo.

## Instalar en una computadora nueva (Windows)

1. Copia la carpeta completa del proyecto. No copies `.venv` de otra computadora: los entornos virtuales de Python guardan rutas locales y deben crearse de nuevo en cada equipo.
2. Instala Python 3.12 o superior y PostgreSQL, o confirma que este equipo puede conectarse al servidor PostgreSQL existente.
3. Ejecuta `instalar_sicae.bat`. Se crea un entorno `.venv` local y se instalan las dependencias.
4. Edita `.env` y configura `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER` y `DATABASE_PASSWORD` para la base de datos que usará SICAE.
5. Si es una base nueva, créala en PostgreSQL. Luego inicializa las tablas con:

   ```powershell
   .\.venv\Scripts\python.exe -m app.database.init_db
   ```

   Ejecuta este comando después de actualizar una instalación existente para aplicar las migraciones incluidas. La inicialización conserva los datos existentes.

6. Ejecuta `iniciar_sicae.bat` y abre `http://127.0.0.1:8000`.

## Usar SICAE desde varios dispositivos

Instala y ejecuta la aplicación en una computadora que permanecerá encendida; esa computadora será el servidor. Configura su `.env` para usar la base PostgreSQL central. En los demás equipos abre el navegador y visita `http://IP_DEL_SERVIDOR:8000`; no necesitan instalar Python ni copiar la aplicación.

El servidor y los demás equipos deben estar en la misma red. Permite conexiones entrantes al puerto TCP 8000 en el firewall de Windows y usa la dirección IP que muestra `iniciar_sicae.bat`. Reserva una IP local para el servidor en el router o actualiza el enlace cuando cambie. Si ejecutas más de un servidor, usa puertos distintos con la variable `PORT`.

Cada instalación que apunte a una base de datos local tendrá datos separados. Para que todos vean los mismos alumnos y asistencias, todos los servidores SICAE deben apuntar a la misma base PostgreSQL. Si PostgreSQL está en otra computadora, configura `DATABASE_HOST` con la IP/nombre de ese servidor y habilita conexiones de red en PostgreSQL y su firewall.

No expongas PostgreSQL ni SICAE directamente a Internet. Para acceso fuera de la escuela, configura una VPN o un despliegue HTTPS con controles de acceso. La cámara del escáner en otros dispositivos requiere HTTPS; en HTTP, los navegadores suelen permitir cámara solo en `localhost`.

## Variables de entorno

Consulta `.env.example`. Usa una `SECRET_KEY` privada y estable. No copies secretos de una computadora a repositorios públicos. SMTP es opcional y también se puede configurar desde el panel del sistema.

### Primer administrador en Render

El Blueprint define el usuario inicial como `admin` y Render genera su contraseña aleatoria. El servicio crea esa cuenta únicamente si la tabla `usuarios` está vacía. Consulta la contraseña en **Environment** del servicio web de Render. La contraseña se genera en Render y no se guarda en `render.yaml` ni en GitHub.

## Despliegue Docker

La imagen escucha en `PORT` (8000 por defecto). Configura las variables de entorno, inicializa las tablas con `python -m app.database.init_db` y monta almacenamiento persistente en `/app/app/static/uploads`, `/app/app/static/reportes` y `/app/backups` si necesitas conservar archivos entre despliegues. Configura HTTPS en el proveedor para habilitar la cámara y las cookies seguras.

```sh
docker build -t sicae-web .
docker run --env-file .env -p 8000:8000 sicae-web
```

Los datos de estudiantes y los archivos generados son información privada. Limita el acceso al servidor y a la base de datos, y conserva respaldos en un lugar seguro.
