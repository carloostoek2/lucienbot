"""
🎩 Voz de Lucien - Guardián de los Secretos de Diana

Este módulo contiene todos los mensajes y respuestas del bot,
diseñados con la personalidad elegante y misteriosa de Lucien.
"""

from datetime import datetime


class LucienVoice:
    """Clase para generar mensajes con la voz de Lucien"""

    # ==================== SALUDOS ====================

    @staticmethod
    def greeting(user_name: str | None = None) -> str:
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
        return """🎩 <b>Lucien:</b>

<i>Ah, el custodio de los dominios de Diana.
Bienvenido al sanctum donde se orquestan los secretos
y se tejen las experiencias de nuestros... visitantes.</i>

¿Qué aspecto del reino requiere su atención hoy?"""

    @staticmethod
    def vip_greeting(user_name: str | None = None) -> str:
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
    def vip_member_free_link_greeting() -> str:
        """Mensaje para usuarios VIP que entran por el link free"""
        return """🎩 <b>Lucien:</b>

<i>Oh, uno de los elegidos.</i>

Usted, por favor, diríjase con Diana porque ella le activará características especiales solo para VIP.

@DianaKinky"""

    @staticmethod
    def vip_and_free_greeting() -> str:
        """Mensaje para usuarios que son VIP y también suscriptores del canal free"""
        return """🎩 <b>Lucien:</b>

<i>Oh, uno de los elegidos.</i>

Usted, por favor, diríjase con Diana porque ella le activará características especiales solo para VIP.

@DianaKinky"""

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
    def free_access_approved(channel_name: str | None = None) -> str:
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
        return """🎩 <b>Lucien:</b>

<i>Interesante... ha retirado su solicitud.
Diana comprende que no todos están listos para lo que
el vestíbulo tiene para ofrecer.</i>

Si cambia de parecer, las puertas siempre están... casi abiertas."""

    @staticmethod
    def free_entry_impatient(channel_name: str) -> str:
        """Mensaje cuando un usuario ya tiene solicitud pendiente e intenta apresurarse"""
        return f"""🎩 <b>Lucien:</b>

<i>Ah, la impaciencia... una cualidad que Diana encuentra
particularmente... reveladora.</i>

Su solicitud para <b>{channel_name}</b> ya está registrada.
Las puertas se abren a su debido tiempo.

<i>La anticipación es parte del ritual, ¿no lo cree?
Diana observa con interés su... entusiasmo.</i>"""

    @staticmethod
    def free_entry_ritual(channel_name: str) -> str:
        """Mensaje ritual enviado tras el periodo de espera del canal free"""
        return f"""🎩 <b>Lucien:</b>

<i>El tiempo ha transcurrido y Diana ha observado su paciencia
con... aprobación. Los velos del vestíbulo se descorren.</i>

Las puertas de <b>{channel_name}</b> están ante usted.

<i>Entre con intención. Diana espera al otro lado.</i>"""

    @staticmethod
    def free_entry_welcome(channel_name: str) -> str:
        """Mensaje de bienvenida cuando se aprueba el acceso al canal free"""
        return f"""🎩 <b>Lucien:</b>

<i>Diana ha decidido abrirle las puertas de <b>{channel_name}</b>.
Su curiosidad no ha pasado... desapercibida.</i>

Bienvenido al vestíbulo. Explore, observe, y recuerde:
todo lo que aquí sucede es un reflejo de los deseos de Diana."""

    # ==================== VIP ACCESS (SIMPLIFIED) ====================

    @staticmethod
    def vip_no_subscription() -> str:
        """Mensaje para usuarios sin VIP - contact Diana"""
        return """🎩 <b>Lucien:</b>

<i>El círculo íntimo no está disponible para usted... aún.</i>

Diana abre las puertas solo a quienes ella considera dignos.
Si desea explorar este camino, contacte a Diana directamente.

<i>@DianaKinky</i>

<i>Diana observa con interés su curiosidad...</i>"""

    @staticmethod
    def vip_direct_access(invite_link: str = None) -> str:
        """Mensaje con enlace directo al canal VIP"""
        link_text = f"\n🔗 <b>Su acceso:</b> {invite_link}" if invite_link else ""
        return f"""🎩 <b>Lucien:</b>

<i>Bienvenido al círculo íntimo de Diana.</i>

Su membresía VIP está activa. El Diván lo espera.
{link_text}

<i>Entre con intención.</i>"""

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
        return """🎩 <b>Lucien:</b>

<i>Su acceso exclusivo ha... pausado.
Pero los recuerdos de lo vivido permanecen, ¿verdad?</i>

Diana espera que haya encontrado valor en su tiempo
entre los privilegiados.

👉 <i>Si desea regresar al círculo, el custodio del reino
puede prepararle un nuevo enlace.</i>"""

    @staticmethod
    def vip_renewed() -> str:
        """Mensaje cuando se renueva VIP"""
        return """🎩 <b>Lucien:</b>

<i>Diana se complace por su regreso al círculo íntimo.
Lo esperaba.</i>

Su membresía ha sido extendida.
Que continúen los secretos compartidos..."""

    # ==================== TOKENS ====================

    @staticmethod
    def token_invalid() -> str:
        """Token inválido o inexistente"""
        return """🎩 <b>Lucien:</b>

<i>Hmm... el enlace que presenta no corresponde a ningún
acceso registrado en los archivos de Diana.</i>

⚠️ <b>Token inválido</b>

<i>Verifique que haya copiado correctamente el enlace,
o consulte con el custodio del reino.</i>"""

    @staticmethod
    def token_used() -> str:
        """Token ya utilizado"""
        return """🎩 <b>Lucien:</b>

<i>Ah... este enlace ya ha servido a su propósito.
Diana diseñó estos accesos para ser únicos, como
las experiencias que otorgan.</i>

⚠️ <b>Token ya utilizado</b>

<i>Si requiere un nuevo acceso, el custodio del reino
puede preparar uno especialmente para usted.</i>"""

    @staticmethod
    def token_expired() -> str:
        """Token expirado"""
        return """🎩 <b>Lucien:</b>

<i>El tiempo, como sabe, tiene sus propias reglas.
Este enlace ha trascendido su vigencia.</i>

⚠️ <b>Token expirado</b>

<i>Los accesos de Diana tienen caducidad por razones...
de discreción. Solicite uno nuevo al custodio.</i>"""

    @staticmethod
    def token_generated(token_url: str, tariff_name: str, is_gift: bool = False) -> str:
        """Token generado exitosamente"""
        gift_line = (
            "\n🎁 <b>Regalo:</b> Sí — este token fue marcado como obsequio\n" if is_gift else ""
        )
        return f"""🎩 <b>Lucien:</b>

<i>Un nuevo acceso ha sido forjado para El Diván.</i>

👑 <b>Tarifa:</b> {tariff_name}
🔗 <b>Enlace:</b> <code>{token_url}</code>{gift_line}
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
            return """🎩 <b>Lucien:</b>

<i>No hay dominios registrados en los archivos de Diana.
El reino aún no tiene vestíbulos ni círculos exclusivos...</i>

👉 <i>Use "Agregar canal" para expandir los territorios.</i>"""

        text = """🎩 <b>Lucien:</b>

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
            return """🎩 <b>Lucien:</b>

<i>No hay tarifas configuradas para El Diván.
Diana aún no ha establecido los términos de acceso privilegiado...</i>

👉 <i>Use "Crear tarifa" para establecer las opciones VIP.</i>"""

        text = """🎩 <b>Lucien:</b>

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
            return """🎩 <b>Lucien:</b>

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

👥 <b>Visitantes totales:</b> {stats.get("total_users", 0)}
💎 <b>VIP activos:</b> {stats.get("active_vip", 0)}
💋 <b>Besitos en circulacion:</b> {stats.get("total_besitos", 0)}
⏰ <b>VIP por expirar (48h):</b> {stats.get("expiring_soon", 0)}
🆕 <b>Nuevos hoy:</b> {stats.get("new_today", 0)}

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
        return """🎩 <b>Lucien:</b>

<i>No hay registros en el reino que exportar...</i>

<i>Aun no hay visitantes registrados.</i>"""

    @staticmethod
    def analytics_access_denied() -> str:
        """Acceso denegado a estadisticas."""
        return """🎩 <b>Lucien:</b>

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
        return """🎩 <b>Lucien:</b>

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
        return """🎩 <b>Lucien:</b>

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
        return """🎩 <b>Lucien:</b>

<i>Hasta que nuestros caminos se crucen nuevamente...
Diana estará... atenta a sus próximos movimientos.</i>

Que la curiosidad lo guíe de vuelta pronto."""

    @staticmethod
    def coming_soon() -> str:
        """Función en desarrollo"""
        return """🎩 <b>Lucien:</b>

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

    # ==================== MOCHILA / BACKPACK ====================

    @staticmethod
    def backpack_summary(summary: dict) -> str:
        """Mensaje principal del menú de mochila"""
        return f"""🎩 <b>Lucien:</b>

<i>Permítame mostrarle los tesoros que Diana ha acumulado
en su mochila a lo largo de su viaje...</i>

📦 <b>Su Inventario</b>

<i>Seleccione una categoría para explorar:</i>

🎁 <b>Mis Recompensas:</b> {summary["rewards_count"]}
🛒 <b>Mis Compras:</b> {summary["purchases_count"]}
👑 <b>Membresías VIP:</b> {summary["vip_count"]}
💋 <b>Besitos:</b> {summary["besitos_balance"]}"""

    @staticmethod
    def backpack_rewards_list(rewards: list) -> str:
        """Mensaje para lista de recompensas"""
        if not rewards:
            return """🎩 <b>Lucien:</b>

<i>Aún no hay tesoros en su colección...
pero el camino apenas comienza.</i>

🏆 <b>No hay recompensas</b>

<i>Complete misiones para ganar tesoros del reino.</i>"""

        text = """🎩 <b>Lucien:</b>

<i>Las recompensas que ha conquistado en su camino...</i>

📋 <b>Recompensas Obtenidas</b>

"""
        for r in rewards:
            reward_type_emoji = {"BESITOS": "💋", "PACKAGE": "📦", "VIP_ACCESS": "👑"}.get(
                r["reward_type"], "🎁"
            )

            date_str = r["delivered_at"].strftime("%d/%m") if r.get("delivered_at") else "??/??"
            name = r["reward_name"][:30] + "..." if len(r["reward_name"]) > 30 else r["reward_name"]

            text += f"{reward_type_emoji} <b>{name}</b>\n"
            text += f"   📅 {date_str}"
            if r.get("besito_amount") and r["besito_amount"] > 0:
                text += f" | +{r['besito_amount']} 💋"
            text += "\n\n"

        return text

    @staticmethod
    def backpack_reward_detail(reward: dict) -> str:
        """Mensaje para detalle de recompensa"""
        reward_type = reward.get("reward_type", "BESITOS")

        if reward_type == "BESITOS":
            return f"""🎩 <b>Lucien:</b>

<i>Diana ha errado en su dirección besitos...</i>

💋 <b>Recompensa de Besitos</b>

🏷️ Nombre: {reward.get("reward_name", "Recompensa")}
📅 Obtenida: {reward.get("delivered_at", "N/A").strftime("%d/%m/%Y") if reward.get("delivered_at") else "N/A"}
💰 Besitos: +{reward.get("besito_amount", 0)}

<i>Los besitos han sido acreditados a su cuenta.</i>"""

        elif reward_type == "PACKAGE":
            has_files = reward.get("package_id") is not None
            btn_text = "📂 Ver Contenido" if has_files else ""
            return f"""🎩 <b>Lucien:</b>

<i>El paquete espera ser descubierto...</i>

📦 <b>Recompensa de Paquete</b>

🏷️ Nombre: {reward.get("reward_name", "Paquete")}
📅 Obtenida: {reward.get("delivered_at", "N/A").strftime("%d/%m/%Y") if reward.get("delivered_at") else "N/A"}
💋 Besitos incluidos: {reward.get("besito_amount", 0)}

<i>¿Desea ver el contenido?</i>"""

        else:  # VIP_ACCESS
            return f"""🎩 <b>Lucien:</b>

<i>Diana le ha abierto las puertas del círculo exclusivo...</i>

👑 <b>Recompensa VIP</b>

🏷️ Nombre: {reward.get("reward_name", "Acceso VIP")}
📅 Obtenida: {reward.get("delivered_at", "N/A").strftime("%d/%m/%Y") if reward.get("delivered_at") else "N/A"}
⏱️ Tarifa: {reward.get("tariff_name", "VIP")}
📅 Vence: {reward.get("end_date", "N/A").strftime("%d/%m/%Y") if reward.get("end_date") else "N/A"}

<i>El círculo exclusivo lo espera.</i>"""

    @staticmethod
    def backpack_purchases_list(purchases: list) -> str:
        """Mensaje para lista de compras"""
        if not purchases:
            return """🎩 <b>Lucien:</b>

<i>No hay tesoros adquiridos en su inventario...
la tienda de Diana le espera.</i>

🛒 <b>No hay compras</b>

<i>Explore la tienda para obtener tesoros exclusivos.</i>"""

        text = """🎩 <b>Lucien:</b>

<i>Los tesoros que ha adquirido en la tienda de Diana...</i>

🛒 <b>Compras Realizadas</b>

"""
        for p in purchases:
            date_str = p["purchased_at"].strftime("%d/%m/%Y") if p.get("purchased_at") else "??/??"
            price = p.get("total_price", 0)
            name = (
                p["product_name"][:25] + "..." if len(p["product_name"]) > 25 else p["product_name"]
            )

            text += f"📦 <b>{name}</b>\n"
            text += f"   💰 {price} 💋 | 📅 {date_str}\n\n"

        return text

    @staticmethod
    def backpack_vip_list(subscriptions: list) -> str:
        """Mensaje para lista de membresías VIP"""
        if not subscriptions:
            return """🎩 <b>Lucien:</b>

<i>El círculo exclusivo aún no lo ha recibido...
pero las puertas siempre están abiertas para quienes buscan.</i>

👑 <b>No hay membresías VIP</b>

<i>Contacte a Diana para obtener acceso a El Diván.</i>"""

        text = """🎩 <b>Lucien:</b>

<i>Los privilegios que Diana le ha conferido...</i>

👑 <b>Membresías VIP Activas</b>

"""
        for sub in subscriptions:
            end_str = sub["end_date"].strftime("%d/%m/%Y") if sub.get("end_date") else "??/??"
            text += f"👑 <b>{sub.get('tariff_name', 'VIP')}</b>\n"
            text += f"   📅 Vence: {end_str}\n\n"

        return text

    @staticmethod
    def backpack_package_delivering(package_name: str, file_count: int) -> str:
        """Mensaje al entregar contenido de paquete"""
        return f"""🎩 <b>Lucien:</b>

<i>Diana ha preparado el contenido...</i>

📦 <b>{package_name}</b>

<i>Entregando {file_count} archivo(s)...</i>"""

    @staticmethod
    def backpack_empty(reward_type: str) -> str:
        """Mensaje cuando no hay elementos"""
        messages = {
            "rewards": """🎩 <b>Lucien:</b>

<i>Aún no hay tesoros en su colección...
pero el camino apenas comienza.</i>

🏆 <b>No hay recompensas</b>

<i>Complete misiones para ganar tesoros del reino.</i>""",
            "purchases": """🎩 <b>Lucien:</b>

<i>No hay tesoros adquiridos en su inventario...
la tienda de Diana le espera.</i>

🛒 <b>No hay compras</b>

<i>Explore la tienda para obtener tesoros exclusivos.</i>""",
            "vip": """🎩 <b>Lucien:</b>

<i>El círculo exclusivo aún no lo ha recibido...
pero las puertas siempre están abiertas para quienes buscan.</i>

👑 <b>No hay membresías VIP</b>

<i>Contacte a Diana para obtener acceso a El Diván.</i>""",
        }
        return messages.get(reward_type, messages["rewards"])

    @staticmethod
    def streak_protection_offer(cost: int, streak: int) -> str:
        """Ofrece proteccion de racha al fallar una pregunta."""
        return (
            f"<b>La respuesta no es correcta, pero Lucien puede proteger su racha.</b>\n\n"
            f"Su racha de {streak} se mantiene si acepta la proteccion.\n"
            f"Costo: {cost} besitos."
        )

    @staticmethod
    def streak_protection_accepted(cost: int, streak: int) -> str:
        """Proteccion de racha aceptada y pagada."""
        return (
            f"Lucien ha protegido su racha. Se han debitado {cost} besitos.\n"
            f"Su racha de {streak} continua. Prosiga con cautela."
        )

    @staticmethod
    def streak_protection_declined(streak: int) -> str:
        """Usuario rechaza proteccion, pierde racha y codigos."""
        return (
            f"Ha decidido no proteger su racha.\n"
            f"Su racha de {streak} se ha roto y los codigos acumulados se han perdido."
        )

    @staticmethod
    def streak_risk_mode_offer(code_value: str, discount_pct: int, promotion_name: str) -> str:
        """Ofrece elegir entre retirarse con el codigo actual o continuar."""
        return (
            f"Ha alcanzado un nuevo nivel en <b>{promotion_name}</b>.\n\n"
            f"Codigo obtenido: <code>{code_value}</code> ({discount_pct}% descuento)\n\n"
            f"Puede retirarse y conservar este codigo, o continuar por un descuento mayor... "
            f"pero si falla, perdera todos los codigos acumulados en esta sesion."
        )

    @staticmethod
    def streak_retire_confirmed(code_count: int) -> str:
        """Usuario se retira conservando codigos."""
        return (
            f"Sabia decision. Lucien ha cerrado su sesion.\n"
            f"Conserva {code_count} codigo(s) de descuento. Visite el panel de Diana para mas informacion."
        )

    @staticmethod
    def streak_continue_confirmed() -> str:
        """Usuario elige continuar en modo arriesgo."""
        return (
            "Ha elegido continuar. Lucien observa con interes.\n"
            "Recuerde: si falla ahora, perdera todos los codigos acumulados.\n\n"
            "Continuemos con la siguiente pregunta."
        )

    @staticmethod
    def streak_timeout_granted(minutes: int, streak: int) -> str:
        """Timeout de 2 minutos para ganar besitos en trivia libre."""
        return (
            f"No tiene besitos suficientes para proteger su racha de {streak}.\n\n"
            f"Lucien le concede {minutes} minutos para ganar besitos en trivia libre.\n"
            f"Use /trivia para jugar. Si no regresa, perdera su racha y codigos."
        )

    @staticmethod
    def streak_codes_cancelled(code_count: int) -> str:
        """Notifica que los codigos han sido cancelados."""
        return (
            f"Los {code_count} codigo(s) acumulados en esta sesion han sido cancelados.\n"
            f"Su racha ha vuelto a 0. Puede intentarlo de nuevo cuando guste."
        )

    # ==================== OBSERVABILITY (Item 11) ====================

    @staticmethod
    def system_health(health: dict) -> str:
        """Pulso del reino para Custodios (elegant 3rd person, emojis per status)."""
        status = health.get("status", "unknown")
        checks = health.get("checks", {})
        lines = [
            "🎩 <b>Pulso del Reino</b>",
            "",
            "<i>El guardián observa el latido del reino de Diana...</i>",
            "",
        ]
        for name, data in checks.items():
            st = data.get("status", "unknown") if isinstance(data, dict) else "unknown"
            e = "✅" if st == "ok" else ("⚠️" if st in ("degraded", "unknown") else "❌")
            if name == "db":
                lines.append(
                    f"{e} <b>DB:</b> latencia {data.get('latency_ms', '?')}ms ({data.get('pool', 'db')})"
                )
            elif name == "bot":
                lines.append(f"{e} <b>Bot:</b> uptime {data.get('uptime_seconds', 0)}s")
            elif name == "channels":
                lines.append(
                    f"{e} <b>Canales:</b> free={data.get('free_channels', 0)} vip={data.get('vip_channels', 0)} pending={data.get('pending_requests', 0)} ready={data.get('ready_to_approve', 0)}"
                )
            elif name == "scheduler":
                lines.append(f"{e} <b>Scheduler:</b> {data.get('jobs_count', 0)} jobs")
            elif name == "event_bus":
                lines.append(
                    f"{e} <b>EventBus:</b> {data.get('total_listeners', 0)} listeners (besitos_awarded={data.get('besitos_awarded_listeners', 0)})"
                )
            elif name == "critical_sanity":
                b = data.get("besitos", {})
                v = data.get("vip", {})
                n = data.get("narrative", {})
                lines.append(
                    f"{e} <b>Sanity:</b> besitos_neg={b.get('neg_balances', 0)} vip_active={v.get('active_subscriptions', 0)} progress={n.get('progress_count', 0)}"
                )
            elif name == "backup":
                lines.append(f"{e} <b>Backup:</b> age {data.get('age_hours', '?')}h")
            else:
                lines.append(f"{e} <b>{name}:</b> {st}")
        lines.append("")
        if status != "healthy":
            lines.append("<i>Diana recomienda revisar los componentes marcados.</i>")
            lines.append("")
        lines.append(f"<i>Timestamp: {health.get('timestamp', '')}</i>")
        lines.append("<i>Los custodios velan por el reino de Diana.</i>")
        return "\n".join(lines)

    @staticmethod
    def health_access_denied() -> str:
        """Acceso denegado a pulso del reino."""
        return """🎩 <b>Lucien:</b>

<i>Estos secretos del pulso son solo para los custodios del reino.</i>

⚠️ <b>Acceso denegado</b>

<i>Solicite acceso a Diana si cree que esto es un error.</i>"""


# Import para evitar dependencia circular
from models.models import ChannelType
