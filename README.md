# Popcorn Palace

Popcorn Palace is a Flask-based web application that provides movie recommendations to users based on their preferences and ratings. The app leverages collaborative filtering and a Convolutional Neural Network (CNN) model to suggest movies.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Configuration](#configuration)
- [File Structure](#file-structure)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- Python 3.x
- Pipenv or virtualenv

### Steps

1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/popcorn-palace.git
    cd popcorn-palace
    ```

2. Create a virtual environment and activate it:
    ```bash
    pipenv shell
    ```

3. Install the required packages:
    ```bash
    pipenv install
    ```

4. Set up environment variables:
    ```bash
    cp .env.example .env
    ```

5. Update the `.env` file with your configuration:
    ```env
    SECRET_KEY=your_secret_key
    TMDB_API_KEY=your_tmdb_api_key
    ```

6. Initialize the database:
    ```bash
    flask db upgrade
    ```

7. Run the application:
    ```bash
    python main.py
    ```

## Usage

1. Navigate to `http://127.0.0.1:5000` in your web browser.
2. Sign up for a new account or log in with an existing account.
3. Set your movie preferences and start getting recommendations.

## Features

- **User Authentication:** Sign up, log in, and manage your profile.
- **Movie Recommendations:** Get personalized movie recommendations based on collaborative filtering and CNN model.
- **User Preferences:** Set and update your movie genre preferences.
- **Movie Search:** Search for movies by title, cast, or director.
- **Rating History:** View and manage your movie ratings.

## Configuration

The application uses environment variables for configuration. These variables are stored in a `.env` file. Here are the key variables:

- `SECRET_KEY`: The secret key for session management.
- `TMDB_API_KEY`: API key for The Movie Database (TMDb).

## File Structure

popcorn-palace/
│
├── app/
│ ├── init.py # Flask app initialization
│ ├── config.py # Configuration settings
│ ├── forms.py # WTForms for user input
│ ├── models.py # SQLAlchemy models
│ ├── routes.py # Flask routes and views
│ ├── utils.py # Utility functions
│ ├── recommendations.py # Recommendation logic
│ ├── cnn_model.py # CNN model for movie recommendations
│ └── templates/ # HTML templates
│
├── instance/
│ └── popcorn_palace.db # SQLite database file
│
├── static/
│ ├── uploads/ # User profile pictures
│ └── posters/ # Movie posters
│
├── .env.example # Example environment variables file
├── main.py # Entry point for the application
├── README.md # This README file
├── Pipfile # Pipenv file for dependencies
└── Pipfile.lock # Pipenv lock file


## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
