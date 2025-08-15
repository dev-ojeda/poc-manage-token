
from flask_socketio import SocketIO


class StreamHandler:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.active = False

    def start(self, config):
        self.active = True
        print(f"[STREAM] Iniciado con config: {config}")

    def process_chunk(self, data):
        if not self.active:
            return
        # Aquí puedes manejar video, audio o datos binarios
        print(f"[STREAM] Chunk recibido: {len(data)} bytes" if isinstance(data, bytes) else data)
        # Reenviar a todos los clientes
        self.socketio.emit('stream_update', data)

    def stop(self):
        self.active = False
        print("[STREAM] Detenido")
