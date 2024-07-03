from . import db
from sqlalchemy.orm import relationship, backref

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_picture = db.Column(db.String(200), nullable=True)

    preferences = relationship('UserPreference', backref='user', cascade="all, delete-orphan")

class UserPreference(db.Model):
    __tablename__ = 'user_preference'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    genre = db.Column(db.String(50), nullable=False)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdbID = db.Column(db.Integer, unique=True, nullable=False)
    movie_title = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(300))
    release_date = db.Column(db.String(50))
    vote_average = db.Column(db.Float)
    poster_path = db.Column(db.String(300))
    budget = db.Column(db.Float)
    overview = db.Column(db.Text)
    director = db.Column(db.String(200))
    cast = db.Column(db.String(500))

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=False)
    tmdbID = db.Column(db.Integer, db.ForeignKey('movie.tmdbID'), nullable=False)
    rating = db.Column(db.Float)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.tmdbID'), nullable=False)
    feedback = db.Column(db.String(50), nullable=False) 
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())