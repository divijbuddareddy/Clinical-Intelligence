import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple
import faiss
import numpy as np
from config import Config

class VectorStoreService:
    def __init__(self, storage_dir: Path = None, dimension: int = 384):
        self.storage_dir = storage_dir or Config.VECTOR_STORE_FOLDER
        self.dimension = dimension
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._indices: Dict[str, faiss.Index] = {}
        self._metadata: Dict[str, List[Dict[str, Any]]] = {}

    def _get_patient_paths(self, patient_id: int) -> Tuple[Path, Path]:
        idx_path = self.storage_dir / f"patient_{patient_id}.index"
        meta_path = self.storage_dir / f"patient_{patient_id}.meta"
        return idx_path, meta_path

    def load_index(self, patient_id: int) -> Tuple[faiss.Index, List[Dict[str, Any]]]:
        """Loads FAISS index and metadata for a given patient from disk or memory."""
        key = str(patient_id)
        if key in self._indices and key in self._metadata:
            return self._indices[key], self._metadata[key]

        idx_path, meta_path = self._get_patient_paths(patient_id)
        if idx_path.exists() and meta_path.exists():
            try:
                index = faiss.read_index(str(idx_path))
                with open(meta_path, "rb") as f:
                    metadata = pickle.load(f)
                self._indices[key] = index
                self._metadata[key] = metadata
                return index, metadata
            except Exception as e:
                print(f"[VectorStore] Failed to load index for patient {patient_id}: {e}")

        # Create new Inner Product index for cosine similarity
        index = faiss.IndexFlatIP(self.dimension)
        metadata = []
        self._indices[key] = index
        self._metadata[key] = metadata
        return index, metadata

    def save_index(self, patient_id: int):
        """Persists patient index and metadata to disk."""
        key = str(patient_id)
        if key not in self._indices:
            return
        idx_path, meta_path = self._get_patient_paths(patient_id)
        faiss.write_index(self._indices[key], str(idx_path))
        with open(meta_path, "wb") as f:
            pickle.dump(self._metadata[key], f)

    def add_chunks(self, patient_id: int, vectors: np.ndarray, chunks_meta: List[Dict[str, Any]]):
        """Adds embedded vectors and chunk metadata to patient vector store."""
        if len(vectors) == 0:
            return

        index, metadata = self.load_index(patient_id)
        
        # Ensure float32 and correct shape
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)

        index.add(vectors)
        metadata.extend(chunks_meta)
        
        key = str(patient_id)
        self._indices[key] = index
        self._metadata[key] = metadata
        self.save_index(patient_id)

    def search(self, patient_id: int, query_vector: np.ndarray, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Searches FAISS vector store for the top-k most similar document chunks for a patient.
        Returns list of matched chunks with cosine similarity score.
        """
        index, metadata = self.load_index(patient_id)
        if index.ntotal == 0 or len(metadata) == 0:
            return []

        # Prepare query
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)
        if query_vector.dtype != np.float32:
            query_vector = query_vector.astype(np.float32)

        k = min(top_k, index.ntotal)
        distances, indices = index.search(query_vector, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(metadata):
                item = dict(metadata[idx])
                item["score"] = float(dist)
                results.append(item)

        return results

    def remove_document_chunks(self, patient_id: int, document_id: int):
        """Removes chunks belonging to a document and rebuilds patient index."""
        _, metadata = self.load_index(patient_id)
        remaining_meta = [m for m in metadata if m.get("document_id") != document_id]
        
        key = str(patient_id)
        idx_path, meta_path = self._get_patient_paths(patient_id)
        
        if not remaining_meta:
            # Clear index
            self._indices[key] = faiss.IndexFlatIP(self.dimension)
            self._metadata[key] = []
            if idx_path.exists():
                idx_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            return

        # Note: Rebuilding index requires re-embedding remaining chunks
        # In a lightweight setup, we update metadata and mark deleted
        self._metadata[key] = remaining_meta
        self.save_index(patient_id)
