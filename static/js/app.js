// Default Clinical Theme
function initTheme() {
  document.documentElement.setAttribute('data-theme', 'cyber');
}

// Toast System
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icon = type === 'success' ? 'check-circle' : (type === 'error' ? 'exclamation-circle' : 'info-circle');
  toast.innerHTML = `<i class="fas fa-${icon}"></i> <span>${message}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    if (modalId === 'ai-settings-modal') {
      checkAIConfig();
    }
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

// Gemini AI Key Config
async function checkAIConfig() {
  try {
    const res = await fetch('/api/ai/config');
    const data = await res.json();
    const statusText = document.getElementById('ai-key-status-text');
    const headerPill = document.getElementById('navbar-ai-status');

    if (statusText) {
      if (data.configured) {
        statusText.innerHTML = `<span style="color: #34D399;"><i class="fas fa-check-circle"></i> Key Active (${data.masked_key})</span>`;
      } else {
        statusText.innerHTML = `<span style="color: #FBBF24;"><i class="fas fa-exclamation-triangle"></i> Not Configured</span>`;
      }
    }

    if (headerPill) {
      if (data.configured) {
        headerPill.className = 'ai-status-pill active';
        headerPill.innerHTML = `<span class="status-dot green"></span> <span>Gemini AI: Active (${data.model})</span>`;
      } else {
        headerPill.className = 'ai-status-pill warning';
        headerPill.innerHTML = `<span class="status-dot amber"></span> <span>Gemini AI: Key Required</span>`;
      }
    }
  } catch (err) {
    console.error('Failed to check AI config:', err);
  }
}

async function handleSaveAIKey(event) {
  event.preventDefault();
  const keyInput = document.getElementById('gemini-key-input');
  const modelSelect = document.getElementById('gemini-model-select');
  const saveBtn = document.getElementById('save-key-btn');

  const apiKey = keyInput.value.trim().replace(/^['"`]+|['"`]+$/g, '');
  const model = modelSelect ? modelSelect.value : 'gemini-1.5-flash';

  if (!apiKey) {
    showToast('Please enter your Google Gemini API key', 'error');
    return;
  }

  saveBtn.disabled = true;
  saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing key with Google AI Studio...';

  try {
    const res = await fetch('/api/ai/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey, model: model })
    });

    const result = await res.json();
    saveBtn.disabled = false;
    saveBtn.innerHTML = '<i class="fas fa-check"></i> Validate & Activate Key';

    if (res.ok) {
      showToast('Google Gemini API Key activated successfully!', 'success');
      keyInput.value = '';
      closeModal('ai-settings-modal');
      checkAIConfig();
    } else {
      showToast(result.error || 'Failed to validate Gemini API Key with Google', 'error');
      const statusText = document.getElementById('ai-key-status-text');
      if (statusText) {
        statusText.innerHTML = `<span style="color: #F87171;"><i class="fas fa-times-circle"></i> ${result.error || 'Invalid Key'}</span>`;
      }
    }
  } catch (err) {
    saveBtn.disabled = false;
    saveBtn.innerHTML = '<i class="fas fa-check"></i> Validate & Activate Key';
    showToast('Network error while validating Gemini API key', 'error');
  }
}

async function handleClearKey() {
  try {
    const res = await fetch('/api/ai/clear-key', { method: 'POST' });
    if (res.ok) {
      showToast('Gemini API key cleared.', 'info');
      checkAIConfig();
    }
  } catch (err) {
    showToast('Failed to clear key', 'error');
  }
}

// Global Auth Logout
async function handleLogout() {
  try {
    const res = await fetch('/api/auth/logout', { method: 'POST' });
    if (res.ok) {
      window.location.href = '/login';
    }
  } catch (err) {
    window.location.href = '/login';
  }
}

// Global Patient Creation
async function handleCreatePatient(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  try {
    const res = await fetch('/api/patients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    const result = await res.json();
    if (res.ok) {
      showToast('Patient record created successfully!', 'success');
      closeModal('create-patient-modal');
      form.reset();
      if (typeof loadPatients === 'function') {
        loadPatients();
      } else {
        setTimeout(() => window.location.reload(), 600);
      }
    } else {
      showToast(result.error || 'Failed to create patient', 'error');
    }
  } catch (err) {
    showToast('Network error while creating patient', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  checkAIConfig();
});
