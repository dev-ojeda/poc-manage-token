#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Blueprint, render_template

from midleware.jwt_guard import jwt_required_global


frontend_bp = Blueprint(
    "frontend",
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates",
)


@frontend_bp.route("/")
@jwt_required_global
def index():
    return render_template("login.html")


@frontend_bp.route('/.well-known/appspecific/com.chrome.devtools.json')
def devtools_stub():
    return {}, 204  # No Content

@frontend_bp.route("/dashboard")
def dash_page(): 
    return render_template("dashboard_user.html")

@frontend_bp.route("/admin/dashboard")
def admin_page(): 
    return render_template("admin_panel.html")


