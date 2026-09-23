from flask import Flask
from flask_cors import CORS

from routes.analyze import analyze_bp
from routes.auth import auth_bp
from routes.history import history_bp
from routes.admin import admin_bp
from routes.github import github_bp


app = Flask(__name__)

CORS(app)


# =========================================================
# REGISTER BLUEPRINTS
# =========================================================

app.register_blueprint(analyze_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(history_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(github_bp)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return {
        "message": "AI Bug Analyzer Backend is running"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/api/health")
def health():

    return {
        "status": "success",
        "message": "Backend is working"
    }


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )