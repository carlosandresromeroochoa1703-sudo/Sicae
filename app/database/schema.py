# ============================================================
# SCHEMA DE BASE DE DATOS - SICAE WEB
# ============================================================


TABLAS = {

    # ========================================================
    # USUARIOS
    # ========================================================

    "usuarios": """
        CREATE TABLE IF NOT EXISTS usuarios (

            id SERIAL PRIMARY KEY,

            usuario VARCHAR(50)
                UNIQUE NOT NULL,

            password VARCHAR(255)
                NOT NULL,

            nombre VARCHAR(150)
                NOT NULL,

            rol VARCHAR(30)
                NOT NULL
                DEFAULT 'operador',

            permisos JSONB NOT NULL DEFAULT '[]'::jsonb,

            activo BOOLEAN
                NOT NULL
                DEFAULT TRUE,

            fecha_creacion TIMESTAMP
                NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        );
    """,


    # ========================================================
    # GRUPOS
    # ========================================================

    "grupos": """
        CREATE TABLE IF NOT EXISTS grupos (

            id SERIAL PRIMARY KEY,

            nombre_grupo VARCHAR(100)
                NOT NULL,

            grado INTEGER
                NOT NULL,

            nombre VARCHAR(20)
                NOT NULL,

            turno VARCHAR(20)
                NOT NULL,

            activo BOOLEAN
                NOT NULL
                DEFAULT TRUE,

            fecha_creacion TIMESTAMP
                NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT grupos_grado_valido
                CHECK (grado > 0)
        );
    """,


    # ========================================================
    # ALUMNOS
    # ========================================================

    "alumnos": """
        CREATE TABLE IF NOT EXISTS alumnos (

            id SERIAL PRIMARY KEY,

            matricula VARCHAR(50)
                UNIQUE NOT NULL,

            nombre VARCHAR(100)
                NOT NULL,

            apellido_paterno VARCHAR(100)
                NOT NULL,

            apellido_materno VARCHAR(100),

            fecha_nacimiento DATE,

            numero_seguro_social VARCHAR(30),

            nombre_padre VARCHAR(200),

            curp VARCHAR(18),

            correo VARCHAR(150),

            telefono VARCHAR(30),

            foto VARCHAR(500),

            qr VARCHAR(500),

            grupo_id INTEGER,

            activo BOOLEAN
                NOT NULL
                DEFAULT TRUE,

            fecha_registro TIMESTAMP
                NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT fk_alumno_grupo

                FOREIGN KEY (grupo_id)

                REFERENCES grupos(id)

                ON DELETE SET NULL
        );
    """,


    # ========================================================
    # ACCESOS
    # ========================================================

    "accesos": """
        CREATE TABLE IF NOT EXISTS accesos (

            id BIGSERIAL PRIMARY KEY,

            alumno_id INTEGER
                NOT NULL,

            fecha DATE
                NOT NULL
                DEFAULT CURRENT_DATE,

            hora TIME(0)
                NOT NULL
                DEFAULT CURRENT_TIME(0),

            movimiento VARCHAR(10)
                NOT NULL,

            registrado_por VARCHAR(120),

            CONSTRAINT fk_acceso_alumno

                FOREIGN KEY (alumno_id)

                REFERENCES alumnos(id)

                ON DELETE CASCADE,

            CONSTRAINT acceso_movimiento_valido

                CHECK (
                    movimiento IN (
                        'ENTRADA',
                        'SALIDA'
                    )
                )
        );
    """,


    # ========================================================
    # CONFIGURACIÓN DE ASISTENCIA
    # ========================================================

    "configuracion_asistencia": """
        CREATE TABLE IF NOT EXISTS configuracion_asistencia (
            id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            hora_entrada TIME NOT NULL DEFAULT '07:30',
            tolerancia_minutos INTEGER NOT NULL DEFAULT 10
                CHECK (tolerancia_minutos BETWEEN 0 AND 180),
            hora_cierre_entrada TIME NOT NULL DEFAULT '08:30',
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """,


    # ========================================================
    # PERSONAL
    # ========================================================

    "personal": """
        CREATE TABLE IF NOT EXISTS personal (

            id SERIAL PRIMARY KEY,

            numero_empleado VARCHAR(50)
                UNIQUE NOT NULL,

            nombre VARCHAR(100)
                NOT NULL,

            apellido_paterno VARCHAR(100)
                NOT NULL,

            apellido_materno VARCHAR(100),

            tipo_personal VARCHAR(50)
                NOT NULL,

            cargo VARCHAR(100),

            area VARCHAR(100),

            correo VARCHAR(150),

            telefono VARCHAR(30),

            foto VARCHAR(500),

            qr VARCHAR(500),

            activo BOOLEAN
                NOT NULL
                DEFAULT TRUE,

            fecha_registro TIMESTAMP
                NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        );
    """,

    # ========================================================`r`n    # ACCESOS DEL PERSONAL
    # ========================================================

    "accesos_personal": """
        CREATE TABLE IF NOT EXISTS accesos_personal (

            id BIGSERIAL PRIMARY KEY,

            personal_id INTEGER
                NOT NULL,

            fecha DATE
                NOT NULL
                DEFAULT CURRENT_DATE,

            hora TIME(0)
                NOT NULL
                DEFAULT CURRENT_TIME(0),

            movimiento VARCHAR(10)
                NOT NULL,

            registrado_por VARCHAR(120),

            CONSTRAINT fk_acceso_personal

                FOREIGN KEY (personal_id)

                REFERENCES personal(id)

                ON DELETE CASCADE,

            CONSTRAINT acceso_personal_movimiento_valido

                CHECK (
                    movimiento IN (
                        'ENTRADA',
                        'SALIDA'
                    )
                )
        );
    """,

    "credenciales_especiales": """
        CREATE TABLE IF NOT EXISTS credenciales_especiales (
            id BIGSERIAL PRIMARY KEY,
            tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('direccion', 'prefectura', 'conferencias', 'proveedores')),
            codigo VARCHAR(30) UNIQUE,
            nombre VARCHAR(100) NOT NULL,
            apellido_paterno VARCHAR(100),
            apellido_materno VARCHAR(100),
            cargo VARCHAR(120),
            organizacion VARCHAR(160),
            telefono VARCHAR(30),
            foto VARCHAR(500),
            qr VARCHAR(500),
            correo_1 VARCHAR(254),
            correo_2 VARCHAR(254),
            correo_3 VARCHAR(254),
            correo_4 VARCHAR(254),
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """,

    "accesos_credenciales_especiales": """
        CREATE TABLE IF NOT EXISTS accesos_credenciales_especiales (
            id BIGSERIAL PRIMARY KEY,
            credencial_id BIGINT NOT NULL REFERENCES credenciales_especiales(id) ON DELETE CASCADE,
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            hora TIME(0) NOT NULL DEFAULT CURRENT_TIME(0),
            movimiento VARCHAR(10) NOT NULL CHECK (movimiento IN ('ENTRADA', 'SALIDA')),
            registrado_por VARCHAR(120)
        );
    """,

    "configuracion_credencial_especial": """
        CREATE TABLE IF NOT EXISTS configuracion_credencial_especial (
            tipo VARCHAR(30) PRIMARY KEY CHECK (tipo IN ('direccion', 'prefectura', 'conferencias', 'proveedores')),
            nombre_institucion VARCHAR(200) NOT NULL DEFAULT 'SICAE WEB',
            subtitulo VARCHAR(300) DEFAULT '',
            texto_pie VARCHAR(300) DEFAULT 'Identificación oficial',
            logo VARCHAR(255),
            color_principal VARCHAR(20) DEFAULT '#1e3a8a',
            color_secundario VARCHAR(20) DEFAULT '#2563eb',
            color_texto VARCHAR(20) DEFAULT '#111827',
            color_fondo VARCHAR(20) DEFAULT '#ffffff',
            fuente VARCHAR(100) DEFAULT 'Arial',
            tamano_nombre INTEGER NOT NULL DEFAULT 20,
            mostrar_foto BOOLEAN NOT NULL DEFAULT TRUE,
            mostrar_qr BOOLEAN NOT NULL DEFAULT TRUE,
            mostrar_codigo BOOLEAN NOT NULL DEFAULT TRUE,
            mostrar_cargo BOOLEAN NOT NULL DEFAULT TRUE,
            mostrar_organizacion BOOLEAN NOT NULL DEFAULT TRUE,
            layout JSONB NOT NULL DEFAULT '{}'::jsonb,
            fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """,
}


# ============================================================
# CONFIGURACIÓN DE CREDENCIAL
# ============================================================

CONFIGURACION_CREDENCIAL = """

CREATE TABLE IF NOT EXISTS configuracion_credencial (

    id SERIAL PRIMARY KEY,

    nombre_institucion VARCHAR(200)
        NOT NULL
        DEFAULT 'SICAE WEB',

    subtitulo VARCHAR(300)
        DEFAULT 'Sistema de Registro BGM José María Chávez',

    logo VARCHAR(255),

    color_principal VARCHAR(20)
        DEFAULT '#1e3a8a',

    color_secundario VARCHAR(20)
        DEFAULT '#2563eb',

    color_texto VARCHAR(20)
        DEFAULT '#111827',

    fuente VARCHAR(100)
        DEFAULT 'Arial',

    tamano_nombre INTEGER
        DEFAULT 30,

    tamano_qr INTEGER
        DEFAULT 100,

    mostrar_foto BOOLEAN
        DEFAULT TRUE,

    mostrar_qr BOOLEAN
        DEFAULT TRUE,

    mostrar_matricula BOOLEAN
        DEFAULT TRUE,

    mostrar_grupo BOOLEAN
        DEFAULT TRUE,

    mostrar_grado BOOLEAN
        DEFAULT TRUE,

    mostrar_turno BOOLEAN
        DEFAULT TRUE,

    texto_pie VARCHAR(300)
        DEFAULT 'Documento de identificación escolar',

    layout JSONB NOT NULL DEFAULT '{}'::jsonb,

    fecha_actualizacion TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
);

"""

# ============================================================
# CONFIGURACIÓN DEL SISTEMA
# ============================================================

CONFIGURACION_SISTEMA = """

CREATE TABLE IF NOT EXISTS configuracion_sistema (

    id SERIAL PRIMARY KEY,

    nombre_sistema VARCHAR(200)
        NOT NULL
        DEFAULT 'SICAE WEB',

    subtitulo VARCHAR(300)
        DEFAULT 'Sistema de Registro BGM José María Chávez',

    titulo_excel VARCHAR(200)
        DEFAULT 'Reporte de Asistencias',

    subtitulo_excel VARCHAR(300)
        DEFAULT 'Sistema de Registro de Asistencias',

    texto_bienvenida TEXT
        DEFAULT 'Sistema de control y registro de asistencias.',

        logo_excel VARCHAR(255),

    color_principal VARCHAR(20)
        DEFAULT '#2563EB',

    color_secundario VARCHAR(20)
        DEFAULT '#1E40AF',

    color_fondo_login VARCHAR(20)
        DEFAULT '#F3F4F6',

    color_texto_login VARCHAR(20)
        DEFAULT '#111827',

    logo_login VARCHAR(255),

    logo_tamano INTEGER
        NOT NULL
        DEFAULT 120,

    fecha_actualizacion TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
);

"""

# ============================================================
# CONFIGURACIÓN DE CREDENCIAL DEL PERSONAL
# ============================================================

CONFIGURACION_CREDENCIAL_PERSONAL = """

CREATE TABLE IF NOT EXISTS configuracion_credencial_personal (

    id SERIAL PRIMARY KEY,

    nombre_institucion VARCHAR(200)
        NOT NULL
        DEFAULT 'SICAE WEB',

    subtitulo VARCHAR(300)
        DEFAULT 'Sistema de Registro BGM José María Chávez',

    logo VARCHAR(255),

    color_principal VARCHAR(20)
        DEFAULT '#1e3a8a',

    color_secundario VARCHAR(20)
        DEFAULT '#2563eb',

    color_texto VARCHAR(20)
        DEFAULT '#111827',

    fuente VARCHAR(100)
        DEFAULT 'Arial',

    tamano_nombre INTEGER
        DEFAULT 30,

    tamano_qr INTEGER
        DEFAULT 300,

    mostrar_foto BOOLEAN
        DEFAULT TRUE,

    mostrar_qr BOOLEAN
        DEFAULT TRUE,

    mostrar_matricula BOOLEAN
        DEFAULT TRUE,

    mostrar_tipo_personal BOOLEAN
        DEFAULT TRUE,

    mostrar_cargo BOOLEAN
        DEFAULT TRUE,

    mostrar_area BOOLEAN
        DEFAULT TRUE,

    mostrar_correo BOOLEAN
        DEFAULT TRUE,

    mostrar_telefono BOOLEAN
        DEFAULT TRUE,

    texto_pie VARCHAR(300)
        DEFAULT 'Documento de identificación del personal',

    layout JSONB NOT NULL DEFAULT '{}'::jsonb,

    fecha_actualizacion TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP

);

"""








# ============================================================
# CONFIGURACIÓN DE NOTIFICACIONES POR CORREO
# ============================================================

CONFIGURACION_NOTIFICACIONES = """

CREATE TABLE IF NOT EXISTS configuracion_notificaciones (

    id SERIAL PRIMARY KEY,

    correo_remitente VARCHAR(150),

    asunto VARCHAR(300)
        NOT NULL
        DEFAULT 'SICAE WEB - Notificación de asistencia',

    mensaje TEXT
        NOT NULL
        DEFAULT 'Estimado padre, madre o tutor:

Le informamos que se ha registrado un movimiento de asistencia en SICAE WEB.

Alumno: {nombre}
Movimiento: {movimiento}
Fecha: {fecha}
Hora: {hora}

Este mensaje fue generado automáticamente por el Sistema de Registro SICAE WEB.

Saludos.',

    notificaciones_activas BOOLEAN
        NOT NULL
        DEFAULT TRUE,

    enviar_entrada BOOLEAN
        NOT NULL
        DEFAULT TRUE,

    enviar_salida BOOLEAN
        NOT NULL
        DEFAULT TRUE,

    fecha_actualizacion TIMESTAMP
        NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);

"""
