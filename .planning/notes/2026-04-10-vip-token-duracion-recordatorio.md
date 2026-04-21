---
date: "2026-04-10 15:42"
promoted: false
---

Hay que agregar un dato más en la vista de la generación de tokens VIP, en donde el bot responde con el token que se generó para darle el acceso a un nuevo suscriptor VIP. Hay que agregarle de cuánto tiempo se activó el bot. Esto solamente para tener confirmación visual del tiempo que se seleccionó porque de pronto puede ser que el administrador se equivoque y haya seleccionado otra opción a la que realmente quería. Ya estando ese dato ahí, puede confirmar que es realmente la que quiere configurar.
Por otro lado, también hay que revisar si ese dato lo tiene el usuario, que ese dato a un usuario VIP cuando ingrese al canal, que el bot ya en el último paso, ya cuando entra, hay que le indique que su suscripción vence el día que le corresponde.
una funcionalidad para que el usuario del canal VIP pueda tener la posibilidad de configurar si quiere o no quiere el recordatorio del vencimiento de la suscripción. Y para esto se va a desarrollar un sistema en donde al ingreso de un usuario, cuando es de nuevo ingreso, el bot le va a indicar qué fecha vence su suscripción, de qué tiempo es la suscripción que adquirió, la fecha exacta en que termina y le va a preguntar que si quiere que le envíe un recordatorio antes de su vencimiento. El usuario podrá seleccionar sí o no. y según su respuesta, es lo que procede. Si dice que sí, pues se guarda su configuración como hasta ahora, que es que envía. Si dice que no, pues se silencia la notificación para ese usuario.
