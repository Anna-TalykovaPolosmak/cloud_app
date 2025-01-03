import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.neighbors import NearestNeighbors
import os
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def load_css(css_file):
    if os.path.exists(css_file):
        with open(css_file, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"Fichier CSS non trouvé: {css_file}")

def load_files(files='films'):
    if isinstance(files, str):
        try:
            path = f'csv/{files}_def.csv'
            return pd.read_csv(path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Le fichier '{path}' est introuvable.")
        except Exception as e:
            raise RuntimeError(f"Erreur lors du chargement de '{path}': {e}")
    
    elif isinstance(files, list):
        dataframes = []
        for file in files:
            try:
                path = f'csv/{file}_def.csv'
                df = pd.read_csv(path)
                dataframes.append(df)
            except FileNotFoundError:
                raise FileNotFoundError(f"Le fichier '{path}' est introuvable.")
            except Exception as e:
                raise RuntimeError(f"Erreur lors du chargement de '{path}': {e}")
        return dataframes
    else:
        raise ValueError("L'argument 'files' doit être une chaîne ou une liste.")

def prepare_features(df):
    try:
        X = df.copy()
        X['year'] = pd.to_datetime(X['release_date']).dt.year
        numeric_features = ['averageRating', 'popularity', 'year']
        
        scaler = RobustScaler()
        X[numeric_features] = scaler.fit_transform(X[numeric_features])
        
        genres_split = X['genres'].str.split(',').apply(lambda x: [genre.strip() for genre in x] if isinstance(x, str) else [])
        genres_dummies = pd.get_dummies(genres_split.explode()).groupby(level=0).sum()
        
        final_features = pd.concat([
            X[numeric_features],
            genres_dummies
        ], axis=1)
        
        return final_features
    except Exception as e:
        st.error(f"Erreur dans prepare_features: {e}")
        return None

def get_recommendations(title, df, features_df, n_recommendations=5, genre_weight=10):
    try:
        movie_index = df[df['title'] == title].index[0]
        genre_columns = [col for col in features_df.columns if col not in ['averageRating', 'popularity', 'year']]
        
        weighted_features = features_df.copy()
        for genre in genre_columns:
            if features_df.iloc[movie_index][genre] == 1:
                weighted_features[genre] = weighted_features[genre] * genre_weight
        
        model = NearestNeighbors(n_neighbors=n_recommendations + 1, metric='euclidean')
        model.fit(weighted_features)
        
        distances, indices = model.kneighbors(weighted_features.iloc[movie_index:movie_index+1])
        
        return df.iloc[indices[0][1:]]
    except Exception as e:
        st.error(f"Erreur dans get_recommendations: {e}")
        return pd.DataFrame()

def format_movie_info(movie):
    try:
        return f"""### 🎬 {movie['title']}
**⭐ Note:** {movie['averageRating']}/10
**📅 Année:** {movie['release_date'][:4] if pd.notna(movie['release_date']) else 'Non disponible'}
**🎭 Genre:** {movie['genres'] if pd.notna(movie['genres']) else 'Non spécifié'}

#### 📝 Synopsis
{movie.get('overview', 'Synopsis non disponible')}
"""
    except Exception as e:
        st.error(f"Erreur dans format_movie_info: {e}")
        return "Information non disponible"

def search_movies(query, films_df, intervenants_df, lien_df, n_recommendations=5):
    try:
        # Поиск по актёрам
        actor_matches = intervenants_df[intervenants_df['primaryName'].str.contains(query, case=False, na=False)]
        if not actor_matches.empty:
            actor_nconst = actor_matches.iloc[0]['nconst']
            actor_movies = lien_df[lien_df['nconst'] == actor_nconst]
            return films_df[films_df['tconst'].isin(actor_movies['tconst'])].head(n_recommendations)
        
        # Поиск по всем критериям
        mask = (
            films_df['title'].str.contains(query, case=False, na=False) |
            films_df['overview'].str.contains(query, case=False, na=False) |
            films_df['genres'].str.contains(query, case=False, na=False) |
            films_df['keywords'].str.contains(query, case=False, na=False) |
            films_df['tagline'].str.contains(query, case=False, na=False) |
            films_df['origin_country'].str.contains(query, case=False, na=False)
        )
        
        direct_matches = films_df[mask]
        if not direct_matches.empty:
            return direct_matches.head(n_recommendations)
            
        # Поиск по TF-IDF если прямых совпадений нет
        films_df['search_text'] = (
            films_df['title'].fillna('') + ' ' +
            films_df['overview'].fillna('') * 3 + ' ' +
            films_df['keywords'].fillna('') + ' ' +
            films_df['genres'].fillna('') + ' ' +
            films_df['tagline'].fillna('') + ' ' +
            films_df['origin_country'].fillna('')
        )
        
        tfidf = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
        
        tfidf_matrix = tfidf.fit_transform(films_df['search_text'])
        query_vec = tfidf.transform([query])
        similarity = cosine_similarity(query_vec, tfidf_matrix)
        top_indices = similarity[0].argsort()[-n_recommendations:][::-1]
        
        return films_df.iloc[top_indices]
        
    except Exception as e:
        st.error(f"Erreur dans search_movies: {str(e)}")
        return pd.DataFrame()