#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional

from flask import request
from flask_socketio import Namespace, emit
from icecream import ic

from app import socketio  # Importar la instancia global de SocketIO

# Diccionario para mantener los usuarios y mensajes
sessions = {}
# Namespace por defecto ('/')
@socketio.on("connect")
def handle_connect() -> None:
    """
    Funcion que realiza la conexion de un namespace por defecto
    """
    ic("Cliente conectado al namespace por defecto")
    emit(
        "respuesta", {"data": "¡Bienvenido al servidor!"}
    )  # Enviar mensaje al cliente conectado


@socketio.on("disconnect")
def handle_disconnect() -> None:
    """
    Funcion que realiza la desconexion de un namespace por defecto
    """
    ic("Cliente desconectado del namespace por defecto")


# Evento personalizado
@socketio.on("mi_evento")
def handle_mi_evento(data) -> None:
    """
    Crea un evento para ser invocado en un namespace por defecto
    Args:
        data (json): Datos que envia del mensaje de un receptor
    """
    ic("Mensaje recibido al namespace por defecto")
    chat_mensaje = {
        "msg": "Mensaje Recibido",
        "username": data["username"],
        "enviado": f"{datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}",
    }
    # Responder al cliente
    emit("respuesta", chat_mensaje)
    emit('chat_web', chat_mensaje)

@socketio.on('mensaje_desde_tk')
def handle_mensaje(data):
    ic(f"[Backend] Recibido desde Tkinter: {data}")
    chat_mensaje = {
        "msg": data["msg"],
        "username": data["username"],
        "enviado": f"{datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}",
    }
    emit("respuesta", chat_mensaje)
    emit('chat_web', chat_mensaje)
@socketio.on_error_default  # capturar errores generales
def default_error_handler(e):
    print(f"💥 Error: {str(e)}")
# Namespace personalizado ('/chat')
class ChatNamespace(Namespace):
    def on_connect(self) -> None:
        ic("Mensaje recibido al namespace /Chat")
        client_id: str = request.sid
        sessions[client_id] = {"data": {}}
        emit("respuesta", {"msg": "Conexión exitosa desde Flask (/tk)"})

    def on_disconnect(self) -> None:
        client_id: str = request.sid

        if client_id in sessions:
            chat_mensaje = {
                "username": sessions[client_id]["data"]["username"],
                "msg": "Cliente desconectado",
            }

            emit("respuesta", chat_mensaje, broadcast=True, namespace="/chat")
            del sessions[client_id]

    def mensaje_desde_tk(self, data: Optional[dict] = None) -> None:
        ic(f"[Backend] Recibido desde Tkinter: {data}")
        chat_mensaje = {
            "msg": data["msg"],
            "username": data["username"],
            "enviado": f"{datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}",
        }
        emit("respuesta", chat_mensaje, broadcast=True, namespace="/chat")
        emit('chat_web', chat_mensaje, broadcast=True, namespace="/chat")

    def on_message(self, data: Optional[dict] = None) -> None:
        client_id: str = request.sid
        ic("Mensaje recibido al namespace /Chat",data)
        chat_mensaje = {
            "msg": data["msg"],
            "username": data["username"],
            "enviado": f"{datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}",
        }
        if client_id in sessions:
            # Almacén para las sesiones
            sessions[client_id]["data"].update(chat_mensaje)
            emit("respuesta", chat_mensaje, broadcast=True, namespace="/chat")
            emit("server_message", chat_mensaje, broadcast=True, namespace="/chat")

    # Escuchar eventos personalizados
    def on_client_message(self, data: Optional[dict] = None) -> None:
        client_id: str = request.sid
        chat_mensaje = {
            "username": data["username"],
            "msg": data["msg"],
        }
        ic("Mensaje enviado al namespace /Chat de Tkinter",chat_mensaje)
        if client_id in sessions:
            sessions[client_id]["data"].update(chat_mensaje)
            emit("respuesta", chat_mensaje, broadcast=True, namespace="/chat")

    # Crea un evento. para enviar mensajes al cliente.
    socketio.on_event("message_cliente", on_client_message, namespace="/chat")


# Namespace personalizado ('/chat')
class QueueNamespace(Namespace):
    def on_connect(self) -> None:
        client_id: str = request.sid
        sessions[client_id] = {"data": {}}
        ic(f"Cliente conectado al namespace /chat: {client_id}")

    def on_disconnect(self) -> None:
        ic("Cliente desconectado del namespace /chat")
        client_id: str = request.sid

        if client_id in sessions:
            chat_mensaje = {
                "username": sessions[client_id]["data"]["username"],
                "msg": "Cliente desconectado",
            }
            socketio.emit("respuesta", chat_mensaje, namespace="/chat")
            del sessions[client_id]

    def on_mensaje(self, data) -> None:
        client_id: str = request.sid
        chat_mensaje = {"username": data["username"], "msg": data["msg"]}
        if client_id in sessions:
            # Almacén para las sesiones
            sessions[client_id]["data"].update(chat_mensaje)
            socketio.emit("respuesta", chat_mensaje, namespace="/chat")

    # Escuchar eventos personalizados
    def on_client_message(self, data: Optional[dict] = None) -> None:
        client_id: str = request.sid
        chat_mensaje = {
            "username": data["username"],
            "msg": data["msg"],
        }
        if client_id in sessions:
            sessions[client_id]["data"].update(chat_mensaje)
            socketio.emit("message_cliente", chat_mensaje, namespace="/chat")

    # Crea un evento. para enviar mensajes al cliente.
    socketio.on_event("message_cliente", on_client_message, namespace="/chat")


# Registrar el namespace personalizado
socketio.on_namespace(ChatNamespace("/chat"))
# socketio.on_namespace(ChatNamespace('/queue'))
