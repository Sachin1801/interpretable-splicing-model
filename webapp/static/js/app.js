/**
 * Home page JavaScript - Form handling and validation
 */

// Example sequences
const EXAMPLES = [
    {
        name: "High Inclusion",
        sequence: "GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT",
        expectedPsi: "~0.98"
    },
    {
        name: "Balanced",
        sequence: "CTACCACCTCCCAAGCTTACCCAGACCGGAAGCCAAGGCACCCCGGACATGCAGGCACTACCCTAAATAG",
        expectedPsi: "~0.49"
    },
    {
        name: "High Skipping",
        sequence: "ACACTCCGCAGCACACTCGGCCGATCCGCCATATTCAATACATACAGTTGCGATGAAGTTGCGGGAAGAG",
        expectedPsi: "~0.00"
    }
];

// DOM Elements
const form = document.getElementById('predict-form');
const sequenceInput = document.getElementById('sequence');
const charCount = document.getElementById('char-count');
const validationMessage = document.getElementById('validation-message');
const submitBtn = document.getElementById('submit-btn');
const submitText = document.getElementById('submit-text');
const loadingSpinner = document.getElementById('loading-spinner');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');
const exampleBtn = document.getElementById('example-btn');
const clearBtn = document.getElementById('clear-btn');

// Current example index for cycling
let currentExampleIndex = 0;

/**
 * Validate the sequence input
 * @param {string} sequence - The input sequence
 * @returns {object} - { valid: boolean, message: string }
 */
function validateSequence(sequence) {
    // Remove whitespace
    const cleaned = sequence.replace(/\s/g, '').toUpperCase();

    if (cleaned.length === 0) {
        return { valid: false, message: '' };
    }

    if (cleaned.length !== 70) {
        return {
            valid: false,
            message: `Sequence must be exactly 70 nucleotides (currently ${cleaned.length})`
        };
    }

    const invalidChars = cleaned.match(/[^ACGT]/g);
    if (invalidChars) {
        const unique = [...new Set(invalidChars)];
        return {
            valid: false,
            message: `Invalid characters: ${unique.join(', ')}. Only A, C, G, T allowed.`
        };
    }

    return { valid: true, message: '' };
}

/**
 * Update the UI based on validation state
 */
function updateValidation() {
    const sequence = sequenceInput.value;
    const cleaned = sequence.replace(/\s/g, '');
    const { valid, message } = validateSequence(sequence);

    // Update character count
    charCount.textContent = `${cleaned.length}/70 nucleotides`;
    charCount.className = 'text-sm ' + (
        cleaned.length === 70 ? 'text-green-600' :
        cleaned.length > 70 ? 'text-red-600' :
        'text-gray-500'
    );

    // Update validation message
    if (message) {
        validationMessage.textContent = message;
        validationMessage.classList.remove('hidden');
    } else {
        validationMessage.classList.add('hidden');
    }

    // Update submit button
    submitBtn.disabled = !valid;

    return valid;
}

/**
 * Show loading state
 */
function setLoading(loading) {
    if (loading) {
        submitBtn.disabled = true;
        submitText.textContent = 'Predicting...';
        loadingSpinner.classList.remove('hidden');
    } else {
        submitBtn.disabled = false;
        submitText.textContent = 'Predict PSI';
        loadingSpinner.classList.add('hidden');
    }
}

/**
 * Show error message
 */
function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
}

/**
 * Hide error message
 */
function hideError() {
    errorMessage.classList.add('hidden');
}

/**
 * Load an example sequence
 */
function loadExample(index) {
    const example = EXAMPLES[index];
    sequenceInput.value = example.sequence;
    updateValidation();
    hideError();
}

/**
 * Submit the prediction
 */
async function submitPrediction(event) {
    event.preventDefault();

    const sequence = sequenceInput.value.replace(/\s/g, '').toUpperCase();

    if (!validateSequence(sequence).valid) {
        return;
    }

    setLoading(true);
    hideError();

    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ sequence })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Prediction failed');
        }

        const result = await response.json();

        // Redirect to result page
        window.location.href = `/result/${result.job_id}`;

    } catch (error) {
        console.error('Prediction error:', error);
        showError(error.message || 'An error occurred. Please try again.');
        setLoading(false);
    }
}

// Event listeners
if (form) {
    form.addEventListener('submit', submitPrediction);
}

if (sequenceInput) {
    sequenceInput.addEventListener('input', updateValidation);
    // Initial validation
    updateValidation();
}

if (exampleBtn) {
    exampleBtn.addEventListener('click', () => {
        loadExample(currentExampleIndex);
        currentExampleIndex = (currentExampleIndex + 1) % EXAMPLES.length;
    });
}

if (clearBtn) {
    clearBtn.addEventListener('click', () => {
        sequenceInput.value = '';
        updateValidation();
        hideError();
    });
}

// Make loadExample available globally for onclick handlers
window.loadExample = loadExample;
