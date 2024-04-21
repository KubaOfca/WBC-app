from flask_login import UserMixin
from sqlalchemy.orm import relationship

from . import db


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    first_name = db.Column(db.String(150))
    password = db.Column(db.String(150))
    secret_key = db.Column(db.String(32))


class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    date = db.Column(db.DateTime(timezone=True))
    image = relationship("Image", backref="user", cascade='all, delete')


class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    name = db.Column(db.String(100))
    date = db.Column(db.DateTime(timezone=True))
    image = db.Column(db.LargeBinary)
    annotated_image = db.Column(db.LargeBinary, default=None)


class Stats(db.Model):
    __tablename__ = 'stats'
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, default=0)
    basophile = db.Column(db.Integer, default=0)
    eosinophile = db.Column(db.Integer, default=0)
    lymphoblast = db.Column(db.Integer, default=0)
    lymphocyte = db.Column(db.Integer, default=0)
    monocyte = db.Column(db.Integer, default=0)
    myeloblast = db.Column(db.Integer, default=0)
    neutrophile_band = db.Column(db.Integer, default=0)
    neutrophile_segment = db.Column(db.Integer, default=0)
    normoblast = db.Column(db.Integer, default=0)
