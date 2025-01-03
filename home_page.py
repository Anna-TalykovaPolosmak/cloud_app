import streamlit as st
import pandas as pd
from utils.utils import load_css, search_movies, get_recommendations
from chatbot.chatbot import MovieChatbot

st.set_page_config(
    page_title="CINEVASION",
    page_icon="🎬",
    layout="wide"
)

load_css('css/style.css')

try:
    films = pd.read_csv("csv/films_def.csv")
    intervenants = pd.read_csv("csv/intervenants_def.csv")
    lien = pd.read_csv("csv/lien_def.csv")
except Exception as e:
    st.error(f"Erreur de chargement des données: {str(e)}")
    st.stop()

films = films.sort_values(by='popularity', ascending=False)

# Préparation des filtres
films['decade'] = pd.to_datetime(films['release_date']).dt.year // 10 * 10
min_decade = films['decade'].min() // 10 * 10
max_decade = films['decade'].max() // 10 * 10
films['averageRating_rounded'] = films['averageRating'].round()

unique_genres = sorted(list({
    genre.strip() 
    for genres in films['genres'].dropna() 
    for genre in genres.split(',')
}))

# Barre latérale
with st.sidebar:
    st.title("Inscription utilisateur")
    login = st.text_input("Nom d'utilisateur", placeholder="LOGIN")
    password = st.text_input("Mot de passe", type="password", placeholder="PASSWORD")

# Titre principal
st.markdown(
    '<div class="title-container"><h1 class="neon-title">CINEVASION 🎬</h1></div>', 
    unsafe_allow_html=True
)

# Zone de recherche
search_container = st.container()
with search_container:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="search-label">Rechercher par le nom d\'un film 🔍</p>', unsafe_allow_html=True)
        film_input = st.text_input(
            "",
            placeholder="Rechercher un film...",
            label_visibility="collapsed",
            key="film_search"
        )
        if st.button("✨ Rechercher", key="search_film_btn"):
            if film_input:
                selected_film = films[films['title'].str.contains(film_input, case=False, na=False)]
                if not selected_film.empty:
                    if st.session_state.get('selected_film_tconst') != selected_film.iloc[0]['tconst']:
                        st.session_state['selected_film_tconst'] = selected_film.iloc[0]['tconst']
                        st.session_state['go_to_details'] = True
                        st.rerun()
                else:
                    st.warning("Aucun film trouvé.")

    with col2:
        st.markdown('<p class="search-label">Rechercher par mot-clé ou nom d\'acteur 🔍</p>', unsafe_allow_html=True)
        keyword_input = st.text_input(
            "",
            placeholder="Entrez un mot-clé ou nom d'acteur...",
            key="keyword",
            label_visibility="collapsed"
        )
        if st.button("✨ Rechercher", key="search_keyword_btn"):
            if keyword_input:
                search_results = search_movies(keyword_input, films, intervenants, lien)
                if not search_results.empty:
                    st.session_state['search_results'] = search_results
                    st.rerun()

# Отображение результатов поиска в отдельном контейнере
results_container = st.container()
if 'search_results' in st.session_state:
    with results_container:
        st.markdown("### Résultats de la recherche")
        cols = st.columns(5)
        search_results = st.session_state['search_results']
        for i in range(5):
            with cols[i]:
                if i < len(search_results):
                    film = search_results.iloc[i]
                    st.image(film['poster_path'], use_container_width=True)
                    if st.button("✨ Détails", key=f"search_{film['tconst']}"):
                        st.session_state['selected_film_tconst'] = film['tconst']
                        st.session_state['go_to_details'] = True
                        st.rerun()

st.markdown("---")

# Filtres
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<p class="filter-label">Décennie 📅</p>', unsafe_allow_html=True)
    decades = range(min_decade, max_decade + 10, 10)
    decade_options = [f"{decade}s" for decade in decades]
    selected_decade = st.selectbox(
        "",
        [''] + decade_options,
        label_visibility="collapsed",
        key="decade_filter"
    )
    selected_decade_start = int(selected_decade[:-1]) if selected_decade else None

with col2:
    st.markdown('<p class="filter-label">Genre 🎭</p>', unsafe_allow_html=True)
    genre = st.selectbox(
        "",
        [''] + unique_genres,
        label_visibility="collapsed",
        key="genre_filter"
    )

with col3:
    st.markdown('<p class="filter-label">Pays d\'origine 🌍</p>', unsafe_allow_html=True)
    country = st.selectbox(
        "",
        [''] + list(films['origin_country'].unique()),
        label_visibility="collapsed",
        key="country_filter"
    )

with col4:
    st.markdown('<p class="filter-label">Note ⭐</p>', unsafe_allow_html=True)
    rating_options = list(range(5, 11))
    selected_rating = st.selectbox(
        "",
        [''] + rating_options,
        label_visibility="collapsed",
        key="rating_filter"
    )

# Application des filtres
try:
    filtered_films = films.copy()

    if selected_decade:
        filtered_films = filtered_films[filtered_films['decade'] == selected_decade_start]
    if genre:
        filtered_films = filtered_films[filtered_films['genres'].str.contains(genre, na=False, case=False)]
    if country:
        filtered_films = filtered_films[filtered_films['origin_country'] == country]
    if selected_rating:
        filtered_films = filtered_films[filtered_films['averageRating_rounded'] == selected_rating]

    if filtered_films.empty:
        st.warning("Aucun film ne correspond aux filtres sélectionnés.")
    else:
        first_films = filtered_films.head(5)
        cols = st.columns(5)
        
        for i, (_, film) in enumerate(first_films.iterrows()):
            with cols[i]:
                if pd.notna(film['poster_path']):
                    st.image(film['poster_path'], use_container_width=True)
                if st.button("✨ Détails", key=f"filter_{film['tconst']}"):
                    st.session_state['selected_film_tconst'] = film['tconst']
                    st.session_state['go_to_details'] = True
                    st.rerun()

except Exception as e:
    st.error(f"Erreur lors du filtrage: {str(e)}")

if st.session_state.get('go_to_details', False):
    st.session_state['go_to_details'] = False
    st.switch_page("pages/details_page.py")

# Initialisation du chatbot
chat = MovieChatbot()
chat.display()


    