let activeReport = null;
let currentPatientId = null;

document.addEventListener('DOMContentLoaded', () => {
  const patientElem = document.getElementById('patient-id-holder');
  if (patientElem) {
    currentPatientId = parseInt(patientElem.dataset.patientId);
    loadPatientDocuments();
    loadPatientReports();
  }

  // Setup Drag and Drop
  setupDropzone();
});

function setupDropzone() {
  const dropzone = document.getElementById('document-dropzone');
  const fileInput = document.getElementById('file-input');
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleDocumentUpload();
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleDocumentUpload();
    }
  });
}

async function loadPatientDocuments() {
  if (!currentPatientId) return;
  const container = document.getElementById('documents-list-container');
  if (!container) return;

  try {
    const res = await fetch(`/api/patients/${currentPatientId}/documents`);
    const data = await res.json();
    
    if (!data.documents || data.documents.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 24px; color: var(--text-muted);">
          <i class="fas fa-folder-open" style="font-size: 2rem; margin-bottom: 8px;"></i>
          <p>No documents uploaded yet for this patient.</p>
        </div>`;
      return;
    }

    container.innerHTML = data.documents.map(doc => `
      <div class="card" style="margin-bottom: 12px; padding: 14px; background: var(--bg-surface); display: flex; align-items: center; justify-content: space-between;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: #FFF;">
            <i class="fas fa-file-pdf" style="color: #38BDF8;"></i>
            <span>${doc.original_filename}</span>
            <span class="badge badge-${doc.status.toLowerCase()}">${doc.status}</span>
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">
            ${(doc.file_size / 1024).toFixed(1)} KB • ${doc.chunk_count || 0} chunks • Added ${new Date(doc.created_at).toLocaleDateString()}
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          ${doc.status !== 'INDEXED' ? `
            <button class="btn btn-primary btn-sm" onclick="processDocument(${doc.id})">
              <i class="fas fa-microchip"></i> Index
            </button>
          ` : `
            <button class="btn btn-secondary btn-sm" onclick="viewDocumentChunks(${doc.id})" title="View FAISS Chunks">
              <i class="fas fa-layer-group"></i>
            </button>
          `}
          <a href="/api/documents/${doc.id}/download" class="btn btn-secondary btn-sm" title="Download">
            <i class="fas fa-download"></i>
          </a>
          <button class="btn btn-secondary btn-sm" onclick="handleDeleteDocument(${doc.id})" title="Delete Document" style="color: #F87171;">
            <i class="fas fa-trash-alt"></i>
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading documents:', err);
  }
}

async function handleDocumentUpload() {
  const fileInput = document.getElementById('file-input');
  const docTypeSelect = document.getElementById('document-type-select');
  if (!fileInput.files.length) return;

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', docTypeSelect ? docTypeSelect.value : 'CLINICAL_NOTE');
  formData.append('auto_process', 'true');

  showToast(`Uploading and indexing ${file.name}...`, 'info');

  try {
    const res = await fetch(`/api/patients/${currentPatientId}/documents`, {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (res.ok) {
      showToast('Document uploaded and indexed successfully into FAISS!', 'success');
      fileInput.value = '';
      loadPatientDocuments();
    } else {
      showToast(result.error || 'Upload failed', 'error');
    }
  } catch (err) {
    showToast('Failed to upload document', 'error');
  }
}

async function processDocument(docId) {
  showToast('Extracting text and building FAISS vector index...', 'info');
  try {
    const res = await fetch(`/api/documents/${docId}/process`, { method: 'POST' });
    const result = await res.json();
    if (res.ok) {
      showToast('Document indexed into vector store!', 'success');
      loadPatientDocuments();
    } else {
      showToast(result.error || 'Processing failed', 'error');
    }
  } catch (err) {
    showToast('Network error processing document', 'error');
  }
}

async function viewDocumentChunks(docId) {
  try {
    const res = await fetch(`/api/documents/${docId}/view`);
    const data = await res.json();
    if (res.ok) {
      const container = document.getElementById('chunks-modal-body');
      container.innerHTML = `
        <p style="margin-bottom: 12px; color: var(--text-secondary);">Showing <b>${data.total_chunks}</b> searchable chunks stored in FAISS for <b>${data.document.original_filename}</b>:</p>
        <div style="display: flex; flex-direction: column; gap: 10px; max-height: 400px; overflow-y: auto;">
          ${data.chunks.map((c, i) => `
            <div style="background: var(--bg-input); padding: 12px; border-radius: 8px; border: 1px solid var(--border-subtle);">
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-highlight); margin-bottom: 4px;">
                <span>#${i+1} • ${c.section_title}</span>
                <span>Page ${c.page_number}</span>
              </div>
              <p style="font-size: 0.85rem; color: var(--text-primary); font-family: var(--font-mono);">${c.text}</p>
            </div>
          `).join('')}
        </div>
      `;
      openModal('view-chunks-modal');
    }
  } catch (err) {
    showToast('Failed to load chunks', 'error');
  }
}

async function handleDeleteDocument(docId) {
  if (!confirm('Are you sure you want to delete this document and remove it from FAISS?')) {
    return;
  }

  try {
    const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast('Document deleted and removed from FAISS vector index', 'info');
      loadPatientDocuments();
    } else {
      showToast(data.error || 'Failed to delete document', 'error');
    }
  } catch (err) {
    showToast('Network error deleting document', 'error');
  }
}

// Ask AI Grounded Question
async function submitAIQuestion(event) {
  event.preventDefault();
  const input = document.getElementById('qa-question-input');
  const question = input.value.trim();
  if (!question) return;

  const thread = document.getElementById('qa-thread-container');
  const submitBtn = document.getElementById('qa-submit-btn');

  // Append user bubble
  thread.innerHTML += `
    <div class="qa-bubble user">
      <b>You:</b> ${question}
    </div>
  `;

  // Loading indicator
  const loadingId = 'loading-' + Date.now();
  thread.innerHTML += `
    <div id="${loadingId}" class="qa-bubble ai" style="display: flex; align-items: center; gap: 8px;">
      <i class="fas fa-spinner fa-spin" style="color: var(--accent-primary);"></i>
      <span>Searching FAISS vector index and generating grounded response...</span>
    </div>
  `;
  thread.scrollTop = thread.scrollHeight;
  input.value = '';
  submitBtn.disabled = true;

  try {
    const res = await fetch(`/api/patients/${currentPatientId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    const data = await res.json();
    document.getElementById(loadingId)?.remove();
    submitBtn.disabled = false;

    if (res.ok && data.report) {
      const rep = data.report;
      activeReport = rep;

      // Render AI response with citations
      let citationsHtml = '';
      if (rep.sources && rep.sources.length > 0) {
        citationsHtml = `
          <div class="qa-sources-list">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-highlight); text-transform: uppercase;">
              <i class="fas fa-book-medical"></i> Verified Document Citations (${rep.sources.length}):
            </div>
            ${rep.sources.map((s, idx) => `
              <div class="citation-chip" onclick='inspectCitation(${JSON.stringify(s)})'>
                <div>
                  <b>[${idx+1}] ${s.document_filename}</b> (Pg ${s.page_number} - ${s.section_title})
                  <div style="font-size: 0.72rem; color: var(--text-muted);">${s.snippet}</div>
                </div>
                <i class="fas fa-external-link-alt" style="color: var(--accent-primary);"></i>
              </div>
            `).join('')}
          </div>
        `;
      }

      thread.innerHTML += `
        <div class="qa-bubble ai">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; color: #38BDF8;">
              <i class="fas fa-robot"></i> Grounded AI Summary
            </div>
            <span class="badge badge-${rep.status.toLowerCase()}">${rep.status}</span>
          </div>
          <div style="white-space: pre-wrap; font-size: 0.9rem;">${rep.answer}</div>
          ${citationsHtml}
          <div style="margin-top: 14px; display: flex; gap: 8px; justify-content: flex-end;">
            <button class="btn btn-secondary btn-sm" onclick="openReviewModal(${rep.id})">
              <i class="fas fa-user-check"></i> Review & Edit
            </button>
            <a href="/api/reports/${rep.id}/export?format=pdf" class="btn btn-primary btn-sm" target="_blank">
              <i class="fas fa-file-pdf"></i> Export PDF
            </a>
          </div>
        </div>
      `;
      thread.scrollTop = thread.scrollHeight;
      loadPatientReports();
    } else {
      const isKeyError = data.error && data.error.includes('Gemini AI API Key Required');
      thread.innerHTML += `
        <div class="qa-bubble ai" style="border-color: rgba(245, 158, 11, 0.4); background: rgba(245, 158, 11, 0.05);">
          <div style="display: flex; align-items: center; gap: 8px; color: #FBBF24; font-weight: 700; margin-bottom: 6px;">
            <i class="fas fa-key"></i> ${isKeyError ? 'Google Gemini API Key Required' : 'Query Notice'}
          </div>
          <p style="font-size: 0.9rem; color: #F8FAFC;">${data.error || 'Failed to retrieve grounded answer.'}</p>
          ${isKeyError ? `
            <div style="margin-top: 12px;">
              <button class="btn btn-primary btn-sm" onclick="openModal('ai-settings-modal')">
                <i class="fas fa-cog"></i> Open Gemini AI Settings
              </button>
            </div>
          ` : ''}
        </div>
      `;
    }
  } catch (err) {
    document.getElementById(loadingId)?.remove();
    submitBtn.disabled = false;
    showToast('Failed to communicate with AI RAG service', 'error');
  }
}

function inspectCitation(citation) {
  const container = document.getElementById('citation-detail-content');
  if (!container) return;

  container.innerHTML = `
    <div style="margin-bottom: 12px;">
      <h4 style="color: #FFF;">${citation.document_filename}</h4>
      <div style="font-size: 0.8rem; color: var(--text-highlight);">
        Section: <b>${citation.section_title}</b> | Page <b>${citation.page_number}</b> | FAISS Similarity: <b>${(citation.similarity_score * 100).toFixed(1)}%</b>
      </div>
    </div>
    <div style="background: var(--bg-input); padding: 14px; border-radius: 8px; border-left: 3px solid var(--accent-primary); font-family: var(--font-mono); font-size: 0.85rem; color: #F1F5F9; white-space: pre-wrap;">
      ${citation.full_text || citation.snippet}
    </div>
  `;
  openModal('citation-modal');
}

async function loadPatientReports() {
  if (!currentPatientId) return;
  const container = document.getElementById('reports-history-container');
  if (!container) return;

  try {
    const res = await fetch(`/api/reports?patient_id=${currentPatientId}`);
    const data = await res.json();
    if (data.reports && data.reports.length > 0) {
      container.innerHTML = data.reports.map(r => `
        <div class="card" style="padding: 12px; margin-bottom: 8px; background: var(--bg-surface);">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.85rem; font-weight: 600; color: #FFF;">${r.question.substring(0, 45)}...</span>
            <span class="badge badge-${r.status.toLowerCase()}">${r.status}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 0.78rem; color: var(--text-muted);">
            <span>${new Date(r.created_at).toLocaleString()}</span>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" onclick="openReviewModal(${r.id})">Review</button>
              <a href="/api/reports/${r.id}/export?format=pdf" class="btn btn-primary btn-sm" target="_blank">PDF</a>
            </div>
          </div>
        </div>
      `).join('');
    } else {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">No historical queries yet.</p>';
    }
  } catch (err) {
    console.error('Error loading reports:', err);
  }
}

async function openReviewModal(reportId) {
  try {
    const res = await fetch(`/api/reports?patient_id=${currentPatientId}`);
    const data = await res.json();
    const rep = data.reports.find(r => r.id === reportId);
    if (!rep) return;

    activeReport = rep;
    document.getElementById('review-report-id').value = rep.id;
    document.getElementById('review-question-display').innerText = rep.question;
    document.getElementById('review-answer-input').value = rep.answer;
    document.getElementById('review-notes-input').value = rep.reviewer_notes || '';
    
    openModal('review-approval-modal');
  } catch (err) {
    showToast('Failed to open review window', 'error');
  }
}

async function handleApproveReport() {
  if (!activeReport) return;
  const reportId = document.getElementById('review-report-id').value;
  const answer = document.getElementById('review-answer-input').value;
  const notes = document.getElementById('review-notes-input').value;

  try {
    const res = await fetch(`/api/reports/${reportId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer, reviewer_notes: notes })
    });

    const result = await res.json();
    if (res.ok) {
      showToast('Report clinically approved and signed off!', 'success');
      closeModal('review-approval-modal');
      loadPatientReports();
    } else {
      showToast(result.error || 'Approval failed', 'error');
    }
  } catch (err) {
    showToast('Network error approving report', 'error');
  }
}
