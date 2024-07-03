import os
import random
import requests
from PIL import Image
from io import BytesIO
import numpy as np
from flask import url_for, current_app
from werkzeug.utils import secure_filename
from .models import Movie, UserPreference
from tmdbv3api import TMDb, Movie as TMDbMovie

tmdb = TMDb()
tmdb.api_key = os.getenv('TMDB_API_KEY', 'default_api_key_if_none_found')

def download_movie_posters():
    movies = Movie.query.all()
    poster_dir = 'static/posters/'
    if not os.path.exists(poster_dir):
        os.makedirs(poster_dir)
    
    for movie in movies:
        url = f"https://image.tmdb.org/t/p/original{movie.poster_path}"
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img.save(os.path.join(poster_dir, f"{movie.tmdbID}.jpg"))

def prepare_metadata():
    movies = Movie.query.all()
    metadata = []
    for movie in movies:
        metadata.append({
            'tmdbID': movie.tmdbID,
            'genre': movie.genre,
            'vote_average': movie.vote_average
        })
    return metadata

def load_image(image_path):
    img = Image.open(image_path)
    img = img.resize((150, 150))
    img = np.array(img) / 255.0
    img = np.expand_dims(img, axis=0)
    return img

def get_random_movie_poster():
    try:
        tmdb_movie = TMDbMovie()
        popular = tmdb_movie.popular()
        random_movie = random.choice(popular)
        poster_path = random_movie.poster_path
        if poster_path:
            return f"https://image.tmdb.org/t/p/original{poster_path}"
    except Exception as e:
        print(f"Failed to retrieve popular movies: {e}")
    return url_for('static', filename='images/default_poster.jpg')

def get_movie_details(tmdb_id):
    tmdb_movie = TMDbMovie()
    movie = tmdb_movie.details(tmdb_id)
    
    movie_details = {
        'tmdbID': movie.id,
        'movie_title': movie.title,
        'genre': ', '.join([genre['name'] for genre in movie.genres]) if hasattr(movie, 'genres') else '',
        'release_date': movie.release_date,
        'poster_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else "",
        'overview': movie.overview,
        'vote_average': movie.vote_average,
        'director': ', '.join([member['name'] for member in movie.credits.crew if member['job'] == 'Director']) if hasattr(movie, 'credits') and hasattr(movie.credits, 'crew') else '',
        'cast': ', '.join([member['name'] for member in movie.credits.cast[:5]]) if hasattr(movie, 'credits') and hasattr(movie.credits, 'cast') else ''
    }
    
    return movie_details

def get_movies_by_genre(genre):
    genre_movies = Movie.query.filter(Movie.genre.like(f"%{genre}%")).order_by(Movie.vote_average.desc()).limit(10).all()
    genre_movies_list = []
    for movie in genre_movies:
        genres = [g.strip() for g in movie.genre.split(',')] if movie.genre else []
        genre_movies_list.append({
            'tmdbID': movie.tmdbID,
            'movie_title': movie.movie_title,
            'average_rating': round(movie.vote_average, 1) if movie.vote_average else 0,
            'poster_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else "",
            'genres': genres,
            'director': movie.director,
            'cast': movie.cast.split(',') if movie.cast else []
        })
    return genre_movies_list

def get_recommended_movies(preferences):
    recommended_movies = {}
    for genre in preferences:
        recommended_movies[genre] = get_movies_by_genre(genre)
    return recommended_movies

def save_profile_picture(profile_picture):
    filename = secure_filename(profile_picture.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    profile_picture.save(filepath)
    return f"uploads/{filename}"

def get_profile_picture_path(profile_picture):
    if not profile_picture:
        return 'uploads/default.png'
    if profile_picture.startswith('http://') or profile_picture.startswith('https://'):
        return profile_picture
    return profile_picture

def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def process_feedback():
    update_user_preferences_from_feedback()
   
