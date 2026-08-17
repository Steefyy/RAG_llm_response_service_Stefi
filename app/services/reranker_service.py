import os
import httpx
from app.logging.logging_ctx import request_id_var, user_var
from app.core.models import Chunk, RerankRequest, RerankedChunk, RerankResponse

RERANKER_URL = os.environ.get("RERANKER_URL", "http://localhost:8002/api/rerank/chunks")
RAG_SERVICE_USERNAME = os.environ.get("RAG_SERVICE_USERNAME")
RAG_SERVICE_PASSWORD = os.environ.get("RAG_SERVICE_PASSWORD")
RERANKER_AUTH = (RAG_SERVICE_USERNAME, RAG_SERVICE_PASSWORD) if RAG_SERVICE_USERNAME and RAG_SERVICE_PASSWORD else None


def reordoneaza_contexte(intrebare: str, contexte_brute: list) -> list:
    """
    Trimite documentele brute catre serviciul de Reranker.
    Daca serviciul de reranking este offline sau returneaza o eroare,
    se revine la fallback-ul implicit (pastrarea primelor rezultate brute).
    """
    if not contexte_brute:
        return []
        
    try:
        # Pregatim payload-ul conform specificatiilor RerankRequest
        chunks_payload = []
        for doc in contexte_brute:
            chunks_payload.append({
                "text": doc["text"],
                "score": 1.0, 
                "chunk_id": str(doc["document_id"])
            })

        request_body = {
            "query": intrebare,
            "chunks": chunks_payload,
            "top_k": 5
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                RERANKER_URL,
                json=request_body,
                headers={"X-Request-ID": request_id_var.get(), "X-User": user_var.get()},
                auth=RERANKER_AUTH,
            )
            
            if response.status_code == 200:
                data = response.json()
                reranked_chunks = data.get("reranked_chunks", [])
                
                # Reordonam documentele originale pastrand metadatele (week_id, curs_id)
                contexte_ordonate = []
                for rc in reranked_chunks:
                    doc_id = int(rc["chunk_id"])
                    
                    original_doc = next((d for d in contexte_brute if d["document_id"] == doc_id), None)
                    if original_doc:
                        contexte_ordonate.append(original_doc)
                    else:
                        contexte_ordonate.append({
                            "document_id": doc_id,
                            "curs_id": 45,
                            "week_id": 1,
                            "text": rc["text"]
                        })
                return contexte_ordonate
    except Exception as e:
        print(f"[RERANKER WARNING] Serviciul Reranker offline sau eroare: {e}. Folosim fallback.")
        
    return contexte_brute[:5]