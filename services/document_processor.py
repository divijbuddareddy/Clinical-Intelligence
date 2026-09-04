import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pypdf
try:
    import docx
except ImportError:
    docx = None

class DocumentProcessor:
    @staticmethod
    def extract_text(file_path: str, mime_type: str = None) -> Tuple[str, List[Dict[str, Any]], int]:
        """
        Extracts plain text and page/section breakdowns from supported file formats.
        Returns: (full_text, pages_data, page_count)
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        pages_data = []
        full_text = ""

        if ext == ".pdf":
            try:
                reader = pypdf.PdfReader(str(path))
                page_count = len(reader.pages)
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    cleaned_page_text = DocumentProcessor.clean_text(page_text)
                    if cleaned_page_text:
                        pages_data.append({
                            "page_number": idx + 1,
                            "text": cleaned_page_text,
                            "section": DocumentProcessor.infer_section_title(cleaned_page_text)
                        })
                        full_text += f"\n--- Page {idx + 1} ---\n" + cleaned_page_text
                return full_text.strip(), pages_data, page_count
            except Exception as e:
                raise RuntimeError(f"Failed to extract text from PDF: {e}")

        elif ext in [".docx", ".doc"] and docx:
            try:
                doc = docx.Document(str(path))
                doc_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                cleaned_text = DocumentProcessor.clean_text(doc_text)
                pages_data.append({
                    "page_number": 1,
                    "text": cleaned_text,
                    "section": "Document Content"
                })
                return cleaned_text, pages_data, 1
            except Exception as e:
                raise RuntimeError(f"Failed to extract text from DOCX: {e}")

        else:
            # Plain text, markdown, csv, or generic text
            try:
                with open(str(path), "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                cleaned_text = DocumentProcessor.clean_text(content)
                pages_data.append({
                    "page_number": 1,
                    "text": cleaned_text,
                    "section": DocumentProcessor.infer_section_title(cleaned_text)
                })
                return cleaned_text, pages_data, 1
            except Exception as e:
                raise RuntimeError(f"Failed to extract text file: {e}")

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans and standardizes raw text."""
        if not text:
            return ""
        # Remove null bytes
        text = text.replace("\x00", "")
        # Normalize multiple spaces and non-standard whitespace
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize multiple newlines
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return text.strip()

    @staticmethod
    def infer_section_title(text: str) -> str:
        """Infers clinical section title from headers in text."""
        headers = [
            "CHIEF COMPLAINT", "HISTORY OF PRESENT ILLNESS", "PAST MEDICAL HISTORY",
            "PHYSICAL EXAMINATION", "LABORATORY FINDINGS", "LABORATORY RESULTS",
            "ASSESSMENT AND PLAN", "DISCHARGE SUMMARY", "MEDICATIONS", "ALLERGIES",
            "IMPRESSION", "DIAGNOSIS", "RECOMMENDATIONS", "CLINICAL COURSE"
        ]
        for h in headers:
            if re.search(rf"\b{re.escape(h)}\b", text, re.IGNORECASE):
                return h.title()
        
        # Take first non-empty line up to 60 chars
        first_line = text.split("\n")[0].strip()
        if first_line and len(first_line) < 60:
            return first_line
        return "Clinical Note Section"

    @staticmethod
    def chunk_document(
        pages_data: List[Dict[str, Any]],
        chunk_size: int = 450,
        overlap: int = 80
    ) -> List[Dict[str, Any]]:
        """
        Splits extracted pages/text into overlapping chunks while tracking page number and section title.
        """
        chunks = []
        chunk_counter = 0

        for page in pages_data:
            page_num = page.get("page_number", 1)
            section = page.get("section", "General Section")
            text = page.get("text", "")
            
            words = text.split()
            if not words:
                continue

            if len(words) <= chunk_size:
                chunks.append({
                    "chunk_index": chunk_counter,
                    "text": text,
                    "page_number": page_num,
                    "section_title": section,
                    "token_count": len(words)
                })
                chunk_counter += 1
                continue

            # Sliding window chunking
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                
                # Try to refine section title from within chunk
                chunk_section = DocumentProcessor.infer_section_title(chunk_text) or section

                chunks.append({
                    "chunk_index": chunk_counter,
                    "text": chunk_text,
                    "page_number": page_num,
                    "section_title": chunk_section,
                    "token_count": len(chunk_words)
                })
                chunk_counter += 1

                if end == len(words):
                    break
                start += max(1, chunk_size - overlap)

        return chunks
