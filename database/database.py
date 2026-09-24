import sqlite3
from pathlib import Path


# --------------------------------------------------
# 1. CHEMIN DE LA BASE DE DONNÉES
# --------------------------------------------------

# Dossier racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Dossier dans lequel sera stockée la base
DATABASE_DIR = BASE_DIR / "database"

# Création du dossier s'il n'existe pas
DATABASE_DIR.mkdir(exist_ok=True)

# Chemin complet du fichier SQLite
DATABASE_PATH = DATABASE_DIR / "mon_prof_ia.db"


# --------------------------------------------------
# 2. CONNEXION À LA BASE DE DONNÉES
# --------------------------------------------------

def get_connection():
    """
    Ouvre une connexion à la base de données SQLite.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    # Permet d'accéder aux colonnes par leur nom
    connection.row_factory = sqlite3.Row

    # Active la vérification des clés étrangères
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# --------------------------------------------------
# 3. INITIALISATION DE LA BASE DE DONNÉES
# --------------------------------------------------

def initialize_database():
    """
    Crée les tables si elles n'existent pas encore.
    """

    with get_connection() as connection:

        # Table du profil de l'apprenante
        connection.execute("""
            CREATE TABLE IF NOT EXISTS learner (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER,
                language TEXT DEFAULT 'français',
                current_phase INTEGER DEFAULT 1,
                current_lesson_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table des leçons
        connection.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phase INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                position INTEGER NOT NULL,
                status TEXT DEFAULT 'not_started'
                    CHECK (
                        status IN (
                            'not_started',
                            'in_progress',
                            'completed'
                        )
                    )
            )
        """)

        # Table des séances
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_id INTEGER NOT NULL,
                lesson_id INTEGER,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                summary TEXT,
                difficulties TEXT,

                FOREIGN KEY (learner_id)
                    REFERENCES learner(id),

                FOREIGN KEY (lesson_id)
                    REFERENCES lessons(id)
            )
        """)

        # Table du niveau de maîtrise des notions
        connection.execute("""
            CREATE TABLE IF NOT EXISTS mastery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_id INTEGER NOT NULL,
                concept TEXT NOT NULL,
                level INTEGER DEFAULT 0
                    CHECK (level BETWEEN 0 AND 3),
                notes TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (learner_id, concept),

                FOREIGN KEY (learner_id)
                    REFERENCES learner(id)
            )
        """)

    print("Base de données initialisée avec succès.")


# --------------------------------------------------
# 4. CRÉER LE PROFIL DE L'APPRENANTE
# --------------------------------------------------

def create_learner(name, age=15):
    """
    Crée le profil de l'apprenante et retourne son identifiant.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO learner (name, age)
            VALUES (?, ?)
        """, (name, age))

        learner_id = cursor.lastrowid

    return learner_id

def initialize_conversation_table():
    """Crée la table qui conserve les messages des conversations."""

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (session_id)
                    REFERENCES sessions(id)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()

def save_conversation_message(session_id, role, content):
    """Enregistre un message dans la base de données."""

    if role not in ("user", "assistant"):
        raise ValueError("Le rôle doit être 'user' ou 'assistant'.")

    if not content or not content.strip():
        return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversation_messages
                (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content.strip())
        )

        conn.commit()


def get_conversation_messages(session_id):
    """Récupère les messages d'une séance dans l'ordre chronologique."""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM conversation_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,)
        ).fetchall()

    return [dict(row) for row in rows]

# --------------------------------------------------
# 5. AJOUTER UNE LEÇON
# --------------------------------------------------

def add_lesson(phase, title, description, position):
    """
    Ajoute une leçon au programme de formation.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO lessons (
                phase,
                title,
                description,
                position
            )
            VALUES (?, ?, ?, ?)
        """, (phase, title, description, position))

        return cursor.lastrowid


# --------------------------------------------------
# 6. ENREGISTRER UNE SÉANCE
# --------------------------------------------------

def create_session(learner_id, lesson_id=None):
    """
    Enregistre le début d'une nouvelle séance.
    """

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO sessions (learner_id, lesson_id)
            VALUES (?, ?)
        """, (learner_id, lesson_id))

        return cursor.lastrowid


def finish_session(session_id, summary, difficulties=""):
    """
    Enregistre le résumé et les difficultés d'une séance.
    """

    with get_connection() as connection:

        connection.execute("""
            UPDATE sessions
            SET summary = ?,
                difficulties = ?
            WHERE id = ?
        """, (summary, difficulties, session_id))


# --------------------------------------------------
# 7. ENREGISTRER LE NIVEAU DE MAÎTRISE
# --------------------------------------------------

def set_mastery(learner_id, concept, level, notes=""):
    """
    Enregistre ou actualise le niveau de maîtrise d'une notion.

    Niveau :
    0 = non évalué
    1 = en difficulté
    2 = compréhension partielle
    3 = maîtrise vérifiée
    """

    if level not in (0, 1, 2, 3):
        raise ValueError("Le niveau doit être compris entre 0 et 3.")

    with get_connection() as connection:

        connection.execute("""
            INSERT INTO mastery (
                learner_id,
                concept,
                level,
                notes,
                updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)

            ON CONFLICT (learner_id, concept)
            DO UPDATE SET
                level = excluded.level,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
        """, (learner_id, concept, level, notes))


# --------------------------------------------------
# 8. RÉCUPÉRER LE PROFIL
# --------------------------------------------------

def get_learner(learner_id):

    with get_connection() as connection:

        learner = connection.execute("""
            SELECT *
            FROM learner
            WHERE id = ?
        """, (learner_id,)).fetchone()

    return learner


# --------------------------------------------------
# 9. RÉCUPÉRER LES NOTIONS MAÎTRISÉES OU À REVOIR
# --------------------------------------------------

def get_mastery(learner_id):

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT concept, level, notes, updated_at
            FROM mastery
            WHERE learner_id = ?
            ORDER BY concept
        """, (learner_id,)).fetchall()

    return rows


# --------------------------------------------------
# 10. RÉCUPÉRER LES DERNIÈRES SÉANCES
# --------------------------------------------------

def get_recent_sessions(learner_id, limit=5):

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                sessions.id,
                sessions.started_at,
                lessons.title AS lesson_title,
                sessions.summary,
                sessions.difficulties
            FROM sessions
            LEFT JOIN lessons
                ON sessions.lesson_id = lessons.id
            WHERE sessions.learner_id = ?
            ORDER BY sessions.id DESC
            LIMIT ?
        """, (learner_id, limit)).fetchall()

    return rows


PROGRAMME_FORMATION = [

    # PHASE 1 : DÉCOUVERTE DE LA PROGRAMMATION
    {
        "phase": 1,
        "lessons": [
            (
                "Découvrir l'informatique",
                "Comprendre simplement ce qu'est l'informatique."
            ),
            (
                "Qu'est-ce qu'un programme ?",
                "Découvrir le rôle des programmes informatiques."
            ),
            (
                "Comprendre les instructions",
                "Comprendre ce qu'est une instruction et pourquoi elle doit être claire."
            ),
            (
                "Découvrir la programmation",
                "Comprendre ce que signifie programmer un ordinateur."
            ),
        ]
    },

    # PHASE 2 : LOGIQUE ET RÉSOLUTION DE PROBLÈMES
    {
        "phase": 2,
        "lessons": [
            (
                "Comprendre un problème",
                "Identifier l'objectif d'un problème et les informations disponibles."
            ),
            (
                "Décomposer un problème",
                "Diviser un problème en petites étapes faciles à résoudre."
            ),
            (
                "Organiser les étapes",
                "Placer les instructions dans un ordre logique."
            ),
            (
                "Vérifier une solution",
                "Vérifier qu'une suite d'étapes permet d'atteindre l'objectif."
            ),
        ]
    },

    # PHASE 3 : INITIATION À L'ALGORITHMIQUE
    {
        "phase": 3,
        "lessons": [
            (
                "Qu'est-ce qu'un algorithme ?",
                "Découvrir la notion d'algorithme à partir d'exemples quotidiens."
            ),
            (
                "Écrire un algorithme simple",
                "Construire une suite d'instructions pour résoudre un problème."
            ),
            (
                "Exécuter un algorithme manuellement",
                "Suivre les instructions dans leur ordre d'exécution."
            ),
            (
                "Repérer une erreur logique",
                "Identifier une instruction incorrecte ou une étape manquante."
            ),
            (
                "Découvrir le pseudo-code",
                "Représenter un algorithme avec une notation simple et structurée."
            ),
        ]
    },

    # PHASE 4 : STRUCTURES ALGORITHMIQUES
    {
        "phase": 4,
        "lessons": [
            (
                "Les données et les variables",
                "Comprendre comment représenter et mémoriser des informations."
            ),
            (
                "Les entrées et les sorties",
                "Comprendre comment un algorithme reçoit des informations et présente un résultat."
            ),
            (
                "Les opérations",
                "Effectuer des calculs et utiliser des expressions simples."
            ),
            (
                "Les conditions",
                "Prendre une décision en fonction d'une situation."
            ),
            (
                "Les répétitions",
                "Comprendre comment répéter des instructions."
            ),
            (
                "Les compteurs et les accumulateurs",
                "Utiliser des variables pour compter ou accumuler des valeurs."
            ),
            (
                "Les listes algorithmiques",
                "Regrouper plusieurs valeurs et les parcourir."
            ),
            (
                "Les fonctions algorithmiques",
                "Décomposer un problème en sous-problèmes réutilisables."
            ),
            (
                "Tester un algorithme",
                "Vérifier une solution à l'aide de plusieurs exemples."
            ),
        ]
    },

    # PHASE 5 : DÉCOUVERTE DE PYTHON
    {
        "phase": 5,
        "lessons": [
            (
                "Découvrir Python",
                "Comprendre ce qu'est Python et à quoi il sert."
            ),
            (
                "Écrire et exécuter un premier programme",
                "Découvrir l'environnement Python et exécuter un programme simple."
            ),
            (
                "Afficher un message avec print()",
                "Afficher du texte et des résultats dans la console."
            ),
            (
                "Les commentaires",
                "Ajouter des explications dans le code."
            ),
            (
                "Les variables en Python",
                "Créer des variables et modifier leurs valeurs."
            ),
            (
                "Les types de données",
                "Découvrir les nombres, les chaînes de caractères et les booléens."
            ),
            (
                "Les opérations en Python",
                "Effectuer des calculs avec Python."
            ),
            (
                "Lire une information avec input()",
                "Récupérer une information saisie par l'utilisateur."
            ),
            (
                "Les conditions en Python",
                "Utiliser if, elif et else."
            ),
            (
                "Les boucles en Python",
                "Utiliser for et while pour répéter des instructions."
            ),
            (
                "Les listes en Python",
                "Créer des listes, accéder à leurs éléments et les parcourir."
            ),
            (
                "Les dictionnaires en Python",
                "Organiser des données sous forme de paires clé-valeur."
            ),
            (
                "Les fonctions en Python",
                "Créer des fonctions et utiliser return."
            ),
            (
                "Comprendre et corriger les erreurs",
                "Lire les messages d'erreur et corriger les problèmes courants."
            ),
            (
                "Découvrir les modules",
                "Réutiliser du code grâce aux modules Python."
            ),
            (
                "Lire et écrire dans des fichiers",
                "Enregistrer et récupérer des informations dans des fichiers."
            ),
        ]
    },

    # PHASE 6 : PROJETS PRATIQUES
    {
        "phase": 6,
        "lessons": [
            (
                "Projet : message personnalisé",
                "Créer un programme qui affiche un message personnalisé."
            ),
            (
                "Projet : calculatrice simple",
                "Construire une calculatrice utilisant les opérations fondamentales."
            ),
            (
                "Projet : calcul de moyenne",
                "Créer un programme qui calcule une moyenne."
            ),
            (
                "Projet : pair ou impair",
                "Écrire un programme qui détermine si un nombre est pair ou impair."
            ),
            (
                "Projet : jeu de devinettes",
                "Créer un jeu simple utilisant les conditions et les boucles."
            ),
            (
                "Projet : questionnaire interactif",
                "Créer un questionnaire qui pose des questions et vérifie les réponses."
            ),
            (
                "Projet : gestionnaire de tâches",
                "Créer un petit programme permettant de gérer une liste de tâches."
            ),
        ]
    },

    # PHASE 7 : APPROFONDISSEMENT ET EXPLORATION
    {
        "phase": 7,
        "lessons": [
            (
                "Introduction à la programmation orientée objet",
                "Découvrir les classes et les objets avec des exemples simples."
            ),
            (
                "Introduction aux bases de données",
                "Comprendre comment une application peut conserver des informations."
            ),
            (
                "Découvrir les interfaces graphiques",
                "Comprendre comment créer une interface utilisateur."
            ),
            (
                "Découvrir les API",
                "Comprendre comment deux applications peuvent communiquer."
            ),
            (
                "Premiers pas en automatisation",
                "Découvrir comment Python peut automatiser certaines tâches."
            ),
            (
                "Introduction à l'intelligence artificielle",
                "Découvrir les grandes idées de l'intelligence artificielle."
            ),
        ]
    },
]

# --------------------------------------------------
# 13. ENREGISTRER LE PROGRAMME SANS DOUBLONS
# --------------------------------------------------

def seed_lessons():
    """
    Enregistre le programme pédagogique initial.

    Une leçon existante avec la même phase et le même titre
    n'est pas ajoutée une seconde fois.
    """

    nombre_ajoute = 0

    with get_connection() as connection:

        for phase_data in PROGRAMME_FORMATION:

            phase = phase_data["phase"]

            for position, lesson_data in enumerate(
                phase_data["lessons"],
                start=1
            ):

                title, description = lesson_data

                existing = connection.execute("""
                    SELECT id
                    FROM lessons
                    WHERE phase = ?
                    AND title = ?
                """, (phase, title)).fetchone()

                if existing is None:

                    connection.execute("""
                        INSERT INTO lessons (
                            phase,
                            title,
                            description,
                            position
                        )
                        VALUES (?, ?, ?, ?)
                    """, (
                        phase,
                        title,
                        description,
                        position
                    ))

                    nombre_ajoute += 1

    print(f"{nombre_ajoute} nouvelle(s) leçon(s) ajoutée(s).")


# --------------------------------------------------
# 14. RÉCUPÉRER LES LEÇONS D'UNE PHASE
# --------------------------------------------------

def get_lessons_by_phase(phase):
    """
    Retourne toutes les leçons d'une phase,
    dans leur ordre pédagogique.
    """

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT id, phase, title, description, position
            FROM lessons
            WHERE phase = ?
            ORDER BY position ASC
        """, (phase,)).fetchall()

    return rows


# --------------------------------------------------
# 15. RÉCUPÉRER TOUTES LES LEÇONS
# --------------------------------------------------

def get_all_lessons():
    """
    Retourne toutes les leçons dans l'ordre du programme.
    """

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT id, phase, title, description, position
            FROM lessons
            ORDER BY phase ASC, position ASC
        """).fetchall()

    return rows

# --------------------------------------------------
# 16. TABLE DE PROGRESSION INDIVIDUELLE
# --------------------------------------------------

def initialize_progress_table():
    """
    Crée la table de progression individuelle.
    """

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS learner_lesson_progress (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                learner_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,

                status TEXT NOT NULL DEFAULT 'not_started'
                    CHECK (
                        status IN (
                            'not_started',
                            'in_progress',
                            'completed'
                        )
                    ),

                mastery_verified INTEGER NOT NULL DEFAULT 0
                    CHECK (mastery_verified IN (0, 1)),

                attempts INTEGER NOT NULL DEFAULT 0,

                notes TEXT DEFAULT '',

                started_at TEXT,
                completed_at TEXT,

                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (learner_id, lesson_id),

                FOREIGN KEY (learner_id)
                    REFERENCES learner(id),

                FOREIGN KEY (lesson_id)
                    REFERENCES lessons(id)
            )
        """)


# --------------------------------------------------
# 17. INITIALISER LA PROGRESSION D'UNE APPRENANTE
# --------------------------------------------------

def initialize_learner_progress(learner_id):
    """
    Crée une entrée de progression pour chaque leçon
    qui n'est pas encore associée à cette apprenante.
    """

    with get_connection() as connection:

        connection.execute("""
            INSERT OR IGNORE INTO learner_lesson_progress (
                learner_id,
                lesson_id
            )
            SELECT ?, id
            FROM lessons
        """, (learner_id,))


# --------------------------------------------------
# 18. COMMENCER UNE LEÇON
# --------------------------------------------------

def start_lesson(learner_id, lesson_id):
    """
    Marque une leçon comme commencée.
    """

    with get_connection() as connection:

        connection.execute("""
            INSERT OR IGNORE INTO learner_lesson_progress (
                learner_id,
                lesson_id
            )
            VALUES (?, ?)
        """, (learner_id, lesson_id))

        connection.execute("""
            UPDATE learner_lesson_progress
            SET status = 'in_progress',
                started_at = COALESCE(
                    started_at,
                    CURRENT_TIMESTAMP
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE learner_id = ?
              AND lesson_id = ?
              AND status != 'completed'
        """, (learner_id, lesson_id))

        connection.execute("""
            UPDATE learner
            SET current_lesson_id = ?
            WHERE id = ?
        """, (lesson_id, learner_id))


# --------------------------------------------------
# 19. ENREGISTRER UNE TENTATIVE
# --------------------------------------------------

def record_lesson_attempt(learner_id, lesson_id):
    """
    Incrémente le nombre de tentatives pour une leçon.
    """

    with get_connection() as connection:

        connection.execute("""
            INSERT OR IGNORE INTO learner_lesson_progress (
                learner_id,
                lesson_id
            )
            VALUES (?, ?)
        """, (learner_id, lesson_id))

        connection.execute("""
            UPDATE learner_lesson_progress
            SET attempts = attempts + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE learner_id = ?
              AND lesson_id = ?
        """, (learner_id, lesson_id))


# --------------------------------------------------
# 20. ENREGISTRER DES NOTES PÉDAGOGIQUES
# --------------------------------------------------

def update_lesson_notes(learner_id, lesson_id, notes):
    """
    Enregistre ou remplace les notes pédagogiques
    associées à une leçon.
    """

    with get_connection() as connection:

        connection.execute("""
            INSERT OR IGNORE INTO learner_lesson_progress (
                learner_id,
                lesson_id
            )
            VALUES (?, ?)
        """, (learner_id, lesson_id))

        connection.execute("""
            UPDATE learner_lesson_progress
            SET notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE learner_id = ?
              AND lesson_id = ?
        """, (notes, learner_id, lesson_id))


# --------------------------------------------------
# 21. TERMINER UNE LEÇON
# --------------------------------------------------

def complete_lesson(
    learner_id,
    lesson_id,
    mastery_verified=False,
    notes=""
):
    """
    Marque une leçon comme terminée.

    mastery_verified=True signifie que la compréhension
    a été vérifiée à l'aide d'éléments pédagogiques suffisants.
    """

    with get_connection() as connection:

        connection.execute("""
            INSERT OR IGNORE INTO learner_lesson_progress (
                learner_id,
                lesson_id
            )
            VALUES (?, ?)
        """, (learner_id, lesson_id))

        connection.execute("""
            UPDATE learner_lesson_progress
            SET status = 'completed',
                mastery_verified = ?,
                notes = ?,
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE learner_id = ?
              AND lesson_id = ?
        """, (
            1 if mastery_verified else 0,
            notes,
            learner_id,
            lesson_id
        ))


# --------------------------------------------------
# 22. RÉCUPÉRER LA PROGRESSION D'UNE APPRENANTE
# --------------------------------------------------

def get_learner_progress(learner_id):
    """
    Retourne toutes les leçons et leur progression
    pour une apprenante.
    """

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                lessons.id AS lesson_id,
                lessons.phase,
                lessons.position,
                lessons.title,
                lessons.description,

                COALESCE(
                    learner_lesson_progress.status,
                    'not_started'
                ) AS status,

                COALESCE(
                    learner_lesson_progress.mastery_verified,
                    0
                ) AS mastery_verified,

                COALESCE(
                    learner_lesson_progress.attempts,
                    0
                ) AS attempts,

                COALESCE(
                    learner_lesson_progress.notes,
                    ''
                ) AS notes,

                learner_lesson_progress.started_at,
                learner_lesson_progress.completed_at

            FROM lessons

            LEFT JOIN learner_lesson_progress
                ON lessons.id =
                    learner_lesson_progress.lesson_id
                AND learner_lesson_progress.learner_id = ?

            ORDER BY lessons.phase, lessons.position
        """, (learner_id,)).fetchall()

    return rows


# --------------------------------------------------
# 23. RÉCUPÉRER LA PROCHAINE LEÇON NON TERMINÉE
# --------------------------------------------------

def get_next_lesson(learner_id):
    """
    Retourne la première leçon non terminée
    dans l'ordre du programme.
    """

    with get_connection() as connection:

        row = connection.execute("""
            SELECT
                lessons.id,
                lessons.phase,
                lessons.position,
                lessons.title,
                lessons.description

            FROM lessons

            LEFT JOIN learner_lesson_progress
                ON lessons.id =
                    learner_lesson_progress.lesson_id
                AND learner_lesson_progress.learner_id = ?

            WHERE COALESCE(
                learner_lesson_progress.status,
                'not_started'
            ) != 'completed'

            ORDER BY lessons.phase ASC, lessons.position ASC
            LIMIT 1
        """, (learner_id,)).fetchone()

    return row


# --------------------------------------------------
# 24. RÉCUPÉRER LES NOTIONS À RÉVISER
# --------------------------------------------------

def get_lessons_to_review(learner_id):
    """
    Retourne les leçons terminées dont la maîtrise
    n'a pas encore été vérifiée.
    """

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                lessons.id,
                lessons.phase,
                lessons.title,
                learner_lesson_progress.notes

            FROM learner_lesson_progress

            JOIN lessons
                ON lessons.id =
                    learner_lesson_progress.lesson_id

            WHERE learner_lesson_progress.learner_id = ?
              AND learner_lesson_progress.status = 'completed'
              AND learner_lesson_progress.mastery_verified = 0

            ORDER BY lessons.phase, lessons.position
        """, (learner_id,)).fetchall()

    return rows


# --------------------------------------------------
# 25. CALCULER UN RÉSUMÉ DE PROGRESSION
# --------------------------------------------------

def get_progress_summary(learner_id):
    """
    Retourne le nombre total de leçons,
    les leçons terminées et les maîtrises vérifiées.
    """

    with get_connection() as connection:

        row = connection.execute("""
            SELECT
                COUNT(*) AS total_lessons,

                SUM(
                    CASE
                        WHEN status = 'completed' THEN 1
                        ELSE 0
                    END
                ) AS completed_lessons,

                SUM(
                    CASE
                        WHEN mastery_verified = 1 THEN 1
                        ELSE 0
                    END
                ) AS verified_lessons

            FROM learner_lesson_progress

            WHERE learner_id = ?
        """, (learner_id,)).fetchone()

    return row

if __name__ == "__main__":
    # 1. Créer les tables principales
    initialize_database()

    # 2. Créer la table de progression
    initialize_progress_table()

    # 3. Ajouter les leçons du programme
    seed_lessons()

    # 4. Retrouver ou créer le profil
    with get_connection() as connection:
        learner = connection.execute("""
            SELECT id
            FROM learner
            LIMIT 1
        """).fetchone()

    if learner is None:
        learner_id = create_learner("Apprenante", 15)
        print("Profil créé. Identifiant :", learner_id)
    else:
        learner_id = learner["id"]
        print("Profil existant. Identifiant :", learner_id)

    # 5. Créer les entrées de progression manquantes
    initialize_learner_progress(learner_id)

    print("Progression pédagogique initialisée.")
def get_previous_session(learner_id):
    """Récupère la dernière séance de l'apprenante et ses messages."""

    with get_connection() as conn:
        session = conn.execute(
            """
            SELECT
                sessions.id,
                sessions.lesson_id,
                sessions.started_at,
                sessions.summary,
                sessions.difficulties,
                lessons.title AS lesson_title
            FROM sessions
            LEFT JOIN lessons
                ON sessions.lesson_id = lessons.id
            WHERE sessions.learner_id = ?
            ORDER BY sessions.id DESC
            LIMIT 1
            """,
            (learner_id,)
        ).fetchone()

        if session is None:
            return None

        messages = conn.execute(
            """
            SELECT role, content, created_at
            FROM conversation_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session["id"],)
        ).fetchall()

    return {
        "session": dict(session),
        "messages": [dict(message) for message in messages]
    }