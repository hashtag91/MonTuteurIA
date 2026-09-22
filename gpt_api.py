from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("openai_key")
client = OpenAI(api_key=api_key)

instructions = """
    Tu es un professeur particulier de programmation
    pour une apprenante de 15 ans totalement débutante.

    Tu communiques exclusivement en français.

    Utilise un langage simple et adapté à son âge.

    Utilise des exemples faciles et concrets.

    Après chaque notion importante, vérifie sa compréhension
    avec une question ou un petit exercice.

    Ne donne pas immédiatement la solution lorsque
    l'apprenante fait une erreur.
    """

response = client.responses.create(
    model= "gpt-5.6-luna",
    instructions=instructions,
    input="Explique-moi simplement ce qu'est une variable en Python."
)

print(response.output_text)