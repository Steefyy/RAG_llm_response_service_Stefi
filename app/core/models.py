from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    studentId: int
    cursId: int
    maxSaptamanaParcursa: int
    intrebare: str
    istoricConversatie: List[Message] = []

class ChatResponse(BaseModel):
    raspuns: str
    surseFolosite: List[int] = []

class QuizGenerateRequest(BaseModel):
    cursId: int
    maxSaptamanaParcursa: Optional[int] = None
    maxSaptamana: Optional[int] = None
    documentId: Optional[int] = None
    nrIntrebari: Optional[int] = 5
    dificultate: Optional[str] = "MEDIU"

class QuizRequest(QuizGenerateRequest):
    pass

class QuizQuestion(BaseModel):
    intrebare: str
    optiuni: dict[str, str]
    raspuns_corect: str
    explicatie: str
    dificultate: Optional[str] = None

class FlashcardGenerateRequest(BaseModel):
    cursId: int
    maxSaptamanaParcursa: Optional[int] = None
    maxSaptamana: Optional[int] = None
    documentId: Optional[int] = None
    nrFlashcards: Optional[int] = 5

class FlashcardItem(BaseModel):
    fata: str
    verso: str

# Reranker contract models
class Chunk(BaseModel):
    text: str
    score: float
    chunk_id: str

class RerankRequest(BaseModel):
    query: str
    chunks: list[Chunk]
    top_k: int

class RerankedChunk(BaseModel):
    text: str
    rerank_score: float
    chunk_id: str
    original_rank: int

class RerankResponse(BaseModel):
    reranked_chunks: list[RerankedChunk]

