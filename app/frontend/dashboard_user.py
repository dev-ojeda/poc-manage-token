from flask import Blueprint, render_template, request

bp = Blueprint(
    "user_dashboard",
    __name__,
    static_folder="static",
    static_url_path="/frontend/static",
    template_folder="templates",
    url_prefix="/user"
)

@bp.get("/dashboard")
def dashboard():
    """Vista principal del dashboard del usuario."""
    return render_template(
        "dashboard/user/dashboard.html",
        title="Dashboard User",
        show_sidebar=True
    )

# @bp.get("/partial")
# def partial():
#     """Vista parcial para contenido dinámico."""
#     return render_template("dashboard/user/dashboard_partial.html")
@bp.get("/partial")
def partial():
    view = request.args.get("view", "panel")

    mapping = {
        "panel": "dashboard/user/partials/_user_panel.html",
        "items": "dashboard/user/partials/_user_items.html",
        "chat": "dashboard/user/partials/_user_chat.html",
        "tokens": "dashboard/user/partials/_token_progress.html",
    }

    template = mapping.get(view, mapping["panel"])
    return render_template(template)
