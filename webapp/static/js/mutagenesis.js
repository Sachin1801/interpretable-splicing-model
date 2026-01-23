/**
 * Mutagenesis Results Visualization
 */

let mutagenesisData = null;
let currentPage = 1;
const pageSize = 25;

async function loadMutagenesisResults(jobId) {
    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error');
    const resultsEl = document.getElementById('results');

    try {
        const response = await fetch(`/api/mutagenesis/${jobId}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load results');
        }

        mutagenesisData = await response.json();

        if (mutagenesisData.status === 'running' || mutagenesisData.status === 'queued') {
            // Poll for results
            setTimeout(() => loadMutagenesisResults(jobId), 2000);
            return;
        }

        if (mutagenesisData.status === 'failed') {
            throw new Error(mutagenesisData.message || 'Analysis failed');
        }

        // Hide loading, show results
        loadingEl.classList.add('hidden');
        resultsEl.classList.remove('hidden');

        // Populate data
        renderResults(mutagenesisData);

    } catch (error) {
        loadingEl.classList.add('hidden');
        errorEl.classList.remove('hidden');
        document.getElementById('error-message').textContent = error.message;
    }
}

function renderResults(data) {
    // Job title
    document.getElementById('job-title').textContent = data.job_title || `Job ${data.job_id.slice(0, 8)}`;

    // Reference info
    document.getElementById('ref-sequence').textContent = data.reference_sequence;
    document.getElementById('ref-psi').textContent = data.reference_psi?.toFixed(3) || 'N/A';
    document.getElementById('mutation-count').textContent = `${data.completed_mutations}/${data.total_mutations}`;

    // Render heatmap
    renderHeatmap(data);

    // Render top mutations
    renderTopMutations(data.top_positive, 'top-positive', true);
    renderTopMutations(data.top_negative, 'top-negative', false);

    // Render table
    renderMutationsTable(data.mutations);

    // Set up event listeners
    document.getElementById('table-search').addEventListener('input', function() {
        currentPage = 1;
        renderMutationsTable(filterAndSortMutations());
    });

    document.getElementById('table-sort').addEventListener('change', function() {
        currentPage = 1;
        renderMutationsTable(filterAndSortMutations());
    });
}

function renderHeatmap(data) {
    const container = document.getElementById('heatmap-container');
    const heatmapData = data.heatmap_data;

    if (!heatmapData) {
        container.innerHTML = '<p class="text-gray-500">Heatmap data not available</p>';
        return;
    }

    // Create position labels
    const positions = heatmapData.positions || Array.from({ length: 70 }, (_, i) => i + 1);
    const originalSeq = heatmapData.original_sequence || '';

    // Nucleotide order for rows
    const nucleotides = ['A', 'C', 'G', 'T'];

    // Build heatmap HTML
    let html = '<div style="min-width: 900px;">';

    // Position labels (every 10)
    html += '<div class="mutation-row mb-1">';
    html += '<div class="mutation-label"></div>';
    positions.forEach((pos, i) => {
        if (pos % 10 === 0 || pos === 1) {
            html += `<span class="heatmap-cell text-center text-xs text-gray-500" style="width: 12px; font-size: 9px;">${pos}</span>`;
        } else {
            html += `<span class="heatmap-cell" style="width: 12px; border: none;"></span>`;
        }
    });
    html += '</div>';

    // Original sequence row
    html += '<div class="mutation-row mb-2">';
    html += '<div class="mutation-label text-gray-500">Ref</div>';
    for (let i = 0; i < originalSeq.length; i++) {
        const nt = originalSeq[i];
        const bgColor = getNucleotideColor(nt);
        html += `<span class="heatmap-cell" style="background: ${bgColor}; text-align: center; font-size: 9px; font-weight: 500; line-height: 24px;">${nt}</span>`;
    }
    html += '</div>';

    // Mutation rows (one for each target nucleotide)
    nucleotides.forEach(toNt => {
        html += '<div class="mutation-row">';
        html += `<div class="mutation-label">→${toNt}</div>`;

        positions.forEach((pos, i) => {
            const original = originalSeq[i];

            if (original === toNt) {
                // This is the reference - gray cell
                html += `<span class="heatmap-cell" style="background: #e5e7eb;" title="Reference"></span>`;
            } else {
                // Get delta PSI for this mutation
                const deltaMatrix = heatmapData.delta_matrix || {};
                const deltaPsi = deltaMatrix[toNt]?.[i];

                if (deltaPsi === null || deltaPsi === undefined) {
                    html += `<span class="heatmap-cell" style="background: #f3f4f6;" title="No data"></span>`;
                } else {
                    const color = getDeltaPsiColor(deltaPsi);
                    const mutation = `${original}${pos}${toNt}`;
                    html += `<span class="heatmap-cell" style="background: ${color};" title="${mutation}: Δ${deltaPsi >= 0 ? '+' : ''}${deltaPsi.toFixed(3)}"></span>`;
                }
            }
        });

        html += '</div>';
    });

    html += '</div>';

    // Color scale legend
    html += `
        <div class="mt-4 flex items-center justify-center space-x-2">
            <span class="text-xs text-gray-500">-0.5</span>
            <div style="width: 200px; height: 12px; background: linear-gradient(to right, #dc2626, #f3f4f6, #16a34a); border-radius: 2px;"></div>
            <span class="text-xs text-gray-500">+0.5</span>
        </div>
    `;

    container.innerHTML = html;
}

function getNucleotideColor(nt) {
    const colors = {
        'A': '#86efac', // green
        'C': '#93c5fd', // blue
        'G': '#fde047', // yellow
        'T': '#fca5a5', // red
    };
    return colors[nt] || '#e5e7eb';
}

function getDeltaPsiColor(deltaPsi) {
    // Clamp to -0.5 to +0.5 range for visualization
    const clamped = Math.max(-0.5, Math.min(0.5, deltaPsi));

    if (clamped === 0) {
        return '#f3f4f6';
    } else if (clamped > 0) {
        // Green gradient
        const intensity = clamped / 0.5;
        const r = Math.round(243 - intensity * (243 - 22));
        const g = Math.round(244 - intensity * (244 - 163));
        const b = Math.round(246 - intensity * (246 - 74));
        return `rgb(${r}, ${g}, ${b})`;
    } else {
        // Red gradient
        const intensity = Math.abs(clamped) / 0.5;
        const r = Math.round(243 + intensity * (220 - 243));
        const g = Math.round(244 - intensity * (244 - 38));
        const b = Math.round(246 - intensity * (246 - 38));
        return `rgb(${r}, ${g}, ${b})`;
    }
}

function renderTopMutations(mutations, containerId, isPositive) {
    const container = document.getElementById(containerId);

    if (!mutations || mutations.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-sm">No mutations found</p>';
        return;
    }

    const html = mutations.map(m => {
        const deltaPsi = m.delta_psi;
        const sign = deltaPsi >= 0 ? '+' : '';
        const colorClass = deltaPsi >= 0 ? 'text-green-600' : 'text-red-600';

        return `
            <div class="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
                <span class="font-mono font-medium">${m.mutation_label}</span>
                <div class="text-right">
                    <span class="text-sm text-gray-600">PSI: ${m.psi?.toFixed(3) || 'N/A'}</span>
                    <span class="ml-2 font-medium ${colorClass}">${sign}${deltaPsi?.toFixed(3) || 'N/A'}</span>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function filterAndSortMutations() {
    let mutations = [...mutagenesisData.mutations];

    // Filter
    const searchTerm = document.getElementById('table-search').value.toLowerCase();
    if (searchTerm) {
        mutations = mutations.filter(m =>
            m.mutation_label.toLowerCase().includes(searchTerm) ||
            m.original.toLowerCase().includes(searchTerm) ||
            m.mutant.toLowerCase().includes(searchTerm) ||
            m.position.toString().includes(searchTerm)
        );
    }

    // Sort
    const sortBy = document.getElementById('table-sort').value;
    switch (sortBy) {
        case 'position':
            mutations.sort((a, b) => a.position - b.position || a.mutant.localeCompare(b.mutant));
            break;
        case 'delta_psi_desc':
            mutations.sort((a, b) => (b.delta_psi || 0) - (a.delta_psi || 0));
            break;
        case 'delta_psi_asc':
            mutations.sort((a, b) => (a.delta_psi || 0) - (b.delta_psi || 0));
            break;
        case 'psi_desc':
            mutations.sort((a, b) => (b.psi || 0) - (a.psi || 0));
            break;
        case 'psi_asc':
            mutations.sort((a, b) => (a.psi || 0) - (b.psi || 0));
            break;
    }

    return mutations;
}

function renderMutationsTable(mutations) {
    const tbody = document.getElementById('mutations-table');
    const paginationEl = document.getElementById('table-pagination');

    // Paginate
    const totalPages = Math.ceil(mutations.length / pageSize);
    const startIdx = (currentPage - 1) * pageSize;
    const paginated = mutations.slice(startIdx, startIdx + pageSize);

    // Render rows
    const html = paginated.map(m => {
        const deltaPsi = m.delta_psi;
        const sign = deltaPsi >= 0 ? '+' : '';
        const colorClass = deltaPsi >= 0 ? 'text-green-600' : 'text-red-600';
        const bgColor = getDeltaPsiColor(deltaPsi);

        return `
            <tr>
                <td class="px-4 py-2 text-sm">${m.position}</td>
                <td class="px-4 py-2 text-sm font-mono font-medium">${m.mutation_label}</td>
                <td class="px-4 py-2 text-sm">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" style="background: ${getNucleotideColor(m.original)}">
                        ${m.original}
                    </span>
                </td>
                <td class="px-4 py-2 text-sm">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" style="background: ${getNucleotideColor(m.mutant)}">
                        ${m.mutant}
                    </span>
                </td>
                <td class="px-4 py-2 text-sm">${m.psi?.toFixed(3) || 'N/A'}</td>
                <td class="px-4 py-2 text-sm">
                    <span class="px-2 py-1 rounded ${colorClass}" style="background: ${bgColor}">
                        ${sign}${deltaPsi?.toFixed(3) || 'N/A'}
                    </span>
                </td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = html;

    // Render pagination
    if (totalPages > 1) {
        let paginationHtml = '<div class="flex items-center space-x-2">';

        // Previous button
        paginationHtml += `
            <button onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}
                class="px-3 py-1 border rounded text-sm ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50'}">
                Previous
            </button>
        `;

        // Page numbers
        const maxButtons = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
        let endPage = Math.min(totalPages, startPage + maxButtons - 1);

        if (endPage - startPage < maxButtons - 1) {
            startPage = Math.max(1, endPage - maxButtons + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <button onclick="changePage(${i})"
                    class="px-3 py-1 border rounded text-sm ${i === currentPage ? 'bg-primary-600 text-white' : 'hover:bg-gray-50'}">
                    ${i}
                </button>
            `;
        }

        // Next button
        paginationHtml += `
            <button onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}
                class="px-3 py-1 border rounded text-sm ${currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50'}">
                Next
            </button>
        `;

        paginationHtml += `<span class="text-sm text-gray-500 ml-4">Page ${currentPage} of ${totalPages}</span>`;
        paginationHtml += '</div>';

        paginationEl.innerHTML = paginationHtml;
    } else {
        paginationEl.innerHTML = '';
    }
}

function changePage(page) {
    currentPage = page;
    renderMutationsTable(filterAndSortMutations());
}
