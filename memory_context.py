from database.database import (
    get_learner,
    get_next_lesson,
    get_lessons_to_review,
    get_recent_sessions,
    get_progress_summary,
    get_mastery,
)


def build_learning_context(learner_id):
    """
    Construit le contexte pédagogique de l'apprenant
    à partir des informations enregistrées dans SQLite.
    """

    learner = get_learner(learner_id)

    if learner is None:
        raise ValueError(
            f"Aucun apprenant trouvé avec l'identifiant {learner_id}."
        )

    next_lesson = get_next_lesson(learner_id)
    lessons_to_review = get_lessons_to_review(learner_id)
    recent_sessions = get_recent_sessions(learner_id, limit=5)
    progress = get_progress_summary(learner_id)
    mastery = get_mastery(learner_id)

    # Informations générales sur l'apprenant
    context_parts = [
        "CONTEXTE PÉDAGOGIQUE DE L'APPRENANTE",
        f"Nom : {learner['name']}",
        f"Âge : {learner['age']} ans",
        f"Langue : {learner['language']}",
        "",
        "PROGRESSION GÉNÉRALE",
        f"Nombre total de leçons : {progress['total_lessons']}",
        f"Leçons terminées : {progress['completed_lessons'] or 0}",
        f"Maîtrises vérifiées : {progress['verified_lessons'] or 0}",
        "",
    ]

    # Prochaine leçon à aborder
    context_parts.append("PROCHAINE LEÇON")

    if next_lesson:
        context_parts.append(
            f"Phase : {next_lesson['phase']}"
        )
        context_parts.append(
            f"Titre : {next_lesson['title']}"
        )
        context_parts.append(
            f"Description : {next_lesson['description']}"
        )
    else:
        context_parts.append(
            "Toutes les leçons du programme sont terminées."
        )

    context_parts.append("")

    # Leçons terminées mais dont la maîtrise n'est pas vérifiée
    context_parts.append("LEÇONS À RÉVISER")

    if lessons_to_review:
        for lesson in lessons_to_review:
            context_parts.append(
                f"- {lesson['title']} (phase {lesson['phase']})"
            )
    else:
        context_parts.append("Aucune leçon à réviser pour le moment.")

    context_parts.append("")

    # Séances récentes
    context_parts.append("SÉANCES RÉCENTES")

    if recent_sessions:
        for session in recent_sessions:
            context_parts.append(
                f"- Date : {session['started_at']}"
            )
            context_parts.append(
                f"  Résumé : {session['summary'] or 'Aucun résumé enregistré.'}"
            )
            context_parts.append(
                f"  Difficultés : {session['difficulties'] or 'Aucune difficulté enregistrée.'}"
            )
    else:
        context_parts.append("Aucune séance précédente enregistrée.")

    context_parts.append("")

    # Niveau de maîtrise par notion
    context_parts.append("NIVEAU DE MAÎTRISE DES NOTIONS")

    if mastery:
        for item in mastery:
            context_parts.append(
                f"- {item['concept']} : niveau {item['level']}/3"
            )
            if item["notes"]:
                context_parts.append(
                    f"  Notes : {item['notes']}"
                )
    else:
        context_parts.append("Aucune maîtrise enregistrée.")

    return "\n".join(context_parts)