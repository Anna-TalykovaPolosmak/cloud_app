import streamlit as st
import pandas as pd
import os
from utils.utils import load_css, load_files, prepare_features, get_recommendations
from chatbot.chatbot import MovieChatbot

# 📘 Configuration de la page Streamlit
st.set_page_config(
    page_title="Cinevasion - Détails du film",  # Titre de la page affiché dans l'onglet du navigateur
    page_icon="🎬",  # Icône affichée dans l'onglet du navigateur
    layout="wide"  # Disposition de la page en mode "large"
)


# 📘 Application du CSS
load_css('css/style.css')

# 📘 Navigation vers d'autres pages
st.page_link("home_page.py", label="Retour à l'accueil")  # Lien pour revenir à la page d'accueil
st.page_link("pages/recommendations_page.py", label="Retour aux recommandations")  # Lien pour revenir aux recommandations


# 📘 Chargement des données
films, intervenants, lien = load_files(files=['films', 'intervenants', 'lien'])

# 📘 Vérification de l'existence d'une sélection de film
if 'selected_film_tconst' not in st.session_state:
    st.warning("Aucun film sélectionné")  # Affiche un message d'avertissement si aucun film n'a été sélectionné
    st.page_link("home_page.py", label="Retour à l'accueil")  # Lien pour revenir à la page d'accueil
    st.stop()  # Arrête l'exécution du script

try:
    # 📘 Récupération du tconst du film sélectionné
    tconst = st.session_state['selected_film_tconst']  # Récupère l'identifiant du film à partir de la session
    film_data = films[films['tconst'] == tconst]  # Filtre les données du film correspondant
    
    if film_data.empty:
        st.error("Film non trouvé")  # Message d'erreur si le film n'est pas trouvé
        st.stop()
        
    selected_film = film_data.iloc[0]  # Sélection de la première (et unique) ligne du DataFrame

    # 📘 Affichage des détails du film
    st.markdown('<div class="neo-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])  # Deux colonnes : une pour l'affiche et une pour les informations du film
    
    with col1:
        if pd.notna(selected_film['poster_path']):
            st.image(selected_film['poster_path'], width=300)  # Affiche l'affiche du film
        else:
            st.warning("Affiche non disponible")  # Message d'avertissement si l'affiche n'est pas disponible
    
    with col2:
        st.title(selected_film['title'])  # Affiche le titre du film
        release_date = pd.to_datetime(selected_film['release_date']).strftime('%Y') if pd.notna(selected_film['release_date']) else 'Non disponible'
        
        st.markdown(f"""
        <div class="movie-info">
            <p><strong>Année :</strong> {release_date}</p>
            <p><strong>Genre :</strong> {selected_film['genres']}</p>
            <p><strong>Note :</strong> {float(selected_film['averageRating']):.1f}/10</p>
            <p><strong>Pays :</strong> {selected_film['origin_country']}</p>
        </div>
        """, unsafe_allow_html=True)  # Affiche les informations clés du film

        # 📘 Affichage du synopsis ou tagline
        if pd.notna(selected_film.get('overview')):
            st.markdown("### Synopsis")
            st.markdown('<div class="overview-container">', unsafe_allow_html=True)
            st.write(selected_film['overview'])  # Affiche le synopsis
            st.markdown('</div>', unsafe_allow_html=True)
        elif pd.notna(selected_film.get('tagline')):
            st.markdown("### Synopsis")
            st.markdown('<div class="overview-container">', unsafe_allow_html=True)
            st.write(selected_film['tagline'])  # Affiche le tagline si le synopsis n'est pas disponible
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # 📘 Affichage de la bande annonce du film
    if pd.notna(selected_film.get('trailer_link')):
        st.markdown('<div class="neo-container">', unsafe_allow_html=True)
        st.subheader("Bande annonce")  # Titre de la section bande annonce
        st.video(selected_film['trailer_link'])  # Lecture de la bande annonce vidéo
        st.markdown('</div>', unsafe_allow_html=True)

    # 📘 Affichage des participants (réalisateurs et acteurs)
    film_participants = lien[lien['tconst'] == selected_film['tconst']]  # Liens entre le film et les intervenants
    
    # 📘 Affichage des réalisateurs
    directors = film_participants[film_participants['category'] == 'director']  # Filtre des réalisateurs
    if not directors.empty:
        st.markdown('<div class="neo-container">', unsafe_allow_html=True)
        st.subheader("Réalisateurs")  # Titre de la section des réalisateurs
        dir_cols = st.columns(len(directors))  # Colonnes pour afficher les réalisateurs
        for i, (p, director_link) in enumerate(directors.iterrows()):
            director = intervenants[intervenants['nconst'] == director_link['nconst']]
            if not director.empty:
                with dir_cols[i]:
                    director = director.iloc[0]
                    st.markdown(f"""
                    <div class="actor-card">
                        <img src="{director['profile_path']}" width="150">
                        <h3>{director['primaryName']}</h3>
                    </div>
                    """, unsafe_allow_html=True)  # Affiche la photo et le nom du réalisateur
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 📘 Affichage des acteurs principaux (limité à 5)
    actors = film_participants[film_participants['category'] == 'actor'].head(5)
    if not actors.empty:
        st.markdown('<div class="neo-container">', unsafe_allow_html=True)
        st.subheader("Acteurs principaux")  # Titre de la section des acteurs
        actor_cols = st.columns(len(actors))  # Colonnes pour afficher les acteurs
        for i, (p, actor_link) in enumerate(actors.iterrows()):
            actor = intervenants[intervenants['nconst'] == actor_link['nconst']]
            if not actor.empty:
                with actor_cols[i]:
                    actor = actor.iloc[0]
                    st.markdown(f"""
                    <div class="actor-card">
                        <img src="{actor['profile_path']}" width="150">
                        <h3>{actor['primaryName']}</h3>
                    </div>
                    """, unsafe_allow_html=True)  # Affiche la photo et le nom de l'acteur
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="neo-container">', unsafe_allow_html=True)
    st.subheader("Films similaires")  # Titre de la section des réalisateurs
    # 📘 Préparation des caractéristiques des films
    features_matrix = prepare_features(films)

    film_choice = selected_film['title']

    try:
        # 📘 Obtenir les recommandations de films
        recommended_films = get_recommendations(
            film_choice, 
            films, 
            features_matrix,
            n_recommendations=5
        )

        cols = st.columns(5)
    
        for i, (_, film) in enumerate(recommended_films.iterrows()):
            with cols[i]:
                with st.container():
                    st.image(film['poster_path'], use_container_width=True)             
                    if st.button("✨ Détails", key=f"details_{i}_{film['tconst']}"):
                        st.session_state.button_state = "action"
                        st.session_state['selected_film_tconst'] = film['tconst']
                        st.switch_page("pages/details_page.py")

    except Exception as exc:
        st.error(f"Erreur lors de la génération des recommandations : {str(exc)}")



except Exception as e:
    # 📘 Gestion des erreurs
    st.error(f"Erreur lors de l'affichage des détails du film : {str(e)}")  # Affiche l'erreur
    st.switch_page("home_page.py")  # Redirige vers la page d'accueil

chat = MovieChatbot()
chat.display()