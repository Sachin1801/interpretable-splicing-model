/**
 * History page JavaScript - Sequence-centric view
 */

// State
let currentPage = 1;
let pageSize = 25;
let totalSequences = 0;
let totalPages = 1;
let currentFilters = {
    search: '',
    dateFrom: null,
    dateTo: null
};
let allSequences = [];  // Current page data
let selectedItems = new Map();  // key: "jobId:batchIndex" or "jobId", value: sequence object
let showSequenceColumn = false;

// DOM Elements
const tokenDisplay = document.getElementById('token-display');
const loadingState = document.getElementById('loading-state');
const noJobsState = document.getElementById('no-jobs-state');
const jobsTableContainer = document.getElementById('jobs-table-container');
const sequencesTableBody = document.getElementById('sequences-table-body');
const pagination = document.getElementById('pagination');
const pageStart = document.getElementById('page-start');
const pageEnd = document.getElementById('page-end');
const totalJobsEl = document.getElementById('total-jobs');
const pageButtons = document.getElementById('page-buttons');
const searchInput = document.getElementById('search-title');
const dateFromInput = document.getElementById('date-from');
const dateToInput = document.getElementById('date-to');
const applyFiltersBtn = document.getElementById('apply-filters-btn');
const clearFiltersBtn = document.getElementById('clear-filters-btn');
const refreshBtn = document.getElementById('refresh-btn');
const selectAllCheckbox = document.getElementById('select-all-checkbox');
const bulkActionsToolbar = document.getElementById('bulk-actions-toolbar');
const selectionCountEl = document.getElementById('selection-count');
const columnVisibility = document.getElementById('column-visibility');
const showSequenceColCheckbox = document.getElementById('show-sequence-col');
const sequenceHeader = document.getElementById('sequence-header');

// Modal elements
const exportModal = document.getElementById('export-modal');
const deleteModal = document.getElementById('delete-modal');
const deleteCountEl = document.getElementById('delete-count');
const deleteBatchWarning = document.getElementById('delete-batch-warning');

/**
 * Initialize the page
 */
document.addEventListener('DOMContentLoaded', () => {
    TokenManager.initTokenDisplay();
    loadSequences();

    // Filter event listeners
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadSequences());
    }

    // Search on Enter
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                applyFilters();
            }
        });
    }

    // Select all checkbox
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                selectAllOnPage();
            } else {
                deselectAllOnPage();
            }
        });
    }

    // Bulk action buttons
    const selectAllBtn = document.getElementById('select-all-btn');
    const deselectAllBtn = document.getElementById('deselect-all-btn');
    const exportSelectedBtn = document.getElementById('export-selected-btn');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');

    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', selectAllOnPage);
    }
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', deselectAll);
    }
    if (exportSelectedBtn) {
        exportSelectedBtn.addEventListener('click', openExportModal);
    }
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', openDeleteModal);
    }

    // Column visibility toggle
    if (showSequenceColCheckbox) {
        showSequenceColCheckbox.addEventListener('change', (e) => {
            toggleSequenceColumn(e.target.checked);
        });
    }

    // Export modal buttons
    const exportCancelBtn = document.getElementById('export-cancel-btn');
    const exportDownloadBtn = document.getElementById('export-download-btn');
    if (exportCancelBtn) {
        exportCancelBtn.addEventListener('click', closeExportModal);
    }
    if (exportDownloadBtn) {
        exportDownloadBtn.addEventListener('click', exportSelected);
    }

    // Delete modal buttons
    const deleteCancelBtn = document.getElementById('delete-cancel-btn');
    const deleteConfirmBtn = document.getElementById('delete-confirm-btn');
    if (deleteCancelBtn) {
        deleteCancelBtn.addEventListener('click', closeDeleteModal);
    }
    if (deleteConfirmBtn) {
        deleteConfirmBtn.addEventListener('click', deleteSelected);
    }

    // Close modals on backdrop click
    if (exportModal) {
        exportModal.addEventListener('click', (e) => {
            if (e.target === exportModal) closeExportModal();
        });
    }
    if (deleteModal) {
        deleteModal.addEventListener('click', (e) => {
            if (e.target === deleteModal) closeDeleteModal();
        });
    }
});

/**
 * Apply current filters and load sequences
 */
function applyFilters() {
    currentFilters.search = searchInput.value.trim();
    currentFilters.dateFrom = dateFromInput.value || null;
    currentFilters.dateTo = dateToInput.value || null;
    currentPage = 1;
    loadSequences();
}

/**
 * Clear all filters
 */
function clearFilters() {
    searchInput.value = '';
    dateFromInput.value = '';
    dateToInput.value = '';
    currentFilters = {
        search: '',
        dateFrom: null,
        dateTo: null
    };
    currentPage = 1;
    loadSequences();
}

/**
 * Load sequences from API
 */
async function loadSequences() {
    const token = TokenManager.getOrCreateToken();
    if (!token) {
        showNoSequences();
        return;
    }

    showLoading();

    try {
        // Build query parameters
        const params = new URLSearchParams({
            access_token: token,
            page: currentPage,
            page_size: pageSize
        });

        if (currentFilters.search) {
            params.append('search', currentFilters.search);
        }
        if (currentFilters.dateFrom) {
            params.append('date_from', currentFilters.dateFrom);
        }
        if (currentFilters.dateTo) {
            params.append('date_to', currentFilters.dateTo);
        }

        const response = await fetch(`/api/history/sequences?${params.toString()}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load sequences');
        }

        const data = await response.json();
        totalSequences = data.total;
        totalPages = data.total_pages;
        allSequences = data.sequences;

        if (data.sequences.length === 0) {
            showNoSequences();
        } else {
            renderSequences(data.sequences);
            renderPagination();
            showTable();
        }

    } catch (error) {
        console.error('Error loading sequences:', error);
        showNoSequences();
    }
}

/**
 * Get selection key for a sequence
 */
function getSelectionKey(seq) {
    if (seq.is_batch && seq.batch_index !== null) {
        return `${seq.job_id}:${seq.batch_index}`;
    }
    return seq.job_id;
}

/**
 * Render sequences in the table
 */
function renderSequences(sequences) {
    sequencesTableBody.innerHTML = '';

    for (const seq of sequences) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 cursor-pointer';

        const key = getSelectionKey(seq);
        const isSelected = selectedItems.has(key);

        const statusBadge = getStatusBadge(seq.status);
        const date = new Date(seq.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        // Format PSI - show as decimal or "-" if null
        const psiDisplay = seq.psi !== null ? seq.psi.toFixed(3) : '-';

        // Truncate sequence for display
        const seqDisplay = seq.sequence.length > 20
            ? seq.sequence.substring(0, 20) + '...'
            : seq.sequence;

        row.innerHTML = `
            <td class="px-4 py-3 whitespace-nowrap" onclick="event.stopPropagation()">
                <input type="checkbox"
                       class="seq-checkbox rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                       data-key="${escapeHtml(key)}"
                       ${isSelected ? 'checked' : ''}>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 group">
                ${seq.is_batch && seq.batch_index !== null
                    ? `<span class="editable-name cursor-pointer hover:bg-gray-100 px-1 py-0.5 rounded inline-flex items-center gap-1"
                             onclick="event.stopPropagation(); startEditHistoryName(this, '${seq.job_id}', ${seq.batch_index}, '${escapeHtml(seq.sequence_id).replace(/'/g, "\\'")}')">
                         ${escapeHtml(seq.sequence_id)}
                         <svg class="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                             <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                         </svg>
                       </span>`
                    : escapeHtml(seq.sequence_id)}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-primary-600 hover:text-primary-800">
                ${escapeHtml(seq.job_title || seq.job_id.substring(0, 8))}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">${date}</td>
            <td class="px-4 py-3 whitespace-nowrap text-sm font-mono ${seq.psi !== null ? 'text-gray-900' : 'text-gray-400'}">${psiDisplay}</td>
            <td class="px-4 py-3 whitespace-nowrap">${statusBadge}</td>
            <td class="seq-col px-4 py-3 whitespace-nowrap text-sm font-mono text-gray-500 ${showSequenceColumn ? '' : 'hidden'}">
                <span title="${escapeHtml(seq.sequence)}">${escapeHtml(seqDisplay)}</span>
            </td>
        `;

        // Row click navigates to detail
        row.addEventListener('click', () => navigateToDetail(seq));

        // Checkbox click
        const checkbox = row.querySelector('.seq-checkbox');
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation();
            toggleSelection(key, seq);
        });

        sequencesTableBody.appendChild(row);
    }

    // Update select all checkbox state
    updateSelectAllCheckbox();
}

/**
 * Navigate to sequence detail page
 */
function navigateToDetail(seq) {
    if (seq.is_batch && seq.batch_index !== null) {
        window.location.href = `/batch/${seq.job_id}/sequence/${seq.batch_index}`;
    } else {
        window.location.href = `/result/${seq.job_id}`;
    }
}

/**
 * Toggle selection for a sequence
 */
function toggleSelection(key, seq) {
    if (selectedItems.has(key)) {
        selectedItems.delete(key);
    } else {
        selectedItems.set(key, seq);
    }
    updateBulkActionsToolbar();
    updateSelectAllCheckbox();
}

/**
 * Select all sequences on current page
 */
function selectAllOnPage() {
    for (const seq of allSequences) {
        const key = getSelectionKey(seq);
        selectedItems.set(key, seq);
    }
    renderSequences(allSequences);
    updateBulkActionsToolbar();
}

/**
 * Deselect all sequences on current page
 */
function deselectAllOnPage() {
    for (const seq of allSequences) {
        const key = getSelectionKey(seq);
        selectedItems.delete(key);
    }
    renderSequences(allSequences);
    updateBulkActionsToolbar();
}

/**
 * Deselect all sequences
 */
function deselectAll() {
    selectedItems.clear();
    renderSequences(allSequences);
    updateBulkActionsToolbar();
}

/**
 * Update the bulk actions toolbar visibility and count
 */
function updateBulkActionsToolbar() {
    const count = selectedItems.size;

    if (count > 0) {
        bulkActionsToolbar.classList.remove('hidden');
        columnVisibility.classList.remove('hidden');
        selectionCountEl.textContent = `${count} selected`;
    } else {
        bulkActionsToolbar.classList.add('hidden');
        // Keep column visibility visible if table is shown
        if (!jobsTableContainer.classList.contains('hidden')) {
            columnVisibility.classList.remove('hidden');
        } else {
            columnVisibility.classList.add('hidden');
        }
    }
}

/**
 * Update select all checkbox state
 */
function updateSelectAllCheckbox() {
    if (!selectAllCheckbox) return;

    const allOnPageSelected = allSequences.length > 0 &&
        allSequences.every(seq => selectedItems.has(getSelectionKey(seq)));
    const someOnPageSelected = allSequences.some(seq => selectedItems.has(getSelectionKey(seq)));

    selectAllCheckbox.checked = allOnPageSelected;
    selectAllCheckbox.indeterminate = someOnPageSelected && !allOnPageSelected;
}

/**
 * Toggle sequence column visibility
 */
function toggleSequenceColumn(show) {
    showSequenceColumn = show;

    // Update header
    if (sequenceHeader) {
        sequenceHeader.classList.toggle('hidden', !show);
    }

    // Update all cells
    document.querySelectorAll('.seq-col').forEach(cell => {
        cell.classList.toggle('hidden', !show);
    });
}

/**
 * Open export modal
 */
function openExportModal() {
    if (selectedItems.size === 0) {
        alert('No sequences selected');
        return;
    }
    exportModal.classList.remove('hidden');
}

/**
 * Close export modal
 */
function closeExportModal() {
    exportModal.classList.add('hidden');
}

/**
 * Export selected sequences
 */
async function exportSelected() {
    const token = TokenManager.getToken();
    if (!token) {
        alert('No access token found');
        return;
    }

    // Gather selected columns
    const columns = ['sequence_id']; // Always included
    const columnCheckboxes = [
        'job_title', 'created_at', 'psi', 'status', 'sequence',
        'interpretation', 'structure', 'mfe'
    ];

    for (const col of columnCheckboxes) {
        const checkbox = document.getElementById(`export-col-${col}`);
        if (checkbox && checkbox.checked) {
            columns.push(col);
        }
    }

    // Build items list
    const items = [];
    for (const [key, seq] of selectedItems) {
        items.push({
            job_id: seq.job_id,
            batch_index: seq.is_batch ? seq.batch_index : null
        });
    }

    try {
        const response = await fetch(`/api/sequences/export?access_token=${encodeURIComponent(token)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ items, columns })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to export sequences');
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sequences_export.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        closeExportModal();

    } catch (error) {
        console.error('Error exporting sequences:', error);
        alert('Failed to export sequences: ' + error.message);
    }
}

/**
 * Open delete modal
 */
function openDeleteModal() {
    if (selectedItems.size === 0) {
        alert('No sequences selected');
        return;
    }

    // Update count
    deleteCountEl.textContent = selectedItems.size;

    // Check if any batch sequences are selected
    let hasBatch = false;
    for (const seq of selectedItems.values()) {
        if (seq.is_batch) {
            hasBatch = true;
            break;
        }
    }

    if (hasBatch) {
        deleteBatchWarning.classList.remove('hidden');
    } else {
        deleteBatchWarning.classList.add('hidden');
    }

    deleteModal.classList.remove('hidden');
}

/**
 * Close delete modal
 */
function closeDeleteModal() {
    deleteModal.classList.add('hidden');
}

/**
 * Delete selected sequences (deletes entire jobs)
 */
async function deleteSelected() {
    const token = TokenManager.getToken();
    if (!token) {
        alert('No access token found');
        return;
    }

    // Collect unique job IDs to delete
    const jobIds = new Set();
    for (const seq of selectedItems.values()) {
        jobIds.add(seq.job_id);
    }

    try {
        // Delete each job
        for (const jobId of jobIds) {
            const response = await fetch(`/api/jobs/${jobId}?access_token=${encodeURIComponent(token)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                console.error(`Failed to delete job ${jobId}:`, error);
            }
        }

        // Clear selection and reload
        selectedItems.clear();
        updateBulkActionsToolbar();
        closeDeleteModal();
        loadSequences();

    } catch (error) {
        console.error('Error deleting sequences:', error);
        alert('Failed to delete some sequences: ' + error.message);
    }
}

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
    const badges = {
        'finished': '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Completed</span>',
        'running': '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Running</span>',
        'queued': '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Queued</span>',
        'failed': '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Failed</span>',
        'invalid': '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">Invalid</span>'
    };
    return badges[status] || `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">${escapeHtml(status)}</span>`;
}

/**
 * Render pagination controls
 */
function renderPagination() {
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalSequences);

    pageStart.textContent = start;
    pageEnd.textContent = end;
    totalJobsEl.textContent = totalSequences;

    // Clear existing buttons
    pageButtons.innerHTML = '';

    // Previous button
    const prevBtn = document.createElement('button');
    prevBtn.className = `relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium ${currentPage === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'}`;
    prevBtn.innerHTML = '<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadSequences();
        }
    });
    pageButtons.appendChild(prevBtn);

    // Page numbers
    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage + 1 < maxButtons) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        const btn = document.createElement('button');
        btn.className = `relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium ${i === currentPage ? 'bg-primary-50 border-primary-500 text-primary-600 z-10' : 'bg-white text-gray-500 hover:bg-gray-50'}`;
        btn.textContent = i;
        btn.addEventListener('click', () => {
            currentPage = i;
            loadSequences();
        });
        pageButtons.appendChild(btn);
    }

    // Next button
    const nextBtn = document.createElement('button');
    nextBtn.className = `relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium ${currentPage === totalPages ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'}`;
    nextBtn.innerHTML = '<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadSequences();
        }
    });
    pageButtons.appendChild(nextBtn);
}

/**
 * Show loading state
 */
function showLoading() {
    loadingState.classList.remove('hidden');
    noJobsState.classList.add('hidden');
    jobsTableContainer.classList.add('hidden');
    pagination.classList.add('hidden');
    columnVisibility.classList.add('hidden');
}

/**
 * Show no sequences state
 */
function showNoSequences() {
    loadingState.classList.add('hidden');
    noJobsState.classList.remove('hidden');
    jobsTableContainer.classList.add('hidden');
    pagination.classList.add('hidden');
    columnVisibility.classList.add('hidden');
    bulkActionsToolbar.classList.add('hidden');
}

/**
 * Show table
 */
function showTable() {
    loadingState.classList.add('hidden');
    noJobsState.classList.add('hidden');
    jobsTableContainer.classList.remove('hidden');
    pagination.classList.remove('hidden');
    columnVisibility.classList.remove('hidden');
    updateBulkActionsToolbar();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Inline Name Editing for Batch Sequences
// ============================================================================

function startEditHistoryName(element, jobId, batchIndex, currentName) {
    if (element.querySelector('input')) return;

    element.innerHTML = `
        <input type="text"
               class="w-full px-2 py-1 text-sm border border-primary-500 rounded focus:ring-2 focus:ring-primary-500 focus:outline-none"
               value="${escapeHtml(currentName)}"
               maxlength="255"
               onclick="event.stopPropagation()"
               onkeydown="handleHistoryEditKeydown(event, this, '${jobId}', ${batchIndex}, '${escapeHtml(currentName).replace(/'/g, "\\'")}')"
               onblur="handleHistoryEditBlur(this, '${jobId}', ${batchIndex}, '${escapeHtml(currentName).replace(/'/g, "\\'")}')">
    `;

    const input = element.querySelector('input');
    input.focus();
    input.select();
}

function handleHistoryEditKeydown(event, input, jobId, batchIndex, originalName) {
    event.stopPropagation();
    if (event.key === 'Enter') {
        event.preventDefault();
        saveHistoryName(input, jobId, batchIndex, originalName);
    } else if (event.key === 'Escape') {
        event.preventDefault();
        cancelHistoryEdit(input, jobId, batchIndex, originalName);
    }
}

function handleHistoryEditBlur(input, jobId, batchIndex, originalName) {
    const newName = input.value.trim();
    if (!newName || newName === originalName) {
        cancelHistoryEdit(input, jobId, batchIndex, originalName);
    } else {
        saveHistoryName(input, jobId, batchIndex, originalName);
    }
}

async function saveHistoryName(input, jobId, batchIndex, originalName) {
    const newName = input.value.trim();
    const parent = input.parentElement;

    if (!newName || newName === originalName) {
        cancelHistoryEdit(input, jobId, batchIndex, originalName);
        return;
    }

    input.disabled = true;
    input.classList.add('opacity-50');

    try {
        const response = await fetch(`/api/batch/${jobId}/sequence/${batchIndex}/name`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save');
        }

        restoreHistoryNameDisplay(parent, jobId, batchIndex, newName);
        parent.classList.add('bg-green-100');
        setTimeout(() => parent.classList.remove('bg-green-100'), 1000);

    } catch (error) {
        console.error('Error saving name:', error);
        alert('Failed to save name: ' + error.message);
        input.disabled = false;
        input.classList.remove('opacity-50');
        input.focus();
    }
}

function cancelHistoryEdit(input, jobId, batchIndex, originalName) {
    restoreHistoryNameDisplay(input.parentElement, jobId, batchIndex, originalName);
}

function restoreHistoryNameDisplay(parent, jobId, batchIndex, name) {
    parent.innerHTML = `
        <span class="editable-name cursor-pointer hover:bg-gray-100 px-1 py-0.5 rounded inline-flex items-center gap-1 group"
              onclick="event.stopPropagation(); startEditHistoryName(this, '${jobId}', ${batchIndex}, '${escapeHtml(name).replace(/'/g, "\\'")}')">
            ${escapeHtml(name)}
            <svg class="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
        </span>
    `;
}

// Export functions globally
window.startEditHistoryName = startEditHistoryName;
window.handleHistoryEditKeydown = handleHistoryEditKeydown;
window.handleHistoryEditBlur = handleHistoryEditBlur;
