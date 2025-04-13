from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    email_drafts = db.relationship('EmailDraft', backref='author', lazy='dynamic')
    reports = db.relationship('Report', backref='author', lazy='dynamic')
    chat_sessions = db.relationship('ChatSession', backref='user', lazy='dynamic')
    preferences = db.relationship('UserPreference', backref='user', uselist=False)
    auto_replies = db.relationship('AutoReply', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class EmailDraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    recipient = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<EmailDraft {self.subject}>'


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    source_data = db.Column(db.Text)  # Storing input data used to generate the report
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Report {self.title}>'


class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship with ChatMessage
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic')
    
    def __repr__(self):
        return f'<ChatSession {self.title}>'


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)  # True if message is from user, False if from AI
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    
    def __repr__(self):
        return f'<ChatMessage {"User" if self.is_user else "AI"}: {self.content[:30]}...>'


class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Email preferences
    email_tone = db.Column(db.String(50), default="professional")  # professional, friendly, formal, etc.
    email_length = db.Column(db.String(50), default="medium")  # short, medium, long
    email_signature = db.Column(db.Text)
    
    # Report preferences
    report_format = db.Column(db.String(50), default="detailed")  # concise, detailed, bullet-points
    report_tone = db.Column(db.String(50), default="formal")
    
    # Chat preferences
    chat_tone = db.Column(db.String(50), default="helpful")
    
    # Auto-reply preferences
    auto_reply_tone = db.Column(db.String(50), default="professional")
    auto_reply_style = db.Column(db.String(50), default="concise")
    auto_reply_signature = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<UserPreference for user_id {self.user_id}>'


class AutoReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_message = db.Column(db.Text, nullable=False)
    reply_subject = db.Column(db.String(200))
    reply_content = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text)  # Additional context provided by user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<AutoReply to message: {self.original_message[:50]}...>'