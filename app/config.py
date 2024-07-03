import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_FILE_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'instance', 'popcorn_palace.db'))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_FILE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'static', 'uploads')
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback_secret_key_if_none_found')
    TMDB_API_KEY = os.getenv('TMDB_API_KEY', 'default_api_key_if_none_found')
