from flask import Flask, render_template
from flask_mail import Mail
from config import Config
import firebase_admin
from firebase_admin import credentials
from datetime import timedelta
import os
import json

app = Flask(__name__)
app.config.from_object(Config)

# Session configuration
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False  # Set True if using HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Flask-Mail
mail = Mail(app)

# Initialize Firebase
def _initialize_firebase_admin():
    if firebase_admin._apps:
        return

    # Preferred for cloud deploy: JSON content in env var.
    creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if creds_json:
        cred = credentials.Certificate(json.loads(creds_json))
        firebase_admin.initialize_app(cred)
        return

    # Fallback: credentials file path from config/env.
    creds_path = Config.FIREBASE_CREDENTIALS or 'firebase-credentials.json'
    if os.path.exists(creds_path):
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred)
        return

    raise RuntimeError(
        "Firebase credentials not found. Set FIREBASE_CREDENTIALS_JSON (recommended for cloud) "
        "or provide FIREBASE_CREDENTIALS file path."
    )


_initialize_firebase_admin()


# Import routes
from routes import main_routes, api_routes, municipal_routes, seminar_routes, service_routes, fisheries_routes, environment_routes, forest_routes, livestock_routes, permits_routes, wildlife_routes, farm_routes, payments_routes,regional_routes,superadmin_routes, national_routes, municipal_api_logs

# Initialize mail in api_routes
api_routes.init_mail(mail)

# Register blueprints
app.register_blueprint(main_routes.bp)
app.register_blueprint(api_routes.bp)
app.register_blueprint(municipal_routes.bp)
app.register_blueprint(seminar_routes.bp)
app.register_blueprint(service_routes.bp)
app.register_blueprint(fisheries_routes.bp)
app.register_blueprint(environment_routes.bp)
app.register_blueprint(forest_routes.bp)
app.register_blueprint(livestock_routes.bp)
app.register_blueprint(permits_routes.bp)
app.register_blueprint(wildlife_routes.bp)
app.register_blueprint(farm_routes.bp)
app.register_blueprint(payments_routes.bp)
app.register_blueprint(regional_routes.bp)
app.register_blueprint(superadmin_routes.bp)
app.register_blueprint(national_routes.bp)
app.register_blueprint(municipal_api_logs.bp)


# Jinja filter for date formatting
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%b %d, %Y'):
    from datetime import datetime
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except Exception:
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                return format  # Return the format string if parsing fails
    try:
        return value.strftime(format)
    except Exception:
        return format

# Route for disabled account page
@app.route('/account-disabled')
def account_disabled():
    return render_template('account-disabled.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
