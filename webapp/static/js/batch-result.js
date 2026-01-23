/**
 * Batch result page JavaScript - Pagination, search, and detail view
 */

// State
let currentPage = 1;
let pageSize = 25;
let totalResults = 0;
let totalPages = 1;
let searchQuery = '';
let jobInfo = null;

// DOM Elements
const loadingState = document.getElementById('loading-state');
const loadingText = document.getElementById('loading-text');
const resultsContainer = document.getElementById('results-container');
const errorState = document.getElementById('error-state');
const errorMessageEl = document.getElementById('error-message');
const jobTitleEl = document.getElementById('job-title');
const resultsTableBody = document.getElementById('results-table-body');
const searchInput = document.getElementById('search-results');

// Pagination elements
const pageStart = document.getElementById('page-start');
const pageEnd = document.getElementById('page-end');
const totalResultsEl = document.getElementById('total-results');
const pageButtons = document.getElementById('page-buttons');

// Export links
const exportCsv = document.getElementById('export-csv');

// Polling configuration
const POLL_INTERVAL = 2000; // 2 seconds
const MAX_POLLS = 120; // 4 minutes max
let pollCount = 0;

/**
 * Initialize the page
 */
document.addEventListener('DOMContentLoaded', () => {
    if (typeof jobId === 'undefined' || !jobId) {
        showError('No job ID provided');
        return;
    }

    // Set export links
    exportCsv.href = `/api/export/${jobId}/csv`;

    // Event listeners
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchQuery = e.target.value.trim();
                currentPage = 1;
                loadResults();
            }, 300);
        });
    }

    // Start loading
    fetchJobInfo();
});

/**
 * Fetch job information first
 */
async function fetchJobInfo() {
    try {
        const response = await fetch(`/api/result/${jobId}`);

        if (response.status === 404) {
            showError('Job not found. It may have expired.');
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to fetch job info');
        }

        const data = await response.json();
        jobInfo = data;

        // Check status
        if (data.status === 'finished' || data.status === 'completed') {
            // Job is done, load results
            updateJobHeader();
            loadResults();
        } else if (data.status === 'failed') {
            showError(data.error || 'Batch processing failed');
        } else if (data.status === 'running' || data.status === 'queued') {
            // Still processing
            loadingText.textContent = `Processing batch... (${pollCount * 2}s)`;
            pollCount++;
            if (pollCount < MAX_POLLS) {
                setTimeout(fetchJobInfo, POLL_INTERVAL);
            } else {
                showError('Request timed out. Please try again later.');
            }
        } else {
            // Try to show results anyway
            updateJobHeader();
            loadResults();
        }

    } catch (error) {
        console.error('Error fetching job info:', error);
        showError('Failed to load job information');
    }
}

/**
 * Update job header with title
 */
function updateJobHeader() {
    if (jobInfo && jobInfo.job_title) {
        jobTitleEl.textContent = jobInfo.job_title;
    }
}

/**
 * Load paginated results
 */
async function loadResults() {
    try {
        const params = new URLSearchParams({
            page: currentPage,
            page_size: pageSize
        });

        if (searchQuery) {
            params.append('search', searchQuery);
        }

        const response = await fetch(`/api/batch/${jobId}/results?${params.toString()}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load results');
        }

        const data = await response.json();

        // Update table
        totalResults = data.total;
        totalPages = data.total_pages;
        renderResults(data.results);
        renderPagination();

        // Show results container
        loadingState.classList.add('hidden');
        resultsContainer.classList.remove('hidden');

    } catch (error) {
        console.error('Error loading results:', error);
        showError(error.message);
    }
}

/**
 * Render results table
 */
function renderResults(results) {
    resultsTableBody.innerHTML = '';

    for (const result of results) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 cursor-pointer';
        row.onclick = () => {
            window.location.href = `/batch/${jobId}/sequence/${result.index}`;
        };

        const statusBadge = getStatusBadge(result.status);
        const psiDisplay = result.status === 'success' && result.psi !== null
            ? result.psi.toFixed(3)
            : '-';
        const psiClass = result.status === 'success' ? getPsiColorClass(result.psi) : 'text-gray-400';

        // Truncate sequence
        const truncatedSeq = result.sequence.length > 30
            ? result.sequence.substring(0, 30) + '...'
            : result.sequence;

        row.innerHTML = `
            <td class="px-4 py-3 text-gray-400">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 group">
                <span class="editable-name cursor-pointer hover:bg-gray-100 px-1 py-0.5 rounded inline-flex items-center gap-1"
                      data-index="${result.index}"
                      onclick="event.stopPropagation(); startEditName(this, ${result.index}, '${escapeHtml(result.name).replace(/'/g, "\\'")}')">
                    ${escapeHtml(result.name)}
                    <svg class="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm font-mono text-gray-500">
                ${escapeHtml(truncatedSeq)}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm font-bold ${psiClass}">
                ${psiDisplay}
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                ${statusBadge}
            </td>
        `;

        resultsTableBody.appendChild(row);
    }
}

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
    if (status === 'success') {
        return '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Success</span>';
    } else if (status === 'invalid') {
        return '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Invalid</span>';
    } else {
        return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">${status}</span>`;
    }
}

/**
 * Get PSI color class
 */
function getPsiColorClass(psi) {
    if (psi >= 0.8) return 'text-green-600';
    if (psi >= 0.3) return 'text-yellow-600';
    return 'text-red-600';
}

/**
 * Render pagination controls
 */
function renderPagination() {
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalResults);

    pageStart.textContent = totalResults > 0 ? start : 0;
    pageEnd.textContent = end;
    totalResultsEl.textContent = totalResults;

    // Clear existing buttons
    pageButtons.innerHTML = '';

    if (totalPages <= 1) return;

    // Previous button
    const prevBtn = document.createElement('button');
    prevBtn.className = `relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium ${currentPage === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-50'}`;
    prevBtn.innerHTML = '<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadResults();
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
            loadResults();
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
            loadResults();
        }
    });
    pageButtons.appendChild(nextBtn);
}


/**
 * Show error state
 */
function showError(message) {
    loadingState.classList.add('hidden');
    resultsContainer.classList.add('hidden');
    errorState.classList.remove('hidden');
    errorMessageEl.textContent = message;
}

/**
 * Copy result link to clipboard
 */
function copyLink() {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
        alert('Link copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
        prompt('Copy this link:', url);
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Inline Name Editing
// ============================================================================

function startEditName(element, index, currentName) {
    if (element.querySelector('input')) return;

    element.innerHTML = `
        <input type="text"
               class="w-full px-2 py-1 text-sm border border-primary-500 rounded focus:ring-2 focus:ring-primary-500 focus:outline-none"
               value="${escapeHtml(currentName)}"
               maxlength="255"
               onclick="event.stopPropagation()"
               onkeydown="handleEditKeydown(event, this, ${index}, '${escapeHtml(currentName).replace(/'/g, "\\'")}')"
               onblur="handleEditBlur(this, ${index}, '${escapeHtml(currentName).replace(/'/g, "\\'")}')">
    `;

    const input = element.querySelector('input');
    input.focus();
    input.select();
}

function handleEditKeydown(event, input, index, originalName) {
    event.stopPropagation();
    if (event.key === 'Enter') {
        event.preventDefault();
        saveName(input, index, originalName);
    } else if (event.key === 'Escape') {
        event.preventDefault();
        cancelEdit(input, index, originalName);
    }
}

function handleEditBlur(input, index, originalName) {
    const newName = input.value.trim();
    if (!newName || newName === originalName) {
        cancelEdit(input, index, originalName);
    } else {
        saveName(input, index, originalName);
    }
}

async function saveName(input, index, originalName) {
    const newName = input.value.trim();
    const parent = input.parentElement;

    if (!newName || newName === originalName) {
        cancelEdit(input, index, originalName);
        return;
    }

    input.disabled = true;
    input.classList.add('opacity-50');

    try {
        const response = await fetch(`/api/batch/${jobId}/sequence/${index}/name`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save');
        }

        restoreNameDisplay(parent, index, newName);
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

function cancelEdit(input, index, originalName) {
    restoreNameDisplay(input.parentElement, index, originalName);
}

function restoreNameDisplay(parent, index, name) {
    parent.innerHTML = `
        <span class="editable-name cursor-pointer hover:bg-gray-100 px-1 py-0.5 rounded inline-flex items-center gap-1 group"
              data-index="${index}"
              onclick="event.stopPropagation(); startEditName(this, ${index}, '${escapeHtml(name).replace(/'/g, "\\'")}')">
            ${escapeHtml(name)}
            <svg class="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
        </span>
    `;
}

// Make functions available globally
window.copyLink = copyLink;
window.startEditName = startEditName;
window.handleEditKeydown = handleEditKeydown;
window.handleEditBlur = handleEditBlur;
