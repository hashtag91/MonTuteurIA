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
    initialize_conversation_table,
    save_conversation_message,
    set_mastery,
    get_next_lesson,
    start_lesson,
    get_previous_session,
    get_all_mastery
)
import json
from memory_context import build_learning_context

# --------------------------------------------------
# 1. Préparation du projet
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BASE_DIR / "prompts" / "teacher_system.txt"

load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "Clé API manquante. Vérifie la variable OPENAI_API_KEY "
        "dans le fichier .env."
    )

client = OpenAI( api_key=api_key, base_url="https://api.groq.com/openai/v1", )

#MODEL_NAME = "openai/gpt-oss-120b"
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
from openai.types.responses import ResponseInputItemParam


def ask_teacher(system_prompt, learning_context, conversation):
    """
    Envoie le contexte pédagogique et une partie récente
    de la conversation à Groq.
    """

    # Limiter la taille du contexte pédagogique
    max_context_chars = 6000

    if len(learning_context) > max_context_chars:
        learning_context = (
            learning_context[:max_context_chars]
            + "\n[Contexte raccourci pour limiter la taille de la requête.]"
        )

    context_message = (
        "Voici les informations pédagogiques issues de la mémoire "
        "de l'application. Utilise-les pour adapter ton enseignement.\n\n"
        + learning_context
    )

    input_messages: list[ResponseInputItemParam] = [
        {
            "role": "user",
            "content": context_message,
        }
    ]

    # Ne conserver que les 8 messages les plus récents
    recent_conversation = conversation[-8:]

    input_messages.extend(recent_conversation)

    print("\n--- TAILLE DE LA REQUÊTE ---")
    print("Prompt système :", len(system_prompt), "caractères")
    print("Contexte pédagogique :", len(learning_context), "caractères")
    print("Nombre de messages :", len(input_messages))
    print(
        "Taille approximative des messages :",
        sum(
            len(str(message.get("content", "")))
            for message in input_messages
        ),
        "caractères"
    )

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=system_prompt,
        input=input_messages,
        max_output_tokens=1200,
    )

    return response.output_text



# --------------------------------------------------
# 4. Démarrage d'une séance
# --------------------------------------------------

def main():
    # Préparation de la base
    initialize_database()
    initialize_progress_table()
    initialize_conversation_table()
    seed_lessons()

    learner_id = get_or_create_learner()

    # Créer les entrées de progression manquantes
    initialize_learner_progress(learner_id)
    mastery_data = get_all_mastery(learner_id)

    print("\nMaîtrises enregistrées :")

    if mastery_data:
        for mastery in mastery_data:
            print(
                f"- {mastery['concept']} : "
                f"niveau {mastery['level']}"
            )
    else:
        print("Aucune maîtrise enregistrée.")

    mastery_context = build_mastery_context(mastery_data)

    # Récupérer la dernière séance avant d'en créer une nouvelle
    previous_session = get_previous_session(learner_id)

    # Identifier la prochaine leçon non terminée
    next_lesson = get_next_lesson(learner_id)

    if next_lesson is not None:
        lesson_id = next_lesson["id"]
        lesson_title = next_lesson["title"]

        # Marquer la leçon comme commencée
        start_lesson(learner_id, lesson_id)

        print(f"\nLeçon prévue : {lesson_title}")
    else:
        lesson_id = None
        lesson_title = None
        print("\nToutes les leçons du programme sont terminées.")

    # Créer une nouvelle séance liée à la leçon
    session_id = create_session(learner_id, lesson_id)

    # Charger les instructions et le contexte pédagogique
    system_prompt = load_system_prompt()
    learning_context = build_learning_context(learner_id)

    # Ajouter un extrait de la séance précédente au contexte
    if previous_session is not None:
        previous_messages = previous_session["messages"][-6:]

        if previous_messages:
            transcript = "\n".join(
                f"{'Apprenante' if msg['role'] == 'user' else 'Professeur'} : "
                f"{msg['content']}"
                for msg in previous_messages
            )

            learning_context += (
                "\n\nÉCHANGES DE LA SÉANCE PRÉCÉDENTE\n"
                f"Leçon précédente : "
                f"{previous_session['session']['lesson_title'] or 'Non précisée'}\n"
                "Utilise cet extrait pour assurer la continuité pédagogique. "
                "Ne prétends pas que les notions sont maîtrisées si les échanges "
                "ne le démontrent pas.\n"
                f"{transcript}"
            )

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

        # Enregistrer le premier message du professeur
        save_conversation_message(
            session_id,
            "assistant",
            answer
        )

        # Boucle de conversation
        while True:
            user_message = input("\nApprenante : ").strip()

            if not user_message:
                continue

            if user_message.lower() in ("quitter", "exit", "quit"):
                break

            # Ajouter le message de l'apprenante à l'historique
            conversation.append({
                "role": "user",
                "content": user_message
            })

            try:
                # Enregistrer le message dans SQLite
                save_conversation_message(
                    session_id,
                    "user",
                    user_message
                )

                # Demander une réponse au professeur IA
                answer = ask_teacher(
                    system_prompt,
                    learning_context,
                    conversation
                )

                print("\nProfesseur :", answer)

                # Ajouter la réponse à l'historique
                conversation.append({
                    "role": "assistant",
                    "content": answer
                })

                # Enregistrer la réponse dans SQLite
                save_conversation_message(
                    session_id,
                    "assistant",
                    answer
                )

            except Exception as error:
                print("\nUne erreur est survenue lors de l'appel à l'IA :")
                print(error)

                # Retirer le message utilisateur si l'appel à l'IA échoue
                conversation.pop()

    finally:
        try:
            # Générer le bilan de la séance
            report = generate_session_report(
                lesson_title,
                conversation
            )

            # Enregistrer le bilan
            finish_session(
                session_id,
                summary=report["summary"],
                difficulties=report["difficulties"]
            )

            print("\nBilan pédagogique enregistré.")

            # Évaluer les notions abordées pendant la séance
            if conversation and lesson_title:

                evaluated_concepts = evaluate_mastery(
                    lesson_title,
                    conversation
                )

                for item in evaluated_concepts:

                    saved = set_mastery(
                        learner_id=learner_id,
                        concept=item["concept"],
                        level=item["level"],
                        notes=item.get("notes", "")
                    )

                    if saved:
                        print(
                            f"  - {item['concept']} : "
                            f"niveau {item['level']}"
                        )
                    else:
                        print(
                            f"  - {item['concept']} : "
                            f"niveau 3 déjà vérifié"
                        )

                print(
                    f"\n{len(evaluated_concepts)} notion(s) "
                    "évaluée(s)."
                )

            else:
                print(
                    "Aucune évaluation de maîtrise : "
                    "la conversation ou la leçon est absente."
                )

        except Exception as error:

            print(
                "Impossible d'enregistrer le bilan ou "
                "l'évaluation pédagogique :",
                error
            )

        print("\nSéance terminée.")

def generate_session_report(lesson_title, conversation):
    """
    Génère un bilan pédagogique à partir de la conversation terminée.
    """

    if not conversation:
        return {
            "summary": "Aucun échange enregistré pendant cette séance.",
            "difficulties": "Aucune difficulté n'a pu être évaluée."
        }

    recent_messages = conversation[-20:]

    transcript = "\n".join(
        f"{'Apprenante' if message['role'] == 'user' else 'Professeur'} : "
        f"{message['content']}"
        for message in recent_messages
    )

    instructions = """
        Tu es un assistant chargé de rédiger le bilan d'une séance pédagogique.

        Analyse uniquement les échanges fournis.
        N'invente aucune réponse, réussite, difficulté ou compétence.

        Rédige un bilan concis en français avec les rubriques suivantes :

        BILAN :
        - Leçon étudiée
        - Notions travaillées
        - Acquis réellement observés
        - Exercices et résultats observés
        - Prochaine étape pédagogique suggérée

        DIFFICULTÉS :
        - Difficultés réellement observées
        - Notions à revoir
        - Si aucune difficulté n'est identifiable, indique-le clairement.

        Ne déclare jamais une notion maîtrisée sans preuve suffisante dans les échanges.
        Ne déclare pas automatiquement la leçon terminée.
        """

    try:
        response = client.responses.create(
            model=MODEL_NAME,
            instructions=instructions,
            input=(
                f"Leçon étudiée : {lesson_title or 'Non précisée'}\n\n"
                f"Conversation :\n{transcript}"
            ),
            max_output_tokens=700,
        )

        report = response.output_text.strip()

        return {
            "summary": report,
            "difficulties": (
                "Voir la rubrique DIFFICULTÉS du bilan pédagogique."
            )
        }

    except Exception as error:
        print("Impossible de générer le bilan pédagogique :", error)

        return {
            "summary": (
                "Le bilan automatique n'a pas pu être généré. "
                "L'historique de la séance reste enregistré."
            ),
            "difficulties": "Bilan des difficultés indisponible."
        }
def evaluate_mastery(lesson_title, conversation):
    """
    Analyse la conversation d'une séance et évalue uniquement
    les notions pour lesquelles l'apprenant a fourni des preuves.
    """

    recent_messages = conversation[-20:]

    transcript = "\n".join(
        f"{'Apprenante' if message['role'] == 'user' else 'Professeur'} : "
        f"{message['content']}"
        for message in recent_messages
    )

    instructions = """
        Tu es un évaluateur pédagogique prudent.

        Analyse la conversation d'une séance d'apprentissage.

        Ton objectif est d'identifier les notions réellement abordées
        et d'évaluer le niveau de maîtrise de l'apprenant.

        Niveaux autorisés :

        0 = non évalué ou preuves insuffisantes
        1 = en difficulté
        2 = compréhension partielle
        3 = maîtrise vérifiée

        RÈGLES IMPORTANTES :

        1. Une notion simplement expliquée par le professeur ne prouve
        PAS que l'apprenant la maîtrise.

        2. Une réponse comme "oui", "d'accord", "je comprends" ou
        "ok" ne constitue PAS une preuve de maîtrise.

        3. Une notion peut être considérée comme niveau 3 uniquement
        lorsqu'une réponse ou une réalisation autonome de l'apprenant
        démontre clairement sa compréhension.

        4. N'invente aucune réponse de l'apprenant.

        5. Ne considère que les notions réellement abordées pendant
        cette séance.

        6. Si les preuves sont insuffisantes, utilise le niveau 0.

        7. Donne une justification courte basée uniquement sur la
        conversation.

        Réponds UNIQUEMENT avec un objet JSON de cette forme :

        {
            "concepts": [
                {
                    "concept": "Nom de la notion",
                    "level": 0,
                    "notes": "Justification courte"
                }
            ]
        }
        """

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=(
            f"Leçon : {lesson_title or 'Non précisée'}\n\n"
            f"Conversation :\n{transcript}"
        ),
        max_output_tokens=700,
    )

    raw_result = response.output_text.strip()

    # Retirer éventuellement les balises Markdown
    if raw_result.startswith("```"):
        raw_result = raw_result.strip("`")

        if raw_result.startswith("json"):
            raw_result = raw_result[4:].strip()

    result = json.loads(raw_result)

    if not isinstance(result, dict):
        raise ValueError(
            "La réponse d'évaluation n'est pas un objet JSON."
        )

    concepts = result.get("concepts")

    if not isinstance(concepts, list):
        raise ValueError(
            "La réponse ne contient pas de liste 'concepts'."
        )

    for item in concepts:

        if not isinstance(item, dict):
            raise ValueError(
                "Une notion évaluée est mal formée."
            )

        if not isinstance(item.get("concept"), str):
            raise ValueError(
                "Une notion ne possède pas de nom valide."
            )

        if not item["concept"].strip():
            raise ValueError(
                "Une notion ne peut pas être vide."
            )

        if item.get("level") not in (0, 1, 2, 3):
            raise ValueError(
                "Un niveau de maîtrise est invalide."
            )

        if not isinstance(item.get("notes", ""), str):
            raise ValueError(
                "Les notes d'évaluation doivent être du texte."
            )

    return concepts

def build_mastery_context(mastery_data):
    """
    Transforme les données de maîtrise en contexte pédagogique
    compréhensible par le professeur IA.
    """

    if not mastery_data:
        return (
            "Aucune notion n'a encore été évaluée. "
            "L'apprenant commence son parcours."
        )

    lines = [
        "Voici l'état actuel des maîtrises de l'apprenant :"
    ]

    for mastery in mastery_data:

        level = mastery["level"]

        if level == 0:
            status = "non évaluée"
        elif level == 1:
            status = "en difficulté"
        elif level == 2:
            status = "compréhension partielle"
        else:
            status = "maîtrise vérifiée"

        lines.append(
            f"- {mastery['concept']} : niveau {level} "
            f"({status})."
        )

    return "\n".join(lines)

if __name__ == "__main__":
    main()