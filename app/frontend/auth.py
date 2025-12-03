import base64
from flask import Blueprint, jsonify, redirect, render_template, request, send_from_directory, url_for
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity
from app.auth import get_auth_services
from app.config import Config
from app.helpers.helpers import log_and_response
from app.logging_config import get_logger
from app.midleware.jwt_guard import decode_token_from_header
bp = Blueprint(
    "frontend",
    __name__,
    static_folder="static",
    static_url_path="/frontend/static",
    template_folder="templates"
)
server = Fido2Server(PublicKeyCredentialRpEntity(name=Config.FIDO2_RP_NAME, id=Config.FIDO2_RP_ID))
services = get_auth_services()
sessions = {}
users = {}  # username -> {password, webauthn}
logger = get_logger("AUTH")
# ============================
# VISTAS PÚBLICAS
# ============================
# ----------------------
# Rutas de interfaz
# ----------------------
@bp.route("/")
def login():
    # Revisar si ya viene un JWT
    # decoded, error = decode_token_from_header(expected_type="access")
    # if not error and decoded:
    #     username = decoded.get("sub")
      
    #     user = services.user_service.get_user_by_username(username=username)

    #     if user and user.rol == "Admin":
    #         return redirect(url_for("frontend.admin_page"))
    #     return redirect(url_for("frontend.dash_page"))

    # Si no hay token → mostrar login
    return render_template(
        "auth/login.html",
        title="Home Page"
    )

# @bp.route("/")
# def index():
#     if sessions.get("user"):
#         return redirect(url_for("frontend.dashboard"))
#     return redirect(url_for("frontend.register"))

# @bp.route("/login")
# def login():
#     if sessions.get("user"):
#         return redirect(url_for("frontend.dashboard"))
#     return render_template("auth/index.html")

@bp.route("/register")
def register():
    if sessions.get("user"):
        return redirect(url_for("frontend.dashboard"))
    return render_template("auth/register.html")

@bp.route("/dashboard")
def dashboard():
    if not sessions.get("user"):
        return redirect(url_for("frontend.login"))
    return render_template("auth/dashboard.html", username=sessions["user"])

@bp.route("/auth/logout", methods=["POST"])
def logout():
    sessions.clear()
    return redirect(url_for("frontend.login"))

# ============================
# REGISTRO USUARIO + WebAuthn
# ============================
@bp.route("/auth/register", methods=["POST"])
def register_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Campos incompletos"}), 400
    if username in users:
        return jsonify({"error": "Usuario ya existe"}), 409

    users[username] = {"password": password, "webauthn": None}
    sessions["user"] = username
    return jsonify({"status": "ok"}), 201

@bp.route("/auth/webauthn/options")
def webauthn_options():
    username = sessions.get("user")
    try:
        options, state = services.webauthn_service.get_registration_options(username)
        sessions["webauthn_state"] = state["challenge"]
        logger.debug(options)
        return jsonify(options), 200
    except Exception as e:
        return log_and_response(False, str(e), "OPTIONS_ERROR", 500, logger=logger)

@bp.route("/auth/webauthn/register", methods=["POST"])
def register_webauthn_credential():
    data = request.get_json()
    username = sessions.get("user")
    data["cred"]["state"] = sessions["webauthn_state"]
    try:
        result = services.webauthn_service.register_credential(data, username)
        return jsonify(result), 201 if result["success"] else 500
    except Exception as e:
        return log_and_response(False, str(e), "REGISTER_ERROR", 500, logger=logger)

# ============================
# LOGIN USUARIO + WebAuthn
# ============================
@bp.route("/auth/user/login", methods=["POST"])
def login_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = users.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Credenciales inválidas"}), 401

    sessions["user"] = username
    return jsonify({"status": "ok"}), 200

@bp.route("/auth/webauthn/assertion-options", methods=["GET"])
def assertion_options():
    username = request.args.get("username")

    creds = []
    if username:
        creds = services.webauthn_service.get_user_credentials(username=username) or []

    options, state = server.authenticate_begin(creds)
    sessions["webauthn_state"] = state  # <--- singular

    def buf2b64u(buf):
        if isinstance(buf, str):
            buf = buf.encode("utf-8")
        return base64.urlsafe_b64encode(buf).rstrip(b"=").decode("utf-8")

    options_json = {
        "challenge": buf2b64u(options.public_key.challenge),
        "rpId": options.public_key.rp_id,
        "allowCredentials": [
            {"id": buf2b64u(c.id), "type": c.type}
            for c in (options.public_key.allow_credentials or [])
        ],
        "timeout": options.public_key.timeout or 120000,
        "userVerification": options.public_key.user_verification or "required",
    }

    return jsonify({"publicKey": options_json})

@bp.route("/auth/webauthn/login", methods=["POST"])
def webauthn_login():
    data = request.get_json()
    assertion = data.get("assertion")
    username = data.get("username")
    if not assertion:
        return jsonify({"error": "Datos incompletos"}), 400

    state = sessions.pop("webauthn_state", None)
    if not state:
        return jsonify({"error": "Estado de autenticación no encontrado"}), 400

    cred = services.webauthn_service.authenticate(assertion)
    if not cred:
        return jsonify({"error": "Credencial no encontrada"}), 404
    username = username or cred.username

    try:
        server.authenticate_complete(
            state=state,
            credentials=[{"id": base64.urlsafe_b64decode(cred.raw_id + "=="), "public_key": cred.pubkey, "sign_count": cred.sign_count}],
            credential_id=base64.urlsafe_b64decode(assertion["id"] + "=="),
            client_data_json=base64.urlsafe_b64decode(assertion["response"]["clientDataJSON"] + "=="),
            authenticator_data=base64.urlsafe_b64decode(assertion["response"]["authenticatorData"] + "=="),
            signature=base64.urlsafe_b64decode(assertion["response"]["signature"] + "==")
        )
    except Exception as e:
        return jsonify({"error": f"Autenticación fallida: {e}"}), 401

    cred.sign_count += 1
    services.webauthn_service.update_sign_count(cred._id, cred.sign_count)
    sessions["user"] = username
    return jsonify({"status": "ok", "username": username})
