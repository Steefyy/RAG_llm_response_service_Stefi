import os
import logging
import httpx
from app.logging.logging_ctx import request_id_var, user_var
from app.core.models import Chunk, RerankRequest, RerankedChunk, RerankResponse

RERANKER_URL = os.environ.get("RERANKER_URL", "http://localhost:8002/api/rerank/chunks")
RAG_SERVICE_USERNAME = os.environ.get("RAG_SERVICE_USERNAME")
RAG_SERVICE_PASSWORD = os.environ.get("RAG_SERVICE_PASSWORD")
RERANKER_AUTH = (RAG_SERVICE_USERNAME, RAG_SERVICE_PASSWORD) if RAG_SERVICE_USERNAME and RAG_SERVICE_PASSWORD else None

log = logging.getLogger(__name__)


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
        for idx, doc in enumerate(contexte_brute):
            chunks_payload.append({
                "text": doc["text"],
                "score": 1.0, 
                "chunk_id": str(idx)
            })

        request_body = {
            "query": intrebare,
            "chunks": chunks_payload,
            "top_k": 8
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
                    idx = int(rc["chunk_id"])
                    if 0 <= idx < len(contexte_brute):
                        contexte_ordonate.append(contexte_brute[idx])
                return contexte_ordonate
            else:
                log.warning("reranker_status_neasteptat", extra={"status": response.status_code, "n_contexte": len(contexte_brute)})
    except Exception as e:
        log.warning("reranker_indisponibil", extra={"eroare": str(e), "n_contexte": len(contexte_brute)})
        
    return contexte_brute[:8]