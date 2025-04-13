import os
import logging
import jinja2
import markupsafe
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_migrate import Migrate

# After creating your app and db objects

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
migrate = Migrate(app, db)

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///communications.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Set up flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# initialize the app with the extension
db.init_app(app)

# Add nl2br Jinja filter (converts newlines to <br> tags)
@app.template_filter('nl2br')
def nl2br(value):
    return markupsafe.Markup(value.replace('\n', '<br>'))

# Set Gemini API key from environment variables
app.config["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
# Set Groq API key from environment variables (as fallback)
app.config["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY", "")

# Import routes after app initialization to avoid circular imports
with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models
    import routes
    
    db.create_all()

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
