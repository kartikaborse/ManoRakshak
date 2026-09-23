#!/usr/bin/env python
"""
ManoKart — CLI tool to trigger RAG indexing
============================================
This script manually re-indexes the vector database using clinical documents and intents.
"""

import sys
import os

# Ensure the root folder is in the Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.rag_engine import index_knowledge_base, check_ollama_model

def main():
    embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    print(f"Checking if embedding model '{embed_model}' is available locally...")
    
    if not check_ollama_model(embed_model):
        print(f"\n⚠️  Warning: Model '{embed_model}' is not pulled in Ollama.")
        print(f"Please run: ollama pull {embed_model}")
        print("Continuing anyway, but embeddings might fail to generate.\n")
    else:
        print(f"✅ Embedding model '{embed_model}' is available.\n")
        
    print("Starting vector database indexing...")
    index_knowledge_base()
    print("Indexing completed!")

if __name__ == "__main__":
    main()
