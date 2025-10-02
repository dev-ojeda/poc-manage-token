#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask_bootstrap import Bootstrap
from flask_cors import CORS
import flask_limiter
from flask_socketio import SocketIO
from flask_limiter import Limiter, RequestLimit
from flask_limiter.util import get_remote_address
bootstrap = Bootstrap()
cors = CORS()
socketio = SocketIO()
limiter  = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
