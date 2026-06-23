"""
🎩 Voz de Lucien - Guardián de los Secretos de Diana

Este módulo contiene todos los mensajes y respuestas del bot,
diseñados con la personalidad elegante y misteriosa de Lucien.
"""

import html
from datetime import datetime


class LucienVoice:
    """Clase para generar mensajes con la voz de Lucien"""

    @staticmethod
    def _safe_channel_name(channel_name: str | None, default: str = "Los Kinkys") -> str:
        """Escapa channel_name para interpolación HTML."""
        return html.escape(channel_name or default)

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
        channel_text = (
            f" a <b>{LucienVoice._safe_channel_name(channel_name)}</b>" if channel_name else ""
        )
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
        safe = LucienVoice._safe_channel_name(channel_name)
        return f"""🎩 <b>Lucien:</b>

<i>Ah, la impaciencia... una cualidad que Diana encuentra
particularmente... reveladora.</i>

Su solicitud para <b>{safe}</b> ya está registrada.
Las puertas se abren a su debido tiempo.

<i>La anticipación es parte del ritual, ¿no lo cree?
Diana observa con interés su... entusiasmo.</i>"""

    @staticmethod
    def free_entry_ritual(channel_name: str) -> str:
        """Mensaje ritual enviado tras el periodo de espera del canal free"""
        safe = LucienVoice._safe_channel_name(channel_name)
        return f"""🎩 <b>Lucien:</b>

<i>El tiempo ha transcurrido y Diana ha observado su paciencia
con... aprobación. Los velos del vestíbulo se descorren.</i>

Las puertas de <b>{safe}</b> están ante usted.

<i>Entre con intención. Diana espera al otro lado.</i>"""

    @staticmethod
    def free_entry_welcome(channel_name: str) -> str:
        """Mensaje de bienvenida cuando se aprueba el acceso al canal free"""
        safe = LucienVoice._safe_channel_name(channel_name)
        return f"""🎩 <b>Lucien:</b>

<i>Diana ha decidido abrirle las puertas de <b>{safe}</b>.
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
        safe = LucienVoice._safe_channel_name(channel_name, "Sin nombre")
        return f"""🎩 <b>Lucien:</b>

<i>El {type_text} <b>{safe}</b> ha sido registrado
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
            safe = LucienVoice._safe_channel_name(ch.channel_name, "Sin nombre")
            text += f"{type_emoji} <b>{safe}</b>\n"
            text += f"   └ {type_text} | ID: <code>{ch.channel_id}</code>\n\n"

        return text

    @staticmethod
    def admin_channel_deleted(channel_name: str) -> str:
        """Canal eliminado"""
        safe = LucienVoice._safe_channel_name(channel_name, "Sin nombre")
        return f"""🎩 <b>Lucien:</b>

<i>El dominio <b>{safe}</b> ha sido removido
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

    @staticmethod
    def admin_channel_access_denied() -> str:
        """Acceso denegado al panel de canales."""
        return """🎩 <b>Lucien:</b>

<i>Los dominios de Diana no responden a su llamada...</i>

⚠️ <b>Acceso denegado</b>

<i>Solo los Custodios del reino pueden gestionar los vestíbulos.</i>"""

    @staticmethod
    def admin_wait_time_invalid() -> str:
        """Tiempo de espera custom inválido."""
        return """🎩 <b>Lucien:</b>

<i>Ese tiempo de espera no es aceptable para los vestíbulos.</i>

⚠️ Indique un valor entre <b>1</b> y <b>1440</b> minutos (24 horas).

<i>Ejemplo: <code>7</code> para siete minutos de paciencia.</i>"""

    @staticmethod
    def admin_messages_menu(channel_name: str) -> str:
        """Menú de configuración de mensajes del canal."""
        safe = LucienVoice._safe_channel_name(channel_name, "Sin nombre")
        return f"""🎩 <b>Lucien:</b>

<i>Mensajes personalizados para <b>{safe}</b>...</i>

📨 <b>Ritual</b> — enviado tras 30s de la solicitud
👋 <b>Bienvenida</b> — enviado tras aprobación

<i>Use HTML básico. Escriba <code>quitar</code> al editar para restaurar el default de Lucien.</i>"""

    @staticmethod
    def admin_message_edit_prompt(msg_type: str) -> str:
        """Prompt para editar mensaje custom."""
        label = "ritual de entrada" if msg_type == "approval" else "bienvenida"
        return f"""🎩 <b>Lucien:</b>

<i>Envíe el nuevo mensaje de <b>{label}</b>...</i>

<i>HTML básico permitido. Escriba <code>quitar</code> para usar el mensaje default de Lucien.</i>"""

    @staticmethod
    def admin_message_saved(msg_type: str) -> str:
        """Mensaje guardado exitosamente."""
        label = "Ritual" if msg_type == "approval" else "Bienvenida"
        return f"""🎩 <b>Lucien:</b>

✅ <b>{label}</b> actualizado correctamente.

<i>Los nuevos visitantes recibirán este mensaje.</i>"""

    @staticmethod
    def admin_message_restored(msg_type: str) -> str:
        """Mensajes restaurados a default."""
        if msg_type == "all":
            detail = "ritual y bienvenida"
        elif msg_type == "approval":
            detail = "ritual"
        else:
            detail = "bienvenida"
        return f"""🎩 <b>Lucien:</b>

✅ Mensaje de <b>{detail}</b> restaurado al estilo de Lucien.

<i>Los defaults volverán a aplicarse en el próximo envío.</i>"""

    @staticmethod
    def admin_message_preview(approval_preview: str, welcome_preview: str) -> str:
        """Vista previa de mensajes actuales (previews ya escapados)."""
        return f"""🎩 <b>Lucien:</b>

<i>Mensajes configurados actualmente:</i>

📨 <b>Ritual:</b>
{approval_preview}

👋 <b>Bienvenida:</b>
{welcome_preview}"""

    @staticmethod
    def admin_pending_requests_empty() -> str:
        """Sin solicitudes pendientes."""
        return """🎩 <b>Lucien:</b>

<i>No hay almas en espera en los vestíbulos de Diana.
Todos los visitantes han sido atendidos...</i>

El reino descansa tranquilo por ahora."""

    @staticmethod
    def admin_pending_requests_header(count: int, page: int, total_pages: int) -> str:
        """Cabecera de lista paginada de solicitudes pendientes."""
        return f"""🎩 <b>Lucien:</b>

<i>Hay <b>{count}</b> visitantes aguardando — página {page + 1}/{total_pages}</i>

"""

    @staticmethod
    def admin_requests_cleared(
        approved: int, failed: int = 0, errors: list[str] | None = None
    ) -> str:
        """Solicitudes aprobadas en lote (con errores parciales opcionales)."""
        if approved == 0 and failed > 0:
            text = f"""🎩 <b>Lucien:</b>

⚠️ <b>Ninguna solicitud pudo aprobarse</b> ({failed} fallidas).

<i>Revise permisos del bot o el estado de las solicitudes.</i>"""
            if errors:
                text += "\n\n" + LucienVoice._format_error_details(errors)
            return text

        if failed == 0:
            return f"""🎩 <b>Lucien:</b>

<i>He abierto las puertas para <b>{approved}</b> visitantes
que aguardaban en los vestíbulos.</i>

✅ <b>Solicitudes aprobadas en lote.</b>

<i>Diana aprecia la eficiencia del custodio del reino.</i>"""

        text = f"""🎩 <b>Lucien:</b>

✅ <b>{approved}</b> aprobados | ⚠️ <b>{failed}</b> fallidos

<i>Algunas puertas resistieron abrirse. Revise permisos del bot
o el estado de las solicitudes.</i>"""
        if errors:
            text += "\n\n" + LucienVoice._format_error_details(errors)
        return text

    @staticmethod
    def _format_error_details(errors: list[str], max_items: int = 3) -> str:
        """Formatea errores truncados para UI admin."""
        import html

        lines = [f"• {html.escape(err)}" for err in errors[:max_items]]
        if len(errors) > max_items:
            lines.append(f"• ... y {len(errors) - max_items} más")
        return "<i>Detalle:</i>\n" + "\n".join(lines)

    @staticmethod
    def admin_approve_all_empty() -> str:
        """Aprobar todas sin solicitudes pendientes."""
        return """🎩 <b>Lucien:</b>

<i>No hay visitantes aguardando en este vestíbulo.</i>

✅ <b>Nada que aprobar.</b>

<i>El reino descansa tranquilo por ahora.</i>"""

    @staticmethod
    def toast_approve_one_success(name: str) -> str:
        """Toast plain-text para callback.answer (sin HTML)."""
        return f"✅ {name} admitido al vestíbulo."

    @staticmethod
    def toast_approve_one_failed() -> str:
        """Toast plain-text: aprobación individual fallida."""
        return "No pude abrir las puertas para ese visitante."

    @staticmethod
    def toast_reject_success(name: str) -> str:
        """Toast plain-text: rechazo individual exitoso."""
        return f"🚫 {name} rechazado."

    @staticmethod
    def toast_reject_failed() -> str:
        """Toast plain-text: rechazo individual fallido."""
        return "No pude rechazar esa solicitud."

    @staticmethod
    def toast_approve_all_empty() -> str:
        """Toast plain-text: sin pendientes para aprobar."""
        return "No hay solicitudes pendientes."

    @staticmethod
    def toast_approve_all_failed() -> str:
        """Toast plain-text: aprobación masiva sin éxitos."""
        return "Ninguna solicitud pudo aprobarse."

    @staticmethod
    def toast_approve_all_success(count: int) -> str:
        """Toast plain-text: aprobación masiva exitosa."""
        return f"{count} solicitudes aprobadas"

    @staticmethod
    def admin_approve_one_success(username: str) -> str:
        """Aprobación individual exitosa (HTML — edit_text/answer con parse_mode)."""
        return f"""🎩 <b>Lucien:</b>

✅ <b>{username}</b> ha sido admitido al vestíbulo.

<i>Las puertas se abrieron sin resistencia.</i>"""

    @staticmethod
    def admin_approve_one_failed() -> str:
        """Aprobación individual fallida (HTML)."""
        return """🎩 <b>Lucien:</b>

⚠️ <i>No pude abrir las puertas para ese visitante.</i>

Verifique permisos del bot o que la solicitud siga pendiente."""

    @staticmethod
    def admin_reject_confirm(username: str) -> str:
        """Confirmación de rechazo individual."""
        return f"""🎩 <b>Lucien:</b>

<i>¿Confirma que desea rechazar a <b>{username}</b>?</i>

⚠️ El visitante <b>no</b> recibirá acceso al vestíbulo."""

    @staticmethod
    def admin_reject_success(username: str) -> str:
        """Rechazo individual exitoso (HTML)."""
        return f"""🎩 <b>Lucien:</b>

🚫 <b>{username}</b> ha sido rechazado.

<i>Las puertas permanecen cerradas para este visitante.</i>"""

    @staticmethod
    def admin_reject_failed() -> str:
        """Rechazo individual fallido (HTML)."""
        return """🎩 <b>Lucien:</b>

⚠️ <i>No pude rechazar esa solicitud.</i>

Verifique permisos del bot o que la solicitud siga pendiente."""

    # ==================== ANALYTICS ====================

    _SOURCE_LABELS = {
        "reaction": "Reacciones",
        "daily_gift": "Regalo diario",
        "mission": "Misiones",
        "game": "Juegos",
        "trivia": "Trivia",
        "admin": "Ajustes de custodios",
        "purchase": "Compras",
        "anonymous_message": "Mensajes anónimos",
        "streak_protection": "Protección de rachas",
    }

    @staticmethod
    def _traducir_fuente(src: str) -> str:
        """Traduce el código de fuente a nombre legible en español."""
        return LucienVoice._SOURCE_LABELS.get(src, src.replace("_", " ").capitalize())

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
    def analytics_patterns_dashboard(
        dashboard: dict, economy: dict, attribution: dict, top_earners: list
    ) -> str:
        """Patrones completos (dashboard + economía) para custodios."""
        d = dashboard or {}
        e = economy or {}
        a = attribution or {}
        t = top_earners or []

        win = e.get("window_days")
        win_str = "histórico" if not win else f"últimos {win} días"

        # Resumen compacto
        resumen = f"""👥 <b>Resumen del Reino</b>
• Visitantes: {d.get("total_users", 0)}   • VIP activos: {d.get("active_vip", 0)}
• Besitos en circulación: {d.get("total_besitos", 0)}"""

        # Economía
        if e.get("status") == "degraded":
            econ_block = "💰 <b>Economía</b>\n<i>Datos temporariamente no disponibles.</i>"
        else:
            econ_block = f"""💰 <b>Economía ({win_str})</b>
• Ingresados: {e.get("total_ever_earned", 0)}   • Gastados: {e.get("total_ever_spent", 0)}
• Circulación: {e.get("circulation", 0)}   • Tasa de gasto: {e.get("burn_rate_pct", 0)}%"""

        # Fuentes (top 5)
        if a.get("status") == "degraded":
            attr_block = "📈 <b>Fuentes de ingreso</b>\n<i>No disponibles en este momento.</i>"
        else:
            srcs = (a.get("sources") or [])[:5]
            src_lines = (
                "\n".join(
                    [
                        f"• {LucienVoice._traducir_fuente(s.get('source', ''))}: {s.get('total', 0)} ({s.get('pct', 0)}%)"
                        for s in srcs
                    ]
                )
                or "• Sin datos"
            )
            attr_block = f"📈 <b>Principales fuentes de ingreso</b>\n{src_lines}"

        # Top extractores
        tops = t[:6] if isinstance(t, list) else []
        if tops:
            top_lines = "\n".join(
                [
                    f"• {(tt.get('username') or str(tt.get('user_id', '?')))} — {tt.get('total_earned', 0)} acumulados (neto {tt.get('net', 0)})"
                    for tt in tops
                ]
            )
        else:
            top_lines = "• Sin datos"

        return f"""🎩 <b>Los patrones que revelan deseos</b>

<i>Los flujos del reino, al descubierto para los custodios...</i>

{resumen}

{econ_block}

{attr_block}

🏆 <b>Los que más han extraído</b>
{top_lines}

<i>Diana observa estos patrones con interés.</i>"""

    @staticmethod
    def economy_report(economy: dict, attribution: dict, top_earners: list) -> str:
        """Reporte enfocado y legible de la economía de besitos. Para /economy."""
        e = economy or {}
        a = attribution or {}
        t = top_earners or []

        win = e.get("window_days")
        win_str = "histórico" if not win else f"últimos {win} días"

        if e.get("status") == "degraded":
            return """🎩 <b>Economía del Reino</b>

<i>Los flujos están velados en este momento...</i>

⚠️ <b>Reporte no disponible</b>
<i>Intente nuevamente en unos minutos.</i>"""

        # Resumen compacto (lo más importante primero)
        resumen = f"""💰 <b>Resumen ({win_str})</b>
Ingresados: {e.get("total_ever_earned", 0)}   •   Gastados: {e.get("total_ever_spent", 0)}
En circulación: {e.get("circulation", 0)}   •   Tasa de gasto: {e.get("burn_rate_pct", 0)}%"""

        # Fuentes principales (máx 5)
        srcs = (a.get("sources") or [])[:5]
        if srcs:
            src_lines = "\n".join(
                [
                    f"• {LucienVoice._traducir_fuente(s.get('source', ''))}: {s.get('total', 0)} ({s.get('pct', 0)}%)"
                    for s in srcs
                ]
            )
        else:
            src_lines = "• Sin datos en el período"

        # Top extractores (máx 6 para no saturar)
        tops = t[:6] if isinstance(t, list) else []
        if tops:
            top_lines = "\n".join(
                [
                    f"• {(tt.get('username') or str(tt.get('user_id', '?')))} — {tt.get('total_earned', 0)} acumulados (neto {tt.get('net', 0)})"
                    for tt in tops
                ]
            )
        else:
            top_lines = "• Sin datos"

        return f"""🎩 <b>Economía del Reino</b>

<i>Las fuentes del deseo, contadas con claridad...</i>

{resumen}

📈 <b>Principales fuentes de ingreso</b>
{src_lines}

🏆 <b>Los que más han extraído</b>
{top_lines}

<i>Diana vigila el equilibrio del reino.</i>"""

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

    # ==================== NOTIFICACIONES A CUSTODIOS (ADMIN) ====================

    @staticmethod
    def store_admin_purchase_notification_enriched(
        user_display: str,
        username: str,
        user_id: int,
        items: list[tuple[str, int, int, str]],
        total_price: int,
        date_str: str,
        order_id: int,
    ) -> str:
        safe_display = html.escape(user_display)
        safe_username = html.escape(username)
        lines = [
            "🛍️ <b>Nueva compra en tienda</b>",
            f"Orden #{order_id} · {date_str}",
            f"Visitante: <b>{safe_display}</b> ({safe_username})",
            f"ID: {user_id}",
            "",
            "<b>Productos:</b>",
        ]
        for name, qty, subtotal, kind in items:
            safe_name = html.escape(name)
            lines.append(f"• {safe_name} x{qty} — {subtotal} besitos · <i>{kind}</i>")
        lines.extend(["", f"<b>Total:</b> {total_price} besitos"])
        return "\n".join(lines)

    @staticmethod
    def store_admin_purchase_notification(
        user_display: str,
        username: str,
        user_id: int,
        items: list[tuple[str, int, int]],
        total_price: int,
        date_str: str,
        order_id: int,
    ) -> str:
        """Notificación completa para administradores cuando se completa una compra en la tienda.

        Centraliza todo el texto en español aquí para cumplir con la auditoría de voz de Lucien
        (test_no_hardcoded_spanish_in_services). Los helpers en services/ solo delegan.
        """
        if not items:
            products_section = f"📦 <b>Items:</b> varios (total {total_price} besitos)"
        elif len(items) == 1:
            name, qty, item_total = items[0]
            products_section = f"📦 <b>Producto:</b> {name} ×{qty} — {item_total} besitos"
        else:
            lines = [f"• {name} ×{qty} — {item_total} besitos" for (name, qty, item_total) in items]
            products_section = "📦 <b>Productos:</b>\n" + "\n".join(lines)

        return (
            f"🎩 <b>Lucien - Notificación de la Tienda</b>\n\n"
            f"🛍️ <b>Producto adquirido</b>\n\n"
            f"👤 <b>Visitante:</b> {user_display}\n"
            f"   ID: <code>{user_id}</code>\n"
            f"   Username: {username}\n\n"
            f"{products_section}\n\n"
            f"💰 <b>Total:</b> {total_price} besitos\n"
            f"📅 <b>Fecha:</b> {date_str}\n"
            f"📋 <b>Orden #:</b> {order_id}\n\n"
            f"<i>Una nueva adquisición ha sido registrada en los dominios de Diana.</i>"
        )

    @staticmethod
    def store_admin_purchase_contact_button() -> str:
        """Label del botón para contactar al comprador en notificaciones de compra admin."""
        return "💬 Contactar al visitante"

    @staticmethod
    def store_admin_purchase_back_button() -> str:
        """Label del botón para volver al menú principal admin."""
        return "🔙 Volver al sanctum"

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
        return "Permítame buscar de nuevo… ese tesoro no figura en el catálogo."

    @staticmethod
    def store_product_unavailable(product_name: str = None) -> str:
        if product_name:
            safe_name = html.escape(product_name)
            return f"<i>{safe_name}</i> ya no está disponible en el Gabinete."
        return "Ese tesoro ya no está disponible en el Gabinete."

    @staticmethod
    def store_cart_updated(quantity: int, product_name: str) -> str:
        safe_name = html.escape(product_name)
        return f"Cantidad ajustada: {quantity} × <i>{safe_name}</i>"

    @staticmethod
    def store_cart_added(product_name: str) -> str:
        safe_name = html.escape(product_name)
        return f"<i>{safe_name}</i> aguarda en su selección."

    @staticmethod
    def store_cart_empty() -> str:
        return "Su selección está vacía por el momento."

    @staticmethod
    def store_stock_insufficient(product_name: str, available: int) -> str:
        safe_name = html.escape(product_name)
        return (
            f"Quedan pocas unidades de <i>{safe_name}</i> "
            f"(disponibles: {available})."
        )

    @staticmethod
    def store_balance_insufficient(needed: int, have: int) -> str:
        return (
            f"Necesita {needed} besitos; dispone de {have} por ahora."
        )

    @staticmethod
    def store_order_not_found() -> str:
        return "No encuentro esa adquisición en los registros del reino."

    @staticmethod
    def store_order_already_processed() -> str:
        return "Esa adquisición ya fue atendida."

    @staticmethod
    def store_payment_failed() -> str:
        return "Hubo un inconveniente al procesar su adquisición."

    @staticmethod
    def store_purchase_completed(total_price: int) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Excelente elección. Diana aprueba su discernimiento…</i>

Se han destinado <b>{total_price}</b> besitos a esta adquisición.

<i>¿Desea continuar explorando el Gabinete?</i>"""

    @staticmethod
    def store_menu_intro(balance: int) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Bienvenido al Gabinete de Tesoros de Diana…
objetos que ella ha seleccionado con particular cuidado.</i>

💋 <b>Su moneda especial:</b> {balance} besitos

<i>Permítame guiarle hacia lo que busca…</i>"""

    @staticmethod
    def store_button_search() -> str:
        return "🔍 Buscar entre los tesoros"

    @staticmethod
    def store_button_categories() -> str:
        return "📁 Recorrer las estanterías"

    @staticmethod
    def store_button_catalog() -> str:
        return "🛍️ Explorar el catálogo completo"

    @staticmethod
    def store_button_history() -> str:
        return "📜 Sus adquisiciones pasadas"

    @staticmethod
    def store_button_back() -> str:
        return "🔙 Volver"

    @staticmethod
    def store_button_back_to_shop() -> str:
        return "🔙 Volver al Gabinete"

    @staticmethod
    def store_button_back_main() -> str:
        return "🔙 Menú principal"

    @staticmethod
    def store_catalog_intro() -> str:
        return """🎩 <b>Lucien:</b>

<i>El catálogo completo de Diana…</i>

Permítame presentarle cada pieza disponible."""

    @staticmethod
    def store_catalog_empty() -> str:
        return """🎩 <b>Lucien:</b>

<i>El Gabinete descansa en silencio por ahora…</i>

Diana prepara nuevas piezas. Permítame invitarle a regresar pronto."""

    @staticmethod
    def store_categories_intro() -> str:
        return """🎩 <b>Lucien:</b>

<i>Las estanterías de Diana aguardan su curiosidad…</i>

Seleccione una sección para explorar."""

    @staticmethod
    def store_categories_empty() -> str:
        return """🎩 <b>Lucien:</b>

<i>El catálogo aún no tiene secciones definidas…</i>

Sin embargo, los tesoros aguardan en el catálogo completo."""

    @staticmethod
    def store_category_header(name: str, description: str = "") -> str:
        safe_name = html.escape(name)
        text = f"""🎩 <b>Lucien:</b>

<i>La estantería «{safe_name}»…</i>"""
        if description:
            text += f"\n\n{html.escape(description)}"
        return text

    @staticmethod
    def store_category_empty(name: str) -> str:
        safe_name = html.escape(name)
        return f"""🎩 <b>Lucien:</b>

<i>La estantería «{safe_name}» aguarda nuevas piezas…</i>

Permítame invitarle a explorar otras secciones."""

    @staticmethod
    def store_tier_menu_intro() -> str:
        return """🎩 <b>Lucien:</b>

<i>Permítame presentarle el Gabinete de Tesoros de Diana,
organizado por el peso del deseo…</i>

Seleccione un nivel para explorar."""

    @staticmethod
    def store_tier_intro_for_slug(slug: str) -> str:
        intros = {
            "impulso": "Curiosidad al alcance de la mano… piezas para quien no puede resistir.",
            "deseo": "El corazón del catálogo… donde el acceso se vuelve irresistible.",
            "exclusivo": "Completitud reservada… tesoros que merecen ser guardados.",
            "reservado": "Poder silencioso… solo para quienes llegaron lejos.",
            "mitico": "Leyenda en existencia limitada… piezas que quizá no vuelvan.",
        }
        tag = intros.get(slug, "Un rincón del Gabinete aguarda su mirada…")
        return f"""🎩 <b>Lucien:</b>

<i>{tag}</i>"""

    @staticmethod
    def store_tier_impulso_intro() -> str:
        return LucienVoice.store_tier_intro_for_slug("impulso")

    @staticmethod
    def store_tier_deseo_intro() -> str:
        return LucienVoice.store_tier_intro_for_slug("deseo")

    @staticmethod
    def store_tier_exclusivo_intro() -> str:
        return LucienVoice.store_tier_intro_for_slug("exclusivo")

    @staticmethod
    def store_tier_reservado_intro() -> str:
        return LucienVoice.store_tier_intro_for_slug("reservado")

    @staticmethod
    def store_tier_mitico_intro() -> str:
        return LucienVoice.store_tier_intro_for_slug("mitico")

    @staticmethod
    def store_product_detail(name: str, desc: str, price: int, tier: str = "") -> str:
        safe_name = html.escape(name)
        safe_desc = html.escape(desc) if desc else "<i>Un tesoro del reino…</i>"
        tier_line = f"\n<i>Nivel {html.escape(tier)}</i>\n" if tier else "\n"
        return f"""🎩 <b>Lucien:</b>
{tier_line}
<b>{safe_name}</b>

{safe_desc}

💋 <b>{price}</b> besitos"""

    @staticmethod
    def store_product_discount_line(list_price: int) -> str:
        return (
            f"\n🏷️ <b>Precio de lista:</b> {list_price} besitos "
            f"· <i>ventaja activa</i>"
        )

    @staticmethod
    def store_product_availability_lines(stock_text: str, file_count: int) -> str:
        return (
            f"\n📊 <b>Existencias:</b> {stock_text}"
            f"\n📦 <b>Contenido:</b> {file_count} archivo(s)"
        )

    @staticmethod
    def store_product_balance_line(balance: int) -> str:
        return f"\n\n💋 <b>Su moneda especial:</b> {balance} besitos"

    @staticmethod
    def store_monthly_cap_inline(product_name: str) -> str:
        safe_name = html.escape(product_name)
        return (
            f"<i>Este mes, <b>{safe_name}</b> ya encontró dueño… "
            f"Diana decidirá cuándo volverá.</i>"
        )

    @staticmethod
    def store_product_detail_card(
        name: str,
        desc: str,
        price: int,
        balance: int,
        stock_text: str,
        file_count: int,
        tier: str = "",
        list_price: int | None = None,
        monthly_cap_available: bool = True,
        tier_lock_message: str | None = None,
    ) -> str:
        """Tarjeta completa de producto para detalle y preview."""
        text = LucienVoice.store_product_detail(name, desc, price, tier)
        if list_price is not None and list_price > price:
            text += LucienVoice.store_product_discount_line(list_price)
        text += LucienVoice.store_product_availability_lines(stock_text, file_count)
        text += LucienVoice.store_product_balance_line(balance)
        if not monthly_cap_available:
            text += f"\n\n⚠️ {LucienVoice.store_monthly_cap_inline(name)}"
        if tier_lock_message:
            text += f"\n\n🔒 <i>{html.escape(tier_lock_message)}</i>"
        if balance < price:
            text += LucienVoice.store_need_more_besitos_hint()
            text += LucienVoice.store_earn_besitos_tips()
        return text

    @staticmethod
    def store_monthly_cap_reached(product_name: str) -> str:
        safe_name = html.escape(product_name)
        return f"""🎩 <b>Lucien:</b>

<i>Este mes, <b>{safe_name}</b> ya encontró dueño…</i>

Permítame consultar con Diana cuándo volverá a estar disponible."""

    @staticmethod
    def fulfillment_package_delivered(name: str) -> str:
        safe_name = html.escape(name)
        return f"""🎩 <b>Lucien:</b>

<i>Su adquisición <b>{safe_name}</b> ya viaja hacia usted…</i>"""

    @staticmethod
    def fulfillment_package_failed_retry_mochila() -> str:
        return """🎩 <b>Lucien:</b>

<i>Hubo un inconveniente al entregar su tesoro.</i>

Revise <b>Sus tesoros adquiridos</b> en la mochila para reintentar."""

    @staticmethod
    def fulfillment_story_unlocked(node_title: str) -> str:
        safe_title = html.escape(node_title)
        return f"""🎩 <b>Lucien:</b>

<i>Un fragmento exclusivo se abre ante usted: <b>{safe_title}</b></i>"""

    @staticmethod
    def fulfillment_early_access_granted(hours: int) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Usted verá el próximo lanzamiento {hours}h antes que nadie.</i>"""

    @staticmethod
    def fulfillment_discount_granted(pct: int, expires: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Un {pct}% de ventaja le acompaña hasta el {expires}.</i>"""

    @staticmethod
    def fulfillment_waitlist_joined(position: int) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Su posición en La Lista: <b>#{position}</b></i>"""

    @staticmethod
    def fulfillment_manual_queued(product_name: str) -> str:
        safe_name = html.escape(product_name)
        return f"""🎩 <b>Lucien:</b>

<i>Excelente elección. Su solicitud de <b>{safe_name}</b> ya viaja hacia Diana…</i>

Lucien le avisará cuando esté lista en su mochila."""

    @staticmethod
    def fulfillment_awaiting_input(prompt: str) -> str:
        return f"""🎩 <b>Lucien:</b>

{prompt}

<i>Escriba su respuesta en este chat.</i>"""

    @staticmethod
    def fulfillment_input_prompt_question() -> str:
        return "<i>Diana escucha con atención quien se atreve a preguntar…</i>"

    @staticmethod
    def fulfillment_input_prompt_director() -> str:
        return "<i>Proponga el tema de la próxima sesión…</i>"

    @staticmethod
    def fulfillment_input_prompt_credits() -> str:
        return "<i>Indique el nombre que desea en los créditos…</i>"

    @staticmethod
    def fulfillment_input_prompt_for_key(prompt_key: str) -> str:
        mapping = {
            "fulfillment_input_prompt_question": LucienVoice.fulfillment_input_prompt_question,
            "fulfillment_input_prompt_director": LucienVoice.fulfillment_input_prompt_director,
            "fulfillment_input_prompt_credits": LucienVoice.fulfillment_input_prompt_credits,
            "question": LucienVoice.fulfillment_input_prompt_question,
            "session_theme": LucienVoice.fulfillment_input_prompt_director,
            "credit_name": LucienVoice.fulfillment_input_prompt_credits,
        }
        fn = mapping.get(prompt_key, LucienVoice.fulfillment_input_prompt_question)
        return fn()

    @staticmethod
    def fulfillment_input_invalid_length(min_len: int, max_len: int) -> str:
        return f"Permítame pedirle entre {min_len} y {max_len} caracteres."

    @staticmethod
    def fulfillment_input_received_queued() -> str:
        return """🎩 <b>Lucien:</b>

<i>Su mensaje fue registrado. Diana fue notificada.</i>"""

    @staticmethod
    def fulfillment_input_already_submitted() -> str:
        return "Su respuesta ya fue registrada."

    @staticmethod
    def fulfillment_input_cancelled() -> str:
        return """🎩 <b>Lucien:</b>

<i>Entendido. Puede enviar su mensaje más tarde desde la mochila.</i>"""

    @staticmethod
    def fulfillment_input_submit_button() -> str:
        return "🌸 Enviar a Diana"

    @staticmethod
    def fulfillment_admin_queue_menu() -> str:
        return """🎩 <b>Lucien:</b>

<i>Cola de entregas del reino — seleccione un filtro.</i>"""

    @staticmethod
    def fulfillment_admin_queue_item(
        product_name: str,
        order_id: int,
        user_id: int,
        status: str,
        user_input: str | None = None,
    ) -> str:
        safe_name = html.escape(product_name)
        safe_input = html.escape(user_input) if user_input else None
        input_block = f"\n\n📝 <i>Su mensaje:</i>\n«{safe_input}»" if safe_input else ""
        return f"""🎩 <b>Lucien:</b>

<b>{safe_name}</b> · Orden #{order_id}
Visitante id: {user_id}
Estado: {status}{input_block}"""

    @staticmethod
    def fulfillment_admin_new_manual_order(
        product_name: str,
        order_id: int,
        user_id: int,
        kind: str,
        status: str,
        user_input: str | None,
    ) -> str:
        return LucienVoice.fulfillment_admin_queue_item(
            product_name, order_id, user_id, f"{kind} / {status}", user_input
        )

    @staticmethod
    def fulfillment_admin_mark_fulfilled_confirm() -> str:
        return "¿Confirma marcar como cumplido?"

    @staticmethod
    def fulfillment_admin_notes_required() -> str:
        return "Las notas son obligatorias al marcar cumplido."

    @staticmethod
    def fulfillment_admin_input_required() -> str:
        return "Aguarde el mensaje del visitante antes de marcar cumplido."

    @staticmethod
    def fulfillment_admin_invalid_status() -> str:
        return "Este ítem no puede marcarse cumplido en su estado actual."

    @staticmethod
    def fulfillment_admin_package_mismatch() -> str:
        return "El paquete indicado no corresponde al producto."

    @staticmethod
    def fulfillment_admin_deliver_invalid_kind() -> str:
        return "Solo se puede entregar paquete en ítems PACKAGE o PACKAGE_DEFERRED."

    @staticmethod
    def fulfillment_admin_queue_empty() -> str:
        return "Cola vacía"

    @staticmethod
    def fulfillment_admin_item_not_found() -> str:
        return "Item no encontrado"

    @staticmethod
    def fulfillment_admin_filter_pending_input() -> str:
        return "⏳ Pendiente input"

    @staticmethod
    def fulfillment_admin_filter_pending_diana() -> str:
        return "🌸 Pendiente Diana"

    @staticmethod
    def fulfillment_admin_filter_failed() -> str:
        return "❌ Fallidos"

    @staticmethod
    def fulfillment_admin_filter_fulfilled() -> str:
        return "✅ Cumplidos"

    @staticmethod
    def fulfillment_retry_not_allowed() -> str:
        return "Solo puede reintentar entregas fallidas."

    @staticmethod
    def fulfillment_retry_limit_reached() -> str:
        return "Límite de reintentos alcanzado."

    @staticmethod
    def fulfillment_retry_cooldown() -> str:
        return "Espere un momento antes de reintentar."

    @staticmethod
    def fulfillment_package_failed_retry_mochila_plain() -> str:
        return "Inconveniente en entrega. Puede reintentar desde la mochila."

    @staticmethod
    def backpack_fulfillment_toast_success(msg: str) -> str:
        import re

        return re.sub(r"<[^>]+>", "", msg).strip()

    @staticmethod
    def fulfillment_admin_wizard_select_tier() -> str:
        return "Seleccione el tier del producto:"

    @staticmethod
    def fulfillment_admin_wizard_delivery_mode() -> str:
        return "Modo de entrega: AUTO o MANUAL"

    @staticmethod
    def fulfillment_admin_wizard_fulfillment_kind() -> str:
        return "Tipo de fulfillment:"

    @staticmethod
    def fulfillment_admin_wizard_start() -> str:
        return (
            "🎩 Lucien:\n\n"
            "Vamos a crear un nuevo producto...\n\n"
            "Paso 1 de 5: Nombre del producto\n\n"
            "Indica un nombre descriptivo:\n"
            "Ejemplo: Pack Fotos Exclusivas Marzo"
        )

    @staticmethod
    def fulfillment_admin_wizard_name_too_short() -> str:
        return "El nombre debe tener al menos 3 caracteres."

    @staticmethod
    def fulfillment_admin_wizard_step_description() -> str:
        return (
            "🎩 Lucien:\n\n"
            "Paso 2 de 5: Descripcion\n\n"
            "Escribe una descripcion (opcional):\n"
            "Ejemplo: Un pack de 10 fotos exclusivas\n\n"
            "O envia /skip para omitir."
        )

    @staticmethod
    def fulfillment_admin_wizard_step_price() -> str:
        return "Paso: Precio\n\nIndica el precio en besitos:"

    @staticmethod
    def fulfillment_admin_wizard_step_price_with_example() -> str:
        return (
            "🎩 Lucien:\n\n"
            "Paso 4 de 5: Precio\n\n"
            "Indica el precio en besitos:\n"
            "Ejemplo: 100"
        )

    @staticmethod
    def fulfillment_admin_wizard_select_tariff() -> str:
        return "Paso: Seleccionar tarifa VIP\n\nElige la tarifa para este producto:"

    @staticmethod
    def fulfillment_admin_wizard_select_story_node() -> str:
        return "Paso: Seleccionar nodo narrativo\n\nElige el nodo a desbloquear:"

    @staticmethod
    def fulfillment_admin_wizard_step_fulfillment_config() -> str:
        return (
            "Paso: Fulfillment config\n\n"
            "Indica JSON de configuración o usa omitir para valores por defecto:"
        )

    @staticmethod
    def fulfillment_admin_wizard_step_monthly_cap() -> str:
        return "Paso: Cupo mensual\n\nIndica unidades máximas por mes (MX) o sin límite:"

    @staticmethod
    def fulfillment_admin_wizard_no_packages() -> str:
        return "No hay paquetes disponibles."

    @staticmethod
    def fulfillment_admin_wizard_no_tariffs() -> str:
        return "No hay tarifas VIP disponibles."

    @staticmethod
    def fulfillment_admin_wizard_no_story_nodes() -> str:
        return "No hay nodos narrativos disponibles."

    @staticmethod
    def fulfillment_admin_wizard_step_select_package() -> str:
        return "Paso: Seleccionar paquete"

    @staticmethod
    def fulfillment_admin_wizard_invalid_json() -> str:
        return "JSON inválido. Revise el formato o use Omitir."

    @staticmethod
    def fulfillment_admin_wizard_invalid_price() -> str:
        return "Por favor indica un numero valido mayor a 0."

    @staticmethod
    def fulfillment_admin_wizard_step_stock() -> str:
        return "🎩 Lucien:\n\nPaso 5 de 5: Stock\n\nConfigura el stock disponible:"

    @staticmethod
    def fulfillment_admin_wizard_step_limited_stock() -> str:
        return (
            "🎩 Lucien:\n\n"
            "Indica la cantidad de unidades disponibles:\n"
            "Ejemplo: 50"
        )

    @staticmethod
    def fulfillment_admin_wizard_invalid_stock() -> str:
        return "Indica un numero valido (0 o mayor)."

    @staticmethod
    def fulfillment_admin_wizard_invalid_monthly_cap() -> str:
        return "Indica un entero >= 1 o use Sin límite."

    @staticmethod
    def fulfillment_admin_wizard_confirmation_summary(
        name: str,
        description: str,
        tier: str,
        delivery: str,
        kind: str,
        price: int,
        stock_text: str,
        cap_text: str,
        tariff_name: str | None = None,
        story_node_title: str | None = None,
    ) -> str:
        safe_name = html.escape(name)
        safe_description = html.escape(description)
        lines = [
            "🎩 Lucien:\n",
            "Resumen del producto:\n",
            f"📦 {safe_name}",
            f"📝 {safe_description}",
            f"✨ Tier: {tier}",
            f"🚚 Modo: {delivery}",
            f"🎯 Kind: {kind}",
        ]
        if tariff_name:
            lines.append(f"👑 Tarifa: {html.escape(tariff_name)}")
        if story_node_title:
            lines.append(f"📖 Nodo: {html.escape(story_node_title)}")
        lines.extend(
            [
                f"💰 Precio: {price} besitos",
                f"📊 Stock: {stock_text}",
                f"📅 Cupo mensual: {cap_text}",
                "",
                "Crear este producto?",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def fulfillment_admin_wizard_product_created(name: str, price: int) -> str:
        safe_name = html.escape(name)
        return (
            f"🎩 Lucien:\n\n"
            f"✅ Producto creado exitosamente!\n\n"
            f"📦 {safe_name}\n"
            f"💰 {price} besitos\n\n"
            f"El producto ya esta disponible en la tienda."
        )

    @staticmethod
    def fulfillment_admin_wizard_product_create_error() -> str:
        return "Error al crear el producto."

    @staticmethod
    def fulfillment_admin_wizard_cap_unlimited_label() -> str:
        return "Sin límite"

    @staticmethod
    def store_need_more_besitos_hint() -> str:
        return (
            "\n\n<i>Ah… parece que necesita acumular más "
            "de la moneda especial de Diana.</i>\n"
        )

    @staticmethod
    def store_earn_besitos_tips() -> str:
        return """👉 <b>Sugerencia:</b> <i>La devoción suele ser recompensada…</i>
• Reclame su regalo diario
• Reaccione a las publicaciones del reino
• Complete los encargos de Diana
• Únase al círculo exclusivo para mayores ventajas"""

    @staticmethod
    def store_confirm_purchase_prompt() -> str:
        return "<i>¿Confirma esta adquisición?</i>\n\n"

    @staticmethod
    def store_confirm_purchase_message(
        product_name: str, price: int, balance: int, remaining: int
    ) -> str:
        safe_name = html.escape(product_name)
        return f"""🎩 <b>Lucien:</b>

{LucienVoice.store_confirm_purchase_prompt()}📦 <b>{safe_name}</b>
💋 <b>Inversión:</b> {price} besitos

{LucienVoice.store_product_balance_line(balance).strip()}
{LucienVoice.store_after_purchase_balance_line(remaining)}"""

    @staticmethod
    def store_after_purchase_balance_line(remaining: int) -> str:
        return f"📊 <b>Tras la adquisición:</b> {remaining} besitos"

    @staticmethod
    def store_search_prompt() -> str:
        return "<i>¿Qué tesoro busca?</i>\n\n"

    @staticmethod
    def store_search_start_message() -> str:
        return f"""🎩 <b>Lucien:</b>

{LucienVoice.store_search_prompt()}<i>Escriba el nombre o una palabra clave…</i>"""

    @staticmethod
    def store_search_min_chars() -> str:
        return "Permítame al menos dos caracteres para orientar la búsqueda."

    @staticmethod
    def store_search_no_results(query: str) -> str:
        safe_query = html.escape(query)
        return f"""🎩 <b>Lucien:</b>

<i>No hallé tesoros para «{safe_query}»…</i>

Quizá otra palabra lo guíe, o prefiera explorar el catálogo."""

    @staticmethod
    def store_search_results(query: str, count: int) -> str:
        safe_query = html.escape(query)
        return f"""🎩 <b>Lucien:</b>

<i>Resultados para «{safe_query}»…</i>

{count} tesoro(s) encontrado(s)"""

    @staticmethod
    def store_button_new_search() -> str:
        return "🔍 Nueva búsqueda"

    @staticmethod
    def store_button_preview() -> str:
        return "👁️ Anticipo del tesoro"

    @staticmethod
    def store_button_buy() -> str:
        return "🌸 Adquirir ahora"

    @staticmethod
    def store_button_insufficient(shortfall: int) -> str:
        return f"❌ Faltan {shortfall} besitos"

    @staticmethod
    def store_button_sold_out() -> str:
        return "🔒 Agotado por ahora"

    @staticmethod
    def store_button_more_products() -> str:
        return "🛍️ Explorar más tesoros"

    @staticmethod
    def store_button_by_categories() -> str:
        return "📁 Por estanterías"

    @staticmethod
    def store_button_other_categories() -> str:
        return "📁 Otras estanterías"

    @staticmethod
    def store_button_see_all() -> str:
        return "🛍️ Ver todo el catálogo"

    @staticmethod
    def store_button_confirm() -> str:
        return "✅ Confirmar adquisición"

    @staticmethod
    def store_button_cancel() -> str:
        return "❌ Reconsiderar"

    @staticmethod
    def store_button_go_shop() -> str:
        return "🛍️ Ir al Gabinete"

    @staticmethod
    def store_preview_caption() -> str:
        return "<i>Un anticipo de lo que aguarda…</i>"

    @staticmethod
    def store_preview_sent_alert() -> str:
        return "Anticipo enviado."

    @staticmethod
    def store_purchase_success_alert() -> str:
        return "Adquisición completada."

    @staticmethod
    def store_balance_insufficient_alert() -> str:
        return "Moneda especial insuficiente."

    @staticmethod
    def store_tier_not_found() -> str:
        return "Ese nivel no figura en el Gabinete."

    @staticmethod
    def store_category_not_found() -> str:
        return "Esa estantería no figura en el catálogo."

    @staticmethod
    def store_tier_locked(
        previous_tier_name: str,
        purchased: int,
        required: int,
        remaining: int,
    ) -> str:
        safe_prev = html.escape(previous_tier_name)
        return (
            f"Para acceder a este nivel, adquiera {required} tesoros de "
            f"«{safe_prev}» primero ({purchased}/{required}; faltan {remaining})."
        )

    @staticmethod
    def store_button_tier_locked(remaining: int) -> str:
        return f"🔒 Requiere {remaining} más en nivel anterior"

    @staticmethod
    def store_purchase_history_empty() -> str:
        return """🎩 <b>Lucien:</b>

<i>Aún no registra adquisiciones en el reino…</i>

Permítame invitarle al Gabinete para su primera elección."""

    @staticmethod
    def store_purchase_history_header() -> str:
        return """🎩 <b>Lucien:</b>

<i>Sus adquisiciones pasadas en el Gabinete de Diana…</i>"""

    @staticmethod
    def store_purchase_history_item(
        order_id: int, date_str: str, total_items: int, total_price: int, status_emoji: str
    ) -> str:
        return (
            f"{status_emoji} Adquisición #{order_id} — {date_str}\n"
            f"   Piezas: {total_items} | Total: {total_price} besitos\n\n"
        )

    @staticmethod
    def store_filters_intro() -> str:
        return """🎩 <b>Lucien:</b>

<i>Permítame ordenar los tesoros a su gusto…</i>

Seleccione cómo desea explorarlos:"""

    @staticmethod
    def store_filter_empty() -> str:
        return """🎩 <b>Lucien:</b>

<i>Ningún tesoro coincide con ese criterio…</i>"""

    @staticmethod
    def store_filter_results(filter_name: str, count: int, overflow: int = 0) -> str:
        safe_filter = html.escape(filter_name)
        text = f"""🎩 <b>Lucien:</b>

<i>Criterio: {safe_filter}</i>

{count} tesoro(s)"""
        if overflow > 0:
            text += f"\n\n<i>…y {overflow} más</i>"
        return text

    @staticmethod
    def store_filter_price_asc() -> str:
        return "💰 Del más accesible al más selecto"

    @staticmethod
    def store_filter_price_desc() -> str:
        return "💰 Del más selecto al más accesible"

    @staticmethod
    def store_filter_in_stock() -> str:
        return "📦 Solo disponibles ahora"

    @staticmethod
    def store_filter_recent() -> str:
        return "🆕 Las piezas más recientes"

    @staticmethod
    def store_filter_label_price_asc() -> str:
        return "Precio: menor a mayor"

    @staticmethod
    def store_filter_label_price_desc() -> str:
        return "Precio: mayor a menor"

    @staticmethod
    def store_filter_label_in_stock() -> str:
        return "Solo disponibles"

    @staticmethod
    def store_filter_label_recent() -> str:
        return "Más recientes"

    @staticmethod
    def backpack_fulfillment_status_pending_input() -> str:
        return "Aguardando su mensaje"

    @staticmethod
    def backpack_fulfillment_status_pending_diana() -> str:
        return "En manos de Diana"

    @staticmethod
    def backpack_fulfillment_status_processing() -> str:
        return "En proceso"

    @staticmethod
    def backpack_fulfillment_status_fulfilled() -> str:
        return "Cumplido"

    @staticmethod
    def backpack_fulfillment_status_failed() -> str:
        return "Inconveniente en entrega"

    @staticmethod
    def backpack_fulfillment_package_detail(name: str, status: str) -> str:
        safe_name = html.escape(name)
        return f"<b>{safe_name}</b>\nEstado: <i>{status}</i>"

    @staticmethod
    def backpack_fulfillment_pending_diana(name: str) -> str:
        safe_name = html.escape(name)
        return f"""🎩 <b>Lucien:</b>

<i>El tesoro <b>{safe_name}</b> aguarda el toque de Diana…</i>"""

    @staticmethod
    def backpack_fulfillment_input_submitted(name: str) -> str:
        safe_name = html.escape(name)
        return f"<b>{safe_name}</b> — su mensaje ya fue enviado a Diana."

    @staticmethod
    def backpack_fulfillment_privilege_active(kind: str, expires: str) -> str:
        return f"Privilegio <b>{kind}</b> activo hasta {expires}."

    @staticmethod
    def backpack_fulfillment_waitlist_position(position: int) -> str:
        return f"Posición en La Lista: <b>#{position}</b>"

    @staticmethod
    def backpack_fulfillment_fulfilled(name: str) -> str:
        safe_name = html.escape(name)
        return f"<b>{safe_name}</b> — cumplido."

    @staticmethod
    def backpack_fulfillment_retry_button() -> str:
        return "🔄 Reintentar entrega"

    @staticmethod
    def backpack_fulfillment_resend_vip_invite_button() -> str:
        return "🔗 Reenviar acceso VIP"

    @staticmethod
    def backpack_fulfillment_read_chapter_button() -> str:
        return "📖 Leer capítulo"

    @staticmethod
    def backpack_fulfillment_waitlist_button() -> str:
        return "📋 Ver posición en La Lista"

    @staticmethod
    def store_catalog_unavailable() -> str:
        return "El Gabinete no está disponible en este momento."

    @staticmethod
    def store_admin_stock_alerts_empty() -> str:
        return (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Todos los tesoros están bien abastecidos...</i>\n\n"
            "No hay alertas de stock."
        )

    @staticmethod
    def backpack_page_load_error() -> str:
        return "Error al cargar página"

    @staticmethod
    def backpack_besitos_balance_message(balance: int) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Los besitos son la moneda del reino de Diana...</i>

💋 <b>Su Balance</b>

💰 <b>Besitos disponibles:</b> {balance}

<i>Use sus besitos para adquirir tesoros en la tienda
o completar misiones para ganar más.</i>"""

    @staticmethod
    def main_menu_shop_button() -> str:
        return "🛍️ El Gabinete de Tesoros"

    @staticmethod
    def store_tier_menu_button() -> str:
        return "✨ Ver por niveles"

    @staticmethod
    def store_acquire_button() -> str:
        return "🌸 Adquirir este privilegio"

    @staticmethod
    def store_back_to_tier_button(tier_name: str) -> str:
        return f"🔙 Volver a {tier_name}"

    @staticmethod
    def store_go_backpack_button() -> str:
        return "🎒 Ir a la mochila"

    @staticmethod
    def store_continue_shopping_button() -> str:
        return "🛍️ Seguir explorando"

    @staticmethod
    def fulfillment_admin_queue_button() -> str:
        return "📬 Cola de entregas del reino"

    @staticmethod
    def fulfillment_admin_mark_fulfilled_button() -> str:
        return "✅ Marcar cumplido (notas)"

    @staticmethod
    def fulfillment_admin_deliver_package_button() -> str:
        return "📦 Entregar paquete"

    @staticmethod
    def fulfillment_admin_deliver_select_package() -> str:
        return "Seleccione el paquete a entregar:"

    @staticmethod
    def fulfillment_admin_contact_visitor_button() -> str:
        return "👤 Contactar visitante"

    @staticmethod
    def fulfillment_post_purchase_message_for_kind(kind: str, product_name: str) -> str:
        fallbacks = {
            "package": LucienVoice.fulfillment_package_delivered(product_name),
            "vip_grant": LucienVoice.vip_direct_access(),
            "story_unlock": LucienVoice.fulfillment_story_unlocked(product_name),
            "early_access": LucienVoice.fulfillment_early_access_granted(24),
            "user_input_manual": LucienVoice.fulfillment_awaiting_input(
                LucienVoice.fulfillment_input_prompt_question()
            ),
        }
        return fallbacks.get(
            kind, LucienVoice.fulfillment_manual_queued(product_name)
        )

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
        safe_name = html.escape(package_name)
        desc = description or "Un obsequio del reino..."
        safe_desc = html.escape(desc)
        return f"""🎩 <b>Lucien:</b>

<i>Diana ha preparado algo especial para usted...</i>

📦 <b>{safe_name}</b>

<i>{safe_desc}</i>

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
    def mission_reward_besitos_delivered(mission_name: str, amount: int, balance: int) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Una misión cumplida. «{mission_name}» — el visitante ha demostrado... constancia.</i>

💋 <b>{amount} besitos</b> han sido acreditados a su favor.
Saldo actual: <b>{balance}</b>.

<i>Diana anota el gesto con interés moderado.</i>"""

    @staticmethod
    def mission_reward_package_delivered(mission_name: str, package_name: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>«{mission_name}» completada. Lucien confirma que el obsequio ha sido despachado.</i>

📦 <b>{package_name}</b> — ya debe estar en su posesión.

<i>Se espera una reacción... apropiada.</i>"""

    @staticmethod
    def mission_reward_vip_delivered(mission_name: str, tariff_name: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>La misión «{mission_name}» ha sido superada. El Diván abre una puerta adicional.</i>

👑 Acceso VIP: <b>{tariff_name}</b>

<i>Lucien observa con curiosidad si el visitante sabrá aprovecharlo.</i>"""

    @staticmethod
    def mission_reward_claim_success(mission_name: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>El obsequio pendiente de «{mission_name}» ha sido despachado.
Lucien prefiere no preguntar por qué tardó tanto.</i>"""

    @staticmethod
    def mission_reward_claim_success_alert(mission_name: str) -> str:
        return (
            f"🎩 Lucien:\n\n"
            f"El obsequio pendiente de «{mission_name}» ha sido despachado. "
            f"Lucien prefiere no preguntar por qué tardó tanto."
        )

    @staticmethod
    def mission_reward_claim_pending() -> str:
        return """🎩 <b>Lucien:</b>

<i>Lucien revisa sus registros... no encuentra obsequios pendientes por despachar.</i>"""

    @staticmethod
    def mission_reward_claim_pending_alert() -> str:
        return (
            "🎩 Lucien:\n\n"
            "Lucien revisa sus registros... no encuentra obsequios pendientes por despachar."
        )

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
    def reward_vip_activation_failed() -> str:
        return "No se pudo activar su membresía VIP. Contacte a soporte."

    @staticmethod
    def reward_vip_invite_failed() -> str:
        return "No se pudo generar su enlace de acceso VIP. Intente desde la mochila."

    @staticmethod
    def fulfillment_vip_delivery_failed() -> str:
        return "Su VIP está activo pero no pudimos enviarle el enlace. Revise la mochila."

    @staticmethod
    def store_vip_purchase_pending_backpack() -> str:
        return """🎩 <b>Lucien:</b>

<i>Su compra se registró, pero el acceso VIP requiere un paso más.</i>

Revise <b>Sus tesoros adquiridos</b> en la mochila."""

    @staticmethod
    def reward_tariff_not_found() -> str:
        return "Tarifa no encontrada"

    @staticmethod
    def reward_emoji_besitos(amount: int) -> str:
        return f"{amount} besitos"

    @staticmethod
    def reward_emoji_package(name: str) -> str:
        return f"Paquete exclusivo: {name}"

    @staticmethod
    def reward_emoji_vip(name: str) -> str:
        return f"Acceso VIP: {name}"

    @staticmethod
    def reward_package_delivery_failed() -> str:
        return "Error al enviar paquete"

    @staticmethod
    def reward_vip_received(tariff_name: str, days: int) -> str:
        return f"Has recibido acceso VIP: {tariff_name} ({days} dias)"

    @staticmethod
    def reward_vip_message(tariff_name: str, duration_days: int, token_url: str) -> str:
        return f"""🎩 <b>Lucien:</b>

<i>Diana le ha concedido acceso a El Diván...</i>

👑 <b>Recompensa VIP Activada</b>

📋 Tarifa: <b>{tariff_name}</b>
⏱ Duración: <b>{duration_days}</b> días

🔗 <a href="{token_url}">Su enlace de acceso</a>

<i>Lucien observa si el visitante sabrá activarlo.</i>"""

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

    @staticmethod
    def story_invalid_choice() -> str:
        return "Esa opcion no esta disponible desde su posicion actual"

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
            raw_name = p["product_name"]
            name = raw_name[:25] + "..." if len(raw_name) > 25 else raw_name
            name = html.escape(name)

            status = p.get("status_display", "")
            status_suffix = f" | {status}" if status else ""
            text += f"📦 <b>{name}</b>\n"
            text += f"   💰 {price} 💋 | 📅 {date_str}{status_suffix}\n\n"

        return text

    @staticmethod
    def backpack_purchase_detail(purchase: dict) -> str:
        """Detalle de compra en mochila con estado fulfillment."""
        date_str = (
            purchase["purchased_at"].strftime("%d/%m/%Y")
            if purchase.get("purchased_at")
            else "N/A"
        )
        status = purchase.get("status_display", LucienVoice.backpack_fulfillment_status_processing())
        product_name = html.escape(purchase.get("product_name", ""))
        return f"""🎩 <b>Lucien:</b>

<i>El tesoro adquirido espera por usted…</i>

📦 <b>{product_name}</b>
📅 {date_str} · 💋 {purchase.get("total_price", 0)} besitos

Estado: <i>{status}</i>"""

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
