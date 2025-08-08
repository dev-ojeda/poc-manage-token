#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import tkinter as tk
from tkinter import scrolledtext

from app.config import Config
from flask import Flask
from flask_socketio import SocketIO, emit
from icecream import ic
from socketio import Client as cliente

from app import create_app

# Configuración del backend con Flask y Flask-SocketIO
app: Flask = create_app()
app.secret_key = Config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Diccionario para mantener los usuarios y mensajes
chat_data = {"users": [], "messages": []}


# Namespace para el chat
@socketio.on("connect", namespace="/chat")
def connect():
    ic("message", {"msg": "Usuario conectado al chat."})
    emit("message", {"msg": "Usuario conectado al chat."})


@socketio.on("message", namespace="/chat")
def handle_message(data):
    chat_data["users"].append(data.get("username"))
    chat_data["messages"].append(data.get("msg"))
    ic("users", chat_data["users"])
    ic("message", chat_data["messages"])

    emit("message", data, broadcast=True, namespace="/chat")


# Ejecutar Flask en un hilo
def run_flask():
    socketio.run(app, port=5000, debug=False)


# Configuración de la interfaz gráfica con Tkinter
class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Cliente")

        # Área de texto para mostrar mensajes
        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state="disabled")
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Campo para ingresar mensajes
        self.message_entry = tk.Entry(root, width=50)
        self.message_entry.pack(padx=10, pady=5, side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", self.send_message)

        # Botón para enviar mensajes
        self.send_button = tk.Button(root, text="Enviar", command=self.send_message)
        self.send_button.pack(padx=5, pady=5, side=tk.RIGHT)

        # Conexión con el servidor Flask-SocketIO
        self.socketio_client = cliente()
        self.socketio_client.connect("http://localhost:5000")
        self.socketio_client.on("message", self.receive_message)

    def send_message(self, event=None):
        message = self.message_entry.get()
        if message:
            chat_mesage = {"username": "DESKTOP", "msg": message}
            self.socketio_client.emit("message", chat_mesage)
            self.message_entry.delete(0, tk.END)

    def receive_message(self, data):
        self.chat_area.configure(state="normal")
        self.chat_area.insert(tk.END, f"{data['username']}:{data['msg']}\n")
        self.chat_area.configure(state="disabled")
        self.chat_area.yview(tk.END)


# Iniciar el servidor Flask en un hilo separado
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# Iniciar la interfaz gráfica Tkinter
root = tk.Tk()
app = ChatApp(root)
root.mainloop()
