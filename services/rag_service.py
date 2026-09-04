from typing import Dict, Any, List
from datetime import datetime, timezone
from config import Config
from models.database import db
from models.document_model import Document, DocumentChunk, DocumentStatus
from models.patient_model import Patient
from models.report_model import Report, ReportStatus
from models.audit_model import log_audit, AuditAction
from services.document_processor import DocumentProcessor
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStoreService
from services.gemini_service import GeminiService, UNSUPPORTED_FALLBACK_MESSAGE

class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService(dimension=Config.EMBEDDING_DIMENSION)
        self.vector_store = VectorStoreService(dimension=Config.EMBEDDING_DIMENSION)
        self.gemini_service = GeminiService()

    def process_and_index_document(self, document_id: int, user_id: int = None) -> Dict[str, Any]:
        """
        Executes end-to-end document ingestion:
        File -> Text Extraction -> Cleaning -> Chunking -> Embeddings -> FAISS Vector Store -> DB Chunks
        """
        doc = db.session.get(Document, document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        doc.status = DocumentStatus.PROCESSING
        db.session.commit()

        try:
            # 1. Text Extraction & Cleaning
            full_text, pages_data, page_count = DocumentProcessor.extract_text(doc.file_path)
            doc.page_count = page_count

            # 2. Chunking
            raw_chunks = DocumentProcessor.chunk_document(
                pages_data,
                chunk_size=Config.CHUNK_SIZE,
                overlap=Config.CHUNK_OVERLAP
            )

            if not raw_chunks:
                # If file had minimal text
                raw_chunks = [{
                    "chunk_index": 0,
                    "text": full_text or "Empty document",
                    "page_number": 1,
                    "section_title": "General",
                    "token_count": len(full_text.split())
                }]

            # 3. Embedding Generation
            chunk_texts = [c["text"] for c in raw_chunks]
            vectors = self.embedding_service.embed_batch(chunk_texts)

            # 4. Remove previous chunks if re-processing
            DocumentChunk.query.filter_by(document_id=doc.id).delete()

            # 5. Insert DB DocumentChunks & Prepare Vector Metadata
            chunks_meta = []
            for i, chunk_data in enumerate(raw_chunks):
                vec_ref = f"doc_{doc.id}_chunk_{i}"
                chunk_obj = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk_data["chunk_index"],
                    text=chunk_data["text"],
                    section_title=chunk_data.get("section_title", "Clinical Finding"),
                    page_number=chunk_data.get("page_number", 1),
                    token_count=chunk_data.get("token_count", 0),
                    vector_reference=vec_ref
                )
                db.session.add(chunk_obj)
                
                chunks_meta.append({
                    "chunk_id": vec_ref,
                    "document_id": doc.id,
                    "document_filename": doc.original_filename,
                    "patient_id": doc.patient_id,
                    "chunk_index": chunk_data["chunk_index"],
                    "page_number": chunk_data.get("page_number", 1),
                    "section_title": chunk_data.get("section_title", "Clinical Finding"),
                    "text": chunk_data["text"]
                })

            db.session.commit()

            # 6. Index into FAISS Vector Store
            self.vector_store.add_chunks(doc.patient_id, vectors, chunks_meta)

            # 7. Update Document Status
            doc.status = DocumentStatus.INDEXED
            doc.processed_at = datetime.now(timezone.utc)
            db.session.commit()

            # Audit Log
            log_audit(
                action=AuditAction.DOC_PROCESS,
                resource_type="Document",
                resource_id=doc.id,
                details=f"Successfully indexed document '{doc.original_filename}' with {len(raw_chunks)} chunks.",
                user_id=user_id
            )

            return {
                "success": True,
                "document_id": doc.id,
                "chunks_count": len(raw_chunks),
                "status": doc.status
            }

        except Exception as e:
            db.session.rollback()
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            db.session.commit()
            raise RuntimeError(f"Processing failed for document {document_id}: {e}")

    def ask_grounded_question(self, patient_id: int, question: str, user_id: int = None, api_key: str = None) -> Report:
        """
        Executes RAG Q&A Pipeline:
        Question -> Query Embedding -> FAISS Top-K -> Context + Gemini LLM -> Grounded Answer + Citations -> Report
        """
        gemini_svc = GeminiService(api_key=api_key) if api_key else self.gemini_service
        # Re-check configuration dynamically
        if not gemini_svc.is_configured():
            # Check if runtime key is available
            gemini_svc = GeminiService()
            if not gemini_svc.is_configured():
                raise ValueError(
                    "Gemini AI API Key Required. Please set your Google Gemini API Key in the AI Settings (top right navbar) to enable grounded clinical analysis."
                )

        patient = db.session.get(Patient, patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # 1. Query Embedding
        q_vector = self.embedding_service.embed_text(question)

        # 2. FAISS Similarity Search (patient-isolated)
        retrieved_chunks = self.vector_store.search(
            patient_id=patient_id,
            query_vector=q_vector,
            top_k=Config.TOP_K_CHUNKS
        )

        # 3. Grounded Answer Generation with Gemini
        answer, is_grounded = gemini_svc.generate_grounded_answer(
            question=question,
            retrieved_chunks=retrieved_chunks,
            patient_meta=patient.to_dict()
        )

        # 4. Citation Mapping
        citations = []
        for chunk in retrieved_chunks:
            citations.append({
                "document_id": chunk.get("document_id"),
                "document_filename": chunk.get("document_filename"),
                "page_number": chunk.get("page_number", 1),
                "section_title": chunk.get("section_title", "Clinical Context"),
                "snippet": chunk.get("text", "")[:280] + ("..." if len(chunk.get("text", "")) > 280 else ""),
                "full_text": chunk.get("text", ""),
                "similarity_score": round(float(chunk.get("score", 0.0)), 4)
            })

        # 5. Persist Report in SQL Database
        report = Report(
            patient_id=patient_id,
            question=question,
            raw_answer=answer,
            answer=answer,
            sources=citations,
            status=ReportStatus.GENERATED,
            is_grounded=is_grounded,
            reviewed_by=user_id if is_grounded else None
        )
        db.session.add(report)
        db.session.commit()

        # Audit Log
        log_audit(
            action=AuditAction.RAG_QUERY,
            resource_type="Report",
            resource_id=report.id,
            details=f"Asked question: '{question[:60]}...' | Retrieved {len(retrieved_chunks)} chunks | Grounded: {is_grounded}",
            user_id=user_id
        )

        return report
