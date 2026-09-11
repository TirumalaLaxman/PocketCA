"""
PocketCA - Retrieval-Augmented Generation (RAG) Engine
Loads and indexes accounting and GST documents, provides semantic search,
and manages dynamic document ingestion.
Supports FAISS with Google Generative AI Embeddings with a resilient fallback
TF-IDF vector search engine when running offline or without an API key.
"""

import os
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path(__file__).parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEX_DIR = Path(__file__).parent / "vector_store"


os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)


class Chunk:
    def __init__(self, text: str, source: str, page: int):
        self.text = text
        self.source = source
        self.page = page

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "page": self.page
        }


class FallbackSearchEngine:
    """
    Lightweight, fast in-memory TF-IDF / BM25 style similarity search.
    Ensures PocketCA can always retrieve relevant tax & accounting rules
    even before the user provides a Google API key.
    """
    def __init__(self):
        self.chunks: List[Chunk] = []
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.doc_lengths: List[int] = []
        self.idf: Dict[str, float] = {}
        self.avg_doc_len: float = 0.0

    def _tokenize(self, text: str) -> List[str]:
        # Normalize and tokenize alphanumeric terms
        words = re.findall(r'\b[a-zA-Z0-9_\-\.\₹\%]+\b', text.lower())
        return [w for w in words if len(w) > 1]

    def index_chunks(self, chunks: List[Chunk]):
        self.chunks = chunks
        self.doc_term_freqs = []
        self.doc_lengths = []
        doc_count = len(chunks)
        df: Dict[str, int] = {}

        for ch in chunks:
            tokens = self._tokenize(ch.text)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs.append(tf)
            self.doc_lengths.append(len(tokens))
            for t in tf.keys():
                df[t] = df.get(t, 0) + 1

        self.avg_doc_len = (sum(self.doc_lengths) / max(1, doc_count)) if doc_count > 0 else 1.0
        self.idf = {}
        for term, freq in df.items():
            # BM25-style IDF
            self.idf[term] = math.log(1.0 + (doc_count - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        k1 = 1.5
        b = 0.75
        scores = []

        for idx, tf in enumerate(self.doc_term_freqs):
            doc_len = self.doc_lengths[idx]
            score = 0.0
            for qt in query_tokens:
                if qt in tf:
                    term_freq = tf[qt]
                    idf_val = self.idf.get(qt, 1.0)
                    numerator = term_freq * (k1 + 1.0)
                    denominator = term_freq + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                    score += idf_val * (numerator / denominator)
            scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            if score > 0.05:  # Relevance threshold
                ch = self.chunks[idx]
                results.append({
                    "text": ch.text,
                    "source": ch.source,
                    "page": ch.page,
                    "score": round(float(score), 3)
                })

        return results


class RAGEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.chunks: List[Chunk] = []
        self.fallback_engine = FallbackSearchEngine()
        self.faiss_store = None
        self.embeddings = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=750,
            chunk_overlap=120,
            separators=["\n\n", "\n", "•", ".", ";", " ", ""]
        )
        self.is_initialized = False

    def extract_text_from_pdf(self, pdf_path: Path) -> List[Chunk]:
        chunks = []
        try:
            reader = PdfReader(str(pdf_path))
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()
                if not text:
                    continue
                # Split page text into manageable chunks
                sub_chunks = self.text_splitter.split_text(text)
                for sc in sub_chunks:
                    if len(sc.strip()) > 30:
                        chunks.append(Chunk(text=sc.strip(), source=pdf_path.name, page=page_num))
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
        return chunks

    def extract_text_from_file(self, file_path: Path) -> List[Chunk]:
        if file_path.suffix.lower() == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif file_path.suffix.lower() in [".txt", ".md", ".csv"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                sub_chunks = self.text_splitter.split_text(content)
                return [Chunk(text=sc.strip(), source=file_path.name, page=1) for sc in sub_chunks if len(sc.strip()) > 20]
            except Exception as e:
                print(f"Error reading text file {file_path}: {e}")
                return []
        return []

    def set_api_key(self, api_key: str):
        if api_key and api_key != self.api_key:
            self.api_key = api_key
            self._try_init_faiss()

    def _try_init_faiss(self):
        if not self.api_key or not self.chunks:
            return

        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            from langchain_community.vectorstores import FAISS

            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=self.api_key
            )

            texts = [c.text for c in self.chunks]
            metadatas = [{"source": c.source, "page": c.page} for c in self.chunks]

            self.faiss_store = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            # Save to disk
            self.faiss_store.save_local(str(INDEX_DIR))
            print("FAISS vector store successfully created and saved to disk.")
        except Exception as e:
            print(f"Notice: FAISS Google Embeddings initialization deferred ({e}). Fallback engine remains active.")
            self.faiss_store = None

    def initialize(self):
        """
        Load standard knowledge base files from data/ directory and build index.
        """
        all_chunks: List[Chunk] = []

        # 1. Load primary knowledge base PDFs from data/
        for fname in ["accounting.pdf", "gst.pdf"]:
            fpath = DATA_DIR / fname
            if fpath.exists() and fpath.stat().st_size > 0:
                extracted = self.extract_text_from_pdf(fpath)
                all_chunks.extend(extracted)
                print(f"Indexed {len(extracted)} chunks from {fname}")

        # 2. Also load any user-uploaded files from data/uploads/
        if UPLOADS_DIR.exists():
            for fpath in UPLOADS_DIR.iterdir():
                if fpath.is_file() and fpath.stat().st_size > 0:
                    extracted = self.extract_text_from_file(fpath)
                    all_chunks.extend(extracted)
                    print(f"Indexed {len(extracted)} chunks from uploaded file: {fpath.name}")

        self.chunks = all_chunks
        self.fallback_engine.index_chunks(all_chunks)
        print(f"Total knowledge base chunks indexed: {len(all_chunks)}")

        # 3. If API key available, attempt FAISS creation
        if self.api_key:
            self._try_init_faiss()

        self.is_initialized = True

    def ingest_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Dynamically ingest a newly uploaded user file into the knowledge base.
        """
        new_chunks = self.extract_text_from_file(file_path)
        if not new_chunks:
            return {"success": False, "error": "No extractable text found in file."}

        self.chunks.extend(new_chunks)
        self.fallback_engine.index_chunks(self.chunks)

        if self.faiss_store and self.embeddings:
            try:
                texts = [c.text for c in new_chunks]
                metadatas = [{"source": c.source, "page": c.page} for c in new_chunks]
                self.faiss_store.add_texts(texts=texts, metadatas=metadatas)
                self.faiss_store.save_local(str(INDEX_DIR))
            except Exception as e:
                print(f"Notice: Failed to update FAISS store ({e}). Fallback store updated.")

        return {
            "success": True,
            "filename": file_path.name,
            "chunks_added": len(new_chunks),
            "total_chunks": len(self.chunks)
        }

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search knowledge base for top matching documents.
        Uses FAISS if available; otherwise uses fallback BM25 search.
        """
        if not self.is_initialized:
            self.initialize()

        if self.faiss_store:
            try:
                docs_and_scores = self.faiss_store.similarity_search_with_score(query, k=top_k)
                results = []
                for doc, score in docs_and_scores:
                    results.append({
                        "text": doc.page_content,
                        "source": doc.metadata.get("source", "Knowledge Base"),
                        "page": doc.metadata.get("page", 1),
                        "score": round(float(score), 3)
                    })
                if results:
                    return results
            except Exception as e:
                print(f"FAISS search encountered error: {e}. Falling back to BM25 engine.")

        # Fallback search
        return self.fallback_engine.search(query, top_k=top_k)


# Singleton RAG instance
rag_engine = RAGEngine()
