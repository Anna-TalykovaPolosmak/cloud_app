import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.neighbors import NearestNeighbors
import os
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# :blue_book: Chargement du fichier CSS
def load_css(css_file):
    """
    Charge et applique un fichier CSS externe pour styliser l’application Streamlit.
    Args:
        css_file (str): Chemin du fichier CSS.
    """
    if os.path.exists(css_file):
        with open(css_file, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"Fichier CSS non trouvé: {css_file}")

# :blue_book: Fonction de chargement des données
def load_files(files='films'):
    """
    Charge les fichiers de données depuis des fichiers CSV.
    Cette fonction permet de charger un ou plusieurs fichiers CSV contenant des données nécessaires à l’application.
    Elle gère les erreurs si le fichier est introuvable ou si le chemin est incorrect.
    Args:
        files (str ou list):
            - Si c’est une chaîne de caractères (str), elle correspond au nom de base du fichier CSV à charger.
            - Si c’est une liste (list), elle contient plusieurs noms de base de fichiers CSV à charger.
    Returns:
        pd.DataFrame ou list:
            - Si un seul fichier est chargé, retourne un DataFrame Pandas.
            - Si plusieurs fichiers sont chargés, retourne une liste de DataFrames Pandas.
    Raises:
        FileNotFoundError: Si un ou plusieurs fichiers sont introuvables.
        ValueError: Si l’argument `files` n’est ni une chaîne ni une liste.
    """
    # Si `files` est une chaîne, tenter de charger un fichier unique
    if isinstance(files, str):
        try:
            path = f'csv/{files}_def.csv'
            return pd.read_csv(path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Le fichier '{path}' est introuvable. Vérifiez le chemin.")
        except Exception as e:
            raise RuntimeError(f"Une erreur inattendue est survenue lors du chargement du fichier '{path}': {e}")
    # Si `files` est une liste, tenter de charger plusieurs fichiers
    elif isinstance(files, list):
        dataframes = []
        for file in files:
            try:
                path = f'csv/{file}_def.csv'
                df = pd.read_csv(path)
                dataframes.append(df)
            except FileNotFoundError:
                raise FileNotFoundError(f"Le fichier '{path}' est introuvable. Vérifiez le chemin.")
            except Exception as e:
                raise RuntimeError(f"Une erreur inattendue est survenue lors du chargement du fichier '{path}': {e}")
        return dataframes
    # Si `files` n’est ni une chaîne ni une liste, lever une erreur explicite
    else:
        raise ValueError("L’argument 'files' doit être une chaîne (str) ou une liste de chaînes (list).")

# :blue_book: Préparation des caractéristiques pour le système de recommandation
def prepare_features(df):
    """
    Prépare les caractéristiques nécessaires au système de recommandation de films.
    Étapes du traitement :
    - Normalisation des colonnes numériques à l’aide de RobustScaler.
    - Encodage des genres de films sous forme de colonnes binaires.
    Args:
        df (pd.DataFrame): Le DataFrame des films d’origine.
    Returns:
        pd.DataFrame: DataFrame contenant les caractéristiques finales prêtes pour l’algorithme de recommandation.
    """
    X = df.copy()
    X['year'] = pd.to_datetime(X['release_date']).dt.year  # Extraction de l’année à partir de la date de sortie
    numeric_features = ['averageRating', 'popularity', 'year']
    # Normalisation des caractéristiques numériques
    scaler = RobustScaler()
    X[numeric_features] = scaler.fit_transform(X[numeric_features])
    # Encodage des genres en colonnes binaires
    genres_split = X['genres'].str.split(',').apply(lambda x: [genre.strip() for genre in x])
    genres_dummies = pd.get_dummies(genres_split.explode()).groupby(level=0).sum()
    # Concaténation des colonnes numériques et des genres encodés
    final_features = pd.concat([
        X[numeric_features],
        genres_dummies
    ], axis=1)
    return final_features

# :blue_book: Fonction de génération des recommandations de films
def get_recommendations(title, df, features_df, n_recommendations=5, genre_weight=10):
    """
    Génère une liste de films recommandés en fonction d’un titre de film donné.
    La recommandation est basée sur la proximité des caractéristiques des films
    dans un espace vectoriel multidimensionnel.
    Args:
        title (str): Le titre du film de référence.
        df (pd.DataFrame): Le DataFrame contenant les informations des films.
        features_df (pd.DataFrame): Le DataFrame des caractéristiques du système de recommandation.
        n_recommendations (int): Nombre de recommandations à générer.
        genre_weight (int): Poids attribué aux genres similaires.
    Returns:
        pd.DataFrame: DataFrame contenant les informations des films recommandés.
    """
    movie_index = df[df['title'] == title].index[0]
    genre_columns = [col for col in features_df.columns if col not in ['averageRating', 'popularity', 'year']]
    # Ajustement du poids des genres similaires
    weighted_features = features_df.copy()
    for genre in genre_columns:
        if features_df.iloc[movie_index][genre] == 1:
            weighted_features[genre] = weighted_features[genre] * genre_weight
    # Application du modèle KNN pour identifier les films les plus proches
    model = NearestNeighbors(n_neighbors=n_recommendations + 1, metric='euclidean')
    model.fit(weighted_features)
    distances, indices = model.kneighbors(weighted_features.iloc[movie_index:movie_index+1])
    return df.iloc[indices[0][1:]]



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