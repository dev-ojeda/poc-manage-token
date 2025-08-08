#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bootstrap import Bootstrap
from flask_cors import CORS
from flask_socketio import SocketIO

bootstrap = Bootstrap()
cors = CORS()
socketio = SocketIO(cors_allowed_origins="*",async_mode="eventlet")
limiter = Limiter(get_remote_address, default_limits=["10 per minute"]) # Protección de tasa (rate limiting por IP)
