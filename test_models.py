from openai import OpenAI

client = OpenAI(api_key=api_key)
MODEL_NAME = "gpt-5.6-luna"

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

# GROQ
from groq import Groq
client = Groq()
completion = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": "Explain why fast inference is critical for reasoning models"
        }
    ]
)
print(completion.choices[0].message.content)