/**
 * Result page JavaScript - Polling and Plotly visualization
 */

// DOM Elements
const loadingState = document.getElementById('loading-state');
const loadingText = document.getElementById('loading-text');
const resultsContainer = document.getElementById('results-container');
const errorState = document.getElementById('error-state');
const errorMessageEl = document.getElementById('error-message');

// Result display elements
const psiCard = document.getElementById('psi-card');
const psiValue = document.getElementById('psi-value');
const psiInterpretation = document.getElementById('psi-interpretation');
const structureEl = document.getElementById('structure');
const mfeEl = document.getElementById('mfe');
const sequenceEl = document.getElementById('sequence');
const forcePlotEl = document.getElementById('force-plot');

// Polling configuration
const POLL_INTERVAL = 1000; // 1 second
const MAX_POLLS = 60; // 1 minute max
let pollCount = 0;

/**
 * Interpret PSI value
 */
function interpretPsi(psi) {
    if (psi >= 0.8) {
        return {
            text: 'High Inclusion',
            description: 'This exon is predicted to be included in most transcripts.',
            colorClass: 'bg-green-50 border-green-200',
            textClass: 'text-green-600'
        };
    } else if (psi >= 0.3) {
        return {
            text: 'Variable/Regulated',
            description: 'This exon shows intermediate inclusion, suggesting regulation.',
            colorClass: 'bg-yellow-50 border-yellow-200',
            textClass: 'text-yellow-600'
        };
    } else {
        return {
            text: 'High Skipping',
            description: 'This exon is predicted to be skipped in most transcripts.',
            colorClass: 'bg-red-50 border-red-200',
            textClass: 'text-red-600'
        };
    }
}

/**
 * Display the results
 */
function displayResults(data) {
    // Hide loading, show results
    loadingState.classList.add('hidden');
    resultsContainer.classList.remove('hidden');

    // For batch sequences, hide elements that don't support batch sequence detail
    if (typeof batchIndex !== 'undefined' && batchIndex !== null) {
        // Hide heatmap tab (shiny app doesn't support batch sequence detail)
        const heatmapTab = document.getElementById('tab-heatmap');
        if (heatmapTab) {
            heatmapTab.classList.add('hidden');
        }
        // Hide CSV download link (not available for individual batch sequences)
        const csvLink = document.querySelector('a[href*="/api/export/"]');
        if (csvLink) {
            csvLink.classList.add('hidden');
        }
    }

    // PSI value
    const psi = data.psi;
    const interp = interpretPsi(psi);

    psiValue.textContent = psi.toFixed(3);
    psiValue.className = `mt-2 text-5xl font-bold ${interp.textClass}`;
    psiInterpretation.textContent = `${interp.text}: ${interp.description}`;
    psiInterpretation.className = `mt-2 text-lg ${interp.textClass}`;
    psiCard.className = `rounded-lg shadow-sm border p-6 ${interp.colorClass}`;

    // Structure
    structureEl.textContent = data.structure || 'N/A';

    // MFE
    mfeEl.textContent = data.mfe ? data.mfe.toFixed(2) : 'N/A';

    // Sequence
    sequenceEl.textContent = data.sequence || 'N/A';

    // Force plot (only if element exists - may be removed in favor of Shiny visualizations)
    if (forcePlotEl && data.force_plot_data && data.force_plot_data.activations) {
        const activations = data.force_plot_data.activations;
        // Combine qc_incl and qc_skip to get position-wise contribution
        // Positive = promotes inclusion (green), Negative = promotes skipping (red)
        if (activations.qc_incl && activations.qc_skip) {
            const forceData = activations.qc_incl.map((incl, i) => {
                const skip = activations.qc_skip[i] || 0;
                return incl - skip;
            });
            createForcePlot(forceData);
        }
    } else if (forcePlotEl && data.force_plot && data.force_plot.length > 0) {
        // Fallback for legacy format
        createForcePlot(data.force_plot);
    }
}

/**
 * Create the force plot using Plotly
 */
function createForcePlot(forceData) {
    // Skip if force plot element doesn't exist
    if (!forcePlotEl) return;

    // forceData is an array of 90 values (one per position)
    const positions = Array.from({ length: forceData.length }, (_, i) => i + 1);

    // Create colors based on values
    const colors = forceData.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)');

    const trace = {
        x: positions,
        y: forceData,
        type: 'bar',
        marker: {
            color: colors
        },
        hovertemplate: 'Position %{x}<br>Contribution: %{y:.4f}<extra></extra>'
    };

    const layout = {
        margin: { t: 20, r: 20, b: 60, l: 60 },
        xaxis: {
            title: {
                text: 'Position',
                font: { size: 12 }
            },
            tickmode: 'linear',
            dtick: 10,
            range: [0, 91]
        },
        yaxis: {
            title: {
                text: 'Contribution to PSI',
                font: { size: 12 }
            },
            zeroline: true,
            zerolinecolor: '#888',
            zerolinewidth: 1
        },
        shapes: [
            // Mark exon region (positions 11-80)
            {
                type: 'rect',
                xref: 'x',
                yref: 'paper',
                x0: 10.5,
                x1: 80.5,
                y0: 0,
                y1: 1,
                fillcolor: 'rgba(59, 130, 246, 0.05)',
                line: { width: 0 }
            }
        ],
        annotations: [
            {
                x: 5,
                y: 1.05,
                xref: 'x',
                yref: 'paper',
                text: "5' flank",
                showarrow: false,
                font: { size: 10, color: '#888' }
            },
            {
                x: 45,
                y: 1.05,
                xref: 'x',
                yref: 'paper',
                text: 'Exon',
                showarrow: false,
                font: { size: 10, color: '#3b82f6' }
            },
            {
                x: 85,
                y: 1.05,
                xref: 'x',
                yref: 'paper',
                text: "3' flank",
                showarrow: false,
                font: { size: 10, color: '#888' }
            }
        ],
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
            family: 'system-ui, -apple-system, sans-serif'
        }
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
    };

    Plotly.newPlot(forcePlotEl, [trace], layout, config);
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
 * Fetch the result
 */
async function fetchResult() {
    if (!jobId) {
        showError('No job ID provided');
        return;
    }

    try {
        // Use different API endpoint for batch sequences
        const apiUrl = (typeof batchIndex !== 'undefined' && batchIndex !== null)
            ? `/api/batch/${jobId}/sequence/${batchIndex}`
            : `/api/result/${jobId}`;

        const response = await fetch(apiUrl);

        if (response.status === 404) {
            showError('Result not found. The job may have expired.');
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to fetch result');
        }

        const data = await response.json();

        if (data.status === 'completed') {
            displayResults(data);
        } else if (data.status === 'failed') {
            showError(data.error || 'Prediction failed');
        } else if (data.status === 'pending' || data.status === 'processing') {
            // Update loading text
            loadingText.textContent = `Processing... (${pollCount + 1}s)`;

            // Continue polling
            pollCount++;
            if (pollCount < MAX_POLLS) {
                setTimeout(fetchResult, POLL_INTERVAL);
            } else {
                showError('Request timed out. Please try again.');
            }
        } else {
            // Unknown status, show what we have
            displayResults(data);
        }

    } catch (error) {
        console.error('Error fetching result:', error);
        showError('An error occurred while fetching the result.');
    }
}

/**
 * Copy result link to clipboard
 */
function copyLink() {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
        // Show feedback (could be improved with a toast)
        alert('Link copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
        // Fallback
        prompt('Copy this link:', url);
    });
}

// Make copyLink available globally
window.copyLink = copyLink;

// Start fetching on page load
document.addEventListener('DOMContentLoaded', () => {
    if (typeof jobId !== 'undefined' && jobId) {
        fetchResult();
    } else {
        showError('No job ID provided');
    }
});
