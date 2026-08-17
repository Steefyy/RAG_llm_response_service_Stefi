# Academic RAG System — Chat & Content Orchestrator

Sistem integrat de **Asistent Academic Inteligent (RAG)** dezvoltat în FastAPI și bazat pe microservicii pentru o platformă universitară. Acest microserviciu orchestrează fluxul de interogare (chat), precum și generarea automată de materiale de studiu (Quiz-uri și Flashcards).

## 🎓 Descriere Generală

Sistemul furnizează răspunsuri precise și generări structurate pe baza suporturilor de curs furnizate de profesori:
1. **Prevenirea halucinațiilor (Strict Grounding)**: Răspunde **exclusiv** pe baza documentelor de curs reale (PDF/Word), evitând adăugarea de cunoștințe exterioare.
2. **Izolarea cunoștințelor pe săptămâni**: Un student dintr-o anumită săptămână de curs are acces strict la informațiile din săptămânile deja finalizate de el.
3. **Scut anti-Prompt injection**: Filtru de securitate local offline (Jailbreak protection) pentru blocarea tentativelor de manipulare a instrucțiunilor AI-ului.
4. **Generare de materiale (Nou)**: Generează teste grilă multiple-choice (cu răspunsuri corecte și explicații) și fișe de memorare (Flashcards concept-definiție) în format structurat (JSON Mode via Gemini).
5. **Arhitectură RAG **: Vectorizare prin Embedder (`BAAI/bge-m3`), căutare semantică în Qdrant și reclasificare de mare precizie prin CrossEncoder Reranker (`mmarco-mMiniLMv2`).

---

> 📘 **Documentația Detaliată a Arhitecturii**:  
> Pentru explicații exhaustive ale fiecărui microserviciu, diagrame de flux Mermaid și configurări detaliate, deschideți [DOCUMENTATIE_RAG.md](docs/DOCUMENTATIE_RAG.md).

---

## 🚀 Rulare Rapidă (Docker Compose)

Porniți întreaga suită de servicii (Chat & LLM Response, Embedder, Reranker și baza de date vectorială Qdrant):

```powershell
# Accesați directorul RAG
cd rag

# 1. Configurați cheia API Gemini în .env din folderul llm-response
copy llm-response/.env.example llm-response/.env

# 2. Lansare containere
docker compose up --build
```

### Dashboard-uri & Interfețe Swagger UI:
- **Chat & LLM Response Orchestrator API (Port 8000)**: `http://localhost:8000/docs`
  * *Rute expuse*: `/chat`, `/quiz/generate`, `/flashcards/generate`, `/health`
- **Embedder Service API (Port 8001)**: `http://localhost:8001/docs`
  * *Rute expuse*: `/api/documents/ingest`, `/api/documents/{document_id}`, `/api/query/embed`, `/api/health`
- **Reranker Service API (Port 8002)**: `http://localhost:8002/docs`
  * *Rute expuse*: `/api/rerank/chunks`, `/api/health`
- **Qdrant Vector DB (Port 6333)**: `http://localhost:6333/dashboard`
