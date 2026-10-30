-- Ejecuta esta instrucción en una sesión del servidor MariaDB.
-- Las tablas, triggers y vistas se crean después con `python manage.py migrate`.
CREATE DATABASE IF NOT EXISTS `educheck`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
