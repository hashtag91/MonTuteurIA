import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv("groq_api_key"),
    base_url="https://api.groq.com/openai/v1",
)

response = client.responses.create(
    model="openai/gpt-oss-120b",
    instructions=(
        "Tu es un professeur d'informatique bienveillant. "
        "Tu enseignes en français à une débutante de 15 ans."
    ),
    input="Présente-toi en deux phrases et explique ce qu'est un algorithme.",
)

print(response.output_text)
