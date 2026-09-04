import os
import re
import json
import requests
from typing import List, Dict, Any, Tuple
from config import Config

UNSUPPORTED_FALLBACK_MESSAGE = "The uploaded documents do not contain enough information to answer this."

SYSTEM_SAFETY_INSTRUCTION = (
    "You are a Clinical Workflow Intelligence assistant designed to help healthcare staff review clinical documents. "
    "CRITICAL SAFETY CONSTRAINTS:\n"
    "1. You are a clinical-information review assistant, NOT a clinician. Do not offer autonomous diagnoses or prescribe treatment plans.\n"
    "2. ANSWER ONLY FROM THE PROVIDED CONTEXT. Do not speculate or introduce medical facts not present in the supplied document text.\n"
    "3. If the context does not contain sufficient facts to answer the question accurately, you MUST reply with exactly: "
    f"'{UNSUPPORTED_FALLBACK_MESSAGE}'\n"
    "4. For every clinical fact, reference the source using citation tags in format [Doc: <filename>, Page: <page>, Section: <section>]."
)

def sanitize_key(key: str) -> str:
    if not key:
        return ""
    # Strip whitespace, single quotes, double quotes, backticks
    return key.strip().strip("'\"` \t\r\n")

def normalize_model_name(model: str) -> str:
    if not model:
        return "gemini-1.5-flash"
    clean = model.strip()
    if clean.startswith("models/"):
        clean = clean.replace("models/", "")
    return clean

# Runtime stored API key (if set via UI or .env)
_RUNTIME_GEMINI_KEY = sanitize_key(os.getenv("GEMINI_API_KEY", ""))
_RUNTIME_GEMINI_MODEL = normalize_model_name(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))

class GeminiService:
    def __init__(self, api_key: str = None, model_name: str = None):
        raw_key = api_key or _RUNTIME_GEMINI_KEY or os.getenv("GEMINI_API_KEY", "")
        self.api_key = sanitize_key(raw_key)
        self.model_name = normalize_model_name(model_name or _RUNTIME_GEMINI_MODEL)
        self.client = None

    @classmethod
    def set_runtime_key(cls, key: str, model: str = "gemini-1.5-flash"):
        global _RUNTIME_GEMINI_KEY, _RUNTIME_GEMINI_MODEL
        _RUNTIME_GEMINI_KEY = sanitize_key(key)
        if model:
            _RUNTIME_GEMINI_MODEL = normalize_model_name(model)

    @classmethod
    def get_runtime_key(cls) -> str:
        global _RUNTIME_GEMINI_KEY
        return _RUNTIME_GEMINI_KEY or sanitize_key(os.getenv("GEMINI_API_KEY", ""))

    @classmethod
    def get_runtime_model(cls) -> str:
        global _RUNTIME_GEMINI_MODEL
        return _RUNTIME_GEMINI_MODEL or "gemini-1.5-flash"

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def validate_api_key(self) -> Tuple[bool, str]:
        """
        Validates the API key directly against Google AI Studio's ModelService endpoint.
        Returns: (is_valid, message)
        """
        clean_key = sanitize_key(self.api_key)
        if not clean_key or len(clean_key) < 10:
            return False, "Please enter a valid Google Gemini API Key (starts with AIzaSy...)."

        try:
            # Query Google's ModelService to list supported models for this key
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
            res = requests.get(url, timeout=12)
            
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
                supported = [m for m in models if "gemini" in m and "vision" not in m]
                
                # Check if current model or fallback is in supported list
                if self.model_name not in models:
                    if "gemini-1.5-flash" in models:
                        self.model_name = "gemini-1.5-flash"
                    elif "gemini-2.0-flash" in models:
                        self.model_name = "gemini-2.0-flash"
                    elif supported:
                        self.model_name = supported[0]

                return True, f"Google Gemini API Key is valid and active! Model connected: {self.model_name}"
            
            # Extract detailed error from Google
            try:
                err_data = res.json()
                err_msg = err_data.get("error", {}).get("message", res.text)
            except Exception:
                err_msg = f"HTTP {res.status_code}: {res.text}"

            return False, f"Google validation error: {err_msg}"

        except requests.exceptions.Timeout:
            return False, "Connection timed out connecting to Google AI Studio. Please check your internet connection."
        except Exception as e:
            return False, f"Connection issue: {str(e)}"

    def generate_grounded_answer(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        patient_meta: Dict[str, Any] = None
    ) -> Tuple[str, bool]:
        """
        Generates grounded response using Google Gemini API.
        Strictly requires a valid Gemini API key.
        """
        clean_key = sanitize_key(self.api_key)
        if not clean_key or len(clean_key) < 10:
            raise ValueError(
                "Gemini AI API Key Required. Please set your Google Gemini API Key in the AI Settings modal (or .env file)."
            )

        if not retrieved_chunks:
            return UNSUPPORTED_FALLBACK_MESSAGE, False

        # Build context prompt
        context_blocks = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            doc_name = chunk.get("document_filename", "Clinical Document")
            page_num = chunk.get("page_number", 1)
            section = chunk.get("section_title", "General")
            text = chunk.get("text", "").strip()
            context_blocks.append(
                f"--- SOURCE CHUNK {i} ---\n"
                f"Document: {doc_name}\n"
                f"Page: {page_num}\n"
                f"Section: {section}\n"
                f"Content: {text}\n"
            )

        context_str = "\n".join(context_blocks)
        
        patient_info = ""
        if patient_meta:
            patient_info = f"Patient ID: {patient_meta.get('patient_code', 'N/A')}, Name: {patient_meta.get('display_name', 'N/A')}\n"

        prompt_text = f"""{SYSTEM_SAFETY_INSTRUCTION}

{patient_info}
RELEVANT CLINICAL CONTEXT:
{context_str}

USER QUESTION:
{question}

GROUNDED CLINICAL SUMMARY & ANSWER:"""

        # Model hierarchy (tries user model first, then standard current models)
        models_to_try = [
            self.model_name,
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-1.5-pro"
        ]
        # Remove duplicates preserving order
        unique_models = []
        for m in models_to_try:
            m_clean = normalize_model_name(m)
            if m_clean not in unique_models:
                unique_models.append(m_clean)

        last_error = None

        for model in unique_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt_text}]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 2048
                    }
                }
                res = requests.post(url, json=payload, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            answer = parts[0].get("text", "").strip()
                            is_grounded = UNSUPPORTED_FALLBACK_MESSAGE.lower() not in answer.lower()
                            return answer, is_grounded
                else:
                    try:
                        err_json = res.json()
                        err_msg = err_json.get("error", {}).get("message", res.text)
                    except Exception:
                        err_msg = res.text
                    last_error = f"{model}: {err_msg}"
            except Exception as e:
                last_error = f"{model}: {str(e)}"

        # Secondary try with Google GenAI SDK
        try:
            from google import genai
            client = genai.Client(api_key=clean_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt_text,
            )
            if response and response.text:
                answer = response.text.strip()
                is_grounded = UNSUPPORTED_FALLBACK_MESSAGE.lower() not in answer.lower()
                return answer, is_grounded
        except Exception as e:
            if not last_error:
                last_error = str(e)

        raise RuntimeError(f"Google Gemini generation failed ({last_error})")
