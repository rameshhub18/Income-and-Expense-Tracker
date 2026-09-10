"""
=============================================
  DhanFlow - Personal Income & Expense Tracker — Flask App
  Entry point: python app.py
=============================================
"""

from flask import Flask
from config.database import init_db
from routes.auth          import auth_bp
from routes.dashboard     import dashboard_bp
from routes.api           import api_bp
from routes.notifications import notifications_bp
from routes.categories    import categories_bp
from routes.budget        import budget_bp
from routes.reports       import reports_bp
from routes.backup        import backup_bp
from routes.reset         import reset_bp

app = Flask(__name__, template_folder="templates", static_folder="static")

# Secret key for sessions (change this in production!)
app.secret_key = "change-this-to-a-random-secret-key-in-production"

# Custom Jinja filters
app.jinja_env.filters['abs'] = abs

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(notifications_bp)
app.register_blueprint(categories_bp)
app.register_blueprint(budget_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(reset_bp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
