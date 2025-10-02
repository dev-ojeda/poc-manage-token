#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
from flask import Blueprint, redirect, render_template, url_for

from app.auth.services.user_service import UserService
from app.midleware.jwt_guard import decode_token_from_header


frontend_bp = Blueprint(
    "frontend",
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates",
)


@frontend_bp.route("/")
def login():
    # Revisar si ya viene un JWT
    decoded, error = decode_token_from_header(expected_type="access")
    if not error and decoded:
        username = decoded.get("sub")
        user_service = UserService()
        user = user_service.get_user_by_username(username=username)

        if user and user.rol == "Admin":
            return redirect(url_for("frontend.admin_page"))
        return redirect(url_for("frontend.dash_page"))

    # Si no hay token → mostrar login
    return render_template(
        "login.html",
        title="Home Page"
    )


@frontend_bp.route("/.well-known/appspecific/com.chrome.devtools.json")
def devtools_stub():
    return {}, 204  # No Content


@frontend_bp.route("/dashboard")
def dash_page():
    return render_template(
        "dashboard_user.html",
        title="Dashboard User"
    )


@frontend_bp.route("/admin/dashboard")
def admin_page():
    return render_template(
        "administrar.html",
        title="Dashboard Admin"
    )
