# app/cnn_model.py
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
import numpy as np
import os
from app import create_app, db
from app.utils import prepare_metadata, download_movie_posters, load_image
from app.models import Movie
from sklearn.preprocessing import LabelBinarizer

def build_cnn_model(num_classes):
    model = models.Sequential([
        layers.Conv2D(32, (3, 3), activation='relu', input_shape=(150, 150, 3)),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(128, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(512, activation='relu'),
        layers.Dense(num_classes, activation='softmax')  
    ])
    
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

def train_cnn_model():
    
    app = create_app()
    with app.app_context():
        
        download_movie_posters()

        
        metadata = prepare_metadata()
        images = []
        labels = []

        for item in metadata:
            img_path = os.path.join('static/posters', f"{item['tmdbID']}.jpg")
            if os.path.exists(img_path):
                img = load_image(img_path)
                if img.shape == (1, 150, 150, 3):
                    images.append(img)
                    labels.append(item['genre'])

        
        images = np.vstack(images) 
        labels = np.array(labels)

        
        lb = LabelBinarizer()
        labels = lb.fit_transform(labels)
        
        num_classes = labels.shape[1]  
        print(f"Number of unique genres: {num_classes}")

        
        X_train, X_val, y_train, y_val = train_test_split(images, labels, test_size=0.2)

        
        model = build_cnn_model(num_classes)
        model.fit(X_train, y_train, epochs=10, validation_data=(X_val, y_val))
        model.save('app/cnn_model.h5')  

if __name__ == '__main__':
    train_cnn_model()
