"""Incremental FAISS retrieval for curated agricultural PDF chunks."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


AI_SERVICE = Path(__file__).resolve().parents[1]
DOCS_DIR = AI_SERVICE / "data" / "agri_docs"
PROCESSED_DIR = DOCS_DIR / "processed"
CATALOG_PATH = Path(__file__).with_name("document_catalog.json")
VECTOR_DIR = Path(__file__).with_name("vector_store")
MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_THRESHOLD = 0.40


def read_jsonl(file_path: Path) -> list[dict[str, Any]]:
    with file_path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


@dataclass
class RetrievalResult:
    status: str
    query: str
    threshold: float
    matches: list[dict[str, Any]]
    diagnostic_candidates: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class RAGRetriever:
    """Persistent, append-friendly FAISS index with explicit coverage safeguards."""

    def __init__(self, model_name: str = MODEL_NAME, vector_dir: Path = VECTOR_DIR, catalog_path: Path = CATALOG_PATH, threshold: float = DEFAULT_THRESHOLD) -> None:
        self.model_name = model_name
        self.vector_dir = vector_dir
        self.catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.threshold = threshold
        self.model: SentenceTransformer | None = None
        self.index: faiss.IndexIDMap2 | None = None
        self.metadata: dict[str, Any] = {}

    @property
    def index_path(self) -> Path:
        return self.vector_dir / "chunks.faiss"

    @property
    def manifest_path(self) -> Path:
        return self.vector_dir / "index_manifest.json"

    def _model(self) -> SentenceTransformer:
        if self.model is None:
            # Docker sets SENTENCE_TRANSFORMERS_HOME to the model cache baked
            # into its Linux image.  Leaving it unset preserves the normal
            # local/Colab cache behaviour used in Stages 3–4.
            cache_folder = os.environ.get("SENTENCE_TRANSFORMERS_HOME")
            kwargs = {"cache_folder": cache_folder} if cache_folder else {}
            self.model = SentenceTransformer(self.model_name, **kwargs)
        return self.model

    def _load(self) -> None:
        if not self.index_path.exists() or not self.manifest_path.exists():
            raise FileNotFoundError("FAISS index is absent. Run retriever.py --build-index first.")
        self.index = faiss.read_index(str(self.index_path))
        self.metadata = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if self.metadata["embedding_model"] != self.model_name:
            raise RuntimeError("Index embedding model differs from the configured model; rebuild the index.")

    def build_incremental(self, processed_dir: Path = PROCESSED_DIR) -> dict[str, int]:
        ingestion_path = processed_dir / "ingestion_manifest.json"
        if not ingestion_path.exists():
            raise FileNotFoundError("No processed-document manifest. Run ingest.py first.")
        ingestion = json.loads(ingestion_path.read_text(encoding="utf-8"))
        processing_version = ingestion.get("processing_version", "1.0")
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        if self.index_path.exists() and self.manifest_path.exists():
            self._load()
        else:
            self.metadata = {"embedding_model": self.model_name, "processing_version": processing_version, "documents": {}, "chunks": {}, "next_id": 0}

        # A cleaner/chunker change invalidates every document's old vectors,
        # even when its source PDF hash is unchanged.
        self.metadata["processing_version"] = processing_version

        added_chunks = skipped_documents = updated_documents = 0
        for source_file, document in sorted(ingestion["documents"].items()):
            if source_file not in self.catalog:
                raise ValueError(f"{source_file} is missing from {CATALOG_PATH.name}; add its coverage metadata first.")
            indexed = self.metadata["documents"].get(source_file)
            if (
                indexed
                and indexed.get("source_sha256") == document["source_sha256"]
                and indexed.get("processing_version") == processing_version
            ):
                skipped_documents += 1
                continue
            if indexed:
                old_ids = np.array(indexed["chunk_ids"], dtype=np.int64)
                assert self.index is not None
                self.index.remove_ids(old_ids)
                for old_id in indexed["chunk_ids"]:
                    self.metadata["chunks"].pop(str(old_id), None)
                updated_documents += 1
            records = read_jsonl(processed_dir / document["chunk_file"])
            if not records:
                continue
            embeddings = self._model().encode([record["text"] for record in records], normalize_embeddings=True, show_progress_bar=True).astype("float32")
            if self.index is None:
                self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(embeddings.shape[1]))
            chunk_ids = np.arange(self.metadata["next_id"], self.metadata["next_id"] + len(records), dtype=np.int64)
            self.index.add_with_ids(embeddings, chunk_ids)
            self.metadata["next_id"] += len(records)
            self.metadata["documents"][source_file] = {
                "source_sha256": document["source_sha256"],
                "processing_version": processing_version,
                "chunk_ids": chunk_ids.tolist(),
            }
            catalog_entry = self.catalog[source_file]
            for chunk_id, record in zip(chunk_ids.tolist(), records):
                self.metadata["chunks"][str(chunk_id)] = {**record, "coverage": catalog_entry["coverage"], "partial_coverage": catalog_entry["partial_coverage"], "document_note": catalog_entry["note"]}
            added_chunks += len(records)

        if self.index is None:
            raise RuntimeError("No chunks were available to index.")
        faiss.write_index(self.index, str(self.index_path))
        self.manifest_path.write_text(json.dumps(self.metadata, indent=2) + "\n", encoding="utf-8")
        return {"added_chunks": added_chunks, "updated_documents": updated_documents, "skipped_documents": skipped_documents, "total_chunks": self.index.ntotal}

    def _raw_candidates(self, query: str) -> list[dict[str, Any]]:
        if self.index is None:
            self._load()
        assert self.index is not None
        vector = self._model().encode([query], normalize_embeddings=True).astype("float32")
        scores, ids = self.index.search(vector, self.index.ntotal)
        return [{"score": round(float(score), 6), **self.metadata["chunks"][str(identifier)]} for score, identifier in zip(scores[0].tolist(), ids[0].tolist()) if identifier >= 0]

    def retrieve(self, query: str, disease_class: str | None = None, top_k: int = 3) -> RetrievalResult:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if disease_class:
            allowed_sources = {filename for filename, entry in self.catalog.items() if disease_class in entry["coverage"]}
            if not allowed_sources:
                # Exact-coverage gaps must not be filled from the broad
                # supplementary PDF or another class's document.
                return RetrievalResult("no_reference_document", query, self.threshold, [], [])
            if self.index is None:
                self._load()
            # Covered diagnoses use an exact class → document lookup. Include
            # every chunk in that small registered document, independent of
            # semantic score, so symptoms and management sections survive.
            assert self.metadata
            matches = [
                chunk
                for chunk in self.metadata["chunks"].values()
                if chunk["source_file"] in allowed_sources
            ]
            matches.sort(key=lambda chunk: (chunk["source_file"], chunk["chunk_id"]))
            # These chunks are selected by catalog coverage, not similarity;
            # remove any stale score value if the index metadata has one.
            matches = [{key: value for key, value in chunk.items() if key != "score"} for chunk in matches]
            return RetrievalResult("ok" if matches else "no_reference_document", query, self.threshold, matches, [])
        raw = self._raw_candidates(query)
        diagnostic = [{key: candidate[key] for key in ("score", "source_file", "chunk_id", "text")} for candidate in raw[:top_k]]
        matches = [candidate for candidate in raw if candidate["score"] >= self.threshold][:top_k]
        return RetrievalResult("ok" if matches else "below_similarity_threshold", query, self.threshold, matches, diagnostic)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--query")
    parser.add_argument("--disease-class")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()
    retriever = RAGRetriever(threshold=args.threshold)
    if args.build_index:
        print(json.dumps(retriever.build_incremental(), indent=2))
    if args.query:
        print(json.dumps(retriever.retrieve(args.query, args.disease_class, args.top_k).to_dict(), indent=2, ensure_ascii=False))
    if not args.build_index and not args.query:
        parser.error("Specify --build-index and/or --query")


if __name__ == "__main__":
    main()
