import os
import logging
import tensorflow as tf
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from .models import db, User, UserPreference, Movie, Rating, Feedback
from .forms import LoginForm, SignupForm, DeleteAccountForm, FeedbackForm
from .utils import get_random_movie_poster, get_movies_by_genre, get_recommended_movies, save_profile_picture, allowed_file, get_profile_picture_path, load_image, get_movie_details
from .recommendations import get_collaborative_recommendations
from . import bcrypt, cache
from tmdbv3api import TMDb, Movie as TMDbMovie
import numpy as np

tmdb = TMDb()
tmdb.api_key = os.getenv('TMDB_API_KEY', 'default_api_key_if_none_found')

bp = Blueprint('main', __name__)

genres = ['Action', 'Comedy', 'Drama', 'TV Movie', 'Adventure', 'History', 'Documentary', 'Romance', 'Music', 'Thriller', 'Horror', 'Crime', 'Mystery', 'Family']

cnn_model = None

def load_cnn_model():
    global cnn_model
    if cnn_model is None:
        model_path = os.path.join('app', 'cnn_model.h5')
        cnn_model = tf.keras.models.load_model(model_path)
    return cnn_model

def decode_predictions(predictions):
    predicted_index = np.argmax(predictions, axis=1)[0]
    return genres[predicted_index]

@bp.route('/cnn_recommendations/<int:tmdbID>', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def cnn_recommendations(tmdbID):
    cnn_model = load_cnn_model()
    movie = Movie.query.filter_by(tmdbID=tmdbID).first()
    if not movie:
        return jsonify({'error': 'Movie not found'}), 404

    img_path = os.path.join('static/posters', f"{tmdbID}.jpg")
    img = load_image(img_path)
    predictions = cnn_model.predict(img)
    recommended_genre = decode_predictions(predictions)

    recommended_movies = get_movies_by_genre(recommended_genre)
    return jsonify(recommended_movies)

@cache.cached(timeout=60)
def get_top_movies():
    return get_movies_by_genre('Thriller')

@bp.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    user_preferences = [pref.genre for pref in user.preferences]

    top_movies = get_top_movies()
    recommended_movies = get_recommended_movies(user_preferences)
    collaborative_recommendations = get_collaborative_recommendations(session['user_name'])

    cnn_recommendations = []
    if top_movies:
        first_movie = top_movies[0]
        tmdbID = first_movie['tmdbID']
        img_path = os.path.join('static/posters', f"{tmdbID}.jpg")
        img = load_image(img_path)
        cnn_model = load_cnn_model()
        predictions = cnn_model.predict(img)
        recommended_genre = decode_predictions(predictions)
        cnn_recommendations = get_movies_by_genre(recommended_genre)

    background_poster_url = get_random_movie_poster()
    user_profile_picture = url_for('static', filename=user.profile_picture) if user.profile_picture else url_for('static', filename='uploads/default.png')

    feedback_form = FeedbackForm()

    return render_template(
        'index.html',
        top_movies=top_movies,
        recommended_movies=recommended_movies,
        collaborative_recommendations=collaborative_recommendations,
        cnn_recommendations=cnn_recommendations,
        background_poster_url=background_poster_url,
        user=session.get('user_name'),
        profile_picture=user_profile_picture,
        form=feedback_form
    )

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            return jsonify(success=False, message='Email already registered.')

        if form.password.data != request.form.get('confirm_password'):
            return jsonify(success=False, message='Passwords do not match.')

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        profile_picture_path = save_profile_picture(form.profile_picture.data) if form.profile_picture.data else 'uploads/default.png'
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            profile_picture=profile_picture_path
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify(success=True)
    if request.method == 'POST':
        return jsonify(success=False, message='Form validation failed.')
    background_poster_url = url_for('static', filename='images/default_poster.jpg')
    return render_template('signup.html', form=form, background_poster_url=background_poster_url)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['profile_picture'] = get_profile_picture_path(user.profile_picture)
            return jsonify(success=True)
        return jsonify(success=False, message='Invalid email or password.')
    if request.method == 'POST':
        return jsonify(success=False, message='Form validation failed.')

    background_poster_url = url_for('static', filename='images/default_poster.jpg')
    return render_template('login.html', form=form, background_poster_url=background_poster_url)

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.home'))

@bp.route('/preferences', methods=['GET', 'POST'])
def preferences():
    background_poster_url = get_random_movie_poster()
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user_profile_picture = session.get('profile_picture', url_for('static', filename='uploads/default.png'))

    if request.method == 'POST':
        genres = request.form.getlist('genre')
        user_id = session['user_id']
        user = User.query.get(user_id)

        UserPreference.query.filter_by(user_id=user.id).delete()

        for genre in genres:
            user_preference = UserPreference(user_id=user.id, genre=genre)
            db.session.add(user_preference)

        db.session.commit()
        session['preferences'] = genres
        return redirect(url_for('main.home'))

    return render_template('preferences.html', background_poster_url=background_poster_url, profile_picture=user_profile_picture)

@bp.route('/save_preferences', methods=['POST'])
def save_preferences():
    if 'user_id' not in session:
        return jsonify(success=False, message='User not logged in'), 401

    genres = request.form.getlist('genre')
    if genres:
        user_id = session['user_id']
        user = User.query.get(user_id)

        UserPreference.query.filter_by(user_id=user.id).delete()

        for genre in genres:
            user_preference = UserPreference(user_id=user.id, genre=genre)
            db.session.add(user_preference)

        db.session.commit()
        session['preferences'] = genres
        return redirect(url_for('main.home'))
    return jsonify(success=False, message='Failed to save preferences')

@bp.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = form.feedback.data
        movie_id = request.form.get('movie_id')
        user_id = session['user_id']
        
        new_feedback = Feedback(user_id=user_id, movie_id=movie_id, feedback=feedback)
        db.session.add(new_feedback)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback submitted successfully!'})
    else:
        return jsonify({'success': False, 'message': 'Form validation failed.'})

@bp.route('/feedback_history')
def feedback_history():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    feedbacks = Feedback.query.filter_by(user_id=user_id).all()
    feedback_list = []
    for feedback in feedbacks:
        movie = Movie.query.filter_by(tmdbID=feedback.movie_id).first()
        feedback_list.append({
            'tmdbID': feedback.movie_id,
            'movie_title': movie.movie_title if movie else 'Unknown',
            'feedback': feedback.feedback,
            'timestamp': feedback.timestamp
        })

    background_poster_url = get_random_movie_poster()
    user_profile_picture = url_for('static', filename='uploads/default.png')
    if 'profile_picture' in session:
        user_profile_picture = url_for('static', filename=session['profile_picture'])

    return render_template(
        'feedback_history.html',
        feedbacks=feedback_list,
        user=session.get('user_name'),
        profile_picture=user_profile_picture,
        background_poster_url=background_poster_url
    )

@bp.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    background_poster_url = get_random_movie_poster()
    user = User.query.get(session['user_id'])
    user_profile_picture = url_for('static', filename=get_profile_picture_path(user.profile_picture)) if user.profile_picture else url_for('static', filename='uploads/default.png')

    return render_template('settings.html', background_poster_url=background_poster_url, user=user.name, profile_picture=user_profile_picture)

@bp.route('/update_profile_picture', methods=['POST'])
def update_profile_picture():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    if 'profile_picture' in request.files:
        profile_picture = request.files['profile_picture']
        if profile_picture and allowed_file(profile_picture.filename):
            profile_picture_path = save_profile_picture(profile_picture)
            user.profile_picture = profile_picture_path
            db.session.commit()
            session['profile_picture'] = profile_picture_path
            flash('Profile picture updated successfully!', 'success')
        else:
            flash('Invalid file format. Please upload a valid image.', 'danger')
    return redirect(url_for('main.settings'))
    
@bp.route('/update_username', methods=['POST'])
def update_username():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    new_username = request.form.get('username')
    if new_username:
        user_id = session['user_id']
        user = User.query.get(user_id)
        user.name = new_username
        db.session.commit()
        session['user_name'] = user.name
        flash('Username updated successfully!', 'success')
    else:
        flash('Failed to update username.', 'danger')
    return redirect(url_for('main.settings'))

@bp.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        flash('New password and confirm password do not match.', 'danger')
        return redirect(url_for('main.settings'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    if not bcrypt.check_password_hash(user.password, old_password):
        flash('Old password is incorrect.', 'danger')
        return redirect(url_for('main.settings'))

    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password = hashed_password
    db.session.commit()
    flash('Password updated successfully!', 'success')
    return redirect(url_for('main.settings'))

@bp.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        logging.error('User not logged in.')
        return redirect(url_for('main.login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    if user:
        try:
            logging.info(f'Deleting user: {user.name}')
            db.session.delete(user)
            db.session.commit()
            session.clear()
            logging.info('Account deleted successfully.')
            flash('Account deleted successfully!', 'success')
            return redirect(url_for('main.signup'))
        except Exception as e:
            logging.error(f'Error deleting account: {str(e)}')
            flash('Account deletion failed.', 'danger')
            return redirect(url_for('main.settings'))
    else:
        logging.error('User not found.')
        flash('Account deletion failed.', 'danger')
        return redirect(url_for('main.settings'))

@bp.route('/movie/<int:tmdb_id>')
def movie_overview(tmdb_id):
    movie_details = get_movie_details(tmdb_id)
    user = User.query.get(session['user_id'])
    user_profile_picture = url_for('static', filename=user.profile_picture) if user.profile_picture else url_for('static', filename='uploads/default.png')
    background_poster_url = get_random_movie_poster()
    
    feedback_form = FeedbackForm()

    return render_template(
        'movie_overview.html',
        movie=movie_details,
        background_poster_url=background_poster_url,
        profile_picture=user_profile_picture,
        user=session.get('user_name'),
        form=feedback_form
    )

@bp.route('/search_movies', methods=['GET', 'POST'])
def search_movies():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    query = request.form.get('query', '')
    if query:
        search_results_list = []
        tmdb_movie = TMDbMovie()

        search_results = Movie.query.filter(
            (Movie.movie_title.ilike(f"%{query}%")) |
            (Movie.cast.ilike(f"%{query}%")) |
            (Movie.director.ilike(f"%{query}%"))
        ).all()

        for result in search_results:
            try:
                movie_data = tmdb_movie.details(result.tmdbID)
                director = ''
                cast = ''

                if hasattr(movie_data, 'credits'):
                    if hasattr(movie_data.credits, 'crew'):
                        director = next((member['name'] for member in movie_data.credits.crew if member['job'] == 'Director'), '')
                    if hasattr(movie_data.credits, 'cast'):
                        cast = ', '.join([member['name'] for member in movie_data.credits.cast[:5]])

                search_results_list.append({
                    'tmdbID': result.tmdbID,
                    'movie_title': result.movie_title,
                    'genre': ', '.join([genre['name'] for genre in movie_data.genres]) if hasattr(movie_data, 'genres') else '',
                    'release_date': result.release_date,
                    'poster_url': f"https://image.tmdb.org/t/p/w500{result.poster_path}" if result.poster_path else "",
                    'overview': movie_data.overview,
                    'vote_average': movie_data.vote_average,
                    'director': director,
                    'cast': cast
                })
            except Exception as e:
                logging.error(f"Failed to fetch details for TMDb ID {result.tmdbID}: {e}")

        background_poster_url = get_random_movie_poster()
        user = User.query.get(session['user_id'])
        user_profile_picture = url_for('static', filename=user.profile_picture) if user.profile_picture else url_for('static', filename='uploads/default.png')
        return render_template('search_results.html', movies=search_results_list, background_poster_url=background_poster_url, user=session['user_name'], profile_picture=user_profile_picture)
    return redirect(url_for('main.home'))

@bp.route('/rating_history')
def rating_history():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user_ratings = Rating.query.filter_by(user=session['user_name']).all()
    ratings_list = []
    for rating in user_ratings:
        movie = Movie.query.filter_by(tmdbID=rating.tmdbID).first()
        ratings_list.append({
            'tmdbID': rating.tmdbID,
            'movie_title': movie.movie_title,
            'rating': rating.rating
        })

    background_poster_url = get_random_movie_poster()
    user = User.query.get(session['user_id'])
    user_profile_picture = url_for('static', filename=user.profile_picture) if user.profile_picture else url_for('static', filename='uploads/default.png')

    return render_template(
        'rating_history.html',
        ratings=ratings_list,
        user=user.name,
        profile_picture=user_profile_picture,
        background_poster_url=background_poster_url
    )

@bp.route('/rate_movies', methods=['POST'])
def rate_movies():
    if 'user_id' not in session:
        return jsonify(success=False, message='User not logged in'), 401

    tmdbID = request.form.get('tmdbID')
    rating = request.form.get('rating')

    if tmdbID and rating:
        try:
            user_rating = Rating.query.filter_by(user=session['user_name'], tmdbID=int(tmdbID)).first()
            if user_rating:
                user_rating.rating = rating
            else:
                new_rating = Rating(user=session['user_name'], tmdbID=int(tmdbID), rating=rating)
                db.session.add(new_rating)
            db.session.commit()
            return jsonify(success=True, message='Rating submitted successfully!', tmdbID=tmdbID, rating=rating)
        except Exception as e:
            current_app.logger.error(f"Error submitting rating: {str(e)}")
            db.session.rollback()
            return jsonify(success=False, message=f'Error submitting rating: {str(e)}'), 500

    return jsonify(success=False, message='Failed to submit rating: Missing tmdbID or rating'), 400

@bp.route('/edit_rating', methods=['POST'])
def edit_rating():
    if 'user_id' not in session:
        return jsonify(success=False, message='User not logged in'), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify(success=False, message='No data provided'), 400

        tmdbID = data.get('tmdbID')
        new_rating = data.get('rating')

        if not tmdbID or not new_rating:
            return jsonify(success=False, message='Missing required data'), 400

        user_rating = Rating.query.filter_by(user=session['user_name'], tmdbID=int(tmdbID)).first()

        if user_rating:
            user_rating.rating = new_rating
            db.session.commit()
            return jsonify(success=True, message='Rating updated successfully', tmdbID=tmdbID, rating=new_rating)
        else:
            return jsonify(success=False, message='Rating not found'), 404
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@bp.route('/delete_rating', methods=['POST'])
def delete_rating():
    if 'user_id' not in session:
        return jsonify(success=False, message='User not logged in'), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify(success=False, message='No data provided'), 400

        tmdbID = data.get('tmdbID')
        if not tmdbID:
            return jsonify(success=False, message='tmdbID is required'), 400

        rating = Rating.query.filter_by(user=session['user_name'], tmdbID=tmdbID).first()
        if rating:
            db.session.delete(rating)
            db.session.commit()
            return jsonify(success=True, message='Rating deleted successfully', tmdbID=tmdbID)
        return jsonify(success=False, message='Rating not found or not authorized'), 404
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@bp.route('/clear_ratings', methods=['POST'])
def clear_ratings():
    if 'user_id' not in session:
        return jsonify(success=False, message='User not logged in'), 401

    try:
        user = session['user_name']
        Rating.query.filter_by(user=user).delete()
        db.session.commit()
        return jsonify(success=True, message='All ratings cleared successfully')
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@bp.route('/uploads/<path:filename>')
def serve_static(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
