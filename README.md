# Clinical Workflow Intelligence Platform

A complete, resume-aligned healthcare software prototype that supports clinical document review and information organization without duplicating brain-imaging analysis or patient-treatment products.

---

## 1. Executive Summary & Purpose

The **Clinical Workflow Intelligence Platform** connects structured patient metadata with searchable clinical documents. Authorized healthcare users (Physicians, Clinical Staff, Admins) can upload clinical reports, retrieve relevant sections using FAISS vector similarity search, ask grounded questions answered with Google Gemini / RAG, review & edit AI outputs, and export approved reports to verified PDFs.

> [!IMPORTANT]
> **Clinical Safety & Scope**: This is a supporting clinical-information workflow application. It does **not** diagnose diseases, analyze MRI/fMRI images, generate brain maps, recommend treatment, or replace a clinician.

---

## 2. Key Features

- **Document Processing Pipeline**:
  - Ingests and cleans PDF (`pypdf`), DOCX (`python-docx`), and plain text.
  - Section-aware sliding-window chunker preserving clinical header and page metadata.
- **FAISS Vector Retrieval**:
  - Dense L2-normalized embeddings for patient-isolated vector similarity search.
  - Fast nearest-neighbor retrieval of the top-$k$ relevant clinical context chunks.
- **Grounded AI Question Answering**:
  - Google AI studio API integration (`gemini-1.5-flash` / `text-embedding-004`) with strict grounded prompting.
  - Anti-hallucination constraint: strictly returns *"The uploaded documents do not contain enough information to answer this."* when ungrounded.
  - Offline / local fallback dense vectorizer + grounded extraction for reliable local demonstrations.
- **Human-in-the-Loop Review Workflow**:
  - 4-stage lifecycle: `GENERATED` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `APPROVED` $\rightarrow$ `EXPORTED`.
  - Clinician editing and notes before sign-off.
- **Clinical Report Export**:
  - Formats verified summaries, patient demographics, citations, and disclaimer into downloadable ReportLab PDFs and JSON bundles.
- **Audit Logging & Security**:
  - Full traceability logging for logins, uploads, searches, reviews, approvals, and exports.

---

## 3. Architecture & Tech Stack

```
Frontend (HTML5 + CSS3 + Vanilla JS)
       │
       ▼ (HTTP / REST APIs)
Flask Application (Python 3.14)
  ├── Authentication & RBAC (Doctor, Staff, Admin)
  ├── SQLite + SQLAlchemy Database
  ├── Document Processor (Text Cleaning & Overlapping Chunker)
  ├── FAISS Vector Store (Patient-Isolated Cosine Similarity)
  ├── Google Gemini / Local Grounded RAG Service
  ├── Human Review & Approval Workflow
  └── ReportLab Structured PDF Export
```


## 4. Quick Start Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.14)

### Running the Application
```bash
# 1. Run the launcher (auto-seeds demo patients & sample PDF report)
python run.py
```

Open your browser at **`http://127.0.0.1:5000`**

### Demo Login Credentials
| Role | Email | Password |
|------|-------|----------|
| **Doctor** | `doctor@brainsight.ai` | `doctor123` |
| **Clinical Staff** | `staff@brainsight.ai` | `staff123` |
| **Admin** | `admin@brainsight.ai` | `admin123` |

*(Quick-login demo buttons are also provided on the sign-in screen)*

---

## 5. Example Demo Walkthrough

1. **Sign in** as **Dr. Sarah Jenkins** (`doctor@brainsight.ai`).
2. On the **Dashboard**, observe the active patient count and audit trail.
3. Select patient **Eleanor Vance (`PT-8942`)** with diagnosis *Refractory Temporal Lobe Epilepsy*.
4. In the patient workspace, view the pre-indexed `patient_report_01.pdf`.
5. In the **AI Grounded Q&A** console, click the sample prompt:
   > *"Summarize the important findings from the previous report."*
6. Review the generated summary citing **left mesial temporal spikes**, **video-EEG concordance**, and **surgical recommendations**.
7. Click the **citation chips** to view the exact matched source document excerpt.
8. Click **"Review & Edit"**, add clinician notes, and click **"Clinically Approve & Sign Off"**.
9. Click **"Export PDF"** to download the signed clinical intelligence summary report.

---

## 6. Running Tests

Run the automated test suite with pytest:

```bash
python -m pytest tests/ -v
```

All unit and integration tests validate authentication, document chunking, FAISS vector indexing, RAG retrieval accuracy, and approval states.
