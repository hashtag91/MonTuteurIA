import os

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import ResponseInputItemParam
from database.database import (
    initialize_database,
    initialize_progress_table,
    seed_lessons,
    initialize_learner_progress,
    get_connection,
    create_learner,
    create_session,
    finish_session,
)

from memory_context import build_learning_context

# --------------------------------------------------
# 1. Préparation du projet
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BASE_DIR / "prompts" / "teacher_system.txt"

load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("groq_api_key")

if not api_key:
    raise RuntimeError(
        "Clé API manquante. Vérifie la variable OPENAI_API_KEY "
        "dans le fichier .env."
    )

client = OpenAI( api_key=api_key, base_url="https://api.groq.com/openai/v1", )

MODEL_NAME = "openai/gpt-oss-120b"

def load_system_prompt():
    """Charge les instructions du professeur depuis le fichier texte."""

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Le prompt système est introuvable : {PROMPT_PATH}"
        )
    return PROMPT_PATH.read_text(encoding="utf-8")

# --------------------------------------------------
# 2. Gestion du profil de l'apprenante
# --------------------------------------------------

def get_or_create_learner():
    """
    Récupère le premier profil existant.
    S'il n'existe pas, crée un profil de démonstration.
    """

    with get_connection() as connection:
        learner = connection.execute("""
            SELECT id
            FROM learner
            ORDER BY id
            LIMIT 1
        """).fetchone()

    if learner is not None:
        return learner["id"]

    return create_learner("Apprenante", 15)


# --------------------------------------------------
# 3. Communication avec le professeur IA
# --------------------------------------------------
def ask_teacher(system_prompt, learning_context, conversation):
    """
    Envoie le contexte pédagogique et l'historique au modèle.
    """

    context_message = (
        "Voici les informations pédagogiques issues de la mémoire "
        "de l'application. Utilise-les pour adapter ton enseignement.\n\n"
        + learning_context
    )

    # Déclaration explicite du type attendu par le SDK OpenAI
    input_messages: list[ResponseInputItemParam] = [
        {
            "role": "user",
            "content": context_message,
        }
    ]

    # Ajouter les messages de la conversation
    input_messages.extend(conversation)

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=system_prompt,
        input=input_messages,
    )

    return response.output_text


# --------------------------------------------------
# 4. Démarrage d'une séance
# --------------------------------------------------

def main():
    # Préparation de la base
    initialize_database()
    initialize_progress_table()
    seed_lessons()

    learner_id = get_or_create_learner()

    # Ajouter les éventuelles nouvelles leçons à la progression
    initialize_learner_progress(learner_id)

    # Créer une séance en base
    session_id = create_session(learner_id)

    # Charger les instructions et la mémoire pédagogique
    system_prompt = load_system_prompt()
    learning_context = build_learning_context(learner_id)

    # Historique des échanges de cette séance
    conversation = []

    print("\n====================================")
    print("       MON PROF IA")
    print("====================================")
    print("Séance commencée.")
    print("Écris 'quitter' pour terminer.\n")

    try:
        # Premier message du professeur
        answer = ask_teacher(
            system_prompt,
            learning_context,
            conversation,
        )

        print("Professeur :", answer)

        conversation.append({
            "role": "assistant",
            "content": answer,
        })

        # Boucle de conversation
        while True:
            user_message = input("\nToi : ").strip()

            if not user_message:
                continue

            if user_message.lower() in ("quitter", "exit", "quit"):
                break

            conversation.append({
                "role": "user",
                "content": user_message,
            })

            try:
                answer = ask_teacher(
                    system_prompt,
                    learning_context,
                    conversation,
                )

                print("\nProfesseur :", answer)

                conversation.append({
                    "role": "assistant",
                    "content": answer,
                })

            except Exception as error:
                print("\nUne erreur est survenue lors de l'appel à l'IA :")
                print(error)

                # Retirer le message utilisateur ajouté si l'appel a échoué,
                # afin de ne pas conserver un échange incomplet.
                conversation.pop()

    finally:
        # Pour l'instant, on enregistre un résumé simple.
        # Nous améliorerons ensuite cette étape pour produire un vrai bilan.
        try:
            finish_session(
                session_id,
                summary="Séance terminée. Historique conservé en mémoire pendant l'exécution.",
                difficulties="",
            )
        except Exception as error:
            print("Impossible de clôturer la séance dans la base :", error)

        print("\nSéance terminée.")


if __name__ == "__main__":
    main()