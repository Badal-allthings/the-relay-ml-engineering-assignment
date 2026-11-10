
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Check your root .env file."
    )

client = Groq(api_key=api_key)

models = client.models.list()

print("Models available to your Groq account:\n")

for model in models.data:
    if getattr(model, "active", False):
        print(model.id)
