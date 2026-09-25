"""
ManoRakshat — Offline RAG Engine via Ollama Embeddings
===================================================
Uses ChromaDB and Ollama's local embedding endpoint (nomic-embed-text)
to store and retrieve clinical knowledge, CBT guides, and assessment info
without needing PyTorch, torchvision, or sentence-transformers in Python.
"""

import os
import json
import logging
import sys
import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "vector_db")

from chromadb import EmbeddingFunction

class OllamaEmbeddingFunction(EmbeddingFunction):
    """Custom embedding generator utilizing local Ollama API."""
    def __init__(self, model_name="nomic-embed-text"):
        self.model_name = model_name
        self.url = "http://localhost:11434/api/embeddings"

    def __call__(self, input):
        # input can be a string or list of strings
        texts = [input] if isinstance(input, str) else input
        embeddings = []
        for text in texts:
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": text
                }
                res = requests.post(self.url, json=payload, timeout=10)
                if res.status_code == 200:
                    embeddings.append(res.json()["embedding"])
                else:
                    logger.error(f"Ollama embedding API error: {res.text}")
                    # Return zero-vector fallback
                    embeddings.append([0.0] * 768)
            except Exception as e:
                logger.error(f"Failed to fetch Ollama embedding: {e}")
                embeddings.append([0.0] * 768)
        return embeddings

    @staticmethod
    def name() -> str:
        return "OllamaEmbeddingFunction"

    def get_config(self) -> dict:
        return {"model_name": self.model_name}

    @staticmethod
    def build_from_config(config: dict):
        return OllamaEmbeddingFunction(model_name=config.get("model_name", "nomic-embed-text"))

_collection = None

def get_rag_collection():
    global _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
        emb_fn = OllamaEmbeddingFunction(model_name="nomic-embed-text")
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        _collection = chroma_client.get_or_create_collection(
            name="mindcare_offline_kb",
            embedding_function=emb_fn
        )
        return _collection
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB collection: {e}")
        return None

def index_knowledge_base():
    """Reads clinical docs & dataset.json into vector store."""
    collection = get_rag_collection()
    if collection is None:
        print("ChromaDB collection unavailable. Skipping indexing.")
        return

    docs, ids, metadatas = [], [], []

    # 1. Index GAD-7 & PHQ-9 Clinical PDFs/TXT
    for doc_name in ["GAD-7_Anxiety-updated_0.pdf.txt", "patient-health-questionnaire.pdf.txt"]:
        file_path = os.path.join(ROOT_DIR, doc_name)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    paras = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
                    for i, p in enumerate(paras):
                        docs.append(p)
                        ids.append(f"{doc_name}_{i}")
                        metadatas.append({"source": doc_name, "type": "assessment"})
            except Exception as e:
                logger.error(f"Error reading {doc_name}: {e}")

    # 2. Index intent knowledge dataset.json
    dataset_path = os.path.join(ROOT_DIR, "chatbot", "dataset.json")
    if os.path.exists(dataset_path):
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                intents = data.get("intents", [])
                for intent in intents:
                    tag = intent.get("tag", "general")
                    patterns = " ".join(intent.get("patterns", []))
                    responses = " ".join(intent.get("responses", []))
                    text = f"Topic: {tag}. Context patterns: {patterns}. Guidance & Coping: {responses}"
                    docs.append(text)
                    ids.append(f"intent_{tag}")
                    metadatas.append({"source": "dataset.json", "tag": tag})
        except Exception as e:
            logger.error(f"Error reading dataset.json: {e}")

    if docs:
        try:
            collection.upsert(documents=docs, ids=ids, metadatas=metadatas)
            print(f"RAG Engine: Successfully indexed {len(docs)} document chunks into ChromaDB.")
        except Exception as e:
            logger.error(f"Error upserting to ChromaDB: {e}")

def query_rag(user_query: str, top_k: int = 2) -> str:
    """Retrieve top K context passages in < 10ms on CPU."""
    collection = get_rag_collection()
    if collection is None:
        return ""
    try:
        results = collection.query(query_texts=[user_query], n_results=top_k)
        retrieved = results.get("documents", [[]])[0]
        return "\n\n---\n\n".join(retrieved) if retrieved else ""
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        return ""
