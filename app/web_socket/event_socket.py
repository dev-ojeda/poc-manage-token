# app/web_socket/eventos.py
from flask import Blueprint
from flask_socketio import emit, join_room
from icecream import ic
from app import socketio

socketio_bp = Blueprint("socketio_bp", __name__)
# Evento para forzar logout en un cliente específico
def notificar_revocacion(username):
    socketio.emit(
        "session_revoked",
        {"message": "Tu sesión ha sido cerrada por seguridad"},
        room=f"user_{username}"
    )

@socketio.on("join")
def join_room_user(data):
    """El cliente se une a una 'room' única basada en su user_id."""
    username = data.get("username")
    if username:
        join_room(f"user_{username}")
        emit("joined", {"room": f"user_{username}"})

# Evento WebSocket
@socketio.on("mensaje")
def manejar_mensaje(data):
    ic(f"📩 Mensaje recibido: {data}")
    emit("respuesta", {"msg": f"Servidor recibió: {data}"})