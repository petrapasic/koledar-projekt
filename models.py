# models.py - Updated with user associations

from database import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # Relationships
    members = relationship('Member', backref='user', lazy=True, cascade='all, delete-orphan')
    tasks = relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(7), default='#6366f1')
    
    # Foreign key to associate with user
    user_id = db.Column(db.Integer, ForeignKey('user.id'), nullable=False)
    
    # Relationship
    tasks = relationship('Task', backref='member', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)  # "HH:MM"
    end_time = db.Column(db.String(5), nullable=False)    # "HH:MM"
    notes = db.Column(db.Text)

    
    # Foreign keys
    member_id = db.Column(db.Integer, ForeignKey('member.id'), nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('user.id'), nullable=False)