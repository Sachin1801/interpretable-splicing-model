/**
 * Token management utilities for user identification.
 * Tokens are stored in localStorage and used to track job history.
 * Format: tok_xxxxxxxxxxxx (12 random alphanumeric characters)
 */

const TOKEN_KEY = 'splicing_access_token';
const TOKEN_PREFIX = 'tok_';
const TOKEN_RANDOM_LENGTH = 12;

/**
 * Generate a random token.
 * @returns {string} Token in format tok_xxxxxxxxxxxx
 */
function generateToken() {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let result = TOKEN_PREFIX;
    for (let i = 0; i < TOKEN_RANDOM_LENGTH; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

/**
 * Validate token format.
 * @param {string} token - Token to validate
 * @returns {boolean} True if valid format
 */
function isValidToken(token) {
    const pattern = new RegExp(`^${TOKEN_PREFIX}[a-z0-9]{${TOKEN_RANDOM_LENGTH}}$`);
    return pattern.test(token);
}

/**
 * Get current token from localStorage, or generate new one.
 * @returns {string} The access token
 */
function getOrCreateToken() {
    let token = localStorage.getItem(TOKEN_KEY);
    if (!token || !isValidToken(token)) {
        token = generateToken();
        localStorage.setItem(TOKEN_KEY, token);
    }
    return token;
}

/**
 * Get current token from localStorage (may be null).
 * @returns {string|null} The access token or null
 */
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Set a new token in localStorage.
 * @param {string} newToken - The new token to set
 * @returns {boolean} True if successfully set
 */
function setToken(newToken) {
    if (!isValidToken(newToken)) {
        return false;
    }
    localStorage.setItem(TOKEN_KEY, newToken);
    return true;
}

/**
 * Clear the token from localStorage.
 */
function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

/**
 * Copy token to clipboard.
 * @returns {Promise<boolean>} True if successfully copied
 */
async function copyTokenToClipboard() {
    const token = getToken();
    if (!token) return false;

    try {
        await navigator.clipboard.writeText(token);
        return true;
    } catch (err) {
        console.error('Failed to copy token:', err);
        return false;
    }
}

/**
 * Initialize token display in the UI.
 * Call this on page load to show current token.
 */
function initTokenDisplay() {
    const token = getOrCreateToken();

    // Update token display element if it exists
    const displayEl = document.getElementById('token-display');
    if (displayEl) {
        displayEl.textContent = token;
        displayEl.title = 'Double-click to edit';
        displayEl.style.cursor = 'pointer';

        // Double-click to edit inline
        displayEl.addEventListener('dblclick', () => {
            startInlineEdit(displayEl);
        });
    }

    // Setup copy button
    const copyBtn = document.getElementById('token-copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            const success = await copyTokenToClipboard();
            if (success) {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }
        });
    }

    return token;
}

/**
 * Start inline editing of the token display.
 * @param {HTMLElement} displayEl - The token display element
 */
function startInlineEdit(displayEl) {
    const currentToken = displayEl.textContent;
    const originalBg = displayEl.style.backgroundColor;

    // Make editable
    displayEl.contentEditable = true;
    displayEl.style.backgroundColor = '#fff';
    displayEl.style.outline = '2px solid #3b82f6';
    displayEl.style.outlineOffset = '1px';
    displayEl.focus();

    // Select all text
    const range = document.createRange();
    range.selectNodeContents(displayEl);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);

    // Handle blur (save on click away)
    const handleBlur = () => {
        finishInlineEdit(displayEl, currentToken, originalBg);
    };

    // Handle keydown (Enter to save, Escape to cancel)
    const handleKeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            displayEl.blur();
        } else if (e.key === 'Escape') {
            displayEl.textContent = currentToken;
            displayEl.blur();
        }
    };

    displayEl.addEventListener('blur', handleBlur, { once: true });
    displayEl.addEventListener('keydown', handleKeydown);

    // Remove keydown listener after blur
    displayEl.addEventListener('blur', () => {
        displayEl.removeEventListener('keydown', handleKeydown);
    }, { once: true });
}

/**
 * Finish inline editing and save if valid.
 * @param {HTMLElement} displayEl - The token display element
 * @param {string} originalToken - The original token before editing
 * @param {string} originalBg - The original background color
 */
function finishInlineEdit(displayEl, originalToken, originalBg) {
    displayEl.contentEditable = false;
    displayEl.style.backgroundColor = originalBg;
    displayEl.style.outline = '';
    displayEl.style.outlineOffset = '';

    const newToken = displayEl.textContent.trim();

    if (newToken === originalToken) {
        // No change
        return;
    }

    if (setToken(newToken)) {
        displayEl.textContent = newToken;
    } else {
        // Invalid token, revert
        displayEl.textContent = originalToken;
        alert('Invalid token format. Token must be: tok_ followed by 12 lowercase letters/numbers');
    }
}

// Export functions for use in other scripts
window.TokenManager = {
    generateToken,
    isValidToken,
    getOrCreateToken,
    getToken,
    setToken,
    clearToken,
    copyTokenToClipboard,
    initTokenDisplay,
    TOKEN_KEY,
};
