#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = False
    TESTING = False
    USE_SOCKETIO = False
    WTF_CSRF_ENABLED = True

    SECRET_KEY = os.getenv('SECRET_KEY')
    HOST = "0.0.0.0"
    PORT = int(os.getenv("PORT",443))

    PATH_PRIVATE_KEY = os.getenv('PATH_PRIVATE_KEY')
    PATH_PUBLIC_KEY = os.getenv('PATH_PUBLIC_KEY')
    PATH_CRT = os.getenv('PATH_CRT')
    PATH_CRT_APP = os.getenv('PATH_CRT_APP')
    PATH_KEY = os.getenv('PATH_KEY')
    PATH_KEY_APP = os.getenv('PATH_KEY_APP')
    MONGODB_X509 = os.getenv('MONGODB_X509')
    REFRESH_TOKEN_EXP_SECONDS = os.getenv('REFRESH_TOKEN_EXP_SECONDS')
    REFRESH_TOKEN_EXP_ADMIN = os.getenv('REFRESH_TOKEN_EXP_ADMIN')
    ACCESS_TOKEN_EXP_SECONDS = os.getenv('ACCESS_TOKEN_EXP_SECONDS')
    ACCESS_TOKEN_EXP_ADMIN = os.getenv('ACCESS_TOKEN_EXP_ADMIN')
    ACCESS_TOKEN_GLOBAL_EXP_SECONDS = os.getenv('ACCESS_TOKEN_GLOBAL_EXP_SECONDS',120)


    JWT_ISSUER = os.getenv("JWT_ISSUER", "neo-auth")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "neo-app")

    API_URL = os.getenv("API_URL", "http://localhost:5000")
    API_EXTERNAL_URL = os.getenv("API_EXTERNAL_URL", "https://localhost")
    
    MONGO_URI_CLUSTER = os.getenv("MONGO_URI_CLUSTER")
    MONGO_URI_CLUSTER_X509 = os.getenv("MONGO_URI_CLUSTER_X509")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB = os.getenv("MONGO_DB", "mdbManageToken")
    
     # ahora lista de admins
    VALID_ROLES = os.getenv("VALID_ROLES", "Admin,Manager,User").split(",")
    ROLE_SCOPES = {
        "Admin": "full_control",
        "Manager": "limited_control",
        "User": "read_only"
    }
    CORS_ORIGINS = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "https://localhost:443",
        "http://127.0.0.1:443"
    ]
    USE_SOCKETIO = False
    SOCKETIO_PING_INTERVAL = 25
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_LOGGER = False
    RUN_SHELL = os.getenv('RUN_SHELL')

class DevConfig(Config):
    DEBUG = True
    TESTING = True

class ProdConfig(Config):
    USE_SOCKETIO = True
    WTF_CSRF_ENABLED = True