// ── THEME ──────────────────────────────────────────────────────────────────
const DARK_ICON  = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
const LIGHT_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>`;

let dark = document.documentElement.getAttribute('data-theme') === 'dark';
const themeBtn = document.getElementById('theme-btn');

function applyTheme() {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : '');
  localStorage.setItem('theme', dark ? 'dark' : 'light');
  if (themeBtn) themeBtn.innerHTML = dark ? DARK_ICON : LIGHT_ICON;
}
function toggleTheme() { dark = !dark; applyTheme(); }
applyTheme();

// ── CREATE FOLDER ──────────────────────────────────────────────────────────
const folderModal = document.getElementById('folder-modal');
const newFolderBtn = document.getElementById('new-folder-btn');
const folderModalCancel = document.getElementById('folder-modal-cancel');
const folderNameInput = document.getElementById('folder-name');

function openFolderModal() {
  if (!folderModal) return;
  folderModal.style.display = 'flex';
  folderNameInput.value = '';
  requestAnimationFrame(() => folderNameInput.focus());
}

function closeFolderModal() {
  if (!folderModal) return;
  folderModal.style.display = 'none';
}

if (newFolderBtn) newFolderBtn.addEventListener('click', openFolderModal);
if (folderModalCancel) folderModalCancel.addEventListener('click', closeFolderModal);
if (folderModal) {
  folderModal.addEventListener('click', (event) => {
    if (event.target === folderModal) closeFolderModal();
  });
  folderModal.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeFolderModal();
  });
}

// ── RENAME / DELETE FOLDER ─────────────────────────────────────────────────
const folderRenameModal = document.getElementById('folder-rename-modal');
const folderRenameForm = document.getElementById('folder-rename-form');
const folderRenameId = document.getElementById('folder-rename-id');
const folderRenameName = document.getElementById('folder-rename-name');
const folderRenameError = document.getElementById('folder-rename-error');
const folderDeleteModal = document.getElementById('folder-delete-modal');
const folderDeleteForm = document.getElementById('folder-delete-form');
const folderDeleteId = document.getElementById('folder-delete-id');
const folderDeleteCopy = document.getElementById('folder-delete-copy');
const folderDeleteError = document.getElementById('folder-delete-error');

function setModalError(element, message = '') {
  if (!element) return;
  element.textContent = message;
  element.classList.toggle('visible', Boolean(message));
}

async function responseError(response, fallback) {
  try {
    const data = await response.json();
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

function closeFolderRenameModal() {
  if (!folderRenameModal) return;
  folderRenameModal.style.display = 'none';
  setModalError(folderRenameError);
}

function closeFolderDeleteModal() {
  if (!folderDeleteModal) return;
  folderDeleteModal.style.display = 'none';
  setModalError(folderDeleteError);
}

document.addEventListener('click', (event) => {
  const renameButton = event.target.closest('.folder-rename-btn');
  if (renameButton && folderRenameModal) {
    folderRenameId.value = renameButton.dataset.folderId;
    folderRenameName.value = renameButton.dataset.folderName;
    setModalError(folderRenameError);
    folderRenameModal.style.display = 'flex';
    requestAnimationFrame(() => {
      folderRenameName.focus();
      folderRenameName.select();
    });
    return;
  }

  const deleteButton = event.target.closest('.folder-delete-btn');
  if (deleteButton && folderDeleteModal) {
    folderDeleteId.value = deleteButton.dataset.folderId;
    folderDeleteCopy.textContent = `Delete “${deleteButton.dataset.folderName}”? The folder must be empty.`;
    setModalError(folderDeleteError);
    folderDeleteModal.style.display = 'flex';
  }
});

document.getElementById('folder-rename-cancel')?.addEventListener('click', closeFolderRenameModal);
document.getElementById('folder-delete-cancel')?.addEventListener('click', closeFolderDeleteModal);

folderRenameModal?.addEventListener('click', (event) => {
  if (event.target === folderRenameModal) closeFolderRenameModal();
});
folderDeleteModal?.addEventListener('click', (event) => {
  if (event.target === folderDeleteModal) closeFolderDeleteModal();
});

folderRenameForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const newName = folderRenameName.value.trim();
  if (!newName) return folderRenameName.focus();

  try {
    const response = await fetch('/folders/rename', {
      method: 'POST',
      body: new FormData(folderRenameForm),
    });
    if (!response.ok) {
      setModalError(folderRenameError, await responseError(response, 'Could not rename folder.'));
      return;
    }
    location.reload();
  } catch {
    setModalError(folderRenameError, 'Network error. Please try again.');
  }
});

folderDeleteForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const response = await fetch('/folders/delete', {
      method: 'POST',
      body: new FormData(folderDeleteForm),
    });
    if (!response.ok) {
      setModalError(folderDeleteError, await responseError(response, 'Could not delete folder.'));
      return;
    }
    location.reload();
  } catch {
    setModalError(folderDeleteError, 'Network error. Please try again.');
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  closeFolderRenameModal();
  closeFolderDeleteModal();
});

// ── UPLOAD PILL ────────────────────────────────────────────────────────────
const fileInput = document.getElementById('file-input');
const pill      = document.getElementById('upload-pill');
const pillFill  = document.getElementById('pill-fill');
const pillPct   = document.getElementById('pill-pct');
const pillName  = document.getElementById('pill-name');

const SVG_UPLOAD = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/></svg>`;
const SVG_SPIN   = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation:spin .8s linear infinite"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;
const SVG_CHECK  = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
const SVG_ERROR  = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

function pillSetIcon(svg) {
  document.getElementById('pill-trigger').innerHTML = svg;
}

function pillUploading(filename) {
  pill.className = 'upload-pill active';
  pillFill.className = 'pill-fill';
  pillFill.style.width = '0%';
  pillName.textContent = filename;
  pillPct.textContent  = '0%';
  pillSetIcon(SVG_SPIN);
}

function pillProgress(pct) {
  pillFill.style.width = pct + '%';
  pillPct.textContent  = pct + '%';
}

function pillProcessing() {
  pillFill.classList.add('processing');
  pillPct.textContent = 'Processing…';
  pill.classList.add('processing');
  pill.classList.remove('active');
  pillSetIcon(SVG_SPIN);
}

function pillDone() {
  pillFill.classList.remove('processing');
  pillFill.style.width = '100%';
  pill.className = 'upload-pill done';
  pillName.textContent = 'Upload complete';
  pillPct.textContent  = '✓';
  pillSetIcon(SVG_CHECK);
}

function pillError() {
  pillFill.classList.remove('processing');
  pill.className = 'upload-pill error';
  pillName.textContent = 'Upload failed';
  pillPct.textContent  = '!';
  pillSetIcon(SVG_ERROR);
}

function pillReset() {
  pill.className = 'upload-pill';
  pillFill.className = 'pill-fill';
  pillFill.style.width = '0%';
  pillName.textContent = '';
  pillPct.textContent  = '';
  pillSetIcon(SVG_UPLOAD);
  fileInput.value = '';
}

function startUpload(file) {
  pillUploading(file.name);

  const uploadForm = document.getElementById('upload-form');
  const formData = new FormData(uploadForm);
  formData.set('file', file);

  const folderInput = uploadForm.querySelector('[name="folder_id"]');
  const folderFromUrl = new URLSearchParams(window.location.search).get('folder_id');
  const currentFolderId = folderInput?.value || folderFromUrl;

  if (currentFolderId) {
    formData.set('folder_id', currentFolderId);
  } else {
    formData.delete('folder_id');
  }

  fetch('/upload', { method: 'POST', body: formData })
    .catch(() => {
      pillError();
      setTimeout(pillReset, 3000);
    });

  setTimeout(() => {
    const sse = new EventSource('/upload/progress');

    sse.onmessage = (e) => {
      const state = JSON.parse(e.data);
      if (state.error) {
        sse.close();
        pillError();
        setTimeout(pillReset, 3000);
        return;
      }
      if (state.done) {
        sse.close();
        pillProgress(100);
        pillDone();
        setTimeout(() => location.reload(), 1000);
        return;
      }
      pillProgress(state.pct);
    };

    sse.onerror = () => {
      sse.close();
      pillError();
      setTimeout(pillReset, 3000);
    };
  }, 100);
}

// ── ЭТОГО НЕ БЫЛО — вот почему кнопка не работала ──────────────────────────
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) startUpload(fileInput.files[0]);
});

// ── DELETE MODAL ───────────────────────────────────────────────────────────
const modal = document.getElementById('delete-modal');
let formToSubmit = null;

document.addEventListener('submit', (e) => {
  if (e.target.classList.contains('delete-form')) {
    e.preventDefault();
    formToSubmit = e.target;
    modal.style.display = 'flex';
  }
});

const closeModal = () => { modal.style.display = 'none'; formToSubmit = null; };
document.getElementById('modal-cancel').onclick = closeModal;
window.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

document.getElementById('modal-confirm').onclick = async () => {
  if (!formToSubmit) return;
  const form = formToSubmit;
  closeModal();
  try {
    const res = await fetch('/delete', { method: 'POST', body: new FormData(form) });
    if (res.ok) location.reload();
    else alert('Server error while deleting');
  } catch (err) {
    console.error(err);
    alert('Network error');
  }
};

// ── DRAG & DROP ────────────────────────────────────────────────────────────
const overlay = document.getElementById('drop-overlay');
let dragCounter = 0;

document.addEventListener('dragenter', (e) => { e.preventDefault(); dragCounter++; overlay.classList.add('active'); });
document.addEventListener('dragover',  (e) => { e.preventDefault(); });
document.addEventListener('dragleave', ()  => { if (--dragCounter === 0) overlay.classList.remove('active'); });
document.addEventListener('drop', (e) => {
  e.preventDefault();
  overlay.classList.remove('active');
  dragCounter = 0;
  const files = e.dataTransfer.files;
  if (files.length > 0) startUpload(files[0]);
});
// ── RENAME MODAL ───────────────────────────────────────────────────────────
const renameModal = document.getElementById('rename-modal');
const extensionModal = document.getElementById('extension-modal');

let currentFileId = null;
let currentFileName = '';
let pendingNewName = '';
let cachedFormData = null;

function openRenameModal(fileId, fileName) {
  currentFileId = fileId;
  currentFileName = fileName;
  
  const form = document.getElementById('rename-form-' + fileId);
  cachedFormData = new FormData(form);
  
  const input = document.getElementById('rename-modal-input');
  input.value = fileName;
  renameModal.style.display = 'flex';
  input.focus();
  input.select();
}

function closeRenameModal() {
  renameModal.style.display = 'none';
}

function getExtension(filename) {
  const parts = filename.split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : '';
}

function submitRename() {
  const input = document.getElementById('rename-modal-input');
  const newName = input.value.trim();
  
  if (!newName || newName === currentFileName) {
    closeRenameModal();
    resetRenameState();
    return;
  }
  
  const oldExt = getExtension(currentFileName);
  const newExt = getExtension(newName);
  
  if (oldExt && newExt && oldExt !== newExt) {
    pendingNewName = newName;
    closeRenameModal();
    extensionModal.style.display = 'flex';
    return;
  }
  
  performRename(newName);
}

function performRename(newName) {
  if (!cachedFormData || !currentFileId) {
    alert('Error: form data not found');
    return;
  }
  
  cachedFormData.set('new_name', newName);
  
  fetch('/rename', { 
    method: 'POST', 
    body: cachedFormData 
  })
  .then(res => {
    if (res.ok) {
      location.reload();
    } else {
      alert('Error renaming file');
      console.error('Rename failed:', res.status);
    }
  })
  .catch(err => {
    console.error(err);
    alert('Network error');
  });
}

function resetRenameState() {
  currentFileId = null;
  currentFileName = '';
  pendingNewName = '';
  cachedFormData = null;
}

// Event listeners for rename modals
if (renameModal) {
  document.getElementById('rename-modal-cancel').onclick = () => {
    closeRenameModal();
    resetRenameState();
  };
  
  document.getElementById('rename-modal-confirm').onclick = submitRename;
  
  const renameInput = document.getElementById('rename-modal-input');
  if (renameInput) {
    renameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitRename();
      if (e.key === 'Escape') {
        closeRenameModal();
        resetRenameState();
      }
    });
  }
  
  window.addEventListener('click', (e) => {
    if (e.target === renameModal) {
      closeRenameModal();
      resetRenameState();
    }
  });
}

// Event listeners for extension warning modal
if (extensionModal) {
  document.getElementById('extension-modal-cancel').onclick = () => {
    extensionModal.style.display = 'none';
    resetRenameState();
  };
  
  document.getElementById('extension-modal-confirm').onclick = () => {
    extensionModal.style.display = 'none';
    if (pendingNewName) {
      performRename(pendingNewName);
      resetRenameState();
    }
  };
  
  window.addEventListener('click', (e) => {
    if (e.target === extensionModal) {
      extensionModal.style.display = 'none';
      resetRenameState();
    }
  });
}
