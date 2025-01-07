import streamlit as st  # Pour créer l'interface utilisateur web
from openai import OpenAI  # Pour l'intégration avec l'API OpenAI
import pandas as pd  # Pour la manipulation des données
from langchain.vectorstores import Chroma  # Pour la base de données vectorielle
from langchain.embeddings import OpenAIEmbeddings  # Pour la création d'embeddings
import os  # Pour les opérations sur le système de fichiers

# Configuration du style CSS pour l'interface utilisateur #__8
st.markdown("""
    <style>
    .stChatMessage {  # Style pour les messages du chat
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    span[style*="color: pink"] {  # Style pour les titres de films en rose
        color: pink !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

class MovieChatbot:
    @staticmethod
    def initialize_session_state():
        # Initialisation de l'état de session si non existant
        if "messages" not in st.session_state:
            st.session_state.messages = [
                # Message système définissant le comportement du bot
                {
                    "role": "system",
                    "content": """Tu es CineBot, un assistant cinéma passionné 🎬. 
                    IMPORTANT: Tu DOIS formatter chaque titre de film en utilisant cette syntaxe Markdown: 
                    **<span style='color: pink'>TITRE DU FILM</span>**
                    
                    Tu donnes des réponses détaillées sur les films jusqu'à l'année 2000, acteurs et réalisateurs.
                    Tu as accès à une base de données de films, d'acteurs et de réalisateurs.
                    
                    Tu peux fournir des informations sur:
                    - Les films (titre, année, genre, note, synopsis)
                    - Les acteurs et réalisateurs (nom, films dans lesquels ils ont joué/qu'ils ont réalisés)
                    - Les recommandations de films similaires
                    
                    Pour chaque film mentionné, tu DOIS inclure:
                    ⭐ Note (si disponible)
                    📅 Année
                    🎭 Genre
                    📝 Synopsis
                    🎬 Acteurs principaux
                    🎥 Lien vers la bande-annonce (si disponible)
                    
                    Tu parles uniquement en français et utilises beaucoup des émojis appropriés."""
                },
                # Message initial du bot
                {
                    "role": "assistant",
                    "content": "Bonjour! 🎬 Je suis CineBot, votre assistant cinéma passionné! Comment puis-je vous aider aujourd'hui? 🍿"
                }
            ]

    def __init__(self):
        try:
            # Initialisation de l'état de session en premier
            self.initialize_session_state()
            
            # Configuration des clients API
            self.client = OpenAI(api_key=st.secrets["OpenAI_key"])  # Client pour l'API OpenAI
            self.embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["OpenAI_key"])  # Configuration des embeddings
            
            # Chargement des fichiers CSV contenant les données des films
            self.films = pd.read_csv("csv/films_def.csv")  # Données principales des films
            self.intervenants = pd.read_csv("csv/intervenants_def.csv")  # Données des acteurs/réalisateurs
            self.lien = pd.read_csv("csv/lien_def.csv")  # Liens entre films et intervenants
            
            # Création ou chargement de la base de données vectorielle
            self.vectorstore = self._create_or_load_vectorstore()
                
        except Exception as e:
            st.error(f"Erreur d'initialisation du chatbot: {str(e)}")

    def _create_or_load_vectorstore(self):
        persist_directory = "./chroma_db"  # Répertoire de stockage de la base vectorielle
        
        # Création du répertoire s'il n'existe pas
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)
            
        try:
            # Tentative de chargement d'une base existante
            vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            vectorstore.similarity_search("test", k=1)  # Test de fonctionnement
            return vectorstore
            
        except Exception:
            # Création d'une nouvelle base si le chargement échoue
            documents = self._prepare_movie_documents()  # Préparation des documents
            vectorstore = Chroma.from_texts(
                texts=[doc["content"] for doc in documents],
                metadatas=[doc["metadata"] for doc in documents],
                embedding_function=self.embeddings,
                persist_directory=persist_directory
            )
            vectorstore.persist()  # Sauvegarde de la base
            return vectorstore
    
    def _prepare_movie_documents(self):
        documents = []  # Liste pour stocker les documents préparés
        for _, movie in self.films.iterrows():
            try:
                # Extraction et validation de l'année du film
                year = int(movie['release_date'][:4]) if pd.notna(movie['release_date']) else 0
                
                # Filtrage des films après 2000
                if year > 2000:
                    continue
                    
                # Formatage du titre avec style HTML
                title = f"**<span style='color: pink'>{movie['title']}</span>**"
                
                # Construction du contenu du document avec toutes les informations
                content = f"Titre: {title}\n"  # Titre du film
                content += f"📅 Année: {year if year != 0 else 'Non disponible'}\n"  # Année
                content += f"🎭 Genre: {movie['genres'] if pd.notna(movie['genres']) else 'Non spécifié'}\n"  # Genre
                content += f"⭐ Note: {movie['averageRating'] if pd.notna(movie['averageRating']) else 'Non disponible'}/10\n"  # Note
                content += f"📝 Synopsis: {movie['overview'] if pd.notna(movie['overview']) else 'Non disponible'}\n"  # Synopsis
                
                # Récupération et ajout des acteurs
                movie_actors = self.lien[
                    (self.lien['tconst'] == movie['tconst']) & 
                    (self.lien['category'] == 'actor')
                ]
                actors = self.intervenants[
                    self.intervenants['nconst'].isin(movie_actors['nconst'])
                ]
                content += f"🎬 Acteurs: {', '.join(actors['primaryName'])}\n"
                
                # Ajout du lien vers la bande-annonce si disponible
                if pd.notna(movie['trailer_link']):
                    content += f"🎥 Bande-annonce: [Regarder le trailer]({movie['trailer_link']})\n"
                    if pd.notna(movie['langue_trailer']):
                        content += f"🌍 Langue du trailer: {movie['langue_trailer']}\n"
                
                # Ajout du tagline si disponible
                if pd.notna(movie['tagline']) and movie['tagline'] != '':
                    content += f"💫 Tagline: {movie['tagline']}\n"
                
                # Création du document avec métadonnées
                documents.append({
                    "content": content,
                    "metadata": {  # Métadonnées pour la recherche
                        "tconst": movie['tconst'],
                        "year": year,
                        "title": movie['title'],
                        "genres": movie['genres'] if pd.notna(movie['genres']) else '',
                        "rating": float(movie['averageRating']) if pd.notna(movie['averageRating']) else 0.0,
                        "trailer_link": movie['trailer_link'] if pd.notna(movie['trailer_link']) else '',
                        "langue_trailer": movie['langue_trailer'] if pd.notna(movie['langue_trailer']) else ''
                    }
                })
            except Exception as e:
                st.warning(f"Erreur lors de la préparation du document pour {movie['title']}: {str(e)}")
                continue
                
        return documents

    def get_response(self, user_input: str) -> str:
        try:
            # Création de l'embedding pour la requête utilisateur
            embedding_response = self.embeddings.embed_documents([user_input])[0]
            
            # Recherche des films similaires dans la base vectorielle
            similar_movies = self.vectorstore.similarity_search_by_vector(
                embedding_response, 
                k=10,  # Nombre de résultats à retourner
                filter={"year": {"$lte": 2000}}  # Filtre pour les films avant 2000
            )
            
            # Préparation du contexte pour la réponse
            context = "Information sur les films disponibles:\n"
            for movie in similar_movies:
                context += f"\n---\n{movie.page_content}\n"
            
            # Configuration du prompt système
            system_prompt = """Tu es CineBot, un assistant cinéma passionné 🎬. 
            
            RÈGLES IMPORTANTES:
            1. Tu ne dois parler QUE des films d'avant 2000!
            2. Chaque titre de film DOIT être formaté ainsi: **<span style='color: pink'>TITRE DU FILM</span>**
            3. Pour CHAQUE film mentionné, tu DOIS inclure:
               - 📅 Année
               - 🎭 Genre
               - ⭐ Note /10
               - 📝 Synopsis
               - 🎬 Acteurs
               - 🎥 Lien de la bande-annonce (si disponible)
            4. Utilise TOUJOURS des émojis appropriés
            5. Si le film a un lien vers la bande-annonce, ajoute "🎥 Cliquez ici pour voir la bande-annonce!"
            6. Sois enthousiaste et passionné!
            
            Contexte des films disponibles:
            {context}
            """
            
            # Préparation des messages pour l'API OpenAI
            messages = [
                {"role": "system", "content": system_prompt.format(context=context)},
                {"role": "user", "content": user_input}
            ]
            
            # Appel à l'API OpenAI pour générer la réponse
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,  # Contrôle de la créativité
                max_tokens=800  # Longueur maximale de la réponse
            )
            
            return response.choices[0].message.content

        except Exception as e:
            error_message = f"Désolé, une erreur s'est produite: {str(e)}"
            st.error(error_message)
            return "Je suis désolé, je ne peux pas répondre pour le moment. 😔"

    def display(self):
        try:
            with st.container():
                # Affichage de l'historique des messages
                for message in st.session_state.messages:
                    if message["role"] != "system":
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"], unsafe_allow_html=True)

                # Gestion des nouvelles entrées utilisateur
                if prompt := st.chat_input("Posez votre question sur les films..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    # Génération et affichage de la réponse
                    with st.chat_message("assistant"):
                        response = self.get_response(prompt)
                        st.markdown(response, unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
        except Exception as e:
            st.error(f"Erreur d'affichage du chat: {str(e)}")

# Point d'entrée de l'application
if __name__ == "__main__":
    st.title("🎬 CineBot - Votre Assistant Cinéma")  # Titre de l'application
    bot = MovieChatbot()  # Création de l'instance du chatbot
    bot.display()  # Lancement de l'interface