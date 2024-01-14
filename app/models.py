from . import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    business = db.relationship('Business', backref='user', uselist=False)
    goals = db.relationship('Goal', backref='user')
    preferences = db.relationship('Preference', backref='user')

class Business(db.Model):
    __tablename__ = 'businesses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    image_url = db.Column(db.String(255))
    subscription = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    rank = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class Preference(db.Model):
    __tablename__ = 'preferences'
    id = db.Column(db.Integer, primary_key=True)
    metric = db.Column(db.String(120))
    rank = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

