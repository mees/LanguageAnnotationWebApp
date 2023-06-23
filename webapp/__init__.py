from os import path

from flask import Flask, session
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import yaml
import pathlib
import os
from .helpers.data_utils import DataManager

db = SQLAlchemy()
DB_NAME = "database.db"


def read_tasks(task_file):
    print("task_file: ", task_file)
    file_dir = pathlib.Path(__file__).parent.resolve()
    file = file_dir / ("helpers/"+task_file+".yaml")
    with open(file.as_posix(), "r") as stream:
        try:
            tasks = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return tasks


def read_colors():
    file_dir = pathlib.Path(__file__).parent.resolve()
    file = file_dir / "helpers/colors.yaml"
    with open(file.as_posix(), "r") as stream:
        try:
            colors = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return colors


# Loading videos from
tasks = read_tasks("tasks")
colors = read_colors()
data_path = "/var/www/LanguageAnnotationApp/500k_all_tasks_dataset_15hz"
data_manager = DataManager(data_path, n_frames=64, grip_pt_h=False)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "hjshjhdjah kjshkjdhjs"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"
    db.init_app(app)

    from .helpers.annotator import annotator
    from .helpers.auth import auth
    from .helpers.views import views

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(annotator, url_prefix="/")

    from .helpers.models import User

    create_database(app)

    login_manager = LoginManager()
    login_manager.session_protection = "strong"
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    if not path.exists("webapp/" + DB_NAME):
        db.create_all(app=app)

        print("Created Database!")
