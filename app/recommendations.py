import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from .models import Rating, Movie, Feedback

def get_collaborative_recommendations(username, num_recommendations=10):
   
    all_ratings = Rating.query.all()

    
    data = {
        'user': [rating.user for rating in all_ratings],
        'tmdbID': [rating.tmdbID for rating in all_ratings],
        'rating': [float(rating.rating) for rating in all_ratings]  # Ensure ratings are treated as floats
    }
    df = pd.DataFrame(data)
    print("Ratings DataFrame:\n", df)

    if df.empty:
        print("No ratings available.")
        return []

    # Create a user-item matrix
    user_item_matrix = df.pivot_table(index='user', columns='tmdbID', values='rating', fill_value=0)
    print("User-Item Matrix:\n", user_item_matrix)

    # Check if the target user exists in the user-item matrix
    if username not in user_item_matrix.index:
        print(f"User {username} not found in ratings.")
        return []

    # Standardize the matrix if needed
    scaler = StandardScaler()
    user_item_matrix_scaled = scaler.fit_transform(user_item_matrix)
    print("Standardized User-Item Matrix:\n", user_item_matrix_scaled)

    # Compute the cosine similarity matrix
    similarity_matrix = cosine_similarity(user_item_matrix_scaled)
    print("Cosine Similarity Matrix:\n", similarity_matrix)

    # Convert the similarity matrix to a DataFrame
    similarity_df = pd.DataFrame(similarity_matrix, index=user_item_matrix.index, columns=user_item_matrix.index)
    print("Similarity DataFrame:\n", similarity_df)

    # Get the similarity scores for the target user
    user_similarity_scores = similarity_df.loc[username]
    print(f"Similarity Scores for {username}:\n", user_similarity_scores)

    # Get the ratings for the target user
    user_ratings = user_item_matrix.loc[username]
    print(f"Ratings for {username}:\n", user_ratings)

    # Compute the weighted sum of ratings for each item
    weighted_sum = user_item_matrix.T.dot(user_similarity_scores)
    print("Weighted Sum of Ratings:\n", weighted_sum)

    # Compute the sum of similarity scores
    sum_of_weights = user_similarity_scores.sum()
    print("Sum of Similarity Scores:\n", sum_of_weights)

    
    if sum_of_weights == 0:
        print("Sum of similarity scores is zero.")
        return []

   
    predicted_ratings = weighted_sum / sum_of_weights
    print("Predicted Ratings:\n", predicted_ratings)

    
    predicted_ratings = predicted_ratings.drop(user_ratings[user_ratings > 0].index, errors='ignore')
    print("Filtered Predicted Ratings:\n", predicted_ratings)

    # Get the top N recommended movies
    recommended_movie_ids = predicted_ratings.nlargest(num_recommendations).index
    print("Recommended Movie IDs:\n", recommended_movie_ids)

    # Get the movie details from the database
    recommended_movies = []
    for tmdbID in recommended_movie_ids:
        movie = Movie.query.filter_by(tmdbID=tmdbID).first()
        if movie:
            recommended_movies.append({
                'tmdbID': movie.tmdbID,
                'movie_title': movie.movie_title,
                'poster_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else "",
                'average_rating': round(movie.vote_average, 1) if movie.vote_average else 0
            })
    print("Recommended Movies:\n", recommended_movies)

    return recommended_movies

def update_user_preferences_from_feedback():
    feedbacks = Feedback.query.all()
    for feedback in feedbacks:
        user = User.query.get(feedback.user_id)
        movie = Movie.query.get(feedback.movie_id)
        if feedback.feedback == 'like':
            user_preference = UserPreference.query.filter_by(user_id=user.id, genre=movie.genre).first()
            if user_preference:
                user_preference.weight += 1
            else:
                new_preference = UserPreference(user_id=user.id, genre=movie.genre, weight=1)
                db.session.add(new_preference)
        elif feedback.feedback == 'dislike':
            user_preference = UserPreference.query.filter_by(user_id=user.id, genre=movie.genre).first()
            if user_preference:
                user_preference.weight -= 1
                if user_preference.weight <= 0:
                    db.session.delete(user_preference)
        db.session.commit()
