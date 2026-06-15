#!/usr/bin/env python3
"""
Aletheia Advanced RAG Engine
Author: Senior AI Architect
Description:
    Implements the semantic document splitting (chunking), local vector storage indexing,
    and hybrid query-time reranking using local HuggingFace embeddings and BGE Cross-Encoder models.

    Heavy models (embedding + cross-encoder) and the Chroma client are loaded ONCE as
    process-wide singletons. Each verification request operates on its own isolated
    collection (keyed by a session id) so concurrent requests never clobber each other.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AletheiaRAGEngine")

# ==========================================
# Process-wide shared resources (loaded once)
# ==========================================

_SHARED: Dict[str, Any] = {}


def _get_shared(db_path: str) -> Dict[str, Any]:
    """
    Lazily loads and caches the expensive, stateless resources: the Chroma
    persistent client, the embedding model, the cross-encoder re-ranker, and
    the text splitter. Subsequent calls return the cached instances.
    """
    if _SHARED:
        return _SHARED

    logger.info("Loading shared Aletheia RAG resources (one-time)...")
    os.makedirs(db_path, exist_ok=True)

    _SHARED["client"] = chromadb.PersistentClient(path=db_path)

    logger.info("Loading sentence embedding model 'all-MiniLM-L6-v2'...")
    _SHARED["embed_model"] = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    logger.info("Loading BGE Cross-Encoder re-ranker 'BAAI/bge-reranker-base'...")
    _SHARED["rerank_model"] = CrossEncoder("BAAI/bge-reranker-base")

    _SHARED["splitter"] = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
    )
    logger.info("Shared RAG resources ready.")
    return _SHARED


class AletheiaRAGEngine:
    def __init__(self, session_id: Optional[str] = None, db_path: str = "./chroma_db"):
        """
        Initializes a session-scoped view over the shared RAG resources.

        Args:
            session_id: Unique id for this verification run. When provided, the engine
                operates on an isolated, per-request collection so parallel requests do
                not interfere. When omitted, a fresh random session is generated.
            db_path: Persistent Chroma storage path.
        """
        try:
            shared = _get_shared(db_path)
            self.client = shared["client"]
            self.embed_model = shared["embed_model"]
            self.rerank_model = shared["rerank_model"]
            self.splitter = shared["splitter"]

            self.session_id = session_id or uuid.uuid4().hex
            self.collection_name = f"aletheia_{self.session_id}"

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"RAG session collection ready: '{self.collection_name}'")

        except Exception as e:
            logger.critical(f"RAG Engine initialization failed: {e}")
            raise e

    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Processes, chunks, and indexes a list of raw documents into the vector database.

        Args:
            documents: List of dicts, each having 'text', 'source_url', 'timestamp', and 'initial_trust_score'.

        Returns:
            bool: True if indexing succeeded, False otherwise.
        """
        if not documents:
            logger.warning("No documents provided to add_documents.")
            return False

        try:
            logger.info(f"Processing {len(documents)} document(s) for indexing...")
            chunk_texts = []
            chunk_metadatas = []
            chunk_ids = []

            for idx, doc in enumerate(documents):
                text = doc.get("text", "").strip()
                if not text:
                    logger.warning(f"Document at index {idx} has no text content. Skipping.")
                    continue

                # Extract metadata with defaults
                metadata = {
                    "source_url": doc.get("source_url", "unknown"),
                    "timestamp": doc.get("timestamp", ""),
                    "initial_trust_score": float(doc.get("initial_trust_score", 1.0)),
                }

                # Split document text into chunks
                chunks = self.splitter.split_text(text)
                logger.info(f"Split document {idx+1} ({metadata['source_url']}) into {len(chunks)} chunks.")

                for chunk_idx, chunk in enumerate(chunks):
                    chunk_texts.append(chunk)
                    # Add chunk tracking metadata
                    chunk_meta = metadata.copy()
                    chunk_meta["chunk_index"] = chunk_idx
                    chunk_metadatas.append(chunk_meta)
                    # Generate a unique ID
                    chunk_ids.append(f"{uuid.uuid4().hex}_{chunk_idx}")

            if not chunk_texts:
                logger.warning("No valid text chunks generated for indexing.")
                return False

            # Generate embeddings
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
            embeddings = self.embed_model.encode(chunk_texts, show_progress_bar=False)

            # Convert numpy embeddings to standard list of lists for Chroma
            embeddings_list = [emb.tolist() for emb in embeddings]

            # Add to collection
            logger.info("Writing chunks to ChromaDB...")
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings_list,
                metadatas=chunk_metadatas,
                documents=chunk_texts,
            )
            logger.info("Successfully indexed all document chunks.")
            return True

        except Exception as e:
            logger.error(f"Error while indexing documents: {e}")
            return False

    def query_and_rerank(self, query: str, top_n: int = 3, min_trust_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Retrieves matching chunks, scores them using BGE Cross-Encoder, and returns top N chunks.

        Args:
            query: The user's research query.
            top_n: Number of high-confidence results to return.
            min_trust_score: Drop candidate chunks whose source trust score is below this
                threshold before re-ranking (0.0 keeps everything).

        Returns:
            List of dicts, sorted by relevancy score descending.
        """
        logger.info(f"Executing query & rerank for query: '{query}'")
        try:
            # 1. Check if collection is empty
            if self.collection.count() == 0:
                logger.warning("Vector database is currently empty. Cannot retrieve results.")
                return []

            # 2. Embed the user query
            query_vector = self.embed_model.encode(query).tolist()

            # 3. Retrieve first 15 candidate matches
            retrieve_limit = min(15, max(self.collection.count(), 1))
            logger.info(f"Retrieving top {retrieve_limit} candidates from ChromaDB...")

            raw_results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=retrieve_limit,
            )

            # 4. Parse retrieved results
            candidates = []
            if raw_results and raw_results.get("documents") and raw_results["documents"][0]:
                ids = raw_results["ids"][0]
                docs = raw_results["documents"][0]
                metas = raw_results["metadatas"][0]

                for i in range(len(docs)):
                    meta = metas[i] or {}
                    # Apply source-trust threshold filtering
                    if float(meta.get("initial_trust_score", 1.0)) < min_trust_score:
                        continue
                    candidates.append({
                        "id": ids[i],
                        "text": docs[i],
                        "metadata": meta,
                    })

            if not candidates:
                logger.info("No candidates found in ChromaDB search (after trust filtering).")
                return []

            # 5. Rerank candidates using Cross-Encoder model
            logger.info(f"Re-ranking {len(candidates)} candidates using BGE Cross-Encoder...")
            pairs = [[query, cand["text"]] for cand in candidates]
            scores = self.rerank_model.predict(pairs)

            # 6. Map scores and sort
            for i, cand in enumerate(candidates):
                cand["rerank_score"] = float(scores[i])

            # Sort descending by Cross-Encoder score
            candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

            # Select top N results
            final_results = candidates[:top_n]
            logger.info(f"Re-ranking completed. Selected top {len(final_results)} results.")
            return final_results

        except Exception as e:
            logger.error(f"Error during query_and_rerank execution: {e}")
            return []

    def clear_database(self) -> bool:
        """
        Clears all items inside the active session collection.
        """
        try:
            logger.info(f"Clearing session collection '{self.collection_name}'...")
            ids = self.collection.get()["ids"]
            if ids:
                self.collection.delete(ids=ids)
            logger.info("Session collection cleared successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False

    def drop(self) -> bool:
        """
        Permanently removes this session's collection from the vector store.
        Should be called once a verification run is fully complete.
        """
        try:
            logger.info(f"Dropping session collection '{self.collection_name}'...")
            self.client.delete_collection(self.collection_name)
            return True
        except Exception as e:
            logger.warning(f"Failed to drop collection '{self.collection_name}': {e}")
            return False
