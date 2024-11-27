import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load the dataset from CSV file
data = pd.read_csv("C:/Users/i3dch/Documents/project 1/goodreads_data.csv") # Reads csv and converts it into a pandas dataframe

data['Description'] = data['Description'].fillna('No description available').apply(str) 
data['Genres'] = data['Genres'].apply(lambda x: x.split(', ') if isinstance(x, str) else [])

# Function to get term frequency recommendations
def get_term_frequency_recommendations(title, data, idx):
    word_counter = TfidfVectorizer(stop_words='english') # It converts a collection of text into a matrix of token counts

    # Then it makes a matrix that shows for each book what unique words they contain
    try:
        tfidf_matrix = word_counter.fit_transform(data['Description']) # This line creates the matrix
        sim = cosine_similarity(tfidf_matrix[idx], tfidf_matrix).flatten() # Computes the cosine simularity which is the best way to see similarities between 2 books
                                                   
    except ValueError as e:
        print(f"Error in CountVectorizer: {e}")
        return {}

    recommendations = {}
    for i, score in enumerate(sim):
        if i != idx:  # Skip the current book
            recommendations[data.iloc[i]['Book']] = score
    # Grabs every book index (except itself) and puts it in a dictionary with idx and cosine sim scores
    sorted_recommendations = dict(sorted(recommendations.items(), key=lambda x: x[1], reverse=True))

    return sorted_recommendations

# Function to get genre-based recommendations
def get_genre_recommendations(title, data, idx):
    genres = data['Genres']
    book_genres = set(genres[idx])

    recommendations = {}
    for i, genre_list in enumerate(genres):
        if i != idx:  # Skip the current book
            overlap = len(book_genres.intersection(set(genre_list)))
            if overlap > 0:
                recommendations[data.iloc[i]['Book']] = overlap

    return recommendations # Returns the number of genres they have in common

# Combine term frequency and genre-based recommendations
def combine_recs(title, data, genre_weight=0.6, tf_weight=0.4):
    try:
        idx = data.index[data['Book'] == title][0] # Finds index of the book inputed
    except IndexError:
        print(f"Book '{title}' not found in data!")
        return []

    # Get term frequency and genre-based recommendations
    tf_recs = get_term_frequency_recommendations(title, data, idx)
    g_recs = get_genre_recommendations(title, data, idx)

    max_genre_count = max(data['Genres'].apply(len), default=1)

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

    # Return top recommendations with their book IDs
    result = []
    for book, score in sorted_recs[:5]:
        try:
            book_id = data.loc[data['Book'] == book, 'id'].values[0]
            result.append({'Book': book, 'score': score, 'id': book_id})
        except IndexError:
            print(f"Error finding ID for book '{book}'. Skipping...")
            continue

    return result
