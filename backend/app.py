import shutil

from flask import Flask, jsonify

from config import Config
from extensions import cors, jwt
from shared.pptx_utils import find_soffice

from features.auth.routes import auth_bp
from features.clients.routes import clients_bp
from features.dashboard.routes import dashboard_bp
from features.notifications.routes import notifications_bp
from features.presentations.routes import presentations_bp
from features.templates_library.routes import templates_bp
from features.users.routes import users_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    cors.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(presentations_bp)

    @app.route("/")
    def root():
        return jsonify({"message": "Propale API v1"})

    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "libreoffice": find_soffice() or "not found",
            "pdftoppm":    shutil.which("pdftoppm") or "not found",
            "generation_mode": "placeholder-replacement",
        })

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
