from flask import Flask, render_template
from flask_mail import Mail
from config import Config
from firebase_config import initialize_firebase_admin
from datetime import timedelta

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
initialize_firebase_admin()


# Import routes
from routes import main_routes, api_routes, municipal_routes, seminar_routes, service_routes, fisheries_routes, environment_routes, forest_routes, livestock_routes, permits_routes, wildlife_routes, farm_routes, payments_routes,regional_routes,superadmin_routes, national_routes

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
    app.run(host='0.0.0.0', port=5000, debug=True)
