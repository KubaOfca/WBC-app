import os
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
socket = SocketIO()


def create_app():
    app = Flask(__name__)
    app.secret_key = "xyz"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://postgres:postgres@localhost:5432/postgres"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"

    db.init_app(app)

    migrate = Migrate(app, db)

    session = Session()
    session.init_app(app)
    socket.init_app(app)
    from .home import home_views
    from .project import project_views
    from .auth import auth

    app.register_blueprint(home_views, url_prefix="/")
    app.register_blueprint(project_views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    from .models import User, Project, Image

    create_database(app)
    initialize_ml_models(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    with app.app_context():
        db.create_all()
        db.session.commit()
        print("DB created!")


def initialize_ml_models(app):
    from .models import MlModels
    with app.app_context():
        # Ensure this runs only if MlModels table is empty
        if not MlModels.query.first():  # Check if table is empty
            base_path = Path(__file__).parent.parent / "ml_models"
            for model_path in os.listdir(base_path):
                full_model_path = base_path / model_path
                db.session.add(
                    MlModels(model=str(full_model_path), name=model_path)
                )
            db.session.commit()
            print("MlModels table initialized!")
