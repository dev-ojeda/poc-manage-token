from flask import Blueprint, render_template
import app.frontend
bp = Blueprint("admin_dashboard", __name__, url_prefix="/admin")

@bp.route("/dashboard")
def dashboard():
    return render_template("dashboard/admin/dashboard.html", title="Dashboard Admin", show_sidebar=True)

@bp.route("/partial")
def partial():
    return render_template("dashboard/admin/dashboard_partial.html")

