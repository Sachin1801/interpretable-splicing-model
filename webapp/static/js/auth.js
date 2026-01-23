/**
 * Authentication utilities for client-side auth management
 * Supports navbar dropdown auth with auto-registration
 */

const AUTH_TOKEN_KEY = 'auth_token';
const USER_DATA_KEY = 'user_data';
const ACCESS_TOKEN_KEY = 'access_token';

/**
 * Get the stored auth token
 */
function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
}

/**
 * Get the stored user data
 */
function getUserData() {
    const data = localStorage.getItem(USER_DATA_KEY);
    return data ? JSON.parse(data) : null;
}

/**
 * Get the access token (for anonymous history)
 */
function getAccessToken() {
    let token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) {
        token = 'user_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
    }
    return token;
}

/**
 * Save auth data to localStorage
 */
function saveAuthData(token, user) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
}

/**
 * Clear auth data from localStorage
 */
function clearAuthData() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_DATA_KEY);
}

/**
 * Check if user is logged in
 */
function isLoggedIn() {
    return !!getAuthToken() && !!getUserData();
}

/**
 * Toggle auth dropdown visibility
 */
function toggleAuthDropdown() {
    const dropdown = document.getElementById('auth-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
        // Reset form when opening
        if (!dropdown.classList.contains('hidden')) {
            resetAuthForm();
        }
    }
}

/**
 * Toggle user dropdown visibility
 */
function toggleUserDropdown() {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

/**
 * Toggle mobile auth form visibility
 */
function toggleMobileAuthForm() {
    const form = document.getElementById('mobile-auth-form');
    if (form) {
        form.classList.toggle('hidden');
        if (!form.classList.contains('hidden')) {
            resetMobileAuthForm();
        }
    }
}

/**
 * Reset the auth form to its initial state
 */
function resetAuthForm() {
    const email = document.getElementById('auth-email');
    const password = document.getElementById('auth-password');
    const message = document.getElementById('auth-message');
    const btnText = document.getElementById('auth-btn-text');
    const loading = document.getElementById('auth-loading');
    const submitBtn = document.getElementById('auth-submit-btn');

    if (email) email.value = '';
    if (password) password.value = '';
    if (message) {
        message.classList.add('hidden');
        message.className = 'hidden mb-3 p-3 rounded-md text-sm';
    }
    if (btnText) btnText.textContent = 'Continue';
    if (loading) loading.classList.add('hidden');
    if (submitBtn) submitBtn.disabled = false;
}

/**
 * Reset mobile auth form
 */
function resetMobileAuthForm() {
    const email = document.getElementById('mobile-auth-email');
    const password = document.getElementById('mobile-auth-password');
    const message = document.getElementById('mobile-auth-message');

    if (email) email.value = '';
    if (password) password.value = '';
    if (message) {
        message.classList.add('hidden');
        message.className = 'hidden p-3 rounded-md text-sm';
    }
}

/**
 * Show message in auth dropdown
 */
function showAuthMessage(message, isError = false) {
    const messageEl = document.getElementById('auth-message');
    if (messageEl) {
        messageEl.textContent = message;
        messageEl.classList.remove('hidden', 'bg-green-50', 'text-green-800', 'bg-red-50', 'text-red-800');
        if (isError) {
            messageEl.classList.add('bg-red-50', 'text-red-800');
        } else {
            messageEl.classList.add('bg-green-50', 'text-green-800');
        }
    }
}

/**
 * Show message in mobile auth form
 */
function showMobileAuthMessage(message, isError = false) {
    const messageEl = document.getElementById('mobile-auth-message');
    if (messageEl) {
        messageEl.textContent = message;
        messageEl.classList.remove('hidden', 'bg-green-50', 'text-green-800', 'bg-red-50', 'text-red-800');
        if (isError) {
            messageEl.classList.add('bg-red-50', 'text-red-800');
        } else {
            messageEl.classList.add('bg-green-50', 'text-green-800');
        }
    }
}

/**
 * Set loading state for auth form
 */
function setAuthLoading(loading) {
    const btnText = document.getElementById('auth-btn-text');
    const spinner = document.getElementById('auth-loading');
    const submitBtn = document.getElementById('auth-submit-btn');

    if (loading) {
        if (btnText) btnText.textContent = 'Please wait...';
        if (spinner) spinner.classList.remove('hidden');
        if (submitBtn) submitBtn.disabled = true;
    } else {
        if (btnText) btnText.textContent = 'Continue';
        if (spinner) spinner.classList.add('hidden');
        if (submitBtn) submitBtn.disabled = false;
    }
}

/**
 * Unified auth submit - handles both login and auto-registration
 */
async function submitAuth() {
    const email = document.getElementById('auth-email')?.value?.trim();
    const password = document.getElementById('auth-password')?.value;

    if (!email || !password) {
        showAuthMessage('Please enter email and password', true);
        return;
    }

    if (password.length < 8) {
        showAuthMessage('Password must be at least 8 characters', true);
        return;
    }

    setAuthLoading(true);

    try {
        // First, try to login
        const loginResponse = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });

        const loginData = await loginResponse.json();

        if (loginResponse.ok) {
            // Login successful
            saveAuthData(loginData.token, loginData.user);
            showAuthMessage('Welcome back!');
            updateAuthUI();

            // Close dropdown after a short delay
            setTimeout(() => {
                toggleAuthDropdown();
                // Refresh the page to update any user-specific content
                window.location.reload();
            }, 1000);
            return;
        }

        // Check if user not found (need to register)
        // FastAPI returns detail as object: {"detail": {"message": "...", "error_code": "..."}}
        const errorCode = loginData.detail?.error_code || loginData.error_code;
        if (errorCode === 'USER_NOT_FOUND') {
            // Auto-register
            const registerResponse = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            const registerData = await registerResponse.json();

            if (registerResponse.ok) {
                // Registration successful
                saveAuthData(registerData.token, registerData.user);

                // Link existing access token
                const existingToken = localStorage.getItem(ACCESS_TOKEN_KEY);
                if (existingToken) {
                    await linkAccessToken(existingToken);
                }

                showAuthMessage('Account created! Your history is linked.');
                updateAuthUI();

                setTimeout(() => {
                    toggleAuthDropdown();
                    window.location.reload();
                }, 1500);
                return;
            } else {
                showAuthMessage(registerData.detail || 'Registration failed', true);
            }
        } else if (errorCode === 'INVALID_PASSWORD') {
            // Wrong password
            showAuthMessage('Incorrect password', true);
        } else {
            // Other login error
            const errorMsg = loginData.detail?.message || loginData.detail || 'Login failed';
            showAuthMessage(errorMsg, true);
        }
    } catch (error) {
        showAuthMessage('Network error. Please try again.', true);
    } finally {
        setAuthLoading(false);
    }
}

/**
 * Mobile auth submit
 */
async function submitMobileAuth() {
    const email = document.getElementById('mobile-auth-email')?.value?.trim();
    const password = document.getElementById('mobile-auth-password')?.value;

    if (!email || !password) {
        showMobileAuthMessage('Please enter email and password', true);
        return;
    }

    if (password.length < 8) {
        showMobileAuthMessage('Password must be at least 8 characters', true);
        return;
    }

    try {
        // First, try to login
        const loginResponse = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });

        const loginData = await loginResponse.json();

        if (loginResponse.ok) {
            saveAuthData(loginData.token, loginData.user);
            showMobileAuthMessage('Welcome back!');
            updateAuthUI();
            setTimeout(() => window.location.reload(), 1000);
            return;
        }

        const mobileErrorCode = loginData.detail?.error_code || loginData.error_code;
        if (mobileErrorCode === 'USER_NOT_FOUND') {
            const registerResponse = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            const registerData = await registerResponse.json();

            if (registerResponse.ok) {
                saveAuthData(registerData.token, registerData.user);
                const existingToken = localStorage.getItem(ACCESS_TOKEN_KEY);
                if (existingToken) {
                    await linkAccessToken(existingToken);
                }
                showMobileAuthMessage('Account created!');
                updateAuthUI();
                setTimeout(() => window.location.reload(), 1500);
                return;
            } else {
                showMobileAuthMessage(registerData.detail || 'Registration failed', true);
            }
        } else if (mobileErrorCode === 'INVALID_PASSWORD') {
            showMobileAuthMessage('Incorrect password', true);
        } else {
            const mobileErrorMsg = loginData.detail?.message || loginData.detail || 'Login failed';
            showMobileAuthMessage(mobileErrorMsg, true);
        }
    } catch (error) {
        showMobileAuthMessage('Network error. Please try again.', true);
    }
}

/**
 * Logout user
 */
function logoutUser() {
    clearAuthData();
    updateAuthUI();
    window.location.href = '/';
}

/**
 * Link an access token to the user account
 */
async function linkAccessToken(accessToken) {
    const authToken = getAuthToken();
    if (!authToken) {
        return { success: false, message: 'Not logged in' };
    }

    try {
        const response = await fetch(`/api/auth/link-token?token=${encodeURIComponent(authToken)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ access_token: accessToken }),
        });

        const data = await response.json();

        if (!response.ok) {
            return { success: false, message: data.detail || 'Failed to link token' };
        }

        // Update stored user data
        if (data.user) {
            localStorage.setItem(USER_DATA_KEY, JSON.stringify(data.user));
        }

        return { success: true, message: data.message };
    } catch (error) {
        return { success: false, message: error.message || 'Network error' };
    }
}

/**
 * Get current user info from server
 */
async function getCurrentUser() {
    const token = getAuthToken();
    if (!token) {
        return null;
    }

    try {
        const response = await fetch(`/api/auth/me?token=${encodeURIComponent(token)}`);

        if (!response.ok) {
            // Token invalid or expired
            clearAuthData();
            return null;
        }

        const user = await response.json();
        localStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
        return user;
    } catch (error) {
        return null;
    }
}

/**
 * Update the auth UI in the navbar
 */
function updateAuthUI() {
    const user = getUserData();

    // Desktop elements
    const loggedOut = document.getElementById('auth-logged-out');
    const loggedIn = document.getElementById('auth-logged-in');
    const emailDisplay = document.getElementById('user-email-display');

    // Mobile elements
    const mobileLoggedOut = document.getElementById('mobile-auth-logged-out');
    const mobileLoggedIn = document.getElementById('mobile-auth-logged-in');
    const mobileEmail = document.getElementById('mobile-user-email');

    if (user) {
        // Logged in state
        if (loggedOut) loggedOut.classList.add('hidden');
        if (loggedIn) loggedIn.classList.remove('hidden');
        if (emailDisplay) emailDisplay.textContent = user.email;

        if (mobileLoggedOut) mobileLoggedOut.classList.add('hidden');
        if (mobileLoggedIn) mobileLoggedIn.classList.remove('hidden');
        if (mobileEmail) mobileEmail.textContent = user.email;
    } else {
        // Logged out state
        if (loggedOut) loggedOut.classList.remove('hidden');
        if (loggedIn) loggedIn.classList.add('hidden');

        if (mobileLoggedOut) mobileLoggedOut.classList.remove('hidden');
        if (mobileLoggedIn) mobileLoggedIn.classList.add('hidden');
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    const authDropdown = document.getElementById('auth-dropdown');
    const authContainer = document.getElementById('auth-logged-out');
    const userDropdown = document.getElementById('user-dropdown');
    const userContainer = document.getElementById('auth-logged-in');

    // Close auth dropdown if clicked outside
    if (authDropdown && authContainer && !authContainer.contains(event.target)) {
        authDropdown.classList.add('hidden');
    }

    // Close user dropdown if clicked outside
    if (userDropdown && userContainer && !userContainer.contains(event.target)) {
        userDropdown.classList.add('hidden');
    }
});

// Handle Enter key in auth form
document.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        const authDropdown = document.getElementById('auth-dropdown');
        if (authDropdown && !authDropdown.classList.contains('hidden')) {
            const activeElement = document.activeElement;
            if (activeElement && (activeElement.id === 'auth-email' || activeElement.id === 'auth-password')) {
                event.preventDefault();
                submitAuth();
            }
        }

        const mobileForm = document.getElementById('mobile-auth-form');
        if (mobileForm && !mobileForm.classList.contains('hidden')) {
            const activeElement = document.activeElement;
            if (activeElement && (activeElement.id === 'mobile-auth-email' || activeElement.id === 'mobile-auth-password')) {
                event.preventDefault();
                submitMobileAuth();
            }
        }
    }
});

// Initialize auth UI on page load
document.addEventListener('DOMContentLoaded', function() {
    updateAuthUI();
});
