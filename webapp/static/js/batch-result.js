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

// Stats elements
const statTotal = document.getElementById('stat-total');
const statSuccess = document.getElementById('stat-success');
const statInvalid = document.getElementById('stat-invalid');
const statAvgPsi = document.getElementById('stat-avg-psi');

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

        // Update stats
        updateStats(data);

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
 * Update stats display
 */
function updateStats(data) {
    statTotal.textContent = data.total_sequences || 0;
    statSuccess.textContent = data.successful_count || 0;
    statInvalid.textContent = data.invalid_count || 0;

    if (data.average_psi !== null && data.average_psi !== undefined) {
        statAvgPsi.textContent = data.average_psi.toFixed(3);
    } else {
        statAvgPsi.textContent = '-';
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
        row.onclick = () => showDetail(result.index);

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
 * Show sequence detail modal
 */
async function showDetail(index) {
    const modal = document.getElementById('detail-modal');
    const detailTitle = document.getElementById('detail-title');
    const detailContent = document.getElementById('detail-content');
    const detailLoading = document.getElementById('detail-loading');

    // Show modal with loading
    modal.classList.remove('hidden');
    detailLoading.classList.remove('hidden');
    detailContent.innerHTML = '';
    detailContent.appendChild(detailLoading);

    try {
        const response = await fetch(`/api/batch/${jobId}/sequence/${index}`, {
            cache: 'no-store'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load sequence details');
        }

        const data = await response.json();
        detailLoading.classList.add('hidden');

        // Update title
        detailTitle.textContent = data.name || `Sequence ${index + 1}`;

        // Build detail content
        let html = '';

        if (data.status === 'invalid') {
            // Show invalid sequence info
            html = `
                <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                    <svg class="h-12 w-12 text-red-400 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <h4 class="mt-4 text-lg font-medium text-red-800">Invalid Sequence</h4>
                    <p class="mt-2 text-red-700">${escapeHtml(data.validation_error || 'Sequence validation failed')}</p>
                </div>
                <div class="bg-gray-50 rounded-lg p-4">
                    <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">Sequence</h4>
                    <p class="font-mono text-sm text-gray-900 break-all">${escapeHtml(data.sequence)}</p>
                </div>
            `;
        } else {
            // Show successful prediction details
            const psi = data.psi;
            const interp = interpretPsi(psi);

            html = `
                <!-- PSI Value -->
                <div class="rounded-lg p-6 text-center ${interp.colorClass}">
                    <p class="text-sm font-medium text-gray-500 uppercase tracking-wide">Predicted PSI</p>
                    <p class="mt-2 text-4xl font-bold ${interp.textClass}">${psi.toFixed(3)}</p>
                    <p class="mt-2 text-sm ${interp.textClass}">${interp.text}: ${interp.description}</p>
                </div>

                <!-- Info Grid -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-gray-50 rounded-lg p-4">
                        <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">RNA Secondary Structure</h4>
                        <p class="font-mono text-sm text-gray-900 break-all">${escapeHtml(data.structure || 'N/A')}</p>
                    </div>
                    <div class="bg-gray-50 rounded-lg p-4">
                        <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">Minimum Free Energy</h4>
                        <p class="text-2xl font-bold text-gray-900">${data.mfe ? data.mfe.toFixed(2) : 'N/A'} <span class="text-base font-normal text-gray-500">kcal/mol</span></p>
                    </div>
                </div>

                <!-- Sequence -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">Sequence</h4>
                    <p class="font-mono text-sm text-gray-900 break-all">${escapeHtml(data.sequence)}</p>
                </div>

                <!-- Force Plot -->
                <div class="bg-white rounded-lg border border-gray-200 p-4">
                    <h4 class="text-sm font-medium text-gray-500 uppercase mb-4">
                        Position-wise Contribution to PSI
                        <span class="ml-2 text-gray-400 font-normal normal-case">
                            (green = promotes inclusion, red = promotes skipping)
                        </span>
                    </h4>
                    <div id="detail-force-plot" class="w-full" style="height: 350px;"></div>
                </div>
            `;
        }

        detailContent.innerHTML = html;

        // Create force plot if we have data
        if (data.status === 'success' && data.force_plot_data && data.force_plot_data.length > 0) {
            setTimeout(() => createForcePlot('detail-force-plot', data.force_plot_data), 100);
        }

    } catch (error) {
        console.error('Error loading detail:', error);
        detailLoading.classList.add('hidden');
        detailContent.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                <p class="text-red-700">${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

/**
 * Close detail modal
 */
function closeDetailModal() {
    document.getElementById('detail-modal').classList.add('hidden');
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeDetailModal();
    }
});

// Close modal on backdrop click
document.getElementById('detail-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        closeDetailModal();
    }
});

/**
 * Interpret PSI value
 */
function interpretPsi(psi) {
    if (psi >= 0.8) {
        return {
            text: 'High Inclusion',
            description: 'This exon is predicted to be included in most transcripts.',
            colorClass: 'bg-green-50 border border-green-200',
            textClass: 'text-green-600'
        };
    } else if (psi >= 0.3) {
        return {
            text: 'Variable/Regulated',
            description: 'This exon shows intermediate inclusion, suggesting regulation.',
            colorClass: 'bg-yellow-50 border border-yellow-200',
            textClass: 'text-yellow-600'
        };
    } else {
        return {
            text: 'High Skipping',
            description: 'This exon is predicted to be skipped in most transcripts.',
            colorClass: 'bg-red-50 border border-red-200',
            textClass: 'text-red-600'
        };
    }
}

/**
 * Create force plot using Plotly
 */
function createForcePlot(elementId, forceData) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const positions = Array.from({ length: forceData.length }, (_, i) => i + 1);
    const colors = forceData.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)');

    const trace = {
        x: positions,
        y: forceData,
        type: 'bar',
        marker: { color: colors },
        hovertemplate: 'Position %{x}<br>Contribution: %{y:.4f}<extra></extra>'
    };

    const layout = {
        margin: { t: 20, r: 20, b: 50, l: 50 },
        xaxis: {
            title: { text: 'Position', font: { size: 11 } },
            tickmode: 'linear',
            dtick: 10,
            range: [0, 91]
        },
        yaxis: {
            title: { text: 'Contribution to PSI', font: { size: 11 } },
            zeroline: true,
            zerolinecolor: '#888',
            zerolinewidth: 1
        },
        shapes: [{
            type: 'rect',
            xref: 'x',
            yref: 'paper',
            x0: 10.5,
            x1: 80.5,
            y0: 0,
            y1: 1,
            fillcolor: 'rgba(59, 130, 246, 0.05)',
            line: { width: 0 }
        }],
        annotations: [
            { x: 5, y: 1.05, xref: 'x', yref: 'paper', text: "5' flank", showarrow: false, font: { size: 9, color: '#888' } },
            { x: 45, y: 1.05, xref: 'x', yref: 'paper', text: 'Exon', showarrow: false, font: { size: 9, color: '#3b82f6' } },
            { x: 85, y: 1.05, xref: 'x', yref: 'paper', text: "3' flank", showarrow: false, font: { size: 9, color: '#888' } }
        ],
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { family: 'system-ui, -apple-system, sans-serif' }
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
    };

    Plotly.newPlot(element, [trace], layout, config);
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
window.closeDetailModal = closeDetailModal;
window.showDetail = showDetail;
window.startEditName = startEditName;
window.handleEditKeydown = handleEditKeydown;
window.handleEditBlur = handleEditBlur;
