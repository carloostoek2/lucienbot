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

<i>Ah{name_part}, bienvenido al círculo exclusivo.
Aquí, Diana puede mostrar facetas que... otros no conocen.
Su presencia ha sido... anticipada.</i>

Permíteme guiarle por los privilegios a su disposición."""
    
    # ==================== CANAL FREE ====================
    
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
    
    # ==================== CANAL VIP ====================
    
    @staticmethod
    def vip_activated(tariff_name: str, expiration_date: datetime) -> str:
        """Mensaje cuando se activa membresía VIP"""
        exp_date_str = expiration_date.strftime("%d/%m/%Y")
        return f"""🎩 <b>Lucien:</b>

<i>Bienvenido al círculo exclusivo de Diana.</i>

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

<i>Una observación delicada... su acceso al círculo exclusivo
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

<i>Un nuevo acceso ha sido forjado para el círculo exclusivo.</i>

👑 <b>Tarifa:</b> {tariff_name}
🔗 <b>Enlace:</b> <code>{token_url}</code>

<i>Este enlace es único, como los secretos que revela.
Compártalo con quien Diana considere digno.</i>"""
    
    # ==================== PANEL ADMIN - CANALES ====================
    
    @staticmethod
    def admin_channel_registered(channel_name: str, channel_type: str) -> str:
        """Canal registrado exitosamente"""
        type_text = "vestíbulo" if channel_type == "free" else "círculo exclusivo"
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

<i>Una nueva tarifa ha sido calibrada para el círculo exclusivo.</i>

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

<i>No hay tarifas configuradas para el círculo exclusivo.
Diana aún no ha establecido los términos de acceso privilegiado...</i>

👉 <i>Use "Crear tarifa" para establecer las opciones VIP.</i>"""
        
        text = f"""🎩 <b>Lucien:</b>

<i>Las tarifas del círculo exclusivo son las siguientes:</i>

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


# Import para evitar dependencia circular
from models.models import ChannelType
