import os
import requests
from dotenv import load_dotenv
from app.core.logging_ctx import request_id_var, user_var

import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Documente simulate pe cursuri si saptamani (metadate)
try:
    from tests.mock_data import MOCK_DOCUMENTS
except ImportError:
    MOCK_DOCUMENTS = []


def obtine_embedding_intrebare(intrebare: str) -> list[float] | None:
    """
    Apeleaza Embedder Service (POST /api/query/embed) pentru a obtine vectorul de embedding al intrebarii.
    """
    embedder_url = os.environ.get("EMBEDDER_URL", "http://localhost:8001/api/query/embed")
    try:
        response = requests.post(
            embedder_url,
            json={"text": intrebare},
            auth=(
                os.environ.get("RAG_SERVICE_USERNAME", "akadion-spring-backend"),
                os.environ.get("RAG_SERVICE_PASSWORD", "parola_spring_rag"),
            ),
            headers={"X-Request-ID": request_id_var.get(), "X-User": user_var.get()},
            timeout=30.0,
        )
        if response.status_code == 200:
            data = response.json()
            embedding = data.get("embedding")
            logger.info(
                "embedding_obtinut",
                extra={"dim": len(embedding) if embedding else 0},
            )
            return embedding
        else:
            logger.warning(
                "embedder_status_neasteptat",
                extra={"status": response.status_code, "url": embedder_url},
            )
    except Exception as e:
        logger.warning(
            "embedder_indisponibil",
            extra={"url": embedder_url, "error": str(e)},
        )
    return None


def cauta_context(intrebare: str, curs_id: int, max_saptamana: int) -> list[dict]:
    """
    Cauta context semantic pentru o intrebare data, filtrat dupa curs_id si saptamana maxima parcursa.
    Efectueaza o cautare vectoriala pe Qdrant daca use_mock este fals.
    """
    use_mock = os.environ.get("USE_QDRANT_MOCK", "true").lower() in ("true", "1", "yes")

    if not use_mock:
        try:
            # Preluare embedding intrebare
            query_vector = obtine_embedding_intrebare(intrebare)

            if query_vector:
                from qdrant_client import QdrantClient
                from qdrant_client.http import models

                host = os.environ.get("QDRANT_HOST", "localhost")
                port = int(os.environ.get("QDRANT_PORT", 6333))
                collection = os.environ.get("QDRANT_COLLECTION", "course_chunks")

                client = QdrantClient(host=host, port=port, timeout=10.0)

                # Filtrare dupa curs si saptamana parcursa
                scroll_filter = models.Filter(
                    should=[
                        models.FieldCondition(key="course_id", match=models.MatchValue(value=curs_id)),
                        models.FieldCondition(key="curs_id", match=models.MatchValue(value=curs_id))
                    ],
                    must=[
                        models.FieldCondition(key="week_id", range=models.Range(lte=max_saptamana))
                    ]
                )

                # Cautare vectorială semantică
                if hasattr(client, "search"):
                    search_results = client.search(
                        collection_name=collection,
                        query_vector=query_vector,
                        query_filter=scroll_filter,
                        limit=10
                    )
                else:
                    response_qp = client.query_points(
                        collection_name=collection,
                        query=query_vector,
                        query_filter=scroll_filter,
                        limit=10
                    )
                    search_results = response_qp.points

                logger.info(
                    "vector_search_done",
                    extra={
                        "curs_id": curs_id,
                        "max_saptamana": max_saptamana,
                        "collection": collection,
                        "n_results": len(search_results),
                        "scores": [round(getattr(pt, "score", 0) or 0, 4) for pt in search_results],
                        "doc_ids": [(pt.payload or {}).get("document_id") for pt in search_results],
                    },
                )

                contexte_qdrant = []
                for pt in search_results:
                    payload = pt.payload or {}
                    text_content = payload.get("chunk_text") or payload.get("text", "")
                    c_id = payload.get("course_id") or payload.get("curs_id", curs_id)
                    doc_id = payload.get("document_id", 999)
                    w_id = payload.get("week_id", max_saptamana)

                    contexte_qdrant.append({
                        "document_id": int(doc_id) if str(doc_id).isdigit() else 999,
                        "curs_id": int(c_id),
                        "week_id": int(w_id),
                        "text": str(text_content)
                    })

                if contexte_qdrant:
                    logger.info(
                        "context_din_qdrant",
                        extra={
                            "n_chunks": len(contexte_qdrant),
                            "chars_total": sum(len(c["text"]) for c in contexte_qdrant),
                            "preview": [c["text"][:80] for c in contexte_qdrant[:3]],
                        },
                    )
                    return contexte_qdrant

                logger.warning(
                    "qdrant_zero_rezultate",
                    extra={"curs_id": curs_id, "max_saptamana": max_saptamana},
                )
            else:
                logger.warning("vector_lipsa_fallback_mock", extra={"curs_id": curs_id})
        except Exception as e:
            logger.warning(
                "qdrant_eroare_fallback_mock",
                extra={"curs_id": curs_id, "error": str(e)},
            )

    # Cautare pe date predefinite (Fallback)
    contexte_gasite = []
    cuvinte_intrebare = set([w for w in intrebare.lower().split() if len(w) > 2])

    for doc in MOCK_DOCUMENTS:
        if doc["curs_id"] == curs_id and doc["week_id"] <= max_saptamana:
            cuvinte_doc = set([w for w in doc["text"].lower().split() if len(w) > 2])
            if cuvinte_intrebare.intersection(cuvinte_doc):
                contexte_gasite.append(doc)

    logger.warning(
        "context_din_mock",
        extra={"n_chunks": len(contexte_gasite), "use_mock": use_mock, "curs_id": curs_id},
    )
    return contexte_gasite


def cauta_contexte_scroll(curs_id: int, max_saptamana: int, document_id: int = None, limit: int = 15) -> list[dict]:
    """
    Recupereaza chunks din Qdrant prin scroll, fara cautare vectoriala.
    Filtrul se bazeaza pe ID-ul cursului/saptamanii sau document_id.
    """
    use_mock = os.environ.get("USE_QDRANT_MOCK", "true").lower() in ("true", "1", "yes")
    import random

    if not use_mock:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            host = os.environ.get("QDRANT_HOST", "localhost")
            port = int(os.environ.get("QDRANT_PORT", 6333))
            collection = os.environ.get("QDRANT_COLLECTION", "course_chunks")

            client = QdrantClient(host=host, port=port, timeout=10.0)

            # Filtre Qdrant
            must_conditions = []
            if document_id is not None:
                must_conditions.append(models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)))
            else:
                must_conditions.append(models.FieldCondition(key="week_id", range=models.Range(lte=max_saptamana)))
                must_conditions.append(models.Filter(
                    should=[
                        models.FieldCondition(key="course_id", match=models.MatchValue(value=curs_id)),
                        models.FieldCondition(key="curs_id", match=models.MatchValue(value=curs_id))
                    ]
                ))

            scroll_filter = models.Filter(must=must_conditions)

            # Scroll pe mai multe puncte
            scroll_results, _ = client.scroll(
                collection_name=collection,
                scroll_filter=scroll_filter,
                limit=100,
                with_payload=True,
                with_vectors=False
            )

            logger.info(
                "scroll_done",
                extra={
                    "curs_id": curs_id,
                    "document_id": document_id,
                    "max_saptamana": max_saptamana,
                    "n_scroll": len(scroll_results),
                    "limit_returnat": limit,
                },
            )

            contexte_qdrant = []
            for pt in scroll_results:
                payload = pt.payload or {}
                text_content = payload.get("chunk_text") or payload.get("text", "")
                c_id = payload.get("course_id") or payload.get("curs_id", curs_id)
                doc_id = payload.get("document_id", 999)
                w_id = payload.get("week_id", max_saptamana)

                contexte_qdrant.append({
                    "document_id": int(doc_id) if str(doc_id).isdigit() else 999,
                    "curs_id": int(c_id),
                    "week_id": int(w_id),
                    "text": str(text_content)
                })

            if contexte_qdrant:
                random.shuffle(contexte_qdrant)
                return contexte_qdrant[:limit]

            logger.warning(
                "scroll_zero_rezultate",
                extra={"curs_id": curs_id, "document_id": document_id},
            )

        except Exception as e:
            logger.warning(
                "scroll_eroare_fallback_mock",
                extra={"curs_id": curs_id, "error": str(e)},
            )

    # Fallback pe date predefinite
    contexte_gasite = []
    for doc in MOCK_DOCUMENTS:
        if document_id is not None:
            if doc.get("document_id") == document_id:
                contexte_gasite.append(doc)
        else:
            if doc["curs_id"] == curs_id and doc["week_id"] <= max_saptamana:
                contexte_gasite.append(doc)

    logger.warning(
        "scroll_context_din_mock",
        extra={"n_chunks": len(contexte_gasite), "use_mock": use_mock, "curs_id": curs_id},
    )

    random.shuffle(contexte_gasite)
    return contexte_gasite[:limit]