import streamlit as st
from openai import OpenAI
import pandas as pd
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from utils.utils import load_css

class MovieChatbot:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            self.embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["OPENAI_API_KEY"])
            self.films = pd.read_csv("csv/films_def.csv")
            self.intervenants = pd.read_csv("csv/intervenants_def.csv")
            self.lien = pd.read_csv("csv/lien_def.csv")
            self.vectorstore = self._create_or_load_vectorstore()
            
            if "messages" not in st.session_state:
                st.session_state["messages"] = self._get_initial_messages()
                
        except Exception as e:
            st.error(f"Erreur d'initialisation du chatbot: {str(e)}")

    def _create_or_load_vectorstore(self):
        try:
            return Chroma(persist_directory="./chroma_db", embedding_function=self.embeddings)
        except Exception:
            documents = self._prepare_movie_documents()
            vectorstore = Chroma.from_texts(
                texts=[doc["content"] for doc in documents],
                metadatas=[doc["metadata"] for doc in documents],
                embedding_function=self.embeddings,
                persist_directory="./chroma_db"
            )
            vectorstore.persist()
            return vectorstore
    
    def _prepare_movie_documents(self):
        documents = []
        for _, movie in self.films.iterrows():
            try:
                content = f"Titre: {movie['title']}\n"
                content += f"Année: {movie['release_date'][:4] if pd.notna(movie['release_date']) else 'Non disponible'}\n"
                content += f"Genre: {movie['genres'] if pd.notna(movie['genres']) else 'Non spécifié'}\n"
                content += f"Synopsis: {movie['overview'] if pd.notna(movie['overview']) else 'Non disponible'}\n"
                
                movie_actors = self.lien[
                    (self.lien['tconst'] == movie['tconst']) & 
                    (self.lien['category'] == 'actor')
                ]
                actors = self.intervenants[
                    self.intervenants['nconst'].isin(movie_actors['nconst'])
                ]
                content += f"Acteurs: {', '.join(actors['primaryName'])}\n"
                
                documents.append({
                    "content": content,
                    "metadata": {"tconst": movie['tconst']}
                })
            except Exception as e:
                st.warning(f"Erreur lors de la préparation du document pour {movie['title']}: {str(e)}")
                continue
                
        return documents

    def _get_initial_messages(self):
        return [
            {
                "role": "system",
                "content": "Tu es CineBot, un assistant cinéma passionné 🎬.Tu donnes des réponses détaillées avec le titre de films apparaît en rose et en gras. ⭐ Note: 📅 Année: 🎭 Genre: 📝 Synopsissur les films jusqu'à l'année 2000, acteurs et réalisateurs. Tu parles uniquement en français et utilises beaucoup des émojis appropriés."
            },
            {
                "role": "assistant",
                "content": "Bonjour! 🎬 Je suis CineBot, votre assistant cinéma! Comment puis-je vous aider aujourd'hui? 🍿"
            }
        ]

    def get_response(self, user_input: str) -> str:
        try:
            embedding_response = self.embeddings.embed_documents([user_input])[0]
            
            similar_movies = self.vectorstore.similarity_search_by_vector(embedding_response, k=5)
            context = "Contexte des films similaires:\n"
            for movie in similar_movies:
                context += f"\n{movie.page_content}\n"
            
            messages = st.session_state.messages + [
                {"role": "system", "content": f"Utilise ce contexte pour répondre: {context}"},
                {"role": "user", "content": user_input}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content

        except Exception as e:
            error_message = f"Désolé, une erreur s'est produite: {str(e)}"
            st.error(error_message)
            return "Je suis désolé, je ne peux pas répondre pour le moment. 😔"

    def display(self):
        try:
            with st.container():
                for message in st.session_state.messages:
                    if message["role"] != "system":
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])

                if prompt := st.chat_input("Posez votre question sur les films..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    with st.chat_message("assistant"):
                        response = self.get_response(prompt)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur d'affichage du chat: {str(e)}")