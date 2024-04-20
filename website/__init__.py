from os import path

from flask import Flask
from flask_login import LoginManager
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
DB_NAME = "database.db"
socket = SocketIO()


def create_app():
    app = Flask(__name__)
    app.secret_key = "xyz"
    app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{DB_NAME}'
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    db.init_app(app)
    session = Session()
    session.init_app(app)
    socket.init_app(app)
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    from .models import User, Project, Image

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    if not path.exists(path.join('instance', DB_NAME)):
        with app.app_context():
            db.create_all()
            print("DB created!")
