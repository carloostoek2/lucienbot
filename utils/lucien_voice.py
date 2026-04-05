"""
🎩 Voz de Lucien - Guardián de los Secretos de Diana

Este módulo contiene todos los mensajes y respuestas del bot,
diseñados con la personalidad elegante y misteriosa de Lucien.
"""
from datetime import datetime, timedelta
from typing import Optional


class LucienVoice:
    """Clase para generar mensajes con la voz de Lucien"""

    # ==================== SALUDOS ====================

    @staticmethod
    def greeting(user_name: Optional[str] = None) -> str:
        """Saludo principal para usuarios"""
        name_part = f", {user_name}," if user_name else ""
        return f"""🎩 <b>Lucien:</b>

<i>Ah{name_part} ha llegado al vestíbulo de Diana.
Puedo ver que su curiosidad lo ha traído hasta aquí...
lo cual, debo admitir, no me sorprende en absoluto.</i>

¿En qué puedo asistirle hoy?"""

    @staticmethod
    def admin_greeting() -> str:
        """Saludo para administradores"""
        return f"""🎩 <b>Lucien:</b>

<i>Ah, el custodio de los dominios de Diana.
Bienvenido al sanctum donde se orquestan los secretos
y se tejen las experiencias de nuestros... visitantes.</i>

¿Qué aspecto del reino requiere su atención hoy?"""

    @staticmethod
    def vip_greeting(user_name: Optional[str] = None) -> str:
        """Saludo para usuarios VIP"""
        name_part = f", {user_name}," if user_name else ""
        return f"""🎩 <b>Lucien:</b>

<i>Ah{name_part}, bienvenido a El Diván.
Aquí, Diana puede mostrar facetas que... otros no conocen.
Su presencia ha sido... anticipada.</i>

Permíteme guiarle por los privilegios a su disposición."""

    # ==================== CANAL FREE ====================

    @staticmethod
    def returning_user_greeting() -> str:
        """Mensaje para usuarios que ya estaban en el canal antes del bot"""
        return """🎩 <b>Lucien:</b>

<i>Ah… un viejo conocido.
Pensé que tardaría más en verle por aquí.
Supongo que observar desde fuera deja de ser suficiente… eventualmente.</i>

Siéntase cómodo de explorar las opciones que tiene a su disposición.

<i>En nombre de Diana, Señorita Kinky, le doy la bienvenida.</i>"""

    @staticmethod
    def free_request_received(wait_minutes: int) -> str:
        """Mensaje cuando se recibe solicitud al canal free"""
        return f"""🎩 <b>Lucien:</b>

<i>Su solicitud ha sido registrada en los archivos de Diana.
Los vestíbulos requieren... cierta paciencia.</i>

⏳ <b>Tiempo de espera estimado:</b> {wait_minutes} minutos

<i>Le notificaré cuando las puertas se abran para usted.
Mientras tanto, Diana observa su interés con... curiosidad.</i>"""

    @staticmethod
    def free_access_approved(channel_name: Optional[str] = None) -> str:
        """Mensaje cuando se aprueba acceso al canal free"""
        channel_text = f" a <b>{channel_name}</b>" if channel_name else ""
        return f"""🎩 <b>Lucien:</b>

<i>Las puertas del vestíbulo se han abierto{channel_text}.
Diana lo recibe entre sus... observados.</i>

✅ <b>Su acceso ha sido concedido.</b>

👉 <i>Puede ingresar cuando lo desee.</i>"""

    @staticmethod
    def free_request_cancelled() -> str:
        """Mensaje cuando el usuario cancela su solicitud"""
        return f"""🎩 <b>Lucien:</b>

<i>Interesante... ha retirado su solicitud.
Diana comprende que no todos están listos para lo que
el vestíbulo tiene para ofrecer.</i>

Si cambia de parecer, las puertas siempre están... casi abiertas."""

    # ==================== RITUALES DE ENTRADA (PHASE 10) ====================

    @staticmethod
    def free_entry_ritual(channel_name: str) -> str:
        """Mensaje 1: Ritual de entrada al canal Free (tras 30s de espera)"""
        return f"""🎩 <b>Lucien:</b>

<i>Ah… alguien ha llamado a la puerta.</i>

Su solicitud para entrar a <b>{channel_name}</b> ha sido registrada en los archivos de Diana.

<i>Diana siempre nota cuando alguien decide cruzar hacia su mundo…</i>

⏳ <b>Su acceso está siendo preparado.</b>

<i>Mientras tanto, hay algo que puede hacer:</i>

💡 <b>Observe sus redes.</b>
No son simples perfiles.
<i>Obsérvela. Escuche el tono.
Empiece a entender el juego.</i>

<i>No necesita quedarse aquí esperando.
Cuando todo esté listo, yo mismo vendré a buscarle.</i>

👇 <i>Entre tanto… puede seguir su rastro.</i>"""

    @staticmethod
    def free_entry_impatient(channel_name: str) -> str:
        """Mensaje 2: Cuando el usuario solicita acceso nuevamente estando pending"""
        return f"""🎩 <b>Lucien:</b>

<i>Veo que el deseo de entrar no ha disminuido…</i>

Su acceso a <b>{channel_name}</b> ya está en movimiento.

<i>Puede cerrar este chat con tranquilidad.
Cuando llegue el momento, no tendrá que buscar la puerta.</i>

🚪 <b>La puerta se abrirá.</b>"""

    @staticmethod
    def free_entry_welcome(channel_name: str) -> str:
        """Mensaje 3: Bienvenida al ser aprobado en el canal Free"""
        return f"""🎩 <b>Lucien:</b>

✨ <b>Las puertas se han abierto.</b>

<i>Diana ha permitido su entrada a <b>{channel_name}</b>.</i>

<i>Este no es el lugar donde ella se entrega.
Es el lugar donde comienza a insinuarse…
y donde algunos descubren que ya no quieren quedarse solo aquí.</i>

⏰ <b> Tiene 24 horas para cruzar.</b>
<i>Entre con intención.</i>

👇 <b>Su enlace de acceso:</b>"""

    @staticmethod
    def vip_entry_expired() -> str:
        """Mensaje cuando expira la suscripción durante el ritual VIP"""
        return """🎩 <b>Lucien:</b>

<i>Su acceso ha expirado antes de completar el ritual.</i>

Diana cierra las puertas cuando el tiempo se agota. Si desea regresar, deberá obtener un nuevo enlace."""

    @staticmethod
    def vip_entry_stage_1() -> str:
        """Fase 1 del ritual de entrada VIP: Confirmación"""
        return """🎩 <b>Lucien:</b>

Veo que ha dado el paso que muchos contemplan… y pocos toman.

Su acceso al Diván de Diana está siendo preparado.

Este no es un espacio público.
No es un canal más.
Y definitivamente no es para quien solo siente curiosidad.

Antes de entregarle la entrada, hay algo que debe saber…"""

    @staticmethod
    def vip_entry_stage_2() -> str:
        """Fase 2 del ritual de entrada VIP: Alineación de expectativas"""
        return """🎩 <b>Lucien:</b>

El Diván no es un lugar donde se mira y se olvida.
Es un espacio íntimo, sin filtros, sin máscaras.

Aquí Diana se muestra sin la distancia de las redes,
y eso exige discreción, respeto y presencia real.

Si ha llegado hasta aquí solo para observar de paso…
este es el momento de detenerse.

Si entiende lo que significa entrar… entonces sí."""

    @staticmethod
    def vip_entry_stage_3() -> str:
        """Fase 3 del ritual de entrada VIP: Entrega del acceso"""
        return """🎩 <b>Lucien:</b>

Entonces no le haré esperar más.

Diana le abre la puerta al Diván.

Este acceso es personal.
No se comparte.
No se replica.
Y se cierra cuando el vínculo termina.

Tiene 24 horas para usar el enlace.

Entre con intención.
👇"""

    # ==================== CANAL VIP ====================

    @staticmethod
    def vip_activated(tariff_name: str, expiration_date: datetime) -> str:
        """Mensaje cuando se activa membresía VIP"""
        exp_date_str = expiration_date.strftime("%d/%m/%Y")
        return f"""🎩 <b>Lucien:</b>

<i>Bienvenido a El Diván de Diana.</i>

👑 <b>Tarifa activada:</b> {tariff_name}
📅 <b>Vencimiento:</b> {exp_date_str}

<i>Aquí, los secretos son más profundos y las experiencias...
más íntimas. Diana se complace de tenerle entre sus selectos.</i>

👉 <i>Su enlace de acceso ha sido preparado especialmente para usted.</i>"""

    @staticmethod
    def vip_renewal_reminder(expiration_date: datetime) -> str:
        """Recordatorio de renovación VIP (24h antes)"""
        exp_date_str = expiration_date.strftime("%d/%m/%Y")
        return f"""🎩 <b>Lucien:</b>

<i>Una observación delicada... su acceso a El Diván
culmina mañana, {exp_date_str}.</i>

Diana se pregunta si desea extender esta... relación privilegiada.

👉 <i>Contacte al custodio del reino para renovar su membresía.</i>"""

    @staticmethod
    def vip_expired() -> str:
        """Mensaje cuando expira la suscripción VIP"""
        return f"""🎩 <b>Lucien:</b>

<i>Su acceso exclusivo ha... pausado.
Pero los recuerdos de lo vivido permanecen, ¿verdad?</i>

Diana espera que haya encontrado valor en su tiempo
entre los privilegiados.

👉 <i>Si desea regresar al círculo, el custodio del reino
puede prepararle un nuevo enlace.</i>"""

    @staticmethod
    def vip_renewed() -> str:
        """Mensaje cuando se renueva VIP"""
        return f"""🎩 <b>Lucien:</b>

<i>Diana se complace por su regreso al círculo íntimo.
Lo esperaba.</i>

Su membresía ha sido extendida.
Que continúen los secretos compartidos..."""

    # ==================== TOKENS ====================

    @staticmethod
    def token_invalid() -> str:
        """Token inválido o inexistente"""
        return f"""🎩 <b>Lucien:</b>

<i>Hmm... el enlace que presenta no corresponde a ningún
acceso registrado en los archivos de Diana.</i>

⚠️ <b>Token inválido</b>

<i>Verifique que haya copiado correctamente el enlace,
o consulte con el custodio del reino.</i>"""

    @staticmethod
    def token_used() -> str:
        """Token ya utilizado"""
        return f"""🎩 <b>Lucien:</b>

<i>Ah... este enlace ya ha servido a su propósito.
Diana diseñó estos accesos para ser únicos, como
las experiencias que otorgan.</i>

⚠️ <b>Token ya utilizado</b>

<i>Si requiere un nuevo acceso, el custodio del reino
puede preparar uno especialmente para usted.</i>"""

    @staticmethod
    def token_expired() -> str:
        """Token expirado"""
        return f"""🎩 <b>Lucien:</b>

<i>El tiempo, como sabe, tiene sus propias reglas.
Este enlace ha trascendido su vigencia.</i>

⚠️ <b>Token expirado</b>

<i>Los accesos de Diana tienen caducidad por razones...
de discreción. Solicite uno nuevo al custodio.</i>"""

    @staticmethod
    def token_generated(token_url: str, tariff_name: str) -> str:
        """Token generado exitosamente"""
        return f"""🎩 <b>Lucien:</b>

<i>Un nuevo acceso ha sido forjado para El Diván.</i>

👑 <b>Tarifa:</b> {tariff_name}
🔗 <b>Enlace:</b> <code>{token_url}</code>

<i>Este enlace es único, como los secretos que revela.
Compártalo con quien Diana considere digno.</i>"""

    # ==================== PANEL ADMIN - CANALES ====================

    @staticmethod
    def admin_channel_registered(channel_name: str, channel_type: str) -> str:
        """Canal registrado exitosamente"""
        type_text = "vestíbulo" if channel_type == "free" else "El Diván"
        return f"""🎩 <b>Lucien:</b>

<i>El {type_text} <b>{channel_name}</b> ha sido registrado
en los dominios de Diana.</i>

✅ <b>Canal configurado correctamente.</b>

<i>Los visitantes podrán solicitar acceso según las reglas
que establezca para este espacio.</i>"""

    @staticmethod
    def admin_channel_list(channels: list) -> str:
        """Lista de canales registrados"""
        if not channels:
            return f"""🎩 <b>Lucien:</b>

<i>No hay dominios registrados en los archivos de Diana.
El reino aún no tiene vestíbulos ni círculos exclusivos...</i>

👉 <i>Use "Agregar canal" para expandir los territorios.</i>"""

        text = f"""🎩 <b>Lucien:</b>

<i>Los dominios bajo nuestra observación son los siguientes:</i>

"""
        for ch in channels:
            type_emoji = "🚪" if ch.channel_type == ChannelType.FREE else "👑"
            type_text = "Vestíbulo" if ch.channel_type == ChannelType.FREE else "Círculo VIP"
            text += f"{type_emoji} <b>{ch.channel_name or 'Sin nombre'}</b>\n"
            text += f"   └ {type_text} | ID: <code>{ch.channel_id}</code>\n\n"

        return text

    @staticmethod
    def admin_channel_deleted(channel_name: str) -> str:
        """Canal eliminado"""
        return f"""🎩 <b>Lucien:</b>

<i>El dominio <b>{channel_name}</b> ha sido removido
de los archivos de Diana.</i>

✅ <b>Canal eliminado correctamente.</b>

<i>Las puertas a ese espacio ya no están bajo nuestra gestión.</i>"""

    # ==================== PANEL ADMIN - TARIFAS ====================

    @staticmethod
    def admin_tariff_created(name: str, days: int, price: str) -> str:
        """Tarifa creada exitosamente"""
        return f"""🎩 <b>Lucien:</b>

<i>Una nueva tarifa ha sido calibrada para El Diván.</i>

📋 <b>Nombre:</b> {name}
⏱ <b>Duración:</b> {days} días
💰 <b>Precio:</b> {price}

✅ <b>Tarifa creada correctamente.</b>

<i>Ahora puede generar tokens vinculados a esta tarifa.</i>"""

    @staticmethod
    def admin_tariff_list(tariffs: list) -> str:
        """Lista de tarifas"""
        if not tariffs:
            return f"""🎩 <b>Lucien:</b>

<i>No hay tarifas configuradas para El Diván.
Diana aún no ha establecido los términos de acceso privilegiado...</i>

👉 <i>Use "Crear tarifa" para establecer las opciones VIP.</i>"""

        text = f"""🎩 <b>Lucien:</b>

<i>Las tarifas de El Diván son las siguientes:</i>

"""
        for t in tariffs:
            status = "✅" if t.is_active else "❌"
            text += f"{status} <b>{t.name}</b>\n"
            text += f"   └ {t.duration_days} días | {t.price} {t.currency}\n\n"

        return text

    # ==================== PANEL ADMIN - SOLICITUDES ====================

    @staticmethod
    def admin_pending_requests(count: int, requests: list) -> str:
        """Lista de solicitudes pendientes"""
        if count == 0:
            return f"""🎩 <b>Lucien:</b>

<i>No hay almas en espera en los vestíbulos de Diana.
Todos los visitantes han sido atendidos...</i>

El reino descansa tranquilo por ahora."""

        text = f"""🎩 <b>Lucien:</b>

<i>Hay <b>{count}</b> visitantes aguardando en los vestíbulos...</i>

"""
        for req in requests:
            username = f"@{req.username}" if req.username else req.first_name or "Anónimo"
            wait_time = req.scheduled_approval_at.strftime("%H:%M")
            text += f"👤 <b>{username}</b>\n"
            text += f"   └ Aprobación: {wait_time}\n\n"

        return text

    @staticmethod
    def admin_requests_cleared(count: int) -> str:
        """Solicitudes aprobadas en lote"""
        return f"""🎩 <b>Lucien:</b>

<i>He abierto las puertas para <b>{count}</b> visitantes
que aguardaban en los vestíbulos.</i>

✅ <b>Solicitudes aprobadas en lote.</b>

<i>Diana aprecia la eficiencia del custodio del reino.</i>"""

    # ==================== PANEL ADMIN - CONFIGURACIÓN ====================

    @staticmethod
    def admin_wait_time_updated(minutes: int) -> str:
        """Tiempo de espera actualizado"""
        return f"""🎩 <b>Lucien:</b>

<i>La paciencia requerida en los vestíbulos ha sido ajustada.</i>

⏱ <b>Nuevo tiempo de espera:</b> {minutes} minutos

✅ <b>Configuración actualizada.</b>

<i>Los nuevos visitantes experimentarán esta espera
antes de acceder a los dominios de Diana.</i>"""

    # ==================== ANALYTICS ====================

    @staticmethod
    def analytics_dashboard(stats: dict) -> str:
        """Dashboard de metricas para Custodios."""
        return f"""🎩 <b>Estadisticas del Reino</b>

<i>Estos son los secretos que Diana guarda...</i>

👥 <b>Visitantes totales:</b> {stats.get('total_users', 0)}
💎 <b>VIP activos:</b> {stats.get('active_vip', 0)}
💋 <b>Besitos en circulacion:</b> {stats.get('total_besitos', 0)}
⏰ <b>VIP por expirar (48h):</b> {stats.get('expiring_soon', 0)}
🆕 <b>Nuevos hoy:</b> {stats.get('new_today', 0)}

<i>El reino de Diana observa con atencion...</i>"""

    @staticmethod
    def export_ready(filename: str) -> str:
        """Confirmacion de exportacion."""
        return f"""🎩 <b>Lucien:</b>

<i>Los archivos del reino han sido compilados.</i>

📎 <b>Archivo:</b> <code>{filename}</code>

<i>Diana ha preparado este documento para usted.</i>"""

    @staticmethod
    def export_no_data() -> str:
        """No hay datos para exportar."""
        return f"""🎩 <b>Lucien:</b>

<i>No hay registros en el reino que exportar...</i>

<i>Aun no hay visitantes registrados.</i>"""

    @staticmethod
    def analytics_access_denied() -> str:
        """Acceso denegado a estadisticas."""
        return f"""🎩 <b>Lucien:</b>

<i>Estos numeros son solo para los custodios del reino.</i>

⚠️ <b>Acceso denegado</b>

<i>Solicite acceso a Diana si cree que esto es un error.</i>"""

    # ==================== ERRORES ====================

    @staticmethod
    def error_message(context: str = "") -> str:
        """Mensaje de error general"""
        context_part = f" con {context}" if context else ""
        return f"""🎩 <b>Lucien:</b>

<i>Hmm... algo inesperado ha ocurrido{context_part}.
Permítame consultar con Diana sobre este inconveniente.</i>

<i>Mientras tanto, ¿hay algo más en lo que pueda asistirle?</i>"""

    @staticmethod
    def permission_error() -> str:
        """Error de permisos"""
        return f"""🎩 <b>Lucien:</b>

<i>Parece que no tengo los privilegios necesarios para
realizar esta acción en el dominio seleccionado.</i>

⚠️ <b>Error de permisos</b>

<i>Asegúrese de que mi rol en el canal incluya:
• Gestionar chat
• Añadir miembros
• Aprobar solicitudes</i>

👉 <i>Verifique la configuración del canal y mis permisos.</i>"""

    @staticmethod
    def not_admin_error() -> str:
        """Usuario no es administrador"""
        return f"""🎩 <b>Lucien:</b>

<i>Interesante... parece que busca acceder al sanctum
de administración.</i>

⚠️ <b>Acceso denegado</b>

<i>Solo los custodios designados por Diana pueden
manejar los hilos del reino.</i>

👉 <i>Su solicitud ha sido... registrada.</i>"""

    # ==================== DESPEDIDAS ====================

    @staticmethod
    def farewell() -> str:
        """Despedida"""
        return f"""🎩 <b>Lucien:</b>

<i>Hasta que nuestros caminos se crucen nuevamente...
Diana estará... atenta a sus próximos movimientos.</i>

Que la curiosidad lo guíe de vuelta pronto."""

    @staticmethod
    def coming_soon() -> str:
        """Función en desarrollo"""
        return f"""🎩 <b>Lucien:</b>

<i>Ah... algo que Diana aún está preparando con
meticulosa atención.</i>

🎭 <b>Próximamente disponible</b>

<i>Los secretos más profundos requieren tiempo para
ser revelados correctamente.</i>"""

    # ==================== SERVICIOS - TIENDA ====================

    @staticmethod
    def store_product_not_found() -> str:
        return "Producto no encontrado"

    @staticmethod
    def store_product_unavailable(product_name: str = None) -> str:
        if product_name:
            return f"Producto no disponible: {product_name}"
        return "Producto no disponible"

    @staticmethod
    def store_cart_updated(quantity: int, product_name: str) -> str:
        return f"Cantidad actualizada: {quantity} x {product_name}"

    @staticmethod
    def store_cart_added(product_name: str) -> str:
        return f"Agregado al carrito: {product_name}"

    @staticmethod
    def store_cart_empty() -> str:
        return "El carrito esta vacio"

    @staticmethod
    def store_stock_insufficient(product_name: str, available: int) -> str:
        return f"Stock insuficiente para: {product_name} (disponible: {available})"

    @staticmethod
    def store_balance_insufficient(needed: int, have: int) -> str:
        return f"Saldo insuficiente. Necesitas: {needed} besitos. Tienes: {have}"

    @staticmethod
    def store_order_not_found() -> str:
        return "Orden no encontrada"

    @staticmethod
    def store_order_already_processed() -> str:
        return "La orden ya fue procesada"

    @staticmethod
    def store_payment_failed() -> str:
        return "Error al procesar el pago"

    @staticmethod
    def store_purchase_completed(total_price: int) -> str:
        return f"Compra completada! Se debitaron {total_price} besitos."

    # ==================== SERVICIOS - PAQUETES ====================

    @staticmethod
    def package_not_found() -> str:
        return "Paquete no encontrado"

    @staticmethod
    def package_empty_files() -> str:
        return "El paquete no contiene archivos"

    @staticmethod
    def package_delivery_success(package_name: str) -> str:
        return f"Paquete '{package_name}' entregado exitosamente"

    @staticmethod
    def package_delivery_failed() -> str:
        return "Error al entregar el paquete"

    @staticmethod
    def package_delivery_intro(package_name: str, description: str = None) -> str:
        desc = description or "Un obsequio del reino..."
        return f"""🎩 <b>Lucien:</b>

<i>Diana ha preparado algo especial para usted...</i>

📦 <b>{package_name}</b>

<i>{desc}</i>

Enviando archivo(s)..."""

    # ==================== SERVICIOS - RECOMPENSAS ====================

    @staticmethod
    def reward_not_found() -> str:
        return "Recompensa no encontrada"

    @staticmethod
    def reward_inactive() -> str:
        return "Recompensa inactiva"

    @staticmethod
    def reward_type_unsupported() -> str:
        return "Tipo de recompensa no soportado"

    @staticmethod
    def reward_delivery_error(error: str = None) -> str:
        if error:
            return f"Error al entregar recompensa: {error}"
        return "Error al entregar recompensa"

    @staticmethod
    def reward_besitos_received(amount: int, balance: int) -> str:
        return f"Has recibido {amount} besitos! Tu saldo es: {balance}"

    @staticmethod
    def reward_besitos_failed() -> str:
        return "Error al acreditar besitos"

    @staticmethod
    def reward_package_not_configured() -> str:
        return "Paquete no configurado"

    @staticmethod
    def reward_package_not_found() -> str:
        return "Paquete no encontrado"

    @staticmethod
    def reward_package_unavailable() -> str:
        return "Paquete no disponible para recompensas"

    @staticmethod
    def reward_stock_depleted() -> str:
        return "Stock de recompensas agotado"

    @staticmethod
    def reward_vip_not_configured() -> str:
        return "Tarifa VIP no configurada"

    @staticmethod
    def reward_tariff_not_found() -> str:
        return "Tarifa no encontrada"

    @staticmethod
    def reward_vip_received(tariff_name: str, days: int) -> str:
        return f"Has recibido acceso VIP: {tariff_name} ({days} dias)"

    @staticmethod
    def reward_vip_message(tariff_name: str, duration_days: int, token_url: str) -> str:
        return f"""🎩 Lucien:

Diana te ha concedido acceso a El Diván...

👑 Recompensa VIP Activada

📋 Tarifa: {tariff_name}
⏱ Duracion: {duration_days} dias

🔗 Tu enlace de acceso:
{token_url}

Haz clic para activar tu membresia VIP."""

    # ==================== SERVICIOS - PROMOCIONES ====================

    @staticmethod
    def promotion_blocked(reason: str) -> str:
        return f"No puedes expresar interes. Razon: {reason}"

    @staticmethod
    def promotion_not_found() -> str:
        return "Promocion no encontrada"

    @staticmethod
    def promotion_unavailable() -> str:
        return "Esta promocion no esta disponible actualmente"

    @staticmethod
    def promotion_already_interested() -> str:
        return "Ya has expresado interes en esta promocion"

    @staticmethod
    def promotion_interest_registered() -> str:
        return "Interes registrado correctamente"

    # ==================== SERVICIOS - NARRATIVA ====================

    @staticmethod
    def story_fragment_unavailable() -> str:
        return "Este fragmento no esta disponible"

    @staticmethod
    def story_fragment_vip_required() -> str:
        return "Este fragmento requiere acceso a El Diván"

    @staticmethod
    def story_fragment_archetype_required(archetype_name: str) -> str:
        return f"Este fragmento solo esta disponible para quienes han despertado el arquetipo del {archetype_name}"

    @staticmethod
    def story_fragment_cost_needed(cost: int) -> str:
        return f"Necesita {cost} besitos para acceder a este fragmento"

    @staticmethod
    def story_payment_failed() -> str:
        return "No se pudo procesar el pago"


# Import para evitar dependencia circular
from models.models import ChannelType
