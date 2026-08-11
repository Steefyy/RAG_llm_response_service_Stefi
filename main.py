import json
import re

from fastapi import FastAPI, HTTPException, Depends
from models import ChatRequest, ChatResponse, QuizGenerateRequest, QuizRequest, QuizQuestion, FlashcardGenerateRequest, FlashcardItem
from llm_service import genereaza_raspuns, verifica_conexiune, genereaza_quiz as genereaza_quiz_llm
from prompt_builder import construieste_prompt, construieste_prompt_quiz, construieste_prompt_flashcards
from retrieval_service import cauta_context, cauta_contexte_scroll
from reranker_service import reordoneaza_contexte
from security_guard import valideaza_intrebare
from auth import verify_credentials
from logging_setup import setup_logging
from middleware import request_context

setup_logging()

app = FastAPI(title="RAG Chatbot Service")
app.middleware("http")(request_context)

def _extrage_json(text: str):
    cleaned = re.sub(r"```(?:json)?|```", "", text or "", flags=re.IGNORECASE).strip()
    starts = [idx for idx in (cleaned.find("["), cleaned.find("{")) if idx != -1]
    if starts:
        start = min(starts)
        end = max(cleaned.rfind("]"), cleaned.rfind("}"))
        if end > start:
            cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


def _normalizeaza_quiz(raw) -> list[QuizQuestion]:
    items = raw.get("intrebari") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []

    questions = []
    for item in items:
        if not isinstance(item, dict):
            continue

        optiuni_raw = item.get("optiuni") or item.get("options") or {}
        if isinstance(optiuni_raw, list):
            optiuni = {chr(65 + index): str(value) for index, value in enumerate(optiuni_raw[:4])}
        elif isinstance(optiuni_raw, dict):
            optiuni = {str(key): str(value) for key, value in optiuni_raw.items()}
        else:
            optiuni = {}

        if not item.get("intrebare") or not optiuni:
            continue

        questions.append(QuizQuestion(
            intrebare=str(item.get("intrebare")),
            optiuni=optiuni,
            raspuns_corect=str(item.get("raspuns_corect") or item.get("raspunsCorect") or item.get("correct_answer") or ""),
            explicatie=str(item.get("explicatie") or item.get("explanation") or ""),
            dificultate=str(item.get("dificultate") or "")
        ))

    return questions


@app.get("/health")
def health():
    connected = verifica_conexiune()
    status = "ok" if connected else "degraded"
    return {
        "status": status,
        "llm_provider": "gemini",
        "llm_connected": connected
    }

@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_credentials)])
def chat(request: ChatRequest):
    # 0. Rulam filtrul de securitate local (Prompt Injection Guard) - 100% Gratuit si Offline
    status_securitate = valideaza_intrebare(request.intrebare)
    if not status_securitate.safe:
        return ChatResponse(
            raspuns=(
                f"Cerere respinsă din motive de securitate. Întrebarea conține instrucțiuni nepermise. "
                f"Motiv: {status_securitate.reason}"
            ),
            surseFolosite=[]
        )

    # 1. Cautam si filtram contextul semantic din Qdrant
    context_chunks_brute = cauta_context(
        request.intrebare, request.cursId, request.maxSaptamanaParcursa
    )

    # 2. Reordonam si selectam cele mai relevante 5 propozitii prin Reranker (Persoana C)
    context_chunks = reordoneaza_contexte(request.intrebare, context_chunks_brute)

    # 3. Construim promptul cu contextul si istoricul trimis de monolit
    prompt = construieste_prompt(request.intrebare, request.istoricConversatie, context_chunks)

    # 4. Apelam LLM-ul (Gemini) cu parametrii de temperatura aplicati
    try:
        raspuns_text = genereaza_raspuns(prompt)
    except Exception:
        raise HTTPException(
            status_code=503, 
            detail="Serviciul LLM este momentan indisponibil. Incearca din nou in cateva momente."
        )

    # 5. Extragem document_id-urile ca surse folosite
    surse_folosite = list(set([c["document_id"] for c in context_chunks]))

    return ChatResponse(raspuns=raspuns_text, surseFolosite=surse_folosite)


@app.post("/quiz/generate", response_model=list[QuizQuestion], dependencies=[Depends(verify_credentials)])
def genereaza_quiz(request: QuizGenerateRequest):
    nr_intrebari = max(1, min(request.nrIntrebari or 5, 20))
    max_saptamana = request.maxSaptamanaParcursa
    if max_saptamana is None:
        max_saptamana = request.maxSaptamana if request.maxSaptamana is not None else 999

    context_chunks = cauta_contexte_scroll(
        request.cursId,
        max_saptamana,
        request.documentId,
    )
    if not context_chunks:
        return []

    prompt = construieste_prompt_quiz(context_chunks, nr_intrebari, request.dificultate or "MEDIU")

    try:
        raspuns_text = genereaza_quiz_llm(prompt)
        return _normalizeaza_quiz(_extrage_json(raspuns_text))
    except Exception as e:
        print(f"[QUIZ GENERATION ERROR] {e}")
        raise HTTPException(
            status_code=503,
            detail="Serviciul de inteligenta artificiala este indisponibil pentru generarea quiz-ului."
        )


def _normalizeaza_flashcards(raw) -> list[FlashcardItem]:
    items = raw.get("flashcards") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []

    flashcards = []
    for item in items:
        if not isinstance(item, dict):
            continue

        fata = item.get("fata") or item.get("front") or item.get("question") or item.get("concept")
        verso = item.get("verso") or item.get("back") or item.get("answer") or item.get("definition")

        if not fata or not verso:
            continue

        flashcards.append(FlashcardItem(
            fata=str(fata),
            verso=str(verso)
        ))

    return flashcards


@app.post("/flashcards/generate", response_model=list[FlashcardItem], dependencies=[Depends(verify_credentials)])
def genereaza_flashcards(request: FlashcardGenerateRequest):
    nr_flashcards = max(1, min(request.nrFlashcards or 5, 20))
    max_saptamana = request.maxSaptamanaParcursa
    if max_saptamana is None:
        max_saptamana = request.maxSaptamana if request.maxSaptamana is not None else 999

    context_chunks = cauta_contexte_scroll(
        request.cursId,
        max_saptamana,
        request.documentId,
    )
    if not context_chunks:
        return []

    prompt = construieste_prompt_flashcards(context_chunks, nr_flashcards)

    try:
        raspuns_text = genereaza_quiz_llm(prompt)
        return _normalizeaza_flashcards(_extrage_json(raspuns_text))
    except Exception as e:
        print(f"[FLASHCARDS GENERATION ERROR] {e}")
        raise HTTPException(
            status_code=503,
            detail="Serviciul de inteligenta artificiala este indisponibil pentru generarea flashcard-urilor."
        )