# 🔐 app_manage_token

Gestor avanzado de autenticación y autorización con **JWT** en Flask.  
Optimizado para **seguridad**, **escalabilidad** y **trazabilidad de sesiones**.

---

## 🚀 Características

- ✅ **JWT con RS256** (claves pública/privada)
- 🔄 **Refresh Tokens** con control de reuso
- 📡 Control de **sesiones activas** por dispositivo, IP y User-Agent
- 🛡️ Bloqueo temporal ante intentos fallidos
- 📊 Registro de auditoría en **MongoDB**
- ⚡ WebSockets con Flask-SocketIO para actualizaciones en tiempo real
- 👨‍💻 Soporte para diferentes roles (Admin, User, etc.)
---

## 📦 Requisitos

- Python 3.10+
- MongoDB
- Node.js y npm (para los assets de frontend si aplican)
- Certificados SSL (opcional, para WebSocket seguro wss)
---

## 📁 Estructura del Proyecto
```
├── app/
│ ├── main.py # Punto de entrada principal
│ ├── config.py # Configuración desde variables de entorno
│ ├── extensions.py # Bootstrap, CORS, etc.
│ ├── utils/ # Funciones auxiliares (ej: acceso DB)
│ └── backend/ # Endpoints API (ej: login, logout)
│ └── frontend/ # Rutas frontend (opcional)
│ └── midleware/ # Headers seguros
│ └── templates/ # Vistas en html
├── requirements.txt
├── setup.py
├── .env # Variables de entorno
```
## ⚙️ Variables
```
FLASK_ENV=development
SECRET_KEY=clave_super_segura
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem
MONGO_URI=mongodb://localhost:27017/manage_token
TOKEN_EXP_MINUTES=15
REFRESH_TOKEN_EXP_DAYS=7
```