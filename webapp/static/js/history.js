/**
 * History page JavaScript
 */

// State
let currentPage = 1;
let pageSize = 25;
let totalJobs = 0;
let totalPages = 1;
let currentFilters = {
    search: '',
    dateFrom: null,
    dateTo: null
};

// DOM Elements
const tokenDisplay = document.getElementById('token-display');
const loadingState = document.getElementById('loading-state');
const noJobsState = document.getElementById('no-jobs-state');
const jobsTableContainer = document.getElementById('jobs-table-container');
const jobsTableBody = document.getElementById('jobs-table-body');
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

/**
 * Initialize the page
 */
document.addEventListener('DOMContentLoaded', () => {
    TokenManager.initTokenDisplay();
    loadJobs();

    // Event listeners
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadJobs());
    }

    // Search on Enter
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                applyFilters();
            }
        });
    }

    // Setup custom token save handler for history page
    const tokenSaveBtn = document.getElementById('token-save-btn');
    if (tokenSaveBtn) {
        tokenSaveBtn.addEventListener('click', () => {
            const editInput = document.getElementById('token-edit-input');
            const newToken = editInput.value.trim();
            if (TokenManager.setToken(newToken)) {
                if (tokenDisplay) {
                    tokenDisplay.textContent = newToken;
                }
                document.getElementById('token-edit-modal').classList.add('hidden');
                loadJobs(); // Reload jobs with new token
            } else {
                alert('Invalid token format. Token must be in format: tok_xxxxxxxxxxxx');
            }
        });
    }
});

/**
 * Apply current filters and load jobs
 */
function applyFilters() {
    currentFilters.search = searchInput.value.trim();
    currentFilters.dateFrom = dateFromInput.value || null;
    currentFilters.dateTo = dateToInput.value || null;
    currentPage = 1;
    loadJobs();
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
    loadJobs();
}

/**
 * Load jobs from API
 */
async function loadJobs() {
    const token = TokenManager.getOrCreateToken();
    if (!token) {
        showNoJobs();
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

        const response = await fetch(`/api/history?${params.toString()}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load jobs');
        }

        const data = await response.json();
        totalJobs = data.total;
        totalPages = data.total_pages;

        if (data.jobs.length === 0) {
            showNoJobs();
        } else {
            renderJobs(data.jobs);
            renderPagination();
            showTable();
        }

    } catch (error) {
        console.error('Error loading jobs:', error);
        showNoJobs();
    }
}

/**
 * Render jobs in the table
 */
function renderJobs(jobs) {
    jobsTableBody.innerHTML = '';

    for (const job of jobs) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';

        const statusBadge = getStatusBadge(job.status);
        const date = new Date(job.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <a href="/result/${job.id}" class="text-primary-600 hover:text-primary-800 font-medium">
                    ${escapeHtml(job.job_title || job.id.substring(0, 8))}
                </a>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${date}</td>
            <td class="px-6 py-4 whitespace-nowrap">${statusBadge}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${job.sequence_count} ${job.is_batch ? 'sequences' : 'sequence'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
                <a href="/result/${job.id}" class="text-primary-600 hover:text-primary-800 mr-3">View</a>
                <button onclick="deleteJob('${job.id}')" class="text-red-600 hover:text-red-800">Delete</button>
            </td>
        `;

        jobsTableBody.appendChild(row);
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
        'failed': '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Failed</span>'
    };
    return badges[status] || `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">${status}</span>`;
}

/**
 * Render pagination controls
 */
function renderPagination() {
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalJobs);

    pageStart.textContent = start;
    pageEnd.textContent = end;
    totalJobsEl.textContent = totalJobs;

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
            loadJobs();
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
            loadJobs();
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
            loadJobs();
        }
    });
    pageButtons.appendChild(nextBtn);
}

/**
 * Delete a job
 */
async function deleteJob(jobId) {
    if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
        return;
    }

    const token = TokenManager.getToken();
    if (!token) {
        alert('No access token found');
        return;
    }

    try {
        const response = await fetch(`/api/jobs/${jobId}?access_token=${encodeURIComponent(token)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete job');
        }

        // Reload jobs
        loadJobs();

    } catch (error) {
        console.error('Error deleting job:', error);
        alert('Failed to delete job: ' + error.message);
    }
}

/**
 * Show loading state
 */
function showLoading() {
    loadingState.classList.remove('hidden');
    noJobsState.classList.add('hidden');
    jobsTableContainer.classList.add('hidden');
    pagination.classList.add('hidden');
}

/**
 * Show no jobs state
 */
function showNoJobs() {
    loadingState.classList.add('hidden');
    noJobsState.classList.remove('hidden');
    jobsTableContainer.classList.add('hidden');
    pagination.classList.add('hidden');
}

/**
 * Show table
 */
function showTable() {
    loadingState.classList.add('hidden');
    noJobsState.classList.add('hidden');
    jobsTableContainer.classList.remove('hidden');
    pagination.classList.remove('hidden');
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make deleteJob available globally
window.deleteJob = deleteJob;
