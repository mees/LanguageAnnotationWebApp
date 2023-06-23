from flask_login import UserMixin
from sqlalchemy.sql import func

from webapp import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(25), unique=True)
    password = db.Column(db.String(25))


class Sequences(db.Model):
    seq_id = db.Column(db.Integer, primary_key=True)
    dir = db.Column(db.String(250))
    n_frames = db.Column(db.Integer)
    start_frame = db.Column(db.String(50))
    end_frame = db.Column(db.String(50))
    video_tag = db.Column(db.String(50))


class LangAnn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seq_id = db.Column(db.Integer, unique=True)
    user_id = db.Column(db.Integer)
    annotation = db.Column(db.String(50))
    task = db.Column(db.String(50))
    color_x = db.Column(db.String(50))
    color_y = db.Column(db.String(50))
