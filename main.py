from fastapi import FastAPI, HTTPException, Depends
from models import ChatRequest, ChatResponse, QuizRequest, FlashcardRequest
from llm_service import genereaza_raspuns, verifica_conexiune, genereaza_quiz, genereaza_flashcards
from prompt_builder import construieste_prompt, construieste_prompt_quiz, construieste_prompt_flashcards
from retrieval_service import cauta_context, cauta_contexte_scroll
from reranker_service import reordoneaza_contexte
from security_guard import valideaza_intrebare
from auth import verify_credentials

import logging

from logging_setup import setup_logging
from middleware import request_context
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()   # re-aplica: uvicorn si-a pus handlerele intre timp
    yield


app = FastAPI(title="RAG Chatbot Service", lifespan=lifespan)
app.middleware("http")(request_context)


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

    logger.info(
        "retrieval_done",
        extra={
            "n_brute": len(context_chunks_brute),
            "n_dupa_rerank": len(context_chunks),
            "chars_context": sum(len(c.get("text", "")) for c in context_chunks),
        },
    )

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


@app.post("/quiz/generate", dependencies=[Depends(verify_credentials)])
def generate_quiz(request: QuizRequest):
    # 1. Recuperăm fragmentele de text (chunks) din Qdrant
    context_chunks = cauta_contexte_scroll(
        curs_id=request.cursId,
        max_saptamana=request.maxSaptamana or 999,
        document_id=request.documentId
    )

    if not context_chunks:
        raise HTTPException(
            status_code=404,
            detail="Nu s-au găsit documente indexate pentru selecția curentă din care să generăm întrebări."
        )

    # 2. Construim promptul cu contextul extras
    prompt = construieste_prompt_quiz(context_chunks, request.nrIntrebari)

    # 3. Apelăm Gemini în format JSON
    try:
        json_response = genereaza_quiz(prompt)
    except Exception as e:
        print(f"[QUIZ GENERATION ERROR] Gemini call failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Serviciul de inteligență artificială este indisponibil pentru generarea quiz-ului."
        )

    import json
    try:
        # Validăm că e JSON valid
        quiz_data = json.loads(json_response)
        return quiz_data
    except Exception as e:
        print(f"[QUIZ PARSING ERROR] Failed to parse JSON response: {json_response}")
        raise HTTPException(
            status_code=500,
            detail="Nu s-a putut genera un test grilă valid în format JSON."
        )

@app.post("/flashcards/generate", dependencies=[Depends(verify_credentials)])
def generate_flashcards_endpoint(request: FlashcardRequest):
    # 1. Recuperăm fragmentele de text (chunks) din Qdrant
    context_chunks = cauta_contexte_scroll(
        curs_id=request.cursId,
        max_saptamana=request.maxSaptamana or 999,
        document_id=request.documentId
    )

    if not context_chunks:
        raise HTTPException(
            status_code=404,
            detail="Nu s-au găsit documente indexate pentru selecția curentă din care să generăm flashcard-uri."
        )

    # 2. Construim promptul cu contextul extras
    prompt = construieste_prompt_flashcards(context_chunks, request.nrFlashcards)

    # 3. Apelăm Gemini în format JSON
    try:
        json_response = genereaza_flashcards(prompt)
    except Exception as e:
        print(f"[FLASHCARDS GENERATION ERROR] Gemini call failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Serviciul de inteligență artificială este indisponibil pentru generarea flashcard-urilor."
        )

    import json
    try:
        # Validăm că e JSON valid
        flashcards_data = json.loads(json_response)
        return flashcards_data
    except Exception as e:
        print(f"[FLASHCARDS PARSING ERROR] Failed to parse JSON response: {json_response}")
        raise HTTPException(
            status_code=500,
            detail="Nu s-a putut genera un set de flashcard-uri valid în format JSON."
        )