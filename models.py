from pydantic import BaseModel
from typing import List

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

class QuizRequest(BaseModel):
    cursId: int
    maxSaptamana: int = None
    documentId: int = None
    nrIntrebari: int = 5
    dificultate: str = "MEDIU"

class FlashcardRequest(BaseModel):
    cursId: int
    maxSaptamana: int = None
    documentId: int = None
    nrFlashcards: int = 5

