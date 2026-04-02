# Reporte de Análisis de Seguridad y Lógica de Negocio - Lucien Bot

Este documento presenta los hallazgos obtenidos durante el análisis estático y dinámico del código fuente del repositorio `lucienbot`. El análisis se centró en identificar vulnerabilidades de seguridad, problemas de concurrencia y fallos en la lógica de negocio, siguiendo la metodología solicitada.

## Resumen Ejecutivo

El análisis reveló que `lucienbot` posee una arquitectura modular bien estructurada utilizando `aiogram 3` y `SQLAlchemy`. Se han implementado buenas prácticas generales, como el uso de `SELECT FOR UPDATE` en operaciones críticas de gamificación (`BesitoService`). Sin embargo, se identificaron varios hallazgos de severidad alta y media relacionados con el manejo de concurrencia en la narrativa, el control de límites de la API de Telegram y la exposición de credenciales durante los respaldos de la base de datos.

A continuación, se detallan los hallazgos clasificados por severidad.

---

### Hallazgo #1: Rate Limiter Global Compartido (Denegación de Servicio)
- **Severidad**: Alta
- **Archivo/línea**: `handlers/rate_limit_middleware.py:L19`
- **Descripción**: El middleware `ThrottlingMiddleware` utiliza una única instancia de `AsyncLimiter` para todos los usuarios. La configuración actual permite 5 solicitudes cada 10 segundos. Al ser un limitador global, si varios usuarios legítimos interactúan simultáneamente con el bot, agotarán el límite y los demás usuarios serán bloqueados temporalmente. Un atacante puede explotar esto enviando ráfagas de mensajes para causar una Denegación de Servicio (DoS) a toda la base de usuarios.
- **Pasos para reproducir**:
  1. Configurar dos usuarios distintos interactuando con el bot.
  2. El Usuario A envía 5 comandos seguidos rápidamente.
  3. Inmediatamente, el Usuario B envía 1 comando.
  4. El Usuario B recibe el mensaje de advertencia "Espera un momento... no tan rápido" a pesar de no haber excedido su propio límite.
- **Impacto**: Interrupción masiva del servicio para usuarios legítimos, afectando la experiencia de gamificación y narrativa.
- **Recomendación**: Implementar un diccionario o caché (como Redis o un `TTLCache` en memoria) que almacene una instancia de `AsyncLimiter` independiente por cada `user_id`.

### Hallazgo #2: Falta de Atomicidad en Transacciones de Narrativa
- **Severidad**: Alta
- **Archivo/línea**: `services/story_service.py:L221-274` (Función `advance_to_node`)
- **Descripción**: La función que avanza al usuario a un nuevo nodo de la historia realiza múltiples operaciones en la base de datos, incluyendo el débito de besitos a través de `BesitoService`. El problema radica en que `debit_besitos` realiza un `db.commit()` internamente. Si el proceso falla posteriormente (por ejemplo, al actualizar el progreso o asignar arquetipos), los besitos ya habrán sido descontados del saldo del usuario, pero este no avanzará en la historia, resultando en pérdida de moneda virtual sin contraprestación.
- **Pasos para reproducir**:
  1. Un usuario intenta acceder a un nodo que cuesta 50 besitos.
  2. La función `debit_besitos` descuenta los 50 besitos y hace commit.
  3. Se simula o ocurre una excepción (ej. desconexión de DB) antes del commit final en `advance_to_node`.
  4. El saldo del usuario disminuye, pero su `current_node_id` no se actualiza.
- **Impacto**: Pérdida de datos financieros virtuales (besitos) e inconsistencia en el estado de la narrativa, generando frustración en los usuarios.
- **Recomendación**: Refactorizar el manejo de transacciones. Los servicios no deben hacer `commit()` si forman parte de una operación más grande. Se recomienda usar un patrón Unit of Work o pasar un flag `commit=False` a las funciones auxiliares, realizando un único `db.commit()` al final de `advance_to_node`.

### Hallazgo #3: Exposición de Credenciales en Respaldos de PostgreSQL
- **Severidad**: Media
- **Archivo/línea**: `services/backup_service.py:L47`
- **Descripción**: El servicio de backup automático extrae la variable `DATABASE_URL` (que contiene el usuario y la contraseña en texto plano) y la pasa directamente como argumento de línea de comandos a la utilidad `pg_dump` mediante `subprocess.run()`.
- **Pasos para reproducir**:
  1. Configurar el bot para usar PostgreSQL.
  2. Esperar a que se ejecute el job programado `_run_backup_job`.
  3. Durante la ejecución, cualquier usuario con acceso al sistema operativo puede ejecutar `ps aux | grep pg_dump` y ver la contraseña de la base de datos en los argumentos del proceso.
- **Impacto**: Fuga de información sensible. Si un atacante obtiene acceso de lectura de procesos en el servidor (ej. vulnerabilidad de contenedor en Railway), puede comprometer la base de datos de producción.
- **Recomendación**: No pasar la URL completa por CLI. Extraer la contraseña de la URL y pasarla a `subprocess.run` a través del diccionario `env` usando la variable de entorno estándar `PGPASSWORD`.

### Hallazgo #4: Race Condition Menor en Ritual de Entrada VIP
- **Severidad**: Media
- **Archivo/línea**: `handlers/vip_handlers.py:L389` (Función `vip_entry_ready`)
- **Descripción**: Durante la fase 3 del ritual de entrada VIP, el bot genera un enlace de invitación único usando `create_chat_invite_link` y luego marca la entrada como completada. Si un usuario hace doble clic muy rápido en el botón "Estoy listo", ambas solicitudes pueden pasar la validación inicial antes de que se actualice el estado en la base de datos.
- **Pasos para reproducir**:
  1. Un usuario en estado `pending_entry` (etapa 2) envía dos peticiones simultáneas del callback `vip_entry_ready`.
  2. Ambas peticiones pasan el chequeo `status == "pending_entry"`.
  3. El bot genera y envía dos enlaces de invitación distintos a través de la API de Telegram.
  4. Ambas peticiones hacen commit del estado final.
- **Impacto**: Generación de enlaces de invitación redundantes. Aunque el daño es limitado porque el usuario ya es VIP, ensucia la lista de enlaces activos del canal.
- **Recomendación**: Implementar un bloqueo optimista o usar `SELECT FOR UPDATE` al obtener el usuario en `get_vip_entry_state` para asegurar que solo una petición procese la generación del enlace.

### Hallazgo #5: Desbordamiento de Enteros en PostgreSQL (Besitos)
- **Severidad**: Baja
- **Archivo/línea**: `models/models.py:L182`
- **Descripción**: El saldo de besitos (`balance`, `total_earned`, `total_spent`) está definido como `Column(Integer)`. En PostgreSQL, esto se traduce a un entero de 32 bits con signo, cuyo valor máximo es 2,147,483,647. Si un usuario acumula más de esta cantidad (por ejemplo, mediante regalos de administradores o recompensas acumuladas a largo plazo), la base de datos arrojará un error de desbordamiento, bloqueando las transacciones del usuario.
- **Pasos para reproducir**:
  1. Usar el panel de administración para acreditar 2,147,483,600 besitos a un usuario.
  2. El usuario reclama un regalo diario de 100 besitos.
  3. La operación falla con un error de `integer out of range` en PostgreSQL.
- **Impacto**: Imposibilidad de actualizar el saldo para usuarios con cantidades extremas de moneda virtual.
- **Recomendación**: Cambiar el tipo de columna de `Integer` a `BigInteger` para los campos financieros en el modelo `BesitoBalance` y `BesitoTransaction`.

---
