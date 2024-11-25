import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
import numpy as np


# Load the dataset from CSV file
data = pd.read_csv("C:/Users/i3dch/Documents/project 1/goodreads_data.csv")  # Make sure the path to the CSV is correct

# Replace NaN values in 'Description' with a placeholder or empty string
data['Description'] = data['Description'].fillna('No description available')

# Debugging step: Ensure all values in 'Description' are strings
data['Description'] = data['Description'].apply(str)

# Check again for NaN values and print sample descriptions
print("After replacing NaN values, sample descriptions:")
print(data['Description'].head())

# Ensure the 'Genres' column is a list (not a string)
data['Genres'] = data['Genres'].apply(lambda x: x.split(', ') if isinstance(x, str) else [])

# Function to get term frequency recommendations
def get_term_frequency_recommendations(title, data, idx):
    data['Description'] = data['Description'].fillna('')
    vectorizer = CountVectorizer(stop_words='english')
    try:
        tf_matrix = vectorizer.fit_transform(data['Description'])
    except ValueError as e:
        print(f"Error in CountVectorizer: {e}")
        return {}

    # Get the cosine similarity between the selected book and all other books
    cosine_sim = np.dot(tf_matrix[idx], tf_matrix.T).toarray().flatten()

    recommendations = {}
    for i, score in enumerate(cosine_sim):
        if i != idx:  # Skip the current book
            recommendations[data['Book'][i]] = score

    return recommendations



# Function to get genre-based recommendations
def get_genre_recommendations(title, data, idx):
    genres = data['Genres']
    book_genres = set(genres[idx])

    recommendations = {}
    for i, genre_list in enumerate(genres):
        if i != idx:  # Skip the current book
            overlap = len(book_genres.intersection(set(genre_list)))
            if overlap > 0:
                recommendations[data['Book'][i]] = overlap

    return recommendations

# Combine term frequency and genre-based recommendations
def combine_recs(title, data, genre_weight=0.6, tf_weight=0.4):
    try:
        idx = data.index[data['Book'] == title][0]
    except IndexError:
        print("Book not found in data!")
        return []

    # Get term frequency and genre-based recommendations
    tf_recs = get_term_frequency_recommendations(title, data, idx)
    g_recs = get_genre_recommendations(title, data, idx)

    # Normalize genre score by the maximum number of genres for any book
    max_genre_count = data['Genres'].apply(len).max()

    # Combine the recommendations based on weighted scoring
    combined_recs = {}
    for book, tf_score in tf_recs.items():
        genre_score = g_recs.get(book, 0) / max_genre_count
        combined_recs[book] = (tf_weight * tf_score) + (genre_score * genre_weight)

    for book, genre_score in g_recs.items():
        if book not in combined_recs:
            combined_recs[book] = (genre_score / max_genre_count) * genre_weight

    # Sort the recommendations by score in descending order
    sorted_recs = sorted(combined_recs.items(), key=lambda x: x[1], reverse=True)

    # Return top recommendations with their book IDs (just a mock ID here)
    result = []
    for book, score in sorted_recs[:5]:
        book_id = data.loc[data['Book'] == book, 'Book'].index[0]  # Mock book ID as index
        result.append({'title': book, 'score': score, 'id': book_id})

    return result

# Example call to combine recommendations function
title = 'Book A'
recommendations = combine_recs(title, data)
print(f"Recommendations for {title}")
print(recommendations)
