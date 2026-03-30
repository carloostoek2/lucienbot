# 🚀 Guía de Despliegue - Lucien Bot

Esta guía te ayudará a desplegar Lucien Bot en Railway de forma rápida y sencilla.

---

## 📋 Requisitos Previos

1. Cuenta en [Railway](https://railway.app) (gratis)
2. Cuenta en [GitHub](https://github.com)
3. Bot de Telegram creado con [@BotFather](https://t.me/BotFather)
4. IDs de administradores (obtener con [@userinfobot](https://t.me/userinfobot))

---

## 🛤️ Opción 1: Despliegue en Railway (Recomendado)

### Paso 1: Preparar el Repositorio

```bash
# 1. Crear repositorio en GitHub
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/lucienbot.git
git push -u origin main
```

### Paso 2: Configurar Railway

1. Ve a [Railway Dashboard](https://railway.app/dashboard)
2. Click en **"New Project"**
3. Selecciona **"Deploy from GitHub repo"**
4. Autoriza Railway y selecciona tu repositorio
5. Railway detectará automáticamente la configuración

### Paso 3: Configurar Variables de Entorno

En el dashboard de Railway, ve a tu proyecto → **Variables**:

```bash
# OBLIGATORIAS
BOT_TOKEN=tu_token_de_botfather
ADMIN_IDS=tu_id,otro_admin_id

# BASE DE DATOS (Railway proporciona PostgreSQL automáticamente)
# Si usas PostgreSQL de Railway, la variable DATABASE_URL se crea sola
# Si usas SQLite:
DATABASE_URL=sqlite:///lucien_bot.db

# OPCIONALES
TIMEZONE=America/Mexico_City
CREATOR_USERNAME=dianita
VIP_CHANNEL_ID=@tu_canal_vip
FREE_CHANNEL_ID=@tu_canal_gratuito
```

### Paso 4: Deploy

1. Railway hará deploy automático al detectar cambios
2. Ve a la pestaña **"Deployments"** para ver el estado
3. Los logs aparecen en **"Logs"**

### Paso 5: Verificar

```bash
# En Telegram, envía /start a tu bot
# Deberías recibir el mensaje de bienvenida de Lucien
```

---

## 🖥️ Opción 2: VPS (Servidor Propio)

### Requisitos del Servidor

- Ubuntu 20.04+ / Debian 11+
- Python 3.11+
- 512MB RAM mínimo
- 1GB espacio en disco

### Instalación

```bash
# 1. Conectar al servidor
ssh usuario@tu-servidor.com

# 2. Actualizar sistema
sudo apt update && sudo apt upgrade -y

# 3. Instalar Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# 4. Clonar repositorio
git clone https://github.com/carlostoek/lucienbot.git
cd lucienbot

# 5. Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# 6. Instalar dependencias
pip install -r requirements.txt

# 7. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus valores

# 8. Ejecutar bot
python bot.py
```

### Ejecutar como Servicio (systemd)

```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/lucienbot.service
```

Contenido:
```ini
[Unit]
Description=Lucien Bot - Telegram Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/home/tu_usuario/lucienbot
Environment=PATH=/home/tu_usuario/lucienbot/venv/bin
ExecStart=/home/tu_usuario/lucienbot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lucienbot
sudo systemctl start lucienbot

# Ver estado
sudo systemctl status lucienbot

# Ver logs
sudo journalctl -u lucienbot -f
```

---

## 🐳 Opción 3: Docker (Avanzado)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Ejecutar
CMD ["python", "bot.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  bot:
    build: .
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    
  # Opcional: PostgreSQL
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: lucien
      POSTGRES_PASSWORD: tu_password
      POSTGRES_DB: lucienbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

Ejecutar:
```bash
docker-compose up -d
```

---

## 📊 Monitoreo

### Logs en Railway

```bash
# Ver logs en tiempo real
railway logs -f
```

### Healthcheck (Opcional)

Agregar a `bot.py`:

```python
from aiogram import types

@dp.message(Command("health"))
async def health_check(message: types.Message):
    """Endpoint para healthcheck"""
    if message.from_user.id in bot_config.ADMIN_IDS:
        await message.answer("✅ Lucien está operativo")
```

---

## 🔧 Troubleshooting

### Problema: Bot no responde

```bash
# Verificar logs
railway logs

# Verificar token
# Asegúrate de que BOT_TOKEN sea correcto

# Verificar que el bot no esté duplicado
# Solo una instancia debe ejecutarse
```

### Problema: Error de base de datos

```bash
# Si usas SQLite en Railway, asegúrate de que
# el directorio tenga permisos de escritura

# Mejor opción: usar PostgreSQL
# Railway crea una instancia automáticamente
```

### Problema: Variables de entorno no cargan

```bash
# Verificar que las variables estén configuradas
railway variables

# Reiniciar deploy
railway up
```

---

## 🔄 Actualizaciones

### Actualizar en Railway

```bash
# 1. Hacer cambios localmente
git add .
git commit -m "Nueva funcionalidad"
git push origin main

# 2. Railway detecta automáticamente y redeploya
```

### Actualizar en VPS

```bash
# 1. Entrar al directorio
cd ~/lucienbot

# 2. Actualizar código
git pull origin main

# 3. Actualizar dependencias
source venv/bin/activate
pip install -r requirements.txt

# 4. Reiniciar servicio
sudo systemctl restart lucienbot
```

---

## 💰 Costos

| Plataforma | Costo | Recomendación |
|------------|-------|---------------|
| Railway | $5/mes (starter) | ✅ Recomendado |
| Railway (free) | $0 (límites) | Para pruebas |
| VPS (DigitalOcean) | $6/mes | Alternativa |
| VPS (AWS/GCP) | Variable | Enterprise |

---

## 📞 Soporte

- Issues: [GitHub Issues](https://github.com/carlostoek/lucienbot/issues)
- Telegram: Contactar a desarrollador

---

**¡Lucien está listo para servir a Diana!** 🎩✨
