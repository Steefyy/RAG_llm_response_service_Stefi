import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

def genereaza_raspuns(prompt: str) -> str:
    # Setam temperature=0.2 pentru ca raspunsurile sa ramana precise, academice si factuale
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2
        )
    )
    return response.text

def verifica_conexiune() -> bool:
    """
    Verifica daca conexiunea la Gemini si cheia API sunt active.
    Folosim list_models deoarece este un apel rapid de metadate, 
    care nu consuma tokeni de generare si valideaza instant cheia.
    """
    try:
        client.models.list()
        return True
    except Exception:
        return False

def genereaza_quiz(prompt: str) -> str:
    """
    Generează un set de întrebări grilă sub formă de JSON structurat folosind Gemini.
    """
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.85,
            response_mime_type="application/json"
        )
    )
    return response.text

def genereaza_flashcards(prompt: str) -> str:
    """
    Generează un set de flashcard-uri sub formă de JSON structurat folosind Gemini.
    """
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json"
        )
    )
    return response.text

