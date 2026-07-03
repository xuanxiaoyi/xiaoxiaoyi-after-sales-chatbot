import os
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings


EMBED_MODEL_NAME = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
DOCS_DIR = Path("docs")
CHROMA_DIR = Path("chroma")


def load_documents():
    documents = []
    for path in sorted(DOCS_DIR.rglob("*")):
        if not path.is_file():
            continue

        text = path.read_text(encoding="utf-8-sig")
        documents.append(
            Document(page_content=text, metadata={"source": str(path)})
        )

    return documents


if __name__ == "__main__":
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

    embeddings = OllamaEmbeddings(model=EMBED_MODEL_NAME)
    docs = load_documents()
    Chroma.from_documents(
        docs,
        embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="planetbucks",
    )
    print(f"Indexed {len(docs)} documents with {EMBED_MODEL_NAME}.")
