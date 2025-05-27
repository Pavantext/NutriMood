from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()  # Do NOT pass app here

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    conversations = db.relationship('Conversation', backref='user', lazy=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender = db.Column(db.String(10))  # 'user' or 'bot'
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    recommended_foods = db.Column(db.JSON)  # Store as JSON if needed